## Description
<!-- Describe your changes in detail -->

## Related Issue
<!-- Link to the related issue (if any) -->
<!-- Example: Closes #123 or Fixes bd issue scraping-abc -->

## Type of Change
<!-- Mark the relevant option(s) -->
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Test addition or update

## Component(s) Affected
- [ ] Individual scraper (`audiobee_*`)
- [ ] HealthSparq library (`healthsparq/`)
- [ ] Core utilities (`core/`)
- [ ] Tools (`tools/`)
- [ ] Documentation (`docs/`)
- [ ] Configuration

## Testing Done
<!-- Describe the tests you ran -->
- [ ] Ran affected scraper(s) successfully
- [ ] Unit tests pass (`pytest`)
- [ ] Linting passes (`ruff check .`)
- [ ] Type checking passes (`mypy`)
- [ ] Manual testing performed

## Test Commands Run
```bash
# List the commands you used to test
pytest healthsparq/tests/ -v
ruff check .
```

## Output Verification
<!-- For scraper changes, verify output quality -->
- [ ] Output schema validation passes (`python -m core.qa validate`)
- [ ] Provider counts are reasonable
- [ ] No duplicate NPIs (or expected duplicates explained)
- [ ] N/A (not a scraper change)

## Checklist
- [ ] My code follows the project's code style (see CODE_STYLE.md)
- [ ] I have updated the documentation (if applicable)
- [ ] I have added tests (if applicable)
- [ ] All new and existing tests pass
- [ ] I have updated CLAUDE.md (if adding new features/patterns)
- [ ] I have synced beads issues (`bd sync`)

## Screenshots / Output
<!-- If applicable, add screenshots or sample output -->

## Additional Notes
<!-- Any other information reviewers should know -->
