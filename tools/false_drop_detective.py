#!/usr/bin/env python3
"""
False Drop Detective - AI-Powered False Drop Prevention & Analysis

WHAT IT SOLVES:
False drops are the #1 issue across all scraper types. This tool:
- Predicts false drops before they happen
- Analyzes patterns across historical runs  
- Provides actionable insights to prevent recurrence
- Monitors in real-time during scraper runs

NEVER RUNS SCRAPERS - Only analyzes existing data for safety.

Usage:
    python tools/false_drop_detective.py --analyze audiobee_bcbs_il
    python tools/false_drop_detective.py --predict --all-projects
    python tools/false_drop_detective.py --monitor --real-time
    python tools/false_drop_detective.py --pattern-analysis --days 30
"""

import argparse
import json
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
import re
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FalseDropDetective:
    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.db_path = self.workspace / "tools" / "false_drop_analysis.db"
        self.init_database()
        
        # False drop patterns learned from debugging entries
        self.drop_indicators = [
            "geo_location",
            "radius", 
            "network_id",
            "empty data",
            "no results",
            "timeout",
            "403",
            "blocked",
            "rate limit"
        ]
        
        # Site-specific patterns from debugging analysis
        self.site_patterns = {
            "sapphire": ["geo_location", "radius", "network_id conflicts"],
            "healthsparq": ["npi vs label search", "network mapping", "autoqa"],
            "carrier": ["algolia search", "pagination", "request blocking"]
        }

    def init_database(self):
        """Initialize SQLite database for tracking patterns"""
        os.makedirs(self.db_path.parent, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS drop_incidents (
                    id INTEGER PRIMARY KEY,
                    project_name TEXT,
                    site_type TEXT,
                    date TEXT,
                    error_type TEXT,
                    root_cause TEXT,
                    fix_applied TEXT,
                    pattern_hash TEXT,
                    provider_count_expected INTEGER,
                    provider_count_actual INTEGER,
                    drop_percentage REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_library (
                    id INTEGER PRIMARY KEY,
                    pattern_name TEXT,
                    pattern_type TEXT,
                    site_type TEXT,
                    indicators TEXT,
                    prevention_strategy TEXT,
                    confidence_score REAL,
                    occurrences INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS live_monitoring (
                    id INTEGER PRIMARY KEY,
                    project_name TEXT,
                    phase TEXT,
                    status TEXT,
                    provider_count INTEGER,
                    warning_flags TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def analyze_project(self, project_name: str) -> Dict:
        """Deep analysis of a project's false drop patterns"""
        logger.info(f"Analyzing false drop patterns for {project_name}")
        
        project_path = self.workspace / project_name
        if not project_path.exists():
            logger.error(f"Project not found: {project_name}")
            return {"error": "Project not found"}
        
        # Analyze recent runs
        analysis = {
            "project": project_name,
            "risk_level": "unknown",
            "patterns_detected": [],
            "recommendations": [],
            "historical_drops": [],
            "prediction": {}
        }
        
        # Get recent run dates
        run_dates = self._get_recent_dates(project_path)
        
        for date in run_dates:
            run_analysis = self._analyze_single_run(project_path, date)
            if run_analysis.get("has_drops"):
                analysis["historical_drops"].append(run_analysis)
        
        # Pattern detection
        analysis["patterns_detected"] = self._detect_patterns(analysis["historical_drops"])
        
        # Risk assessment
        analysis["risk_level"] = self._assess_risk(analysis["patterns_detected"], analysis["historical_drops"])
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(
            project_name, analysis["patterns_detected"], analysis["risk_level"]
        )
        
        # Predictive analysis
        analysis["prediction"] = self._predict_next_run_risk(analysis["historical_drops"])
        
        return analysis

    def _get_recent_dates(self, project_path: Path, days: int = 30) -> List[str]:
        """Get recent run dates for analysis"""
        dates = []
        for item in project_path.iterdir():
            if item.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', item.name):
                try:
                    run_date = datetime.strptime(item.name, '%Y-%m-%d')
                    if (datetime.now() - run_date).days <= days:
                        dates.append(item.name)
                except ValueError:
                    continue
        return sorted(dates, reverse=True)

    def _analyze_single_run(self, project_path: Path, date: str) -> Dict:
        """Analyze a single run for false drop indicators"""
        run_path = project_path / date
        
        analysis = {
            "date": date,
            "has_drops": False,
            "drop_indicators": [],
            "provider_counts": {},
            "error_patterns": []
        }
        
        # Check processed output
        processed_path = run_path / "processed"
        if processed_path.exists():
            for file in processed_path.glob("*.jsonl"):
                count = self._count_jsonl_lines(file)
                analysis["provider_counts"][file.stem] = count
        
        # Check for error logs
        log_files = list(run_path.glob("**/*.log"))
        for log_file in log_files:
            errors = self._scan_log_for_errors(log_file)
            analysis["error_patterns"].extend(errors)
        
        # Check debugging entries
        debug_entry = self._find_debug_entry(project_path.name, date)
        if debug_entry:
            analysis["has_drops"] = True
            analysis["drop_indicators"].append("manual_debug_entry")
            analysis["debug_info"] = debug_entry
        
        return analysis

    def _count_jsonl_lines(self, file_path: Path) -> int:
        """Count lines in JSONL file"""
        try:
            with open(file_path) as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def _scan_log_for_errors(self, log_path: Path) -> List[str]:
        """Scan log file for false drop indicators"""
        indicators = []
        try:
            with open(log_path) as f:
                content = f.read().lower()
                for indicator in self.drop_indicators:
                    if indicator in content:
                        indicators.append(indicator)
        except Exception:
            pass
        return indicators

    def _find_debug_entry(self, project_name: str, date: str) -> Optional[Dict]:
        """Find corresponding debugging entry"""
        debug_path = self.workspace / "docs" / "debugging"
        
        # Search all site types
        for site_type in ["carrier", "healthsparq", "sapphire"]:
            entry_path = debug_path / site_type / project_name / f"{date}.md"
            if entry_path.exists():
                try:
                    with open(entry_path) as f:
                        content = f.read()
                        return {"content": content, "site_type": site_type}
                except Exception:
                    pass
        return None

    def _detect_patterns(self, historical_drops: List[Dict]) -> List[Dict]:
        """Detect recurring patterns in false drops"""
        patterns = []
        
        # Group by error indicators
        indicator_freq = {}
        for drop in historical_drops:
            for indicator in drop.get("drop_indicators", []):
                indicator_freq[indicator] = indicator_freq.get(indicator, 0) + 1
        
        # Identify significant patterns (>= 2 occurrences)
        for indicator, count in indicator_freq.items():
            if count >= 2:
                patterns.append({
                    "pattern": indicator,
                    "frequency": count,
                    "confidence": min(count * 0.3, 1.0),
                    "type": "recurring_error"
                })
        
        return patterns

    def _assess_risk(self, patterns: List[Dict], historical_drops: List[Dict]) -> str:
        """Assess risk level for next run"""
        if not historical_drops:
            return "low"
        
        recent_drops = len([d for d in historical_drops if d.get("has_drops")])
        
        if recent_drops >= 3:
            return "high"
        elif recent_drops >= 1 or patterns:
            return "medium" 
        else:
            return "low"

    def _generate_recommendations(self, project: str, patterns: List[Dict], risk: str) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if risk == "high":
            recommendations.append("🚨 HIGH RISK: Review project configuration before next run")
        
        for pattern in patterns:
            indicator = pattern["pattern"]
            
            if indicator == "geo_location":
                recommendations.append("Remove geo_location parameter from API calls - causes false empty responses")
            elif indicator == "radius":
                recommendations.append("Remove or increase radius parameter - small radius causes data loss")
            elif indicator == "network_id":
                recommendations.append("Verify network ID mapping - wrong network causes provider drops")
            elif indicator == "npi vs label search":
                recommendations.append("Separate NPI-only and name-only AutoQA to prevent wrong mappings")
            elif indicator == "manual_debug_entry":
                recommendations.append("Review recent debugging entry for specific fixes")
        
        if not recommendations:
            recommendations.append("✅ No major drop patterns detected - monitor during next run")
        
        return recommendations

    def _predict_next_run_risk(self, historical_drops: List[Dict]) -> Dict:
        """Predict risk for next scraper run"""
        if not historical_drops:
            return {"risk_score": 0.1, "confidence": "low", "reasoning": "No historical data"}
        
        # Calculate trend
        recent_drop_rate = len([d for d in historical_drops[:5] if d.get("has_drops")]) / min(5, len(historical_drops))
        
        risk_score = recent_drop_rate * 0.7 + (len(historical_drops) > 3) * 0.3
        
        confidence = "high" if len(historical_drops) >= 5 else "medium" if len(historical_drops) >= 2 else "low"
        
        return {
            "risk_score": round(risk_score, 2),
            "confidence": confidence,
            "reasoning": f"Based on {len(historical_drops)} recent runs with {int(recent_drop_rate*100)}% drop rate"
        }

    def analyze_all_projects(self) -> Dict[str, Dict]:
        """Analyze false drop patterns across all projects"""
        logger.info("Analyzing false drop patterns for all projects")
        
        results = {}
        projects = []
        
        # Find all audiobee projects
        for item in self.workspace.iterdir():
            if item.is_dir() and item.name.startswith("audiobee_"):
                projects.append(item.name)
        
        for project in sorted(projects):
            results[project] = self.analyze_project(project)
        
        # Generate summary
        summary = self._generate_fleet_summary(results)
        results["_summary"] = summary
        
        return results

    def _generate_fleet_summary(self, results: Dict[str, Dict]) -> Dict:
        """Generate fleet-wide summary"""
        total_projects = len([k for k in results.keys() if not k.startswith("_")])
        high_risk = len([r for r in results.values() if r.get("risk_level") == "high"])
        medium_risk = len([r for r in results.values() if r.get("risk_level") == "medium"])
        
        # Most common patterns
        all_patterns = []
        for result in results.values():
            if isinstance(result, dict) and "patterns_detected" in result:
                all_patterns.extend([p["pattern"] for p in result["patterns_detected"]])
        
        pattern_freq = {}
        for pattern in all_patterns:
            pattern_freq[pattern] = pattern_freq.get(pattern, 0) + 1
        
        top_patterns = sorted(pattern_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_projects": total_projects,
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "low_risk_count": total_projects - high_risk - medium_risk,
            "top_patterns": top_patterns,
            "fleet_risk_score": (high_risk * 1.0 + medium_risk * 0.5) / max(total_projects, 1)
        }

    def real_time_monitor(self) -> None:
        """Real-time monitoring of running scrapers"""
        logger.info("Starting real-time false drop monitoring...")
        logger.info("This monitors existing data - does not run scrapers")
        
        # Monitor mode - check for running processes and analyze outputs
        while True:
            try:
                # Check all projects for new data
                for project_dir in self.workspace.glob("audiobee_*"):
                    if project_dir.is_dir():
                        self._check_project_activity(project_dir.name)
                
                # Sleep for monitoring interval
                import time
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                import time
                time.sleep(30)

    def _check_project_activity(self, project_name: str) -> None:
        """Check for recent activity in project"""
        project_path = self.workspace / project_name
        
        # Check for recent date directories
        today = datetime.now().strftime("%Y-%m-%d")
        today_path = project_path / today
        
        if today_path.exists():
            # Check for signs of active processing
            recent_files = []
            for file_path in today_path.rglob("*"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if (datetime.now() - mtime).seconds < 300:  # Modified in last 5 minutes
                        recent_files.append(file_path)
            
            if recent_files:
                logger.info(f"🔍 Active processing detected in {project_name}")
                
                # Quick analysis for warning signs
                warnings = self._quick_warning_check(today_path)
                if warnings:
                    logger.warning(f"⚠️ Potential issues in {project_name}: {', '.join(warnings)}")

    def _quick_warning_check(self, run_path: Path) -> List[str]:
        """Quick check for warning signs in active run"""
        warnings = []
        
        # Check log files for error patterns
        for log_file in run_path.glob("**/*.log"):
            try:
                # Only check recent log entries (last 1KB)
                with open(log_file, 'rb') as f:
                    f.seek(max(0, f.seek(0, 2) - 1024))  # Seek to last 1KB
                    recent_content = f.read().decode('utf-8', errors='ignore').lower()
                    
                    for indicator in self.drop_indicators:
                        if indicator in recent_content:
                            warnings.append(f"detected_{indicator}")
            except Exception:
                pass
        
        return warnings

def main():
    parser = argparse.ArgumentParser(description="False Drop Detective - Prevent & Analyze False Drops")
    parser.add_argument("--analyze", help="Analyze specific project")
    parser.add_argument("--predict", action="store_true", help="Predict false drop risks")
    parser.add_argument("--all-projects", action="store_true", help="Analyze all projects")
    parser.add_argument("--monitor", action="store_true", help="Real-time monitoring mode")
    parser.add_argument("--pattern-analysis", action="store_true", help="Deep pattern analysis")
    parser.add_argument("--days", type=int, default=30, help="Days of history to analyze")
    parser.add_argument("--output", default="console", choices=["console", "json", "summary"])
    
    args = parser.parse_args()
    
    detective = FalseDropDetective()
    
    if args.monitor:
        detective.real_time_monitor()
    elif args.analyze:
        result = detective.analyze_project(args.analyze)
        _print_analysis_result(result, args.output)
    elif args.all_projects or args.predict:
        results = detective.analyze_all_projects()
        _print_fleet_results(results, args.output)
    else:
        parser.print_help()

def _print_analysis_result(result: Dict, output_format: str):
    """Print analysis result in specified format"""
    if output_format == "json":
        print(json.dumps(result, indent=2))
    elif output_format == "summary":
        print(f"\n🔍 FALSE DROP ANALYSIS: {result.get('project', 'Unknown')}")
        print(f"Risk Level: {result.get('risk_level', 'Unknown').upper()}")
        print(f"Patterns Detected: {len(result.get('patterns_detected', []))}")
        
        if result.get('recommendations'):
            print("\n📋 RECOMMENDATIONS:")
            for rec in result['recommendations']:
                print(f"  • {rec}")
        
        prediction = result.get('prediction', {})
        if prediction:
            print(f"\n🎯 NEXT RUN PREDICTION:")
            print(f"  Risk Score: {prediction.get('risk_score', 0)}")
            print(f"  Confidence: {prediction.get('confidence', 'Unknown')}")
            print(f"  Reasoning: {prediction.get('reasoning', 'N/A')}")
    else:
        # Console format
        print(json.dumps(result, indent=2))

def _print_fleet_results(results: Dict[str, Dict], output_format: str):
    """Print fleet analysis results"""
    summary = results.get("_summary", {})
    
    if output_format == "summary":
        print(f"\n🚨 FLEET FALSE DROP ANALYSIS")
        print(f"Total Projects: {summary.get('total_projects', 0)}")
        print(f"High Risk: {summary.get('high_risk_count', 0)} 🔴")
        print(f"Medium Risk: {summary.get('medium_risk_count', 0)} 🟡")
        print(f"Low Risk: {summary.get('low_risk_count', 0)} 🟢")
        print(f"Fleet Risk Score: {summary.get('fleet_risk_score', 0):.2f}")
        
        if summary.get('top_patterns'):
            print(f"\n📊 TOP RISK PATTERNS:")
            for pattern, count in summary['top_patterns']:
                print(f"  • {pattern}: {count} projects")
        
        # Show high-risk projects
        high_risk_projects = [name for name, data in results.items() 
                            if not name.startswith("_") and data.get('risk_level') == 'high']
        if high_risk_projects:
            print(f"\n🚨 HIGH RISK PROJECTS:")
            for project in high_risk_projects:
                print(f"  • {project}")
    else:
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()