---
date: 2026-01-11
type: migration-plan
scope: audiobee-projects
status: planning
---

# audiobee_* Migration Plan Index

Master plan for migrating 87 audiobee_* projects to use core/ packages.

## Executive Summary

| Category | Count | Status |
|----------|-------|--------|
| **Already Migrated** | 4 | ✅ Complete |
| **HealthSparq Platform** | 23 | 🟢 Ready (configs exist) |
| **Sapphire Platform** | 11 | 🟡 Ready (need configs) |
| **Anthem Platform** | 5 | 🔴 BLOCKED (no library) |
| **UHC Platform** | 3 | 🔴 BLOCKED (no library) |
| **Other/Custom** | 42 | 🟡 Needs analysis |
| **Total** | 88 | |

**Pre-Mortem Status**: 9 risks identified and mitigated (see Risk Mitigations section)

## Migration Priority

### Phase 1: Quick Wins (HealthSparq + Sapphire)
Projects that can use existing platform libraries with minimal changes.

### Phase 2: Platform Extensions (Anthem + UHC)
Projects requiring new platform library creation.

### Phase 3: Custom Migrations
Projects with unique implementations needing individual analysis.

---

## Risk Mitigations (Pre-Mortem)

### Rollback Strategy (Git Branches)

Each migration uses a dedicated branch for safety:

```bash
# 1. Create migration branch
git checkout -b migrate/{project_slug}

# 2. Perform migration steps
# - Create/update YAML config
# - Test with library
# - Archive legacy code

# 3. Validate before merge
python -m {platform} run {project} --curr $(date +%Y%m%d) --dry-run
# Compare output with legacy run

# 4. Merge to master only after validation
git checkout master
git merge migrate/{project_slug}

# ROLLBACK: If issues found post-merge
git revert HEAD  # Revert the merge commit
# OR restore from archive/
```

### Output Comparison

Before archiving legacy code, run comparison:

```bash
# Run legacy scraper
cd audiobee_{project}
python run.py --curr YYYYMMDD
mv YYYYMMDD/ ../legacy_output/

# Run library scraper
python -m {platform} run {project} --curr YYYYMMDD

# Compare outputs (manual for now)
diff -r legacy_output/processed/ YYYYMMDD/processed/
```

### Custom Project Analysis Checklist

For 42 "Custom" projects, follow this analysis process:

1. **Platform Detection**
   - [ ] Check for healthsparq/sapphire imports
   - [ ] Check for anthem/sydneyhealth URLs
   - [ ] Check for uhc/optum URLs
   - [ ] Check for custom API patterns

2. **Effort Assessment**
   - [ ] Low: Config-only migration (uses known platform)
   - [ ] Medium: Needs custom mapper but existing platform
   - [ ] High: Needs new platform library or standalone

3. **Recommendation**
   - [ ] Migrate to existing platform
   - [ ] Migrate to new platform (Anthem/UHC when available)
   - [ ] Keep standalone with core/ dependencies
   - [ ] Archive (if unused/dead)

### Test Coverage Verification

Before mass migration, verify platform library test coverage:

```bash
# Check healthsparq test coverage
.venv/bin/pytest healthsparq/tests/ --cov=healthsparq --cov-report=term-missing

# Check sapphire test coverage
.venv/bin/pytest sapphire/tests/ --cov=sapphire --cov-report=term-missing

# Minimum acceptable coverage: 70% for critical paths (phases 1-3)
# If below threshold, add tests before migration
```

**Critical paths to verify:**
- [ ] Phase 1 (search): County iteration, result parsing
- [ ] Phase 2 (details): Provider detail fetching, error handling
- [ ] Phase 3 (normalize): NPI deduplication, mapper injection
- [ ] Config loading: YAML parsing, validation

### Dead/Unused Project Detection

Before migrating, check if project is actively used:

```bash
# Check last modification date
ls -la audiobee_{project}/

# Check git history for recent activity
git log --oneline -5 -- audiobee_{project}/

# Check if project has run output directories
ls audiobee_{project}/*/processed/ 2>/dev/null | head -5
```

**Decision matrix:**
| Last Modified | Git Activity | Output Exists | Action |
|---------------|--------------|---------------|--------|
| < 6 months | Active | Yes | Migrate |
| 6-12 months | Some | Yes | Migrate (lower priority) |
| > 12 months | None | No | Archive without migration |
| Any | Any | No data ever | Confirm with team before archiving |

### Output Difference Handling

Library output may differ from legacy in acceptable ways:

**Acceptable differences (don't block migration):**
- Field ordering changes
- Whitespace/formatting differences
- Additional fields in library output
- Sorted vs unsorted arrays (if content same)
- Fixed bugs (more accurate data)

**Blocking differences (must resolve):**
- Missing providers (count regression)
- Missing required fields
- Changed NPI values
- Significantly different field values

**Handling expected differences:**
```bash
# Normalize both outputs before comparison
jq -S '.' legacy_output.jsonl | sort > legacy_sorted.jsonl
jq -S '.' library_output.jsonl | sort > library_sorted.jsonl

# Compare provider counts first
wc -l legacy_sorted.jsonl library_sorted.jsonl

# Then field-level comparison
diff legacy_sorted.jsonl library_sorted.jsonl | head -50
```

### Gradual Rollout Strategy

Don't migrate all projects at once. Use phased approach:

**Week 1: Pilot (2-3 projects)**
- Choose 1 HealthSparq + 1 Sapphire project
- Full validation including production comparison
- Document any issues found

**Week 2-3: HealthSparq batch (10 projects)**
- Migrate in batches of 3-5 projects
- Wait 24-48 hours between batches
- Monitor for issues before next batch

**Week 4-5: Sapphire batch (11 projects)**
- Same batch approach
- Validate against production data

**Week 6+: Custom projects**
- Analyze and migrate individually
- Higher scrutiny per project

### Blocked Projects (Anthem/UHC)

These projects are **BLOCKED** until platform libraries exist:

**Anthem Platform (5 projects) - BLOCKED:**
- `audiobee_amerigroup`
- `audiobee_anthem`
- `audiobee_blueshield_ca`
- `audiobee_elderplan`
- `audiobee_healthy_blue`

**UHC Platform (3 projects) - BLOCKED:**
- `audiobee_uhc_behavioral_health`
- `audiobee_uhc_individual`
- `audiobee_uhc_medicaid`

**Unblocking criteria:**
1. Create `anthem/` platform library with:
   - SydneyHealth API integration
   - AnthemConfig in core/
   - At least one working pilot project

2. Create `uhc/` platform library with:
   - Optum API integration
   - UHCConfig in core/
   - At least one working pilot project

**Alternative path:** Keep these as standalone projects using only `core/` utilities.

### Stale Plan Verification

Before starting any migration, verify plan accuracy:

```bash
# Check actual HealthSparq configs
ls healthsparq/configs/*.yaml | wc -l
# Compare with INDEX.md count (should be ~24)

# Check actual Sapphire configs
ls sapphire/configs/*.yaml | wc -l
# Compare with INDEX.md count (should be ~3, needs 11 more)

# List projects that may already be migrated
for cfg in healthsparq/configs/*.yaml; do
  project=$(basename $cfg .yaml)
  if [ -d "audiobee_${project}" ]; then
    echo "VERIFY: $project has both config and legacy dir"
  fi
done
```

**Update INDEX.md if counts differ from plan.**

### Pre-Mortem Findings (2026-01-11)

| Risk | Severity | Mitigation |
|------|----------|------------|
| No rollback strategy | HIGH | Git branches per migration |
| 42 custom projects unanalyzed | HIGH | Analysis checklist above |
| Anthem/UHC libraries blocked | HIGH | Marked as BLOCKED, defined unblocking criteria |
| No output comparison tooling | MEDIUM | Manual comparison + acceptable difference guide |
| INDEX.md counts may be stale | MEDIUM | Verification script above |
| Test coverage unknown | MEDIUM | Coverage check before mass migration |
| Dead/unused projects | LOW | Activity check before migrating |
| Output differences expected | MEDIUM | Acceptable vs blocking difference guide |
| No gradual rollout | MEDIUM | Phased weekly rollout plan |

---

## Category 1: Already Migrated (4)

These projects are complete and serve as reference implementations.

| Project | Platform | Config | Status |
|---------|----------|--------|--------|
| `audiobee_christus_health_plan` | HealthSparq | `healthsparq/configs/christus_health_plan.yaml` | ✅ Complete |
| `audiobee_wellmark` | HealthSparq | `healthsparq/configs/wellmark.yaml` | ✅ Complete |
| `audiobee_bcbs_il` | Sapphire | `sapphire/configs/bcbs_il.yaml` | ✅ Complete |
| `audiobee_bcbs_mt` | Sapphire | `sapphire/configs/bcbs_mt.yaml` | ✅ Complete |

**Reference**: Use these as templates for similar migrations.

---

## Category 2: HealthSparq Platform (23)

Projects using HealthSparq-style provider directories. Migrate to `healthsparq/` library.

### Subcategory 2a: High Priority (Active Projects)

| Project | States | Migration Plan |
|---------|--------|----------------|
| `audiobee_medica_sg` | MN, WI, ND, SD | [projects/medica_sg.md](./projects/medica_sg.md) |
| `audiobee_medica` | MN, WI, ND, SD | [projects/medica.md](./projects/medica.md) |
| `audiobee_florida_blue` | FL | [projects/florida_blue.md](./projects/florida_blue.md) |
| `audiobee_capital_blue` | PA | [projects/capital_blue.md](./projects/capital_blue.md) |
| `audiobee_ibx` | PA | [projects/ibx.md](./projects/ibx.md) |
| `audiobee_excellus` | NY | [projects/excellus.md](./projects/excellus.md) |
| `audiobee_tufts_health_plans` | MA | [projects/tufts_health_plans.md](./projects/tufts_health_plans.md) |

### Subcategory 2b: AmeriHealth Family

| Project | States | Migration Plan |
|---------|--------|----------------|
| `audiobee_amerihealth_administrators_pa` | PA | [projects/amerihealth_administrators_pa.md](./projects/amerihealth_administrators_pa.md) |
| `audiobee_amerihealth_caritas_fl` | FL | [projects/amerihealth_caritas_fl.md](./projects/amerihealth_caritas_fl.md) |
| `audiobee_amerihealth_caritas_vip_de` | DE | [projects/amerihealth_caritas_vip_de.md](./projects/amerihealth_caritas_vip_de.md) |
| `audiobee_amerihealth_nj` | NJ | [projects/amerihealth_nj.md](./projects/amerihealth_nj.md) |

### Subcategory 2c: Other HealthSparq Sites

| Project | States | Migration Plan |
|---------|--------|----------------|
| `audiobee_alliance_trilogy` | - | [projects/alliance_trilogy.md](./projects/alliance_trilogy.md) |
| `audiobee_asuris_northwest` | WA, OR | [projects/asuris_northwest.md](./projects/asuris_northwest.md) |
| `audiobee_bcbs_ne` | NE | [projects/bcbs_ne.md](./projects/bcbs_ne.md) |
| `audiobee_bluecard_national` | National | [projects/bluecard_national.md](./projects/bluecard_national.md) |
| `audiobee_first_choice_sc` | SC | [projects/first_choice_sc.md](./projects/first_choice_sc.md) |
| `audiobee_health_plan_nv_medicaid` | NV | [projects/health_plan_nv_medicaid.md](./projects/health_plan_nv_medicaid.md) |
| `audiobee_highmark_wholecare` | PA | [projects/highmark_wholecare.md](./projects/highmark_wholecare.md) |
| `audiobee_hma` | - | [projects/hma.md](./projects/hma.md) |
| `audiobee_maine_community_health_options` | ME | [projects/maine_community_health_options.md](./projects/maine_community_health_options.md) |
| `audiobee_medical_mutual` | OH | [projects/medical_mutual.md](./projects/medical_mutual.md) |
| `audiobee_mvp_health` | NY, VT | [projects/mvp_health.md](./projects/mvp_health.md) |
| `audiobee_quartz` | WI | [projects/quartz.md](./projects/quartz.md) |
| `audiobee_sentara` | VA | [projects/sentara.md](./projects/sentara.md) |
| `audiobee_wellmark_medicare` | IA, SD | [projects/wellmark_medicare.md](./projects/wellmark_medicare.md) |

---

## Category 3: Sapphire Platform (11)

Projects using ProviderFinderOnline (PFO) directories. Migrate to `sapphire/` library.

| Project | States | Migration Plan |
|---------|--------|----------------|
| `audiobee_bcbs_kc` | KS, MO | [projects/bcbs_kc.md](./projects/bcbs_kc.md) |
| `audiobee_bcbs_la` | LA | [projects/bcbs_la.md](./projects/bcbs_la.md) |
| `audiobee_bcbs_mn` | MN | [projects/bcbs_mn.md](./projects/bcbs_mn.md) |
| `audiobee_bcbs_nm` | NM | [projects/bcbs_nm.md](./projects/bcbs_nm.md) |
| `audiobee_bcbs_sc_medicaid` | SC | [projects/bcbs_sc_medicaid.md](./projects/bcbs_sc_medicaid.md) |
| `audiobee_bcbs_tx` | TX | [projects/bcbs_tx.md](./projects/bcbs_tx.md) |
| `audiobee_bcbs_vt` | VT | [projects/bcbs_vt.md](./projects/bcbs_vt.md) |
| `audiobee_carefirst` | MD, DC, VA | [projects/carefirst.md](./projects/carefirst.md) |
| `audiobee_cox_health_plans` | MO | [projects/cox_health_plans.md](./projects/cox_health_plans.md) |
| `audiobee_horizon` | NJ | [projects/horizon.md](./projects/horizon.md) |
| `audiobee_instil_health` | - | [projects/instil_health.md](./projects/instil_health.md) |
| `audiobee_molina` | Multi-state | [projects/molina.md](./projects/molina.md) |
| `audiobee_st_lukes` | - | [projects/st_lukes.md](./projects/st_lukes.md) |

---

## Category 4: Anthem Platform (4)

Projects using Anthem/Wellpoint/SydneyHealth infrastructure. **Requires new platform library.**

| Project | States | Migration Plan |
|---------|--------|----------------|
| `audiobee_amerigroup` | Multi-state | [projects/amerigroup.md](./projects/amerigroup.md) |
| `audiobee_anthem` | Multi-state | [projects/anthem.md](./projects/anthem.md) |
| `audiobee_blueshield_ca` | CA | [projects/blueshield_ca.md](./projects/blueshield_ca.md) |
| `audiobee_elderplan` | NY | [projects/elderplan.md](./projects/elderplan.md) |
| `audiobee_healthy_blue` | Multi-state | [projects/healthy_blue.md](./projects/healthy_blue.md) |

**Action Required**: Create `anthem/` platform library similar to healthsparq/sapphire.

---

## Category 5: UHC Platform (3)

Projects using UnitedHealthcare/Optum infrastructure. **Requires new platform library.**

| Project | States | Migration Plan |
|---------|--------|----------------|
| `audiobee_uhc_behavioral_health` | National | [projects/uhc_behavioral_health.md](./projects/uhc_behavioral_health.md) |
| `audiobee_uhc_individual` | National | [projects/uhc_individual.md](./projects/uhc_individual.md) |
| `audiobee_uhc_medicaid` | Multi-state | [projects/uhc_medicaid.md](./projects/uhc_medicaid.md) |

**Action Required**: Create `uhc/` platform library similar to healthsparq/sapphire.

---

## Category 6: Other/Custom (42)

Projects with unique implementations requiring individual analysis.

### Subcategory 6a: BCBS Variants (Non-PFO)

| Project | Notes | Migration Plan |
|---------|-------|----------------|
| `audiobee_bcbs_ma` | Custom API | [projects/bcbs_ma.md](./projects/bcbs_ma.md) |

### Subcategory 6b: Regional Health Plans

| Project | Notes | Migration Plan |
|---------|-------|----------------|
| `audiobee_banner_health` | AZ health system | [projects/banner_health.md](./projects/banner_health.md) |
| `audiobee_baylor_scott_white` | TX health system | [projects/baylor_scott_white.md](./projects/baylor_scott_white.md) |
| `audiobee_champion_health` | - | [projects/champion_health.md](./projects/champion_health.md) |
| `audiobee_community_care_ca` | CA | [projects/community_care_ca.md](./projects/community_care_ca.md) |
| `audiobee_delaware_first` | DE | [projects/delaware_first.md](./projects/delaware_first.md) |
| `audiobee_emblem` | NY | [projects/emblem.md](./projects/emblem.md) |
| `audiobee_firstcare_health` | TX | [projects/firstcare_health.md](./projects/firstcare_health.md) |
| `audiobee_fl_community_care` | FL | [projects/fl_community_care.md](./projects/fl_community_care.md) |
| `audiobee_gateway_health` | PA | [projects/gateway_health.md](./projects/gateway_health.md) |
| `audiobee_harvard_pilgrim` | MA, NH, ME | [projects/harvard_pilgrim.md](./projects/harvard_pilgrim.md) |
| `audiobee_healthy_mississippi` | MS | [projects/healthy_mississippi.md](./projects/healthy_mississippi.md) |
| `audiobee_innovataion_health` | VA | [projects/innovataion_health.md](./projects/innovataion_health.md) |
| `audiobee_jefferson_health` | PA | [projects/jefferson_health.md](./projects/jefferson_health.md) |
| `audiobee_kelseycare` | TX | [projects/kelseycare.md](./projects/kelseycare.md) |
| `audiobee_la_care_health` | CA | [projects/la_care_health.md](./projects/la_care_health.md) |
| `audiobee_mass_gen` | MA | [projects/mass_gen.md](./projects/mass_gen.md) |
| `audiobee_multiplan` | National | [projects/multiplan.md](./projects/multiplan.md) |
| `audiobee_my_choice_wi` | WI | [projects/my_choice_wi.md](./projects/my_choice_wi.md) |
| `audiobee_nc_medicaid` | NC | [projects/nc_medicaid.md](./projects/nc_medicaid.md) |
| `audiobee_nextblue_nd` | ND | [projects/nextblue_nd.md](./projects/nextblue_nd.md) |
| `audiobee_northwell_direct` | NY | [projects/northwell_direct.md](./projects/northwell_direct.md) |
| `audiobee_or_health_share_medicaid` | OR | [projects/or_health_share_medicaid.md](./projects/or_health_share_medicaid.md) |
| `audiobee_partners_health_plan` | NY | [projects/partners_health_plan.md](./projects/partners_health_plan.md) |
| `audiobee_pehp` | UT | [projects/pehp.md](./projects/pehp.md) |
| `audiobee_physicians_health_plan_mi` | MI | [projects/physicians_health_plan_mi.md](./projects/physicians_health_plan_mi.md) |
| `audiobee_qualcare` | NJ | [projects/qualcare.md](./projects/qualcare.md) |
| `audiobee_qualchoice` | AR | [projects/qualchoice.md](./projects/qualchoice.md) |
| `audiobee_scan_health` | CA | [projects/scan_health.md](./projects/scan_health.md) |
| `audiobee_security_health_plan` | WI | [projects/security_health_plan.md](./projects/security_health_plan.md) |
| `audiobee_ucla_health` | CA | [projects/ucla_health.md](./projects/ucla_health.md) |
| `audiobee_upmc` | PA | [projects/upmc.md](./projects/upmc.md) |
| `audiobee_vermont_blue_advantage` | VT | [projects/vermont_blue_advantage.md](./projects/vermont_blue_advantage.md) |
| `audiobee_wellcare` | Multi-state | [projects/wellcare.md](./projects/wellcare.md) |
| `audiobee_wyoblue_advantage` | WY | [projects/wyoblue_advantage.md](./projects/wyoblue_advantage.md) |

### Subcategory 6c: BlueShield CA Variants

| Project | Notes | Migration Plan |
|---------|-------|----------------|
| `audiobee_blueshield_ca_server` | Server variant | [projects/blueshield_ca_server.md](./projects/blueshield_ca_server.md) |
| `audiobee_blueshield_ca-new` | New implementation | [projects/blueshield_ca-new.md](./projects/blueshield_ca-new.md) |

---

## Required Platform Updates

### core/ Updates

See [core-updates.md](./core-updates.md) for detailed changes.

| Update | Priority | Description |
|--------|----------|-------------|
| AnthemConfig enhancement | High | Add missing fields for Anthem platform |
| UHCConfig creation | High | New config class for UHC platform |
| Mapper registry unification | Medium | Converge factory + registry patterns |

### healthsparq/ Updates

See [healthsparq-updates.md](./healthsparq-updates.md) for detailed changes.

| Update | Priority | Description |
|--------|----------|-------------|
| Add 23 new configs | High | YAML configs for each migrating project |
| Custom mapper registry | Medium | Support project-specific mappers |

### sapphire/ Updates

See [sapphire-updates.md](./sapphire-updates.md) for detailed changes.

| Update | Priority | Description |
|--------|----------|-------------|
| Add 11 new configs | High | YAML configs for each migrating project |
| Recovery phase | Medium | Port Phase 6 from HealthSparq |

### New Platform Libraries

| Library | Priority | Description |
|---------|----------|-------------|
| `anthem/` | High | Anthem/Wellpoint/SydneyHealth platform |
| `uhc/` | High | UnitedHealthcare/Optum platform |

---

## Migration Workflow

### For HealthSparq Projects

```bash
# 1. Create config
cp healthsparq/configs/_template.yaml healthsparq/configs/{project}.yaml
# Edit with project-specific values

# 2. Validate config
python -m healthsparq validate {project}

# 3. Test with dry run
python -m healthsparq run {project} --curr $(date +%Y%m%d) --dry-run

# 4. Create thin wrapper (optional)
mkdir audiobee_{project}
cp healthsparq/templates/run.py.template audiobee_{project}/run.py

# 5. Run full pipeline
python -m healthsparq run {project} --curr $(date +%Y%m%d)
```

### For Sapphire Projects

```bash
# 1. Create config
cp sapphire/configs/_template.yaml sapphire/configs/{project}.yaml
# Edit with project-specific values

# 2. Validate config
python -m sapphire validate {project}

# 3. Test with dry run
python -m sapphire run {project} --curr $(date +%Y%m%d) --dry-run

# 4. Run full pipeline
python -m sapphire run {project} --curr $(date +%Y%m%d)
```

---

## Success Criteria

A project is considered migrated when:

1. ✅ Config exists in platform configs/ directory
2. ✅ `python -m {platform} validate {project}` passes
3. ✅ `python -m {platform} run {project} --curr YYYYMMDD` produces valid output
4. ✅ Output matches or improves on legacy scraper output
5. ✅ Legacy project directory can be archived

---

## Timeline Recommendations

| Phase | Projects | Estimated Effort |
|-------|----------|------------------|
| Phase 1a | HealthSparq (23) | Config creation only |
| Phase 1b | Sapphire (11) | Config creation only |
| Phase 2 | Anthem (5) | New platform library |
| Phase 2 | UHC (3) | New platform library |
| Phase 3 | Custom (42) | Individual analysis |

---

## Document Maintenance

- Update this INDEX when projects are migrated
- Move completed projects to "Already Migrated" section
- Update counts in Executive Summary
- Add learnings to respective platform update docs
