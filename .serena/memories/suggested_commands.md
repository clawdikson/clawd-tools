# Suggested Commands

## Running Individual Scrapers

```bash
# Navigate to project
cd audiobee_bcbs_il

# Run individual phases
python index_1.py    # Phase 1: Discovery
python index_2.py    # Phase 2: Details
python index_3.py    # Phase 3: Normalization

# Or use orchestrator
python run_all.py
```

## Healthsparq Projects (Require Browser Server)

```bash
# Terminal 1: Start browser server
cd healthsparq-server && npm start  # Runs on port 1018

# Terminal 2: Run scraper
cd audiobee_mvp_health
python run_all.py
```

## Output Validation

```bash
# Validate output schema
python output_generator/type_check.py audiobee_bcbs_il/

# Generate sample data
python output_generator/sample_generator.py audiobee_bcbs_il/

# Compare runs
python output_generator/comparison_creator.py audiobee_bcbs_il/ --prev 20251010 --curr 20251110

# Create Excel report
python output_generator/report_generator.py audiobee_bcbs_il/
```

## Package Management (uv)

```bash
# Install dependencies for a project
cd audiobee_bcbs_il
uv sync

# Add a dependency
uv add httpx

# Create virtual environment
uv venv
source .venv/bin/activate  # macOS/Linux
```

## Config Date Updates

Before running scrapers, update dates in config.py:
```python
PREV_DATE = "20251010"  # Previous run date
CURR_DATE = "20251210"  # Current run date
```

## Git (No repo at root, individual projects may have .git)

```bash
# For projects with their own git
cd audiobee_bcbs_il
git status
git diff
```

## System Commands (Darwin/macOS)

```bash
# List projects
ls -la audiobee_*

# Find files
find . -name "config.py" -path "*/audiobee_*"

# Search in files
grep -r "network_id" audiobee_bcbs_il/

# Check processes
ps aux | grep python

# Kill process
kill -9 <PID>
```

## Parallel Execution (When Available)

```bash
# Run API scrapers in parallel
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210 --prev 20251110

# Run by pattern
python tools/run_parallel.py --pattern "audiobee_bcbs*" --workers 8
```
