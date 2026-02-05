# Task Completion Checklist

## After Completing a Scraper Run

1. **Verify Output Files Exist**
   ```bash
   ls -la {CURR_DATE}/processed/
   ```

2. **Run Type Check**
   ```python
   python output_generator/type_check.py {project_name}/
   ```

3. **Generate Samples**
   ```python
   python output_generator/sample_generator.py {project_name}/
   ```

4. **Run Comparison (if previous run exists)**
   ```python
   python output_generator/comparison_creator.py {project_name}/
   ```

5. **Check for Empty/Corrupt Files**
   - Verify JSONL files are not empty
   - Spot-check JSON structure

## After Modifying Code

1. **Test Individual Phase**
   ```bash
   python index_1.py  # Test the modified phase
   ```

2. **Verify Config**
   - Check CURR_DATE/PREV_DATE are correct
   - Check network_id matches target plan

3. **Check Output Schema**
   - Verify NPI field is populated
   - Check required fields match schema

4. **No Linting Required** (project doesn't enforce)

## After Creating New Scraper

1. **Create Directory Structure**
   ```
   audiobee_new_carrier/
   ├── config.py
   ├── index_1.py
   ├── index_2.py (optional)
   ├── index_3.py
   ├── run_all.py
   └── pyproject.toml
   ```

2. **Add pyproject.toml with Dependencies**

3. **Follow Existing Patterns**
   - Use same config.py structure
   - Use orjson for JSON handling
   - Date-versioned output directories

4. **Test Full Pipeline**
   ```bash
   python run_all.py
   ```

5. **Validate Output**
   ```bash
   python output_generator/type_check.py audiobee_new_carrier/
   ```

## Quality Gates

- [ ] Output file exists and is non-empty
- [ ] JSONL format is valid (one JSON object per line)
- [ ] NPI field populated for all records
- [ ] No duplicate NPIs in output (unless different networks)
- [ ] State matches expected states in config
- [ ] type_check.py passes without errors
