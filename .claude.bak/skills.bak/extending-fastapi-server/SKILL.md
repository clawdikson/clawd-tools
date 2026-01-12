---
name: extending-fastapi-server
description: Extend the FastAPI server in the Beena native app. Covers adding endpoints, middleware, dependency injection, background tasks, error handling, and lifecycle management. Use when adding new API features or modifying server configuration.
---

# Extending FastAPI Server

Extend and configure the FastAPI server in the Beena Native App for browser automation. Focuses on the project's service class pattern, modular routing, dependency injection, and thread-safe communication.

## When to Use This Skill

- Adding new API endpoints for automation features
- Creating background tasks or scheduled jobs
- Implementing custom middleware for logging, authentication, or monitoring
- Adding dependency injection for shared services
- Configuring CORS, error handlers, or startup/shutdown hooks
- Integrating with JobStatusManager for worker communication
- Adding health checks or monitoring endpoints

## Architecture Overview

### Service Class Pattern

The project uses a service class to configure the FastAPI application:

```
server.py                          # Entry point, starts uvicorn
└── FastApiService                 # Configures the entire FastAPI app
    ├── _configure_app()           # Create FastAPI instance
    ├── _add_middleware()          # Add CORS, monitoring, logging
    ├── _add_exception_handlers()  # Custom error handlers
    ├── _include_routers()         # Include domain routers
    └── lifespan()                 # Startup/shutdown hooks
```

### Modular Router Structure

```
api/
├── router.py                      # Main API router
└── endpoints/
    ├── automation.py              # /automation/* endpoints
    ├── health.py                  # /health endpoints
    ├── chrome.py                  # /chrome/* endpoints
    ├── shared_variables.py        # /shared/* endpoints
    └── status.py                  # /status endpoint
```

## Basic Server Configuration

### FastApiService Class

Located at `services/fastapi_service.py`:

```python
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from beenanativeapp.api.router import api_router
from beenanativeapp.config.config_manager import config
from beenanativeapp.utils.job_status import JobStatusManager
from beenanativeapp.utils.logging import logger

class FastApiService:
    """Service class that configures and manages the FastAPI application."""

    def __init__(self, job_status_manager: Optional[JobStatusManager] = None):
        """Initialize FastAPI application with middleware and exception handlers.

        Args:
            job_status_manager: The job status manager to use for the application.
        """
        logger.info("[FastAPI Service] --- FastApiService.__init__ START ---")

        # Store the job status manager
        self.job_status_manager = job_status_manager

        self._configure_app()

        # Set the job status manager in app state
        if self.job_status_manager:
            self.app.state.job_status_manager = self.job_status_manager
            logger.info("[FastAPI Service] JobStatusManager set in app state.")

        self.app.state.shutdown_event = asyncio.Event()
        self._add_middleware()
        self._add_exception_handlers()
        self._include_routers()

        logger.info("[FastAPI Service] --- FastAPIService.__init__ END ---")

    def _configure_app(self):
        """Configure the main FastAPI application."""
        self.app = FastAPI(
            title=config.get("APP_NAME", "Beena Automation Interface"),
            description="API for automating browser tasks using Playwright",
            version=config.get("APP_VERSION", "0.1.0"),
            lifespan=self.lifespan,
        )

    def get_app(self):
        """Get the configured FastAPI application."""
        return self.app
```

**Key patterns:**

- Service class encapsulates all FastAPI configuration
- JobStatusManager injected via constructor and stored in `app.state`
- Lifespan method handles startup/shutdown
- Methods are private (`_`) for internal configuration

## Adding New Endpoints

### Step 1: Create Endpoint Module

Create a new file in `api/endpoints/`:

```python
# api/endpoints/workflows.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from beenanativeapp.utils.job_status import JobStatusManager
from beenanativeapp.utils.logging import logger
from .dependencies import get_job_status_manager

router = APIRouter()

# Request/Response Models
class WorkflowCreateRequest(BaseModel):
    name: str
    actions: list[dict]
    description: str = ""

class WorkflowResponse(BaseModel):
    id: str
    name: str
    status: str

@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    job_manager: JobStatusManager = Depends(get_job_status_manager)
):
    """Create a new workflow and queue it for execution."""
    try:
        # Generate workflow ID
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"

        # Queue the workflow
        job_id = job_manager.add_job({
            "workflow_id": workflow_id,
            "actions": request.actions,
            "metadata": {
                "name": request.name,
                "description": request.description
            }
        })

        logger.info(f"Workflow {workflow_id} queued as job {job_id}")

        return WorkflowResponse(
            id=workflow_id,
            name=request.name,
            status="queued"
        )
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    job_manager: JobStatusManager = Depends(get_job_status_manager)
):
    """Get workflow status by ID."""
    # Implementation
    pass
```

### Step 2: Add Dependency Injection

Create `api/endpoints/dependencies.py` if it doesn't exist:

```python
# api/endpoints/dependencies.py
from fastapi import Request

from beenanativeapp.utils.job_status import JobStatusManager

def get_job_status_manager(request: Request) -> JobStatusManager:
    """Get the JobStatusManager from app state."""
    return request.app.state.job_status_manager
```

### Step 3: Register Router

Update `api/router.py`:

```python
from fastapi import APIRouter

# Create main router
api_router = APIRouter()

# Import and include routers
from .endpoints import automation, chrome, health, shared_variables, status, workflows

# Include routers
api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(chrome.router, prefix="/chrome", tags=["chrome"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(shared_variables.router, prefix="/shared", tags=["shared-variables"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
```

## Dependency Injection Pattern

### Using App State

```python
from fastapi import Depends, Request

# Store dependencies in app.state during startup
app.state.job_status_manager = job_manager
app.state.config = config
app.state.db_connection = db_conn

# Dependency functions
def get_job_status_manager(request: Request) -> JobStatusManager:
    """Get JobStatusManager from app state."""
    return request.app.state.job_status_manager

def get_config(request: Request) -> dict:
    """Get configuration from app state."""
    return request.app.state.config

# Use in endpoints
@router.post("/automation/run")
async def run_automation(
    request: AutomationRequest,
    job_manager: JobStatusManager = Depends(get_job_status_manager),
    config: dict = Depends(get_config)
):
    # Use injected dependencies
    job_id = job_manager.add_job(request.dict())
    timeout = config.get("PLAYWRIGHT_TIMEOUT", 60)
    return {"job_id": job_id, "timeout": timeout}
```

### Using Pydantic Settings

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    api_port: int = 8000
    api_host: str = "127.0.0.1"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Use in endpoints
@router.get("/config")
async def get_config(settings: Settings = Depends(get_settings)):
    return {
        "api_port": settings.api_port,
        "log_level": settings.log_level
    }
```

## Middleware

### Adding Custom Middleware

In `FastApiService._add_middleware()`:

```python
def _add_middleware(self):
    """Add CORS and monitoring middleware."""
    # CORS middleware
    self.app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Performance monitoring
    if config.get("ENABLE_PERFORMANCE_MONITORING", True):
        self.app.add_middleware(PerformanceMonitoringMiddleware)

    # Request logging
    if config.get("ENABLE_REQUEST_LOGGING", False):
        self.app.add_middleware(RequestLoggingMiddleware)
```

### Custom Middleware Example

```python
# utils/middleware.py
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor request performance."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        logger.info(
            f"{request.method} {request.url.path} completed in {process_time:.3f}s"
        )

        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests."""

    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        logger.debug(f"Headers: {request.headers}")

        response = await call_next(request)

        logger.info(f"Response: {response.status_code}")
        return response
```

## Exception Handling

### Global Exception Handlers

In `FastApiService._add_exception_handlers()`:

```python
def _add_exception_handlers(self):
    """Configure exception handlers for different error scenarios."""

    @self.app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exc: Exception):
        """Handle 404 Not Found exceptions."""
        error = NotFoundError(detail={"path": request.url.path})
        error.log()
        return JSONResponse(
            status_code=404,
            content=error.to_response().model_dump(),
        )

    @self.app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors."""
        error = ValidationError(
            message="Request validation failed",
            detail={"errors": exc.errors()}
        )
        error.log()
        return JSONResponse(
            status_code=422,
            content=error.to_response().model_dump(),
        )

    @self.app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all uncaught exceptions."""
        error_response = handle_exception(exc)
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(),
        )
```

### Custom Error Classes

```python
# utils/errors.py
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = False
    error: str
    detail: dict | None = None
    timestamp: str

class AppError(Exception):
    """Base application error."""
    def __init__(self, message: str, status_code: int = 500, detail: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)

    def to_response(self) -> ErrorResponse:
        """Convert error to response model."""
        return ErrorResponse(
            error=self.message,
            detail=self.detail,
            timestamp=datetime.utcnow().isoformat()
        )

    def log(self):
        """Log the error."""
        logger.error(f"{self.__class__.__name__}: {self.message}", extra={"detail": self.detail})

class NotFoundError(AppError):
    """Resource not found error."""
    def __init__(self, message: str = "Resource not found", detail: dict | None = None):
        super().__init__(message, status_code=404, detail=detail)

class ValidationError(AppError):
    """Request validation error."""
    def __init__(self, message: str = "Validation failed", detail: dict | None = None):
        super().__init__(message, status_code=422, detail=detail)
```

## Lifecycle Management

### Lifespan Context Manager

```python
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(self, app: FastAPI):
    """Handle application startup and shutdown."""
    logger.info("[FastAPI Lifespan] --- STARTUP phase BEGIN ---")

    # Startup actions
    logger.info(f"Starting {config.get('APP_NAME')} version {config.get('APP_VERSION')}")
    logger.info(f"Environment: {config.get('ENVIRONMENT', 'development')}")

    # Initialize resources
    app.state.shutdown_event = asyncio.Event()
    app.state.shutdown_event.clear()

    # Start background tasks if needed
    # app.state.background_task = asyncio.create_task(periodic_cleanup())

    logger.info("[FastAPI Lifespan] --- STARTUP complete, yielding ---")
    yield
    logger.info("[FastAPI Lifespan] --- SHUTDOWN phase BEGIN ---")

    # Shutdown actions
    logger.info(f"Shutting down {config.get('APP_NAME')}")
    app.state.shutdown_event.set()

    # Signal shutdown to JobStatusManager
    if hasattr(app.state, "job_status_manager") and app.state.job_status_manager:
        app.state.job_status_manager.shutdown()
        logger.info("[FastAPI Lifespan] JobStatusManager shutdown signaled.")

    # Cancel background tasks
    # if hasattr(app.state, "background_task"):
    #     app.state.background_task.cancel()

    logger.info("[FastAPI Lifespan] --- SHUTDOWN complete ---")
```

## Background Tasks

### Using asyncio.create_task

```python
import asyncio

async def periodic_cleanup():
    """Periodic cleanup task."""
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            logger.info("Running periodic cleanup...")
            # Cleanup logic
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

# In lifespan startup
app.state.cleanup_task = asyncio.create_task(periodic_cleanup())

# In lifespan shutdown
if hasattr(app.state, "cleanup_task"):
    app.state.cleanup_task.cancel()
    await app.state.cleanup_task
```

### Using BackgroundTasks

```python
from fastapi import BackgroundTasks

def send_notification(email: str, message: str):
    """Send email notification (synchronous)."""
    logger.info(f"Sending notification to {email}")
    # Email sending logic

@router.post("/automation/run")
async def run_automation(
    request: AutomationRequest,
    background_tasks: BackgroundTasks
):
    job_id = job_manager.add_job(request.dict())

    # Add background task
    background_tasks.add_task(
        send_notification,
        email="user@example.com",
        message=f"Job {job_id} started"
    )

    return {"job_id": job_id}
```

## Server Entry Point

### server.py

```python
import asyncio
import platform
import uvicorn

from beenanativeapp.config.config_manager import config
from beenanativeapp.services.fastapi_service import FastApiService
from beenanativeapp.utils.job_status import JobStatusManager
from beenanativeapp.utils.logging import logger

def start_server(job_status_manager: JobStatusManager):
    """
    Start the FastAPI server with the provided JobStatusManager.

    Args:
        job_status_manager: The shared JobStatusManager instance for job coordination
    """
    fastapi_service = FastApiService(job_status_manager)
    app = fastapi_service.get_app()

    api_port = config.get("API_PORT", 8000)
    api_host = config.get("API_HOST", "127.0.0.1")
    logger.info(f"Starting server on {api_host}:{api_port}")

    # Configure event loop policy for Windows
    if platform.system() == "Windows":
        logger.info(
            "Windows system detected, setting event loop policy to WindowsSelectorEventLoopPolicy"
        )
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(app, host=api_host, port=api_port, loop="asyncio")
```

**Important for Windows:**

- Must set `WindowsSelectorEventLoopPolicy` for async operations to work correctly
- Without this, async operations will fail with cryptic errors on Windows

## Best Practices

1. **Use service class pattern** for FastAPI configuration
2. **Inject dependencies via app.state** - thread-safe, global access
3. **Use Pydantic models** for request/response validation
4. **Add comprehensive error handlers** for better debugging
5. **Log at INFO level** for important events, DEBUG for details
6. **Use routers** to organize endpoints by domain
7. **Implement lifespan hooks** for resource management
8. **Add middleware sparingly** - only what's needed
9. **Use BackgroundTasks** for fire-and-forget operations
10. **Configure CORS properly** - restrict origins in production

## Common Pitfalls

❌ **Direct FastAPI instantiation**

```python
# BAD: Bypasses service class configuration
app = FastAPI()
```

✅ **Use service class**

```python
# GOOD: Centralized configuration
service = FastApiService(job_manager)
app = service.get_app()
```

❌ **Storing state in global variables**

```python
# BAD: Not thread-safe
job_manager = None

@router.post("/run")
async def run():
    global job_manager
    job_manager.add_job(...)
```

✅ **Use dependency injection**

```python
# GOOD: Thread-safe via app.state
@router.post("/run")
async def run(job_manager: JobStatusManager = Depends(get_job_status_manager)):
    job_manager.add_job(...)
```

❌ **Not handling Windows async**

```python
# BAD: Will fail on Windows
uvicorn.run(app)
```

✅ **Set Windows event loop policy**

```python
# GOOD: Works on all platforms
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
uvicorn.run(app, loop="asyncio")
```

## Next Steps

- See `managing-jobstatus-communication` skill for JobStatusManager patterns
- Check FastAPI docs for advanced features (WebSockets, streaming, etc.)
- Review existing endpoints in `api/endpoints/` for implementation patterns
- See `reference/async-best-practices.md` for async/await patterns
