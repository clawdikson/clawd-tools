# Custom Carrier Templates

Templates for creating new custom carrier scrapers following the Custom Carrier Architecture Pattern.

## Quick Start

```bash
# 1. Create project directory
mkdir audiobee_my_carrier && cd audiobee_my_carrier

# 2. Copy templates
cp ../docs/templates/custom/*.template .

# 3. Rename files
mv config.yaml.template config.yaml
mv run.py.template run.py
mv collector.py.template collector.py
mv pipeline.py.template pipeline.py
mv pyproject.toml.template pyproject.toml

# 4. Replace placeholders
sed -i 's/{{PROJECT_NAME}}/My Carrier/g' *.py *.yaml pyproject.toml
sed -i 's/{{PROJECT_SLUG}}/my_carrier/g' *.py *.yaml pyproject.toml
sed -i 's/{{CLASS_NAME}}/MyCarrier/g' collector.py
sed -i 's/{{BASE_URL}}/https:\/\/api.mycarrier.com/g' config.yaml
sed -i 's/{{STATES}}/TX, CA, NY/g' config.yaml

# 5. Create .env with secrets
cat > .env << 'EOF'
# Carrier-specific secrets
# CLIENT_ID=xxx
# CLIENT_SECRET=xxx

# Optional: Capsolver for CAPTCHA
# CAPSOLVER_API_KEY=CAP-xxx
EOF

# 6. Validate config
python run.py validate

# 7. Dry run
python run.py run --curr $(date +%Y%m%d) --dry-run

# 8. Run collection
python run.py run --curr $(date +%Y%m%d)
```

## Template Files

| File | Purpose |
|------|---------|
| `config.yaml.template` | Project configuration with all settings |
| `run.py.template` | Typer CLI entry point |
| `collector.py.template` | Phase 1 data collection with checkpointing |
| `pipeline.py.template` | Phase orchestration and metrics |
| `pyproject.toml.template` | Project dependencies |

## Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{PROJECT_NAME}}` | Human-readable name | "Harvard Pilgrim" |
| `{{PROJECT_SLUG}}` | Lowercase slug | "harvard_pilgrim" |
| `{{CLASS_NAME}}` | PascalCase class name | "HarvardPilgrim" |
| `{{BASE_URL}}` | API base URL | "https://api.example.com" |
| `{{STATES}}` | Coverage states | "MA, ME, NH" |

## Customization

### Collector (collector.py)

The collector template provides the skeleton. You need to implement:

1. **`collect()`**: Main collection logic with progress bars
2. **`_fetch_state()`**: State-level data fetching with pagination
3. **`get_record_id()`**: Unique ID extraction for checkpointing

### Pipeline (pipeline.py)

The pipeline handles:
- Phase selection and orchestration
- Metrics tracking
- Integration with core.mapper and core.qa

### Custom Mapper (optional)

If `phases.custom_mapper: true` in config.yaml, create `mapper.py`:

```python
def custom_mapper(raw: dict) -> dict:
    """Custom normalization for this carrier."""
    from core.mapper import default_mapper

    result = default_mapper(raw)

    # Add carrier-specific mappings
    if "custom_field" in raw:
        result["mapped_field"] = raw["custom_field"]

    return result
```

## Documentation

- Full spec: `docs/CUSTOM_ARCHITECTURE.md`
- Progress bars: `core/progress/CLAUDE.md`
- CAPTCHA solving: `core/antibot/CLAUDE.md`
- Storage: `core/io/CLAUDE.md`
