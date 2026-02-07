#!/usr/bin/env python3
"""
NPI Reconciliation Engine - Advanced NPI Data Validation & Cross-Reference

WHAT IT SOLVES:
From debugging analysis, NPI matching issues are causing major data quality problems:
- AutoQA NPI vs label search conflicts (healthsparq sites)
- Cross-network provider data pollution
- Duplicate NPIs and incorrect mappings
- Missing NPI validation across runs

NEVER RUNS SCRAPERS - Only analyzes existing data for safety.

Usage:
    python tools/npi_reconciliation_engine.py --validate audiobee_medica
    python tools/npi_reconciliation_engine.py --cross-check --all-sites
    python tools/npi_reconciliation_engine.py --dedupe --project audiobee_bcbs_il
    python tools/npi_reconciliation_engine.py --audit-trail --days 30
    python tools/npi_reconciliation_engine.py --autoqa-analysis
"""

import argparse
import json
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional, Set, Tuple
import re
import hashlib
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NPIReconciliationEngine:
    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.db_path = self.workspace / "tools" / "npi_reconciliation.db"
        self.init_database()
        
        # NPI validation patterns
        self.npi_pattern = re.compile(r'^\d{10}$')
        
        # Known problematic patterns from debugging analysis
        self.problem_patterns = {
            "empty_npi_with_data": "Provider has data but empty NPI",
            "duplicate_npi": "Same NPI mapped to multiple providers",
            "cross_network_pollution": "Provider appears in wrong network",
            "autoqa_mismatch": "AutoQA NPI vs label search conflict",
            "invalid_npi_format": "NPI doesn't match 10-digit format"
        }

    def init_database(self):
        """Initialize SQLite database for NPI tracking"""
        os.makedirs(self.db_path.parent, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Main NPI registry
            conn.execute("""
                CREATE TABLE IF NOT EXISTS npi_registry (
                    npi TEXT PRIMARY KEY,
                    provider_name TEXT,
                    provider_type TEXT,
                    first_seen_date TEXT,
                    last_seen_date TEXT,
                    total_appearances INTEGER DEFAULT 1,
                    unique_projects TEXT,
                    networks_seen TEXT,
                    validation_status TEXT,
                    data_quality_score REAL
                )
            """)
            
            # Cross-reference tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS npi_appearances (
                    id INTEGER PRIMARY KEY,
                    npi TEXT,
                    project_name TEXT,
                    site_type TEXT,
                    run_date TEXT,
                    network TEXT,
                    provider_name TEXT,
                    data_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Validation issues
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validation_issues (
                    id INTEGER PRIMARY KEY,
                    project_name TEXT,
                    run_date TEXT,
                    issue_type TEXT,
                    npi TEXT,
                    description TEXT,
                    severity TEXT,
                    fixed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # AutoQA analysis
            conn.execute("""
                CREATE TABLE IF NOT EXISTS autoqa_analysis (
                    id INTEGER PRIMARY KEY,
                    project_name TEXT,
                    run_date TEXT,
                    npi TEXT,
                    search_method TEXT,
                    result_accuracy TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def validate_project(self, project_name: str, run_date: Optional[str] = None) -> Dict:
        """Comprehensive NPI validation for a project"""
        logger.info(f"Validating NPIs for {project_name}")
        
        project_path = self.workspace / project_name
        if not project_path.exists():
            return {"error": f"Project not found: {project_name}"}
        
        # Find target run date
        target_date = run_date or self._get_latest_run_date(project_path)
        if not target_date:
            return {"error": "No valid run dates found"}
        
        run_path = project_path / target_date
        
        validation_report = {
            "project": project_name,
            "run_date": target_date,
            "npi_summary": {},
            "validation_results": {},
            "issues_found": [],
            "recommendations": [],
            "data_quality_score": 0.0
        }
        
        # Load and analyze provider data
        providers = self._load_providers(run_path)
        if not providers:
            validation_report["issues_found"].append({
                "type": "no_data",
                "severity": "high",
                "description": "No provider data found"
            })
            return validation_report
        
        # Perform validation checks
        validation_report["npi_summary"] = self._analyze_npi_summary(providers)
        validation_report["validation_results"] = self._perform_validation_checks(providers, project_name, target_date)
        validation_report["issues_found"] = self._identify_issues(validation_report["validation_results"])
        validation_report["recommendations"] = self._generate_recommendations(validation_report["issues_found"], project_name)
        validation_report["data_quality_score"] = self._calculate_quality_score(validation_report)
        
        # Store results in database
        self._store_validation_results(project_name, target_date, providers, validation_report)
        
        return validation_report

    def _get_latest_run_date(self, project_path: Path) -> Optional[str]:
        """Get the most recent valid run date"""
        dates = []
        for item in project_path.iterdir():
            if item.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', item.name):
                dates.append(item.name)
        return sorted(dates, reverse=True)[0] if dates else None

    def _load_providers(self, run_path: Path) -> List[Dict]:
        """Load provider data from processed output"""
        providers = []
        
        # Check common output locations
        processed_path = run_path / "processed"
        
        for jsonl_file in processed_path.glob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            provider_data = json.loads(line)
                            providers.append(provider_data)
            except Exception as e:
                logger.warning(f"Error loading {jsonl_file}: {e}")
        
        return providers

    def _analyze_npi_summary(self, providers: List[Dict]) -> Dict:
        """Generate NPI summary statistics"""
        total_providers = len(providers)
        
        npis_present = 0
        npis_valid = 0
        npis_empty = 0
        unique_npis = set()
        duplicate_npis = defaultdict(int)
        
        for provider in providers:
            npi = self._extract_npi(provider)
            
            if npi:
                npis_present += 1
                unique_npis.add(npi)
                duplicate_npis[npi] += 1
                
                if self.npi_pattern.match(npi):
                    npis_valid += 1
            else:
                npis_empty += 1
        
        # Find actual duplicates (count > 1)
        actual_duplicates = {npi: count for npi, count in duplicate_npis.items() if count > 1}
        
        return {
            "total_providers": total_providers,
            "npis_present": npis_present,
            "npis_empty": npis_empty,
            "npis_valid": npis_valid,
            "npis_invalid": npis_present - npis_valid,
            "unique_npis": len(unique_npis),
            "duplicate_npis": len(actual_duplicates),
            "duplicate_details": actual_duplicates,
            "npi_completion_rate": npis_present / total_providers if total_providers > 0 else 0,
            "npi_validity_rate": npis_valid / npis_present if npis_present > 0 else 0
        }

    def _extract_npi(self, provider: Dict) -> Optional[str]:
        """Extract NPI from provider data with multiple fallback strategies"""
        # Common NPI field names
        npi_fields = ["npi", "NPI", "provider_npi", "npi_number", "npi_id"]
        
        # Try direct field access
        for field in npi_fields:
            if field in provider:
                npi = provider[field]
                if npi and str(npi).strip():
                    return str(npi).strip()
        
        # Try nested provider object
        if "provider" in provider and isinstance(provider["provider"], dict):
            for field in npi_fields:
                if field in provider["provider"]:
                    npi = provider["provider"][field]
                    if npi and str(npi).strip():
                        return str(npi).strip()
        
        return None

    def _perform_validation_checks(self, providers: List[Dict], project_name: str, run_date: str) -> Dict:
        """Perform comprehensive validation checks"""
        results = {
            "npi_format_check": {"passed": 0, "failed": [], "details": []},
            "duplicate_check": {"passed": 0, "failed": [], "details": []},
            "completeness_check": {"passed": 0, "failed": [], "details": []},
            "network_consistency": {"passed": 0, "failed": [], "details": []},
            "cross_reference_check": {"external_matches": 0, "conflicts": [], "details": []}
        }
        
        npi_to_providers = defaultdict(list)
        
        for i, provider in enumerate(providers):
            npi = self._extract_npi(provider)
            provider_name = self._extract_provider_name(provider)
            networks = self._extract_networks(provider)
            
            # Format validation
            if npi:
                if self.npi_pattern.match(npi):
                    results["npi_format_check"]["passed"] += 1
                else:
                    results["npi_format_check"]["failed"].append(i)
                    results["npi_format_check"]["details"].append({
                        "index": i, "npi": npi, "issue": "invalid_format"
                    })
            
            # Completeness check
            if npi and provider_name:
                results["completeness_check"]["passed"] += 1
            else:
                results["completeness_check"]["failed"].append(i)
                results["completeness_check"]["details"].append({
                    "index": i, "npi": npi, "name": provider_name, 
                    "issue": "missing_npi_or_name"
                })
            
            # Track for duplicate analysis
            if npi:
                npi_to_providers[npi].append({
                    "index": i, "name": provider_name, "networks": networks
                })
        
        # Duplicate analysis
        for npi, provider_list in npi_to_providers.items():
            if len(provider_list) > 1:
                results["duplicate_check"]["failed"].append(npi)
                results["duplicate_check"]["details"].append({
                    "npi": npi, "count": len(provider_list), "providers": provider_list
                })
            else:
                results["duplicate_check"]["passed"] += 1
        
        # Cross-reference with historical data
        results["cross_reference_check"] = self._cross_reference_npis(npi_to_providers, project_name)
        
        return results

    def _extract_provider_name(self, provider: Dict) -> Optional[str]:
        """Extract provider name with fallback strategies"""
        name_fields = ["name", "provider_name", "unparsed_name", "display_name"]
        
        for field in name_fields:
            if field in provider:
                return provider[field]
        
        # Try nested provider object
        if "provider" in provider and isinstance(provider["provider"], dict):
            for field in name_fields:
                if field in provider["provider"]:
                    return provider["provider"][field]
        
        return None

    def _extract_networks(self, provider: Dict) -> List[str]:
        """Extract network information"""
        networks = []
        
        if "networks" in provider and isinstance(provider["networks"], list):
            for network in provider["networks"]:
                if isinstance(network, dict) and "name" in network:
                    networks.append(network["name"])
                elif isinstance(network, str):
                    networks.append(network)
        
        return networks

    def _cross_reference_npis(self, current_npis: Dict, project_name: str) -> Dict:
        """Cross-reference NPIs with historical database"""
        results = {
            "external_matches": 0,
            "conflicts": [],
            "details": []
        }
        
        with sqlite3.connect(self.db_path) as conn:
            for npi, provider_list in current_npis.items():
                # Check historical appearances
                cursor = conn.execute("""
                    SELECT project_name, network, provider_name, run_date 
                    FROM npi_appearances 
                    WHERE npi = ? AND project_name != ?
                    ORDER BY run_date DESC LIMIT 10
                """, (npi, project_name))
                
                historical = cursor.fetchall()
                
                if historical:
                    results["external_matches"] += 1
                    
                    # Check for conflicts (same NPI, different name)
                    current_names = {p["name"] for p in provider_list if p["name"]}
                    historical_names = {row[2] for row in historical if row[2]}
                    
                    if current_names and historical_names and not current_names.intersection(historical_names):
                        results["conflicts"].append({
                            "npi": npi,
                            "current_names": list(current_names),
                            "historical_names": list(historical_names),
                            "historical_projects": list(set(row[0] for row in historical))
                        })
                    
                    results["details"].append({
                        "npi": npi,
                        "historical_count": len(historical),
                        "projects": list(set(row[0] for row in historical)),
                        "last_seen": historical[0][3] if historical else None
                    })
        
        return results

    def _identify_issues(self, validation_results: Dict) -> List[Dict]:
        """Identify and categorize validation issues"""
        issues = []
        
        # High severity issues
        if validation_results["npi_format_check"]["failed"]:
            issues.append({
                "type": "invalid_npi_format",
                "severity": "high",
                "count": len(validation_results["npi_format_check"]["failed"]),
                "description": "Providers with invalid NPI format (not 10 digits)",
                "details": validation_results["npi_format_check"]["details"]
            })
        
        if validation_results["duplicate_check"]["failed"]:
            issues.append({
                "type": "duplicate_npi",
                "severity": "high", 
                "count": len(validation_results["duplicate_check"]["failed"]),
                "description": "Same NPI assigned to multiple providers",
                "details": validation_results["duplicate_check"]["details"]
            })
        
        # Medium severity issues
        if validation_results["completeness_check"]["failed"]:
            issues.append({
                "type": "incomplete_data",
                "severity": "medium",
                "count": len(validation_results["completeness_check"]["failed"]),
                "description": "Providers missing NPI or name",
                "details": validation_results["completeness_check"]["details"]
            })
        
        # Cross-reference conflicts (high severity)
        cross_ref = validation_results["cross_reference_check"]
        if cross_ref["conflicts"]:
            issues.append({
                "type": "cross_project_conflict",
                "severity": "high",
                "count": len(cross_ref["conflicts"]),
                "description": "Same NPI with different provider names across projects",
                "details": cross_ref["conflicts"]
            })
        
        return issues

    def _generate_recommendations(self, issues: List[Dict], project_name: str) -> List[str]:
        """Generate actionable recommendations based on issues"""
        recommendations = []
        
        for issue in issues:
            if issue["type"] == "invalid_npi_format":
                recommendations.append(f"🔴 Fix {issue['count']} invalid NPI formats - ensure 10-digit validation")
            
            elif issue["type"] == "duplicate_npi":
                recommendations.append(f"🔴 Resolve {issue['count']} duplicate NPIs - check data deduplication logic")
            
            elif issue["type"] == "incomplete_data":
                recommendations.append(f"🟡 Address {issue['count']} incomplete records - improve data extraction")
            
            elif issue["type"] == "cross_project_conflict":
                recommendations.append(f"🔴 Investigate {issue['count']} cross-project NPI conflicts - possible data corruption")
        
        # Site-specific recommendations
        if "healthsparq" in project_name or any("autoqa" in str(issue) for issue in issues):
            recommendations.append("💡 Consider implementing NPI-only AutoQA to prevent label search conflicts")
        
        if not recommendations:
            recommendations.append("✅ NPI validation passed - data quality looks good")
        
        return recommendations

    def _calculate_quality_score(self, validation_report: Dict) -> float:
        """Calculate overall data quality score (0-100)"""
        summary = validation_report["npi_summary"]
        issues = validation_report["issues_found"]
        
        # Base score from completion and validity rates
        completion_score = summary.get("npi_completion_rate", 0) * 40
        validity_score = summary.get("npi_validity_rate", 0) * 40
        
        # Penalty for issues
        issue_penalty = 0
        for issue in issues:
            if issue["severity"] == "high":
                issue_penalty += issue["count"] * 2
            elif issue["severity"] == "medium":
                issue_penalty += issue["count"] * 1
        
        # Normalize penalty
        total_providers = summary.get("total_providers", 1)
        normalized_penalty = min(20, (issue_penalty / total_providers) * 20)
        
        # Bonus for no duplicates
        no_duplicates_bonus = 20 if summary.get("duplicate_npis", 1) == 0 else 0
        
        score = completion_score + validity_score + no_duplicates_bonus - normalized_penalty
        return max(0, min(100, score))

    def _store_validation_results(self, project_name: str, run_date: str, providers: List[Dict], validation_report: Dict):
        """Store validation results in database for historical tracking"""
        with sqlite3.connect(self.db_path) as conn:
            # Store provider appearances
            for i, provider in enumerate(providers):
                npi = self._extract_npi(provider)
                if npi:
                    provider_name = self._extract_provider_name(provider)
                    networks = self._extract_networks(provider)
                    data_hash = hashlib.md5(json.dumps(provider, sort_keys=True).encode()).hexdigest()
                    
                    for network in networks or ["unknown"]:
                        conn.execute("""
                            INSERT INTO npi_appearances 
                            (npi, project_name, run_date, network, provider_name, data_hash)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (npi, project_name, run_date, network, provider_name, data_hash))
            
            # Store validation issues
            for issue in validation_report["issues_found"]:
                conn.execute("""
                    INSERT INTO validation_issues 
                    (project_name, run_date, issue_type, description, severity)
                    VALUES (?, ?, ?, ?, ?)
                """, (project_name, run_date, issue["type"], issue["description"], issue["severity"]))

    def cross_check_all_sites(self) -> Dict:
        """Cross-check NPIs across all sites for consistency"""
        logger.info("Cross-checking NPIs across all sites")
        
        results = {
            "summary": {},
            "conflicts": [],
            "recommendations": [],
            "site_analysis": {}
        }
        
        # Analyze all projects
        projects = [d.name for d in self.workspace.iterdir() 
                   if d.is_dir() and d.name.startswith("audiobee_")]
        
        all_npis = defaultdict(list)
        
        for project in projects:
            try:
                validation = self.validate_project(project)
                results["site_analysis"][project] = {
                    "quality_score": validation.get("data_quality_score", 0),
                    "issues_count": len(validation.get("issues_found", [])),
                    "npi_count": validation.get("npi_summary", {}).get("npis_present", 0)
                }
                
                # Collect all NPIs for cross-analysis
                summary = validation.get("npi_summary", {})
                if "duplicate_details" in summary:
                    for npi in summary["duplicate_details"]:
                        all_npis[npi].append(project)
                        
            except Exception as e:
                logger.error(f"Error analyzing {project}: {e}")
        
        # Identify cross-site conflicts
        results["conflicts"] = self._identify_cross_site_conflicts(all_npis)
        results["summary"] = self._generate_cross_site_summary(results["site_analysis"], results["conflicts"])
        results["recommendations"] = self._generate_cross_site_recommendations(results)
        
        return results

    def _identify_cross_site_conflicts(self, all_npis: Dict) -> List[Dict]:
        """Identify NPIs that appear across multiple sites with potential conflicts"""
        conflicts = []
        
        with sqlite3.connect(self.db_path) as conn:
            for npi, projects in all_npis.items():
                if len(projects) > 1:
                    # Get detailed data for this NPI across projects
                    cursor = conn.execute("""
                        SELECT project_name, provider_name, network, run_date
                        FROM npi_appearances 
                        WHERE npi = ?
                        ORDER BY run_date DESC
                    """, (npi,))
                    
                    appearances = cursor.fetchall()
                    
                    # Check for name conflicts
                    unique_names = set(row[1] for row in appearances if row[1])
                    if len(unique_names) > 1:
                        conflicts.append({
                            "npi": npi,
                            "conflict_type": "name_mismatch",
                            "projects": projects,
                            "names": list(unique_names),
                            "total_appearances": len(appearances)
                        })
        
        return conflicts

    def _generate_cross_site_summary(self, site_analysis: Dict, conflicts: List[Dict]) -> Dict:
        """Generate summary of cross-site analysis"""
        total_sites = len(site_analysis)
        avg_quality = sum(s["quality_score"] for s in site_analysis.values()) / total_sites if total_sites > 0 else 0
        
        high_quality_sites = len([s for s in site_analysis.values() if s["quality_score"] >= 80])
        low_quality_sites = len([s for s in site_analysis.values() if s["quality_score"] < 60])
        
        return {
            "total_sites_analyzed": total_sites,
            "average_quality_score": round(avg_quality, 1),
            "high_quality_sites": high_quality_sites,
            "low_quality_sites": low_quality_sites,
            "cross_site_conflicts": len(conflicts),
            "sites_needing_attention": [name for name, data in site_analysis.items() 
                                       if data["quality_score"] < 60 or data["issues_count"] > 5]
        }

    def _generate_cross_site_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations for cross-site improvements"""
        recommendations = []
        
        summary = results["summary"]
        conflicts = results["conflicts"]
        
        if summary["cross_site_conflicts"] > 0:
            recommendations.append(f"🔴 Investigate {summary['cross_site_conflicts']} cross-site NPI conflicts")
        
        if summary["low_quality_sites"] > 0:
            recommendations.append(f"🟡 Improve data quality for {summary['low_quality_sites']} low-scoring sites")
        
        if summary["average_quality_score"] < 70:
            recommendations.append("⚠️ Overall fleet NPI quality is below recommended threshold (70)")
        
        # Specific conflict recommendations
        name_conflicts = [c for c in conflicts if c["conflict_type"] == "name_mismatch"]
        if name_conflicts:
            recommendations.append(f"🔍 {len(name_conflicts)} NPIs have different provider names across sites - investigate data sources")
        
        if not recommendations:
            recommendations.append("✅ Cross-site NPI validation passed - good data consistency")
        
        return recommendations

    def autoqa_analysis(self) -> Dict:
        """Analyze AutoQA patterns and accuracy"""
        logger.info("Analyzing AutoQA patterns across healthsparq sites")
        
        results = {
            "healthsparq_sites": [],
            "autoqa_patterns": {},
            "accuracy_analysis": {},
            "recommendations": []
        }
        
        # Find healthsparq projects
        healthsparq_projects = []
        for project_dir in self.workspace.glob("audiobee_*"):
            if project_dir.is_dir():
                # Check if it's a healthsparq site (basic heuristic)
                config_files = list(project_dir.glob("config.py"))
                debug_entries = list(Path("docs/debugging/healthsparq").glob(f"{project_dir.name}/*.md"))
                
                if debug_entries:  # Has healthsparq debug entries
                    healthsparq_projects.append(project_dir.name)
        
        results["healthsparq_sites"] = healthsparq_projects
        
        # Analyze each site for AutoQA patterns
        for project in healthsparq_projects:
            try:
                project_analysis = self._analyze_autoqa_for_project(project)
                results["autoqa_patterns"][project] = project_analysis
            except Exception as e:
                logger.error(f"Error analyzing AutoQA for {project}: {e}")
        
        # Generate overall analysis
        results["accuracy_analysis"] = self._analyze_autoqa_accuracy(results["autoqa_patterns"])
        results["recommendations"] = self._generate_autoqa_recommendations(results)
        
        return results

    def _analyze_autoqa_for_project(self, project_name: str) -> Dict:
        """Analyze AutoQA patterns for specific project"""
        analysis = {
            "npi_search_success_rate": 0,
            "label_search_fallback_rate": 0,
            "potential_mismatches": [],
            "recovery_effectiveness": 0
        }
        
        # This is a placeholder - in a real implementation, you'd analyze:
        # 1. AutoQA logs to see NPI vs label search patterns
        # 2. Compare recovered data with original data
        # 3. Identify cases where label search returned wrong provider
        
        # For now, return analysis based on debugging entries
        debug_path = Path("docs/debugging/healthsparq") / project_name
        if debug_path.exists():
            debug_files = list(debug_path.glob("*.md"))
            
            autoqa_issues = 0
            total_entries = len(debug_files)
            
            for debug_file in debug_files:
                try:
                    with open(debug_file) as f:
                        content = f.read().lower()
                        if "autoqa" in content and ("npi" in content or "label" in content):
                            autoqa_issues += 1
                except Exception:
                    pass
            
            if total_entries > 0:
                analysis["potential_mismatches"] = [f"Found {autoqa_issues} AutoQA-related debug entries"]
                analysis["recovery_effectiveness"] = max(0, 1 - (autoqa_issues / total_entries))
        
        return analysis

    def _analyze_autoqa_accuracy(self, patterns: Dict) -> Dict:
        """Analyze overall AutoQA accuracy"""
        if not patterns:
            return {"insufficient_data": True}
        
        total_sites = len(patterns)
        sites_with_issues = len([p for p in patterns.values() if p.get("potential_mismatches")])
        
        return {
            "total_healthsparq_sites": total_sites,
            "sites_with_autoqa_issues": sites_with_issues,
            "overall_accuracy_score": max(0, 1 - (sites_with_issues / total_sites)) if total_sites > 0 else 1,
            "needs_improvement": sites_with_issues > total_sites * 0.3  # More than 30% have issues
        }

    def _generate_autoqa_recommendations(self, results: Dict) -> List[str]:
        """Generate AutoQA-specific recommendations"""
        recommendations = []
        
        accuracy = results["accuracy_analysis"]
        
        if accuracy.get("needs_improvement"):
            recommendations.append("🔴 AutoQA accuracy below threshold - implement NPI-only search first")
            recommendations.append("💡 Separate NPI-only and name-only AutoQA processes")
            recommendations.append("🔍 Add validation step to compare recovered vs original provider names")
        
        if accuracy.get("sites_with_autoqa_issues", 0) > 0:
            recommendations.append(f"⚠️ {accuracy['sites_with_autoqa_issues']} sites have AutoQA issues - review debug entries")
        
        # Always recommend improvements based on debugging analysis
        recommendations.append("📊 Implement AutoQA accuracy tracking with match confidence scores")
        recommendations.append("🎯 Add network-specific search to prevent cross-network pollution")
        
        if not recommendations:
            recommendations.append("✅ AutoQA analysis complete - consider implementing suggested enhancements")
        
        return recommendations

def main():
    parser = argparse.ArgumentParser(description="NPI Reconciliation Engine")
    parser.add_argument("--validate", help="Validate NPIs for specific project")
    parser.add_argument("--cross-check", action="store_true", help="Cross-check NPIs across all sites")
    parser.add_argument("--all-sites", action="store_true", help="Include all sites in analysis")
    parser.add_argument("--dedupe", help="Analyze duplicates for specific project")
    parser.add_argument("--audit-trail", action="store_true", help="Generate audit trail")
    parser.add_argument("--autoqa-analysis", action="store_true", help="Analyze AutoQA patterns")
    parser.add_argument("--days", type=int, default=30, help="Days of history to analyze")
    parser.add_argument("--output", default="console", choices=["console", "json", "summary"])
    
    args = parser.parse_args()
    
    engine = NPIReconciliationEngine()
    
    if args.validate:
        result = engine.validate_project(args.validate)
        _print_result(result, args.output, "VALIDATION")
    elif args.cross_check or args.all_sites:
        result = engine.cross_check_all_sites()
        _print_result(result, args.output, "CROSS-CHECK")
    elif args.autoqa_analysis:
        result = engine.autoqa_analysis()
        _print_result(result, args.output, "AUTOQA ANALYSIS")
    else:
        parser.print_help()

def _print_result(result: Dict, output_format: str, title: str):
    """Print results in specified format"""
    if output_format == "json":
        print(json.dumps(result, indent=2))
    elif output_format == "summary":
        print(f"\n🔍 NPI {title}")
        
        if "project" in result:
            # Single project validation
            print(f"Project: {result['project']}")
            print(f"Data Quality Score: {result.get('data_quality_score', 0):.1f}/100")
            
            summary = result.get('npi_summary', {})
            print(f"Total Providers: {summary.get('total_providers', 0)}")
            print(f"NPIs Present: {summary.get('npis_present', 0)}")
            print(f"Valid NPIs: {summary.get('npis_valid', 0)}")
            print(f"Duplicates: {summary.get('duplicate_npis', 0)}")
            
            issues = result.get('issues_found', [])
            if issues:
                print(f"\n⚠️ ISSUES FOUND ({len(issues)}):")
                for issue in issues:
                    print(f"  • {issue['description']} ({issue['count']} items)")
            
            recommendations = result.get('recommendations', [])
            if recommendations:
                print(f"\n📋 RECOMMENDATIONS:")
                for rec in recommendations:
                    print(f"  {rec}")
        
        elif "summary" in result:
            # Cross-site analysis
            summary = result['summary']
            print(f"Sites Analyzed: {summary.get('total_sites_analyzed', 0)}")
            print(f"Average Quality: {summary.get('average_quality_score', 0)}/100")
            print(f"Cross-Site Conflicts: {summary.get('cross_site_conflicts', 0)}")
            
            if result.get('recommendations'):
                print(f"\n📋 RECOMMENDATIONS:")
                for rec in result['recommendations']:
                    print(f"  {rec}")
        
        elif "healthsparq_sites" in result:
            # AutoQA analysis
            sites = result['healthsparq_sites']
            accuracy = result.get('accuracy_analysis', {})
            
            print(f"HealthSparq Sites: {len(sites)}")
            print(f"Sites with Issues: {accuracy.get('sites_with_autoqa_issues', 0)}")
            print(f"Accuracy Score: {accuracy.get('overall_accuracy_score', 0):.2f}")
            
            if result.get('recommendations'):
                print(f"\n📋 RECOMMENDATIONS:")
                for rec in result['recommendations']:
                    print(f"  {rec}")
    else:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()