#!/usr/bin/env python3
"""Update config.yaml files with site_type: carrier for audiobee projects."""

import os
from pathlib import Path

# List of 61 audiobee folders
FOLDERS = [
    "audiobee_aetna_better_health_of_oklahoma",
    "audiobee_amerigroup",
    "audiobee_amerihealth_caritas_fl",
    "audiobee_anthem",
    "audiobee_banner_health",
    "audiobee_baylor_scott_white",
    "audiobee_bcbs_kc",
    "audiobee_bcbs_la",
    "audiobee_bcbs_ma",
    "audiobee_bcbs_mn",
    "audiobee_bcbs_ne",
    "audiobee_bcbs_nm",
    "audiobee_bcbs_sc_medicaid",
    "audiobee_bcbs_tx",
    "audiobee_bcbs_vt",
    "audiobee_bluecard_national",
    "audiobee_blueshield_ca",
    "audiobee_blueshield_ca-new",
    "audiobee_carefirst",
    "audiobee_champion_health",
    "audiobee_community_care_ca",
    "audiobee_cox_health_plans",
    "audiobee_delaware_first",
    "audiobee_elderplan",
    "audiobee_emblem",
    "audiobee_firstcare_health",
    "audiobee_fl_community_care",
    "audiobee_florida_blue",
    "audiobee_gateway_health",
    "audiobee_harvard_pilgrim",
    "audiobee_healthy_blue",
    "audiobee_healthy_mississippi",
    "audiobee_horizon",
    "audiobee_innovataion_health",
    "audiobee_instil_health",
    "audiobee_jefferson_health",
    "audiobee_kelseycare",
    "audiobee_la_care_health",
    "audiobee_mass_gen",
    "audiobee_multiplan",
    "audiobee_my_choice_wi",
    "audiobee_nc_medicaid",
    "audiobee_nextblue_nd",
    "audiobee_northwell_direct",
    "audiobee_or_health_share_medicaid",
    "audiobee_partners_health_plan",
    "audiobee_pehp",
    "audiobee_physicians_health_plan_mi",
    "audiobee_qualcare",
    "audiobee_qualchoice",
    "audiobee_scan_health",
    "audiobee_security_health_plan",
    "audiobee_st_lukes",
    "audiobee_ucla_health",
    "audiobee_uhc_behavioral_health",
    "audiobee_uhc_individual",
    "audiobee_uhc_medicaid",
    "audiobee_upmc",
    "audiobee_vermont_blue_advantage",
    "audiobee_wellcare",
    "audiobee_wyoblue_advantage",
]

BASE_DIR = Path("/Users/dikson/Work/ideon_scraping/scraping")
SITE_TYPE_LINE = "site_type: carrier\n"

created = 0
updated = 0
skipped = 0
errors = []

for folder in FOLDERS:
    folder_path = BASE_DIR / folder
    config_path = folder_path / "config.yaml"

    # Check if folder exists
    if not folder_path.exists():
        errors.append(f"{folder}: folder does not exist")
        continue

    # Case 1: config.yaml doesn't exist - create it
    if not config_path.exists():
        try:
            config_path.write_text(SITE_TYPE_LINE)
            created += 1
            print(f"✓ Created: {folder}/config.yaml")
        except Exception as e:
            errors.append(f"{folder}: failed to create - {e}")
        continue

    # Case 2 & 3: config.yaml exists
    try:
        content = config_path.read_text()

        # Check if site_type already exists
        if "site_type:" in content:
            skipped += 1
            print(f"⊘ Skipped: {folder}/config.yaml (already has site_type)")
        else:
            # Add site_type as first line
            new_content = SITE_TYPE_LINE + content
            config_path.write_text(new_content)
            updated += 1
            print(f"✓ Updated: {folder}/config.yaml")
    except Exception as e:
        errors.append(f"{folder}: failed to process - {e}")

print("\n" + "="*60)
print(f"Summary:")
print(f"  Created: {created}")
print(f"  Updated: {updated}")
print(f"  Skipped: {skipped}")
print(f"  Errors:  {len(errors)}")
print("="*60)

if errors:
    print("\nErrors:")
    for error in errors:
        print(f"  ✗ {error}")
