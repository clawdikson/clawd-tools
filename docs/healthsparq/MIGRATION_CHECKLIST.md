# HealthSparq Migration Checklist

## Per-Project Migration Tasks

Use this checklist for migrating each legacy `audiobee_*` healthsparq project to the singleton.

---

## Project Template

### [ ] Project: ********\_\_\_\_********

**Legacy Path**: `audiobee_<slug>/`
**Config Created**: [ ]
**Validated**: [ ]
**Output Verified**: [ ]

#### Pre-Migration Analysis

- [ ] Identify base domain from `config.py` or `healthspark.py`
- [ ] Extract all PLANS from `config.py`
- [ ] Extract REQ_STATES from `config.py`
- [ ] Note any custom filters (provider_types, specialties, etc.)
- [ ] Check for custom concurrency settings
- [ ] Identify API version (v3, v4)
- [ ] Note any project-specific edge cases

#### Configuration Creation

```bash
# Initialize config
healthsparq init <slug> --domain <domain>.healthsparq.com --states <states>
```

- [ ] Create YAML config in `healthsparq/configs/<slug>.yaml`
- [ ] Set `project.name` and `project.slug`
- [ ] Set `site.domain`, `site.brand_code`, `site.insurer_code`
- [ ] Add all plans with `product_code` and `name`
- [ ] Set `coverage.states`
- [ ] Configure any custom filters
- [ ] Set concurrency overrides if needed

#### Validation

```bash
# Validate config
healthsparq validate <slug>

# Dry run
healthsparq run <slug> --curr 20251214 --dry-run
```

- [ ] Config passes Pydantic validation
- [ ] Dry run shows correct settings
- [ ] All plans listed correctly
- [ ] All states listed correctly

#### Output Verification

```bash
# Run both implementations
python audiobee_ < slug > /run_all.py    # Legacy
healthsparq run 20251214 < slug > --curr # Singleton

# Compare outputs
diff -r audiobee_ healthsparq/output/ < slug > /20251214/processed < slug > /20251214/processed
healthsparq compare 20251214 --prev legacy < slug > --curr
```

- [ ] Provider count matches within 0.1%
- [ ] NPI list matches
- [ ] Field values match
- [ ] No missing plans
- [ ] No missing states

#### Cleanup

- [ ] Add note to legacy `audiobee_<slug>/CLAUDE.md`: "DEPRECATED - Use `healthsparq run <slug>`"
- [ ] Update project docs if any

---

## Migration Priority

### Priority 1: Reference Implementations

These projects have the most up-to-date code and should be migrated first:

| #   | Project              | Domain                             | States      | Complexity | Status |
| --- | -------------------- | ---------------------------------- | ----------- | ---------- | ------ |
| 1   | christus_health_plan | christushealthplan.healthsparq.com | LA, NM, TX  | Low        | [ ]    |
| 2   | bluecard_national    | provider.bcbs.com                  | All 50 + DC | High       | [ ]    |

### Priority 2: High-Volume Projects

| #   | Project    | Domain                        | States | Complexity | Status |
| --- | ---------- | ----------------------------- | ------ | ---------- | ------ |
| 3   | excellus   | excellusbcbs.healthsparq.com  | NY     | Low        | [ ]    |
| 4   | ibx        | ibx.healthsparq.com           | PA     | Low        | [ ]    |
| 5   | mvp_health | mvphealthcare.healthsparq.com | NY, VT | Low        | [ ]    |

### Priority 3: Standard Projects

| #   | Project             | Domain                            | States         | Complexity | Status |
| --- | ------------------- | --------------------------------- | -------------- | ---------- | ------ |
| 6   | medica              | medica.healthsparq.com            | MN, WI, ND, SD | Low        | [ ]    |
| 7   | selecthealth        | selecthealth.healthsparq.com      | UT, ID         | Low        | [ ]    |
| 8   | bcbs_tn             | bcbst.healthsparq.com             | TN             | Low        | [ ]    |
| 9   | aetna_better_health | aetnabetterhealth.healthsparq.com | Multiple       | Medium     | [ ]    |
| 10  | emblem_health       | emblemhealth.healthsparq.com      | NY, NJ         | Low        | [ ]    |
| ... | ...                 | ...                               | ...            | ...        | [ ]    |

### Priority 4: Complex/Edge Cases

Projects with custom logic that may need special handling:

| #   | Project | Notes                    | Status |
| --- | ------- | ------------------------ | ------ |
| -   | TBD     | Custom filter logic      | [ ]    |
| -   | TBD     | Non-standard API version | [ ]    |

---

## Common Issues & Solutions

### Issue: Different API Version

**Symptom**: API calls fail with 404 or unexpected response format

**Solution**: Set `site.api_version` in config:

```yaml
site:
    api_version: v3 # or v4
```

### Issue: Custom Provider Types

**Symptom**: Missing providers in output

**Solution**: Override filters in config:

```yaml
filters:
    provider_types:
        - Facility
        - Group
        - Pharmacy
        - Dental
        - Physician
        - BehavioralHealth # Custom type
        - Other
```

### Issue: Rate Limiting

**Symptom**: 429 errors or incomplete results

**Solution**: Reduce concurrency:

```yaml
concurrency:
    max_workers: 25
    request_delay_ms: 500
```

### Issue: Authentication Differences

**Symptom**: Login fails or session expires

**Solution**: Check `brand_code` and `insurer_code` match exactly with legacy config

### Issue: County-Specific Searches

**Symptom**: Some areas missing providers

**Solution**: Add county overrides:

```yaml
coverage:
    states: [NY]
    counties:
        NY: [Kings, Queens, New York, Bronx, Richmond]
```

---

## Verification Script

```python
#!/usr/bin/env python3
"""Compare legacy and singleton outputs."""
import json
from pathlib import Path

def compare_outputs(legacy_dir: Path, singleton_dir: Path) -> dict:
    """Compare JSONL outputs between legacy and singleton."""

    def load_npis(path: Path) -> set[str]:
        npis = set()
        for f in path.glob("*.jsonl"):
            with open(f) as fp:
                for line in fp:
                    data = json.loads(line)
                    if "npi" in data:
                        npis.add(data["npi"])
        return npis

    legacy_npis = load_npis(legacy_dir)
    singleton_npis = load_npis(singleton_dir)

    return {
        "legacy_count": len(legacy_npis),
        "singleton_count": len(singleton_npis),
        "only_in_legacy": len(legacy_npis - singleton_npis),
        "only_in_singleton": len(singleton_npis - legacy_npis),
        "match_rate": len(legacy_npis & singleton_npis) / max(len(legacy_npis), 1),
    }

if __name__ == "__main__":
    import sys
    project = sys.argv[1]
    date = sys.argv[2]

    legacy = Path(f"audiobee_{project}/{date}/processed")
    singleton = Path(f"healthsparq/output/{project}/{date}/processed")

    result = compare_outputs(legacy, singleton)
    print(f"Legacy:    {result['legacy_count']:,}")
    print(f"Singleton: {result['singleton_count']:,}")
    print(f"Match:     {result['match_rate']:.1%}")

    if result["only_in_legacy"] > 0:
        print(f"WARNING: {result['only_in_legacy']} NPIs only in legacy")
    if result["only_in_singleton"] > 0:
        print(f"INFO: {result['only_in_singleton']} NPIs only in singleton")
```

---

## Post-Migration Cleanup

After all projects are migrated and verified:

1. **Archive Legacy Code**

    ```bash
    mkdir -p archive/healthsparq_legacy
    mv audiobee_christus_health_plan archive/healthsparq_legacy/
    mv audiobee_excellus archive/healthsparq_legacy/
    # ... etc
    ```

2. **Update Documentation**
    - [ ] Update main CLAUDE.md to reference singleton
    - [ ] Update docs/site-type-mapping.md
    - [ ] Update docs/README.md

3. **Update Parallel Runner**
    - [ ] Modify `tools/run_parallel.py` to use singleton CLI
    - [ ] Update `projects/healthsparq.txt` project list

4. **Clean Up**
    - [ ] Remove duplicate code from archive after 30 days
    - [ ] Close any related GitHub issues

---

## Timeline Tracking

| Week | Phase       | Projects | Target                   |
| ---- | ----------- | -------- | ------------------------ |
| 1-2  | Foundation  | -        | Package structure, CLI   |
| 3-4  | Core        | 1-5      | Reference + high-volume  |
| 5-6  | Expansion   | 6-15     | Standard projects        |
| 7-8  | Completion  | 16-28    | Remaining + edge cases   |
| 9+   | Enhancement | -        | Optimization, monitoring |

---

## Sign-Off

| Role      | Name | Date | Signature |
| --------- | ---- | ---- | --------- |
| Developer |      |      |           |
| Reviewer  |      |      |           |
| QA        |      |      |           |
