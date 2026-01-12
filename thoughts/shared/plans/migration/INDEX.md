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
| **Already Migrated** | 4 | Complete |
| **HealthSparq Platform** | 23 | Ready for migration |
| **Sapphire Platform** | 11 | Ready for migration |
| **Anthem Platform** | 4 | Needs platform library |
| **UHC Platform** | 3 | Needs platform library |
| **Other/Custom** | 42 | Needs individual analysis |
| **Total** | 87 | |

## Migration Priority

### Phase 1: Quick Wins (HealthSparq + Sapphire)
Projects that can use existing platform libraries with minimal changes.

### Phase 2: Platform Extensions (Anthem + UHC)
Projects requiring new platform library creation.

### Phase 3: Custom Migrations
Projects with unique implementations needing individual analysis.

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
