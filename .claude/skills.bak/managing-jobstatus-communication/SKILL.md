---
name: managing-jobstatus-communication
description: Manage thread-safe IPC between FastAPI server and Playwright worker using JobStatusManager. Covers job queuing, status updates, shared variables, graceful shutdown, and progress tracking. Use when implementing worker communication or debugging job flow issues.
---

# Managing JobStatus Communication

Implement thread-safe inter-process communication between the FastAPI server thread and Playwright worker thread using JobStatusManager. This skill covers the project's pattern that replaced ZeroMQ for simpler, more reliable IPC.

## When to Use This Skill

- Implementing job submission from FastAPI endpoints
- Creating worker loops that process jobs from the queue
- Updating job status and progress from worker threads
- Sharing variables across server and worker threads
- Implementing graceful shutdown for multi-threaded applications
- Debugging job flow or communication issues
- Adding progress tracking to long-running jobs

## Architecture Overview

### Thread Communication Pattern

```
┌─────────────────────┐         ┌──────────────────────┐
│  FastAPI Server     │         │  Playwright Worker   │
│  (Main Thread)      │         │  (Worker Thread)     │
└─────────────────────┘         └──────────────────────┘
          │                               │
          ├───────── create_job() ───────>│
          │                               │
          │<──── Job Queue (FIFO) ────────│
          │                               │
          │<─── update_job_status() ──────│
          │                               │
          ├──── get_job() ───────────────>│
          │                               │
          │<─── Shared Variables ─────────│
          │      (Thread-Safe Dict)       │
          │                               │
          └───────── shutdown() ──────────┘
```

### Key Components

1. **Job Queue** - Thread-safe FIFO queue for job submission
2. **Jobs Dictionary** - Thread-safe dict with job status/results
3. **Shared Variables** - Cross-thread state with optional TTL
4. **Shutdown Event** - Graceful termination signaling

## JobStatusManager Class

### Initialization

```python
from beenanativeapp.utils.job_status import JobStatusManager, JobState, Job

# Initialize (typically in app.py)
job_status_manager = JobStatusManager()

# Store in FastAPI app state for dependency injection
app.state.job_status_manager = job_status_manager
```

### Core Data Structures

```python
class JobStatusManager:
    def __init__(self):
        # Thread-safe queue for jobs to be processed
        self.job_queue = queue.Queue()

        # Thread-safe dictionary of all jobs
        self.jobs: Dict[str, Job] = {}
        self.jobs_lock = threading.RLock()

        # Thread-safe shared variables
        self._shared_variables: Dict[str, Any] = {}
        self._shared_variables_lock = threading.RLock()

        # Optional type validators for shared variables
        self._variable_validators: Dict[str, Callable[[Any], bool]] = {}

        # Optional TTL for variables (key -> expiration time)
        self._variable_ttl: Dict[str, datetime] = {}

        # Event for shutdown signaling
        self.shutdown_event = threading.Event()
```

**Key patterns:**

- `threading.RLock()` for reentrant locks (safe for nested acquisition)
- `queue.Queue()` for thread-safe FIFO job queue
- `threading.Event()` for shutdown coordination
- Separate locks for jobs and shared variables (fine-grained locking)

## Job Lifecycle

### 1. Create Job (Server Thread)

```python
# In FastAPI endpoint
from beenanativeapp.utils.job_status import JobStatusManager
from fastapi import Depends

def get_job_status_manager(request: Request) -> JobStatusManager:
    return request.app.state.job_status_manager

@router.post("/automation/run")
async def run_automation(
    request: AutomationRequest,
    job_manager: JobStatusManager = Depends(get_job_status_manager)
):
    # Create and queue job
    job_id = job_manager.create_job(
        actions=request.actions,
        job_id=None  # Auto-generate UUID
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": "Job queued successfully"
    }
```

**create_job() implementation:**

```python
def create_job(
    self, actions: List[Dict[str, Any]], job_id: Optional[str] = None
) -> str:
    """Create a new job and add it to the queue."""
    if job_id is None:
        job_id = str(uuid.uuid4())

    job = Job(job_id=job_id, actions=actions, status=JobState.QUEUED)

    with self.jobs_lock:
        self.jobs[job_id] = job
        job.logs.append(
            f"Job {job_id} created and queued at {job.created_at}"
        )

    # Add to queue for processing
    self.job_queue.put(job)

    logger.info(f"Created and queued job {job_id} with {len(actions)} actions")
    return job_id
```

### 2. Get Next Job (Worker Thread)

```python
# In Playwright worker thread
async def worker_loop(job_manager: JobStatusManager):
    """Main worker loop processing jobs from queue."""
    while not job_manager.shutdown_event.is_set():
        # Get next job with timeout
        job = job_manager.get_next_job(timeout=1.0)

        if job is None:
            # No job available, continue loop
            continue

        # Process the job
        try:
            result = await process_job(job)
            job_manager.update_job_status(
                job.job_id,
                JobState.SUCCESS,
                result=result
            )
        except Exception as e:
            job_manager.update_job_status(
                job.job_id,
                JobState.FAILED,
                error_message=str(e)
            )
```

**get_next_job() implementation:**

```python
def get_next_job(self, timeout: Optional[float] = None) -> Optional[Job]:
    """Get the next job from the queue."""
    try:
        job = self.job_queue.get(timeout=timeout)

        # Update status to processing
        with self.jobs_lock:
            if job.job_id in self.jobs:
                self.jobs[job.job_id].status = JobState.PROCESSING
                self.jobs[job.job_id].updated_at = datetime.now(
                    timezone.utc
                ).isoformat()
                self.jobs[job.job_id].logs.append("Job processing started")

        return job
    except queue.Empty:
        return None
```

**Pattern explanation:**

- `timeout=1.0` allows periodic check of shutdown event
- Returns `None` if queue empty (non-blocking)
- Automatically updates job status to PROCESSING

### 3. Update Job Status (Worker Thread)

```python
# During job processing
job_manager.update_job_status(
    job_id,
    JobState.PROCESSING,
    logs=["Starting migration step 1"]
)

# Update progress
job_manager.update_job_progress(
    job_id,
    progress_details={
        "total_items": 100,
        "completed_items": 25,
        "current_item": "Contact: john@example.com",
        "percentage": 25.0
    }
)

# On success
job_manager.update_job_status(
    job_id,
    JobState.SUCCESS,
    result={"migrated_count": 100, "errors": []},
    logs=["Migration completed successfully"]
)

# On failure
job_manager.update_job_status(
    job_id,
    JobState.FAILED,
    error_message="Connection timeout to Klaviyo API",
    logs=["Failed after 3 retry attempts"]
)
```

**update_job_status() implementation:**

```python
def update_job_status(
    self,
    job_id: str,
    status: JobState,
    result: Optional[Any] = None,
    error_message: Optional[str] = None,
    logs: Optional[List[str]] = None,
) -> Optional[Job]:
    """Update a job's status and related information."""
    with self.jobs_lock:
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"Cannot update job {job_id}: not found")
            return None

        job.status = status
        job.updated_at = datetime.now(timezone.utc).isoformat()

        if result is not None:
            job.result = result
        if error_message is not None:
            job.error_message = error_message
        if logs:
            job.logs.extend(logs)

        logger.info(f"Updated job {job_id} status to {status.value}")
        return job
```

### 4. Get Job Status (Server Thread)

```python
# In FastAPI endpoint
@router.get("/automation/status/{job_id}")
async def get_job_status(
    job_id: str,
    job_manager: JobStatusManager = Depends(get_job_status_manager)
):
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "success": True,
        "job": job.to_dict()
    }
```

**get_job() implementation:**

```python
def get_job(self, job_id: str) -> Optional[Job]:
    """Get a job by its ID."""
    with self.jobs_lock:
        return self.jobs.get(job_id)
```

## Job States

### JobState Enum

```python
class JobState(Enum):
    """Enumeration of possible job states."""
    PENDING = "pending"        # Job created but not queued
    QUEUED = "queued"          # Job in queue, waiting
    PROCESSING = "processing"  # Job being processed by worker
    SUCCESS = "success"        # Job completed successfully
    FAILED = "failed"          # Job failed with error
    ERROR = "error"            # Job encountered error
    CANCELLED = "cancelled"    # Job was cancelled
    QUEUE_FAILED = "queue_failed"  # Failed to queue job
```

### Job Dataclass

```python
@dataclass
class Job:
    """Represents a single job with its data and status."""
    job_id: str
    actions: List[Dict[str, Any]]
    status: JobState = JobState.PENDING
    result: Optional[Any] = None
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    progress_details: Optional[Dict[str, Any]] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API responses."""
        return {
            "id": self.job_id,
            "actions": self.actions,
            "status": self.status.value,
            "result": self.result,
            "error": self.error_message,
            "logs": self.logs,
            "progress_details": self.progress_details,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
```

## Progress Tracking

### Update Progress

```python
def update_job_progress(
    self,
    job_id: str,
    progress_details: Dict[str, Any]
) -> Optional[Job]:
    """Update job progress details."""
    with self.jobs_lock:
        job = self.jobs.get(job_id)
        if not job:
            return None

        job.progress_details = progress_details
        job.updated_at = datetime.now(timezone.utc).isoformat()

        return job
```

### Progress Structure

```python
progress_details = {
    "total_items": 100,
    "completed_items": 25,
    "current_item": "Contact: john@example.com",
    "percentage": 25.0,
    "stage": "contacts",  # Optional
    "substage": "importing"  # Optional
}
```

### Worker Usage

```python
async def migrate_contacts(job_id, contacts):
    total = len(contacts)

    for idx, contact in enumerate(contacts):
        # Process contact
        await process_contact(contact)

        # Update progress
        job_manager.update_job_progress(
            job_id,
            {
                "total_items": total,
                "completed_items": idx + 1,
                "current_item": f"Contact: {contact['email']}",
                "percentage": ((idx + 1) / total) * 100
            }
        )
```

## Shared Variables

### Set Shared Variable

```python
# From server thread
job_manager.set_shared_variable(
    "migration_source_email",
    "user@mailchimp.com",
    ttl_minutes=30  # Expires after 30 minutes
)

# With type validation
job_manager.set_shared_variable(
    "max_concurrent_jobs",
    5,
    validator=lambda x: isinstance(x, int) and x > 0
)
```

**Implementation:**

```python
def set_shared_variable(
    self,
    key: str,
    value: Any,
    ttl_minutes: Optional[int] = None,
    validator: Optional[Callable[[Any], bool]] = None
) -> bool:
    """Set a shared variable accessible across threads."""
    # Validate if validator provided
    if validator and not validator(value):
        logger.warning(f"Validation failed for shared variable {key}")
        return False

    with self._shared_variables_lock:
        self._shared_variables[key] = value

        # Set TTL if provided
        if ttl_minutes:
            expiration = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
            self._variable_ttl[key] = expiration

        # Store validator for future updates
        if validator:
            self._variable_validators[key] = validator

    logger.info(f"Set shared variable: {key}")
    return True
```

### Get Shared Variable

```python
# From worker thread
source_email = job_manager.get_shared_variable(
    "migration_source_email",
    default="unknown@example.com"
)

# Check if exists
if job_manager.has_shared_variable("migration_source_email"):
    email = job_manager.get_shared_variable("migration_source_email")
```

**Implementation:**

```python
def get_shared_variable(
    self, key: str, default: Any = None
) -> Any:
    """Get a shared variable value."""
    with self._shared_variables_lock:
        # Check TTL
        if key in self._variable_ttl:
            if datetime.now(timezone.utc) > self._variable_ttl[key]:
                # Expired, remove it
                del self._shared_variables[key]
                del self._variable_ttl[key]
                logger.info(f"Shared variable {key} expired")
                return default

        return self._shared_variables.get(key, default)
```

### Delete Shared Variable

```python
job_manager.delete_shared_variable("migration_source_email")
```

### List All Shared Variables

```python
variables = job_manager.list_shared_variables()
# Returns: {"migration_source_email": "user@mailchimp.com", ...}
```

## Graceful Shutdown

### Signal Shutdown

```python
# In FastAPI lifespan shutdown
async def shutdown():
    logger.info("Shutting down application")
    app.state.job_status_manager.shutdown()
```

**Implementation:**

```python
def shutdown(self):
    """Signal shutdown to all threads."""
    logger.info("JobStatusManager shutdown initiated")
    self.shutdown_event.set()
```

### Worker Loop with Shutdown

```python
async def worker_loop(job_manager: JobStatusManager):
    """Worker loop with graceful shutdown."""
    logger.info("Worker loop started")

    while not job_manager.shutdown_event.is_set():
        try:
            # Get next job with timeout (allows periodic shutdown check)
            job = job_manager.get_next_job(timeout=1.0)

            if job is None:
                continue

            # Process job
            await process_job(job)

        except Exception as e:
            logger.error(f"Error in worker loop: {e}")

    logger.info("Worker loop shutting down")

    # Cleanup: mark any processing jobs as failed
    with job_manager.jobs_lock:
        for job_id, job in job_manager.jobs.items():
            if job.status == JobState.PROCESSING:
                job.status = JobState.FAILED
                job.error_message = "Worker shutdown during processing"

    logger.info("Worker loop stopped")
```

**Pattern explanation:**

- Check `shutdown_event` in loop condition
- Use timeout on `get_next_job()` to periodically check shutdown
- Clean up resources on shutdown
- Mark in-progress jobs appropriately

## Thread Architecture

### App Initialization

```python
# In app.py (Toga application)
import threading

class BeenaApp(toga.App):
    def startup(self):
        # Initialize shared JobStatusManager
        self.job_status_manager = JobStatusManager()

        # Start FastAPI server thread
        self.server_thread = threading.Thread(
            target=start_server,
            args=(self.job_status_manager,),
            daemon=True
        )
        self.server_thread.start()

        # Start Playwright worker thread
        self.worker_thread = threading.Thread(
            target=start_worker,
            args=(self.job_status_manager,),
            daemon=True
        )
        self.worker_thread.start()

        # UI setup
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.show()

    def shutdown(self):
        """Graceful shutdown of threads."""
        logger.info("Shutting down Beena application")

        # Signal shutdown
        self.job_status_manager.shutdown()

        # Wait for threads with timeout
        self.server_thread.join(timeout=5)
        self.worker_thread.join(timeout=5)

        logger.info("All threads stopped")
```

## Best Practices

1. **Always use locks** when accessing shared data structures
2. **Use RLock** instead of Lock for reentrant safety
3. **Timeout on queue operations** to allow shutdown checks
4. **Update job status frequently** for real-time feedback
5. **Use JobState enum** instead of string literals
6. **Log all state transitions** for debugging
7. **Implement graceful shutdown** with event signaling
8. **Clean up resources** on worker shutdown
9. **Use TTL for shared variables** that expire
10. **Validate shared variables** with type checkers

## Common Pitfalls

❌ **Forgetting locks**

```python
# BAD: Race condition
self.jobs[job_id] = job
```

✅ **Always use locks**

```python
# GOOD: Thread-safe
with self.jobs_lock:
    self.jobs[job_id] = job
```

❌ **Blocking indefinitely on queue**

```python
# BAD: Can't shutdown cleanly
job = self.job_queue.get()  # Blocks forever
```

✅ **Use timeout**

```python
# GOOD: Allows periodic shutdown check
job = self.job_queue.get(timeout=1.0)
```

❌ **Not checking shutdown event**

```python
# BAD: Loop never exits
while True:
    job = get_next_job()
```

✅ **Check shutdown event**

```python
# GOOD: Exits on shutdown
while not shutdown_event.is_set():
    job = get_next_job(timeout=1.0)
```

## Complete Example

### Server Endpoint

```python
@router.post("/automation/run")
async def run_automation(
    request: AutomationRequest,
    job_manager: JobStatusManager = Depends(get_job_status_manager)
):
    """Queue automation job."""
    job_id = job_manager.create_job(actions=request.actions)
    return {"success": True, "job_id": job_id}

@router.get("/automation/status/{job_id}")
async def get_status(
    job_id: str,
    job_manager: JobStatusManager = Depends(get_job_status_manager)
):
    """Get job status."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"success": True, "job": job.to_dict()}
```

### Worker Loop

```python
async def worker_loop(job_manager: JobStatusManager):
    """Process jobs from queue."""
    while not job_manager.shutdown_event.is_set():
        job = job_manager.get_next_job(timeout=1.0)

        if job is None:
            continue

        try:
            result = await process_automation_job(job)
            job_manager.update_job_status(
                job.job_id,
                JobState.SUCCESS,
                result=result
            )
        except Exception as e:
            job_manager.update_job_status(
                job.job_id,
                JobState.FAILED,
                error_message=str(e)
            )

    logger.info("Worker shutting down")
```

## Next Steps

- See `extending-fastapi-server` skill for FastAPI integration patterns
- Check `building-playwright-migrations` for worker job processing
- Review threading documentation for advanced synchronization patterns
- See `reference/performance-optimization.md` for queue tuning
