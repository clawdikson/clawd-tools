#!/usr/bin/env python3
"""Environment variable validation for shared_package projects.

Usage:
    python tools/validate_env.py --project audiobee_bcbs_il --site-type sapphire
    python tools/validate_env.py --check-all  # Validate all .env files
"""
import argparse
import sys
from pathlib import Path

# Site type requirements
SITE_TYPE_REQUIRED_VARS = {
    "sapphire": ["SCRAPER_PROJECT_NAME", "SCRAPER_SITE_TYPE"],
    "healthsparq": ["SCRAPER_PROJECT_NAME", "SCRAPER_SITE_TYPE"],
    "carrier": ["SCRAPER_PROJECT_NAME", "SCRAPER_SITE_TYPE"],
    "anthem": ["SCRAPER_PROJECT_NAME", "SCRAPER_SITE_TYPE"],
}

# Proxy provider requirements
PROXY_PROVIDER_VARS = {
    "nordvpn": ["NORD_USERNAME", "NORD_PASSWORD"],
    "surfshark": ["SURFSHARK_USERNAME", "SURFSHARK_PASSWORD"],
    "smartproxy_session": ["SMARTPROXY_USERNAME", "SMARTPROXY_PASSWORD", "SMARTPROXY_HOST"],
    "smartproxy_rotating": ["SMARTPROXY_USERNAME", "SMARTPROXY_PASSWORD", "SMARTPROXY_HOST"],
    "dataimpulse_session": ["DATAIMPULSE_PROXY_USERNAME", "DATAIMPULSE_PROXY_PASSWORD", "DATAIMPULSE_PROXY_HOST"],
    "dataimpulse_rotating": ["DATAIMPULSE_PROXY_USERNAME", "DATAIMPULSE_PROXY_PASSWORD", "DATAIMPULSE_PROXY_HOST"],
    "decodo_dc_static": ["DECODO_DC_USERNAME", "DECODO_DC_PASSWORD", "DECODO_DC_HOST"],
}


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    if not env_path.exists():
        return env_vars

    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '=' not in line:
                continue

            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()

            # Remove quotes if present
            if value.startswith('"') and value.endswith('"') or value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            env_vars[key] = value

    return env_vars


def validate_env(
    env_path: Path,
    project_name: str | None = None,
    site_type: str | None = None,
) -> tuple[bool, list[str]]:
    """Validate environment configuration.

    Returns:
        Tuple of (is_valid, errors_list)
    """
    errors = []

    # Load .env file
    if not env_path.exists():
        errors.append(f"Environment file not found: {env_path}")
        return False, errors

    env_vars = load_env_file(env_path)

    # Check site type requirements
    if site_type:
        if site_type not in SITE_TYPE_REQUIRED_VARS:
            errors.append(f"Unknown site type: {site_type}")
            errors.append(f"Valid types: {', '.join(SITE_TYPE_REQUIRED_VARS.keys())}")
        else:
            required_vars = SITE_TYPE_REQUIRED_VARS[site_type]
            for var in required_vars:
                if not env_vars.get(var):
                    errors.append(f"Missing required variable for {site_type}: {var}")

    # Check proxy configuration
    proxy_types_raw = env_vars.get("PROXY_TYPES", "")
    if proxy_types_raw:
        proxy_types = [pt.strip() for pt in proxy_types_raw.split(",") if pt.strip()]

        for proxy_type in proxy_types:
            if proxy_type == "none":
                continue

            if proxy_type not in PROXY_PROVIDER_VARS:
                errors.append(f"Unknown proxy type: {proxy_type}")
                continue

            # Check required vars for this proxy provider
            required_vars = PROXY_PROVIDER_VARS[proxy_type]
            for var in required_vars:
                if not env_vars.get(var):
                    errors.append(f"Missing required variable for {proxy_type}: {var}")

    # Check for common mistakes
    if "SCRAPER_PROJECT_NAME" in env_vars and not env_vars["SCRAPER_PROJECT_NAME"]:
        errors.append("SCRAPER_PROJECT_NAME is empty")

    if "SCRAPER_SITE_TYPE" in env_vars:
        site_type_value = env_vars["SCRAPER_SITE_TYPE"]
        if site_type_value and site_type_value not in SITE_TYPE_REQUIRED_VARS:
            errors.append(f"Invalid SCRAPER_SITE_TYPE: {site_type_value}")

    # Check date format if present
    for date_var in ["SCRAPER_CURR_DATE", "SCRAPER_PREV_DATE"]:
        if env_vars.get(date_var):
            date_val = env_vars[date_var]
            if len(date_val) != 8 or not date_val.isdigit():
                errors.append(f"{date_var} must be YYYYMMDD format, got: {date_val}")

    # Security check: warn about possible plaintext credentials
    for key in env_vars:
        if any(cred in key.upper() for cred in ["PASSWORD", "USERNAME", "KEY", "SECRET"]):
            value = env_vars[key]
            if value and len(value) > 0:
                # Don't show actual values in output!
                print(f"  ✓ {key} is set (value hidden for security)")

    is_valid = len(errors) == 0
    return is_valid, errors


def main():
    parser = argparse.ArgumentParser(description="Validate environment configuration")
    parser.add_argument("--project", help="Project name (e.g., audiobee_bcbs_il)")
    parser.add_argument("--site-type", help="Site type (sapphire, healthsparq, carrier, anthem)")
    parser.add_argument("--env-file", help="Path to .env file (default: .env in current dir)")
    parser.add_argument("--check-all", action="store_true", help="Check all .env files in project subdirectories")

    args = parser.parse_args()

    if args.check_all:
        # Find all .env files
        root = Path.cwd()
        env_files = list(root.glob("**/.env"))

        print(f"Found {len(env_files)} .env files to validate\n")

        all_valid = True
        for env_file in env_files:
            project_dir = env_file.parent.name
            print(f"Validating {project_dir}/.env...")

            is_valid, errors = validate_env(env_file)

            if is_valid:
                print("  ✓ Valid\n")
            else:
                print("  ✗ Invalid:")
                for error in errors:
                    print(f"    - {error}")
                print()
                all_valid = False

        sys.exit(0 if all_valid else 1)

    else:
        # Validate single .env file
        env_path = Path(args.env_file) if args.env_file else Path(".env")

        print(f"Validating {env_path}...")

        is_valid, errors = validate_env(env_path, args.project, args.site_type)

        if is_valid:
            print("✓ Environment configuration is valid!")
            sys.exit(0)
        else:
            print("✗ Environment configuration has errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)


if __name__ == "__main__":
    main()
