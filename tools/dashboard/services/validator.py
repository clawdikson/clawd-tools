"""Validation service for checking project configuration and security.

Provides validation for:
- Environment variable configuration (.env files)
- Security scanning for hardcoded credentials
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    """Result of a validation check.

    Attributes:
        category: Validation category (env, security, config)
        status: Result status (error, warning, ok)
        message: Human-readable description
        fix_action: Suggested fix action, or None
    """

    category: str
    status: str
    message: str
    fix_action: str | None


@dataclass
class SecurityIssue:
    """A security issue found in code.

    Attributes:
        file: Path to the file containing the issue
        line_num: Line number where issue was found
        pattern: Type of credential pattern matched
        value: Truncated value found (for display)
    """

    file: Path
    line_num: int
    pattern: str
    value: str


# Required environment variables by site type
SITE_TYPE_REQUIRED_VARS = {
    "sapphire": ["SCRAPER_PROJECT_NAME", "SCRAPER_SITE_TYPE"],
    "healthsparq": ["SCRAPER_PROJECT_NAME", "SCRAPER_SITE_TYPE"],
    "carrier": ["SCRAPER_PROJECT_NAME", "SCRAPER_SITE_TYPE"],
    "anthem": ["SCRAPER_PROJECT_NAME", "SCRAPER_SITE_TYPE"],
    "standalone": ["SCRAPER_PROJECT_NAME"],
}

# Proxy provider required variables
PROXY_PROVIDER_VARS = {
    "nordvpn": ["NORD_USERNAME", "NORD_PASSWORD"],
    "surfshark": ["SURFSHARK_USERNAME", "SURFSHARK_PASSWORD"],
    "smartproxy_session": ["SMARTPROXY_USERNAME", "SMARTPROXY_PASSWORD", "SMARTPROXY_HOST"],
    "smartproxy_rotating": ["SMARTPROXY_USERNAME", "SMARTPROXY_PASSWORD", "SMARTPROXY_HOST"],
    "dataimpulse_session": [
        "DATAIMPULSE_PROXY_USERNAME",
        "DATAIMPULSE_PROXY_PASSWORD",
        "DATAIMPULSE_PROXY_HOST",
    ],
    "dataimpulse_rotating": [
        "DATAIMPULSE_PROXY_USERNAME",
        "DATAIMPULSE_PROXY_PASSWORD",
        "DATAIMPULSE_PROXY_HOST",
    ],
    "decodo_dc_static": ["DECODO_DC_USERNAME", "DECODO_DC_PASSWORD", "DECODO_DC_HOST"],
}

# Credential patterns to scan for
CREDENTIAL_PATTERNS = [
    (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', "API Key"),
    (r'apikey\s*=\s*["\']([^"\']+)["\']', "API Key"),
    (r'api[_-]?secret\s*=\s*["\']([^"\']+)["\']', "API Secret"),
    (r'password\s*=\s*["\']([^"\']+)["\']', "Password"),
    (r'passwd\s*=\s*["\']([^"\']+)["\']', "Password"),
    (r'pwd\s*=\s*["\']([^"\']+)["\']', "Password"),
    (r'username\s*=\s*["\']([^"\']+)["\']', "Username"),
    (r'user\s*=\s*["\']([^"\']+)["\']', "Username"),
    (r'token\s*=\s*["\']([^"\']+)["\']', "Token"),
    (r'auth[_-]?token\s*=\s*["\']([^"\']+)["\']', "Auth Token"),
    (r'access[_-]?token\s*=\s*["\']([^"\']+)["\']', "Access Token"),
    (r'secret[_-]?token\s*=\s*["\']([^"\']+)["\']', "Secret Token"),
    (r'bearer\s+([a-zA-Z0-9_\-\.]{20,})', "Bearer Token"),
    (r'aws[_-]?access[_-]?key[_-]?id\s*=\s*["\']([^"\']+)["\']', "AWS Access Key"),
    (r'aws[_-]?secret[_-]?access[_-]?key\s*=\s*["\']([^"\']+)["\']', "AWS Secret Key"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private Key"),
    (r'(?:postgres|mysql|mongodb)://[^:]+:([^@]+)@', "Database Password in URL"),
]

# Patterns that indicate safe usage (loading from env/config)
SAFE_PATTERNS = [
    r"os\.getenv",
    r"os\.environ",
    r"config\.",
    r"settings\.",
    r"SecretStr\(",
    r"input\(",
    r"#.*",  # Comments
    r'""".*"""',  # Docstrings
    r"'''.*'''",
]

# File extensions to scan
SCAN_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".md"}

# Directories to skip
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}


class Validator:
    """Service for validating project configuration and security.

    Example:
        >>> validator = Validator()
        >>> results = validator.validate_env(Path("audiobee_project"))
        >>> issues = validator.scan_credentials(Path("audiobee_project"))
    """

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate_env(self, project_path: Path) -> list[ValidationResult]:
        """Validate environment configuration.

        Checks:
        - .env file exists
        - Required variables are present
        - Proxy configuration is valid
        - Date formats are correct

        Args:
            project_path: Path to project directory

        Returns:
            List of validation results
        """
        results = []
        env_file = project_path / ".env"

        # Check if .env exists
        if not env_file.exists():
            results.append(
                ValidationResult(
                    category="env",
                    status="error",
                    message=".env file not found",
                    fix_action="Create .env file from .env.example template",
                )
            )
            return results

        # Load environment variables
        env_vars = self._load_env_file(env_file)

        # Check for empty file
        if not env_vars:
            results.append(
                ValidationResult(
                    category="env",
                    status="warning",
                    message=".env file is empty or has no valid variables",
                    fix_action="Add required environment variables",
                )
            )
            return results

        # Check site type requirements
        site_type = env_vars.get("SCRAPER_SITE_TYPE", "standalone")
        required_vars = SITE_TYPE_REQUIRED_VARS.get(site_type, ["SCRAPER_PROJECT_NAME"])

        for var in required_vars:
            if not env_vars.get(var):
                results.append(
                    ValidationResult(
                        category="env",
                        status="error",
                        message=f"Missing required variable: {var}",
                        fix_action=f"Add {var}=<value> to .env file",
                    )
                )

        # Check proxy configuration
        proxy_types_raw = env_vars.get("PROXY_TYPES", "")
        if proxy_types_raw:
            proxy_types = [pt.strip() for pt in proxy_types_raw.split(",") if pt.strip()]

            for proxy_type in proxy_types:
                if proxy_type == "none":
                    continue

                if proxy_type not in PROXY_PROVIDER_VARS:
                    results.append(
                        ValidationResult(
                            category="env",
                            status="warning",
                            message=f"Unknown proxy type: {proxy_type}",
                            fix_action="Check PROXY_TYPES value",
                        )
                    )
                    continue

                required_proxy_vars = PROXY_PROVIDER_VARS[proxy_type]
                for var in required_proxy_vars:
                    if not env_vars.get(var):
                        results.append(
                            ValidationResult(
                                category="env",
                                status="warning",
                                message=f"Missing {var} for {proxy_type} proxy",
                                fix_action=f"Add {var} to .env file",
                            )
                        )

        # Check date format
        for date_var in ["SCRAPER_CURR_DATE", "SCRAPER_PREV_DATE"]:
            if env_vars.get(date_var):
                date_val = env_vars[date_var]
                if len(date_val) != 8 or not date_val.isdigit():
                    results.append(
                        ValidationResult(
                            category="env",
                            status="error",
                            message=f"{date_var} must be YYYYMMDD format, got: {date_val}",
                            fix_action=f"Change {date_var} to YYYYMMDD format",
                        )
                    )

        return results

    def _load_env_file(self, env_path: Path) -> dict[str, str]:
        """Load environment variables from .env file.

        Args:
            env_path: Path to .env file

        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue

                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]

                    env_vars[key] = value
        except Exception:
            pass

        return env_vars

    def scan_credentials(self, project_path: Path) -> list[SecurityIssue]:
        """Scan for hardcoded credentials in project files.

        Args:
            project_path: Path to project directory

        Returns:
            List of security issues found
        """
        issues = []

        for file_path in project_path.rglob("*"):
            if file_path.is_dir():
                continue
            if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
                continue
            if file_path.suffix not in SCAN_EXTENSIONS:
                continue

            file_issues = self._scan_file(file_path)
            issues.extend(file_issues)

        return issues

    def _scan_file(self, file_path: Path) -> list[SecurityIssue]:
        """Scan a single file for credentials.

        Args:
            file_path: Path to file

        Returns:
            List of security issues found
        """
        issues = []

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return issues

        for line_num, line in enumerate(lines, start=1):
            # Skip safe patterns
            if self._is_safe_line(line):
                continue

            # Check for credential patterns
            for pattern, pattern_name in CREDENTIAL_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)

                for match in matches:
                    try:
                        value = (
                            match.group(1)
                            if match.lastindex and match.lastindex >= 1
                            else match.group(0)
                        )
                    except IndexError:
                        value = match.group(0)

                    # Skip safe values
                    if value in [
                        "",
                        "your_api_key",
                        "your_password",
                        "***",
                        "xxxx",
                        "placeholder",
                    ]:
                        continue
                    if value.startswith("$"):  # Shell variable
                        continue
                    if len(value) < 3:
                        continue

                    issues.append(
                        SecurityIssue(
                            file=file_path,
                            line_num=line_num,
                            pattern=pattern_name,
                            value=value[:20] + "..." if len(value) > 20 else value,
                        )
                    )

        return issues

    def _is_safe_line(self, line: str) -> bool:
        """Check if line uses safe patterns (env/config loading).

        Args:
            line: Line of code to check

        Returns:
            True if line is safe, False otherwise
        """
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in SAFE_PATTERNS)

    def validate_all(self, project_path: Path) -> dict[str, Any]:
        """Run all validations on a project.

        Args:
            project_path: Path to project directory

        Returns:
            Dictionary with 'env' and 'security' validation results
        """
        return {
            "env": self.validate_env(project_path),
            "security": self.scan_credentials(project_path),
        }

    def get_summary(self, results: list[ValidationResult]) -> dict[str, int]:
        """Get summary counts of validation results.

        Args:
            results: List of validation results

        Returns:
            Dictionary with error, warning, ok counts
        """
        summary = {"errors": 0, "warnings": 0, "ok": 0}

        for result in results:
            if result.status == "error":
                summary["errors"] += 1
            elif result.status == "warning":
                summary["warnings"] += 1
            else:
                summary["ok"] += 1

        return summary
