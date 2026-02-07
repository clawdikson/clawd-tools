#!/usr/bin/env python3
"""
Scraper Pulse Monitor - Real-time Fleet Monitoring Dashboard

WHAT IT SOLVES:
- No real-time visibility into 95+ scrapers during runs
- Manual monitoring overhead
- Late detection of stalled or failing scrapers
- No centralized view of fleet progress

Creates a live, lightweight dashboard showing:
- All scrapers status and progress in real-time
- Early warning system for stuck processes
- Performance metrics and ETA predictions
- Resource usage monitoring

NEVER RUNS SCRAPERS - Only monitors existing processes and files.

Usage:
    python tools/scraper_pulse_monitor.py --dashboard
    python tools/scraper_pulse_monitor.py --check-all
    python tools/scraper_pulse_monitor.py --alert-thresholds
    python tools/scraper_pulse_monitor.py --export-metrics
"""

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
import sqlite3
import re
import signal
import sys
from collections import defaultdict
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScraperPulseMonitor:
    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.db_path = self.workspace / "tools" / "scraper_pulse.db"
        self.running = True
        self.init_database()
        
        # Monitoring thresholds
        self.thresholds = {
            "stall_minutes": 15,  # No new files in 15 minutes = stalled
            "slow_progress": 0.1,  # Less than 10% progress per hour = slow
            "high_memory_mb": 1024,  # >1GB memory usage = high
            "high_cpu_percent": 80,  # >80% CPU = high
            "eta_warning_hours": 8,  # ETA >8 hours = warning
        }
        
        # Process patterns
        self.scraper_patterns = [
            "python.*run_all.py",
            "python.*main.py", 
            "python.*-m.*healthsparq",
            "python.*-m.*sapphire"
        ]

    def init_database(self):
        """Initialize monitoring database"""
        os.makedirs(self.db_path.parent, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Scraper status tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scraper_status (
                    project_name TEXT PRIMARY KEY,
                    status TEXT,
                    phase TEXT,
                    progress_percent REAL,
                    providers_count INTEGER,
                    start_time TIMESTAMP,
                    last_activity TIMESTAMP,
                    estimated_completion TIMESTAMP,
                    pid INTEGER,
                    memory_mb REAL,
                    cpu_percent REAL,
                    warnings TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance metrics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY,
                    project_name TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Alert history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY,
                    project_name TEXT,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def start_monitoring(self, dashboard_mode: bool = False):
        """Start real-time monitoring"""
        logger.info("Starting Scraper Pulse Monitor...")
        
        if dashboard_mode:
            self._start_dashboard()
        else:
            self._start_background_monitoring()

    def _start_dashboard(self):
        """Start interactive dashboard"""
        print("\n" + "="*80)
        print("🚀 SCRAPER PULSE MONITOR - Real-time Fleet Dashboard")
        print("="*80)
        print("Press Ctrl+C to exit")
        print()
        
        # Handle graceful shutdown
        def signal_handler(signum, frame):
            self.running = False
            print("\n\n👋 Shutting down monitor...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        while self.running:
            try:
                # Clear screen (works on most terminals)
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Get current status
                status = self.check_all_scrapers()
                
                # Display dashboard
                self._display_dashboard(status)
                
                # Wait before refresh
                time.sleep(10)  # Refresh every 10 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
                time.sleep(5)

    def _display_dashboard(self, status: Dict):
        """Display live dashboard"""
        print(f"🕒 Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Fleet summary
        summary = status.get("summary", {})
        print("📊 FLEET SUMMARY")
        print(f"Total Projects: {summary.get('total', 0)}")
        print(f"🟢 Running: {summary.get('running', 0)}  "
              f"🟡 Warning: {summary.get('warning', 0)}  "
              f"🔴 Error: {summary.get('error', 0)}  "
              f"⚪ Idle: {summary.get('idle', 0)}")
        print()
        
        # Active scrapers
        active_scrapers = [s for s in status.get("scrapers", []) if s.get("status") != "idle"]
        
        if active_scrapers:
            print("🔥 ACTIVE SCRAPERS")
            print(f"{'Project':<30} {'Status':<12} {'Phase':<15} {'Progress':<10} {'ETA':<12} {'Alerts':<15}")
            print("-" * 110)
            
            for scraper in sorted(active_scrapers, key=lambda x: x.get("progress_percent", 0), reverse=True):
                name = scraper["name"][:28]
                status_icon = self._get_status_icon(scraper["status"])
                phase = scraper.get("phase", "unknown")[:13]
                progress = f"{scraper.get('progress_percent', 0):.1f}%"
                eta = self._format_eta(scraper.get("estimated_completion"))
                warnings = len(scraper.get("warnings", []))
                alert_text = f"{warnings} alerts" if warnings > 0 else ""
                
                print(f"{name:<30} {status_icon:<12} {phase:<15} {progress:<10} {eta:<12} {alert_text:<15}")
        else:
            print("😴 No active scrapers detected")
        
        print()
        
        # Recent alerts
        recent_alerts = status.get("recent_alerts", [])
        if recent_alerts:
            print("⚠️  RECENT ALERTS (Last 10)")
            for alert in recent_alerts[:10]:
                timestamp = alert.get("created_at", "")[:16]  # YYYY-MM-DD HH:MM
                severity_icon = "🔴" if alert.get("severity") == "high" else "🟡"
                project = alert.get("project_name", "")[:20]
                message = alert.get("message", "")[:50]
                print(f"  {severity_icon} [{timestamp}] {project}: {message}")
        
        print("\n" + "="*80)
        print("🔄 Refreshing in 10 seconds... (Ctrl+C to exit)")

    def _get_status_icon(self, status: str) -> str:
        """Get status icon for display"""
        icons = {
            "running": "🟢 Running",
            "warning": "🟡 Warning", 
            "error": "🔴 Error",
            "stalled": "🟠 Stalled",
            "idle": "⚪ Idle"
        }
        return icons.get(status, "❓ Unknown")

    def _format_eta(self, eta_timestamp: Optional[str]) -> str:
        """Format ETA for display"""
        if not eta_timestamp:
            return "Unknown"
        
        try:
            eta = datetime.fromisoformat(eta_timestamp.replace('Z', '+00:00'))
            now = datetime.now().replace(tzinfo=eta.tzinfo) if eta.tzinfo else datetime.now()
            delta = eta - now
            
            if delta.total_seconds() < 0:
                return "Overdue"
            elif delta.total_seconds() < 3600:  # Less than 1 hour
                return f"{int(delta.total_seconds() / 60)}m"
            elif delta.total_seconds() < 86400:  # Less than 1 day
                return f"{delta.total_seconds() / 3600:.1f}h"
            else:
                return f"{delta.days}d"
        except Exception:
            return "Unknown"

    def check_all_scrapers(self) -> Dict:
        """Check status of all scrapers"""
        scrapers = []
        summary = {"total": 0, "running": 0, "warning": 0, "error": 0, "idle": 0}
        
        # Find all audiobee projects
        projects = [d.name for d in self.workspace.iterdir() 
                   if d.is_dir() and d.name.startswith("audiobee_")]
        
        for project in projects:
            try:
                scraper_status = self._check_project_status(project)
                scrapers.append(scraper_status)
                
                status = scraper_status.get("status", "idle")
                summary["total"] += 1
                summary[status] = summary.get(status, 0) + 1
                
                # Store in database
                self._update_scraper_status(scraper_status)
                
            except Exception as e:
                logger.error(f"Error checking {project}: {e}")
        
        # Get recent alerts
        recent_alerts = self._get_recent_alerts()
        
        return {
            "scrapers": scrapers,
            "summary": summary,
            "recent_alerts": recent_alerts,
            "timestamp": datetime.now().isoformat()
        }

    def _check_project_status(self, project_name: str) -> Dict:
        """Check status of individual project"""
        project_path = self.workspace / project_name
        
        status = {
            "name": project_name,
            "status": "idle",
            "phase": "unknown",
            "progress_percent": 0.0,
            "providers_count": 0,
            "start_time": None,
            "last_activity": None,
            "estimated_completion": None,
            "pid": None,
            "memory_mb": 0.0,
            "cpu_percent": 0.0,
            "warnings": []
        }
        
        # Check for running processes
        process_info = self._find_scraper_process(project_name)
        if process_info:
            status.update(process_info)
            status["status"] = "running"
        
        # Check for recent activity (files modified recently)
        activity_info = self._check_recent_activity(project_path)
        if activity_info:
            status.update(activity_info)
            
            # Determine status based on activity
            if not process_info and activity_info.get("last_activity"):
                # No process but recent activity - might be batch job
                last_activity = datetime.fromisoformat(activity_info["last_activity"])
                if (datetime.now() - last_activity).seconds < 300:  # Active in last 5 minutes
                    status["status"] = "running"
                elif (datetime.now() - last_activity).seconds < self.thresholds["stall_minutes"] * 60:
                    status["status"] = "warning"
                else:
                    status["status"] = "stalled"
        
        # Check for warning conditions
        warnings = self._check_warnings(status, project_path)
        status["warnings"] = warnings
        
        if warnings and status["status"] == "running":
            status["status"] = "warning"
        
        return status

    def _find_scraper_process(self, project_name: str) -> Optional[Dict]:
        """Find running scraper process for project using ps command"""
        try:
            # Use ps to find processes (works on most Unix systems)
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            
            for line in result.stdout.split('\n'):
                if project_name in line and any(pattern.replace('python.*', 'python') in line for pattern in self.scraper_patterns):
                    # Parse ps output (simplified)
                    parts = line.split()
                    if len(parts) >= 11:
                        pid = parts[1]
                        memory_mb = float(parts[5]) / 1024  # Convert KB to MB
                        cpu_percent = float(parts[2])
                        
                        return {
                            "pid": int(pid),
                            "memory_mb": memory_mb,
                            "cpu_percent": cpu_percent,
                            "start_time": datetime.now().isoformat()  # Simplified - actual start time would need more parsing
                        }
        except Exception as e:
            logger.debug(f"Error finding processes: {e}")
        
        return None

    def _check_recent_activity(self, project_path: Path) -> Dict:
        """Check for recent file activity in project"""
        activity = {
            "last_activity": None,
            "phase": "unknown",
            "progress_percent": 0.0,
            "providers_count": 0
        }
        
        # Look for today's run directory
        today = datetime.now().strftime("%Y-%m-%d")
        today_path = project_path / today
        
        if not today_path.exists():
            return activity
        
        # Find most recently modified file
        most_recent = None
        most_recent_time = None
        
        for file_path in today_path.rglob("*"):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if not most_recent_time or mtime > most_recent_time:
                    most_recent = file_path
                    most_recent_time = mtime
        
        if most_recent_time:
            activity["last_activity"] = most_recent_time.isoformat()
            
            # Determine phase from file location
            rel_path = most_recent.relative_to(today_path)
            if "search_results" in str(rel_path):
                activity["phase"] = "search"
                activity["progress_percent"] = 25.0
            elif "provider_details" in str(rel_path):
                activity["phase"] = "details"
                activity["progress_percent"] = 60.0
            elif "processed" in str(rel_path):
                activity["phase"] = "normalize"
                activity["progress_percent"] = 85.0
            elif "output" in str(rel_path) or "reports" in str(rel_path):
                activity["phase"] = "complete"
                activity["progress_percent"] = 100.0
        
        # Count providers if in processed folder
        processed_path = today_path / "processed"
        if processed_path.exists():
            for jsonl_file in processed_path.glob("*.jsonl"):
                try:
                    with open(jsonl_file) as f:
                        activity["providers_count"] += sum(1 for _ in f)
                except Exception:
                    pass
        
        # Estimate completion time
        if activity["progress_percent"] > 0 and activity["last_activity"]:
            start_time = self._estimate_start_time(today_path)
            if start_time:
                elapsed = most_recent_time - start_time
                if activity["progress_percent"] < 100:
                    total_estimated = elapsed * (100 / activity["progress_percent"])
                    eta = start_time + total_estimated
                    activity["estimated_completion"] = eta.isoformat()
        
        return activity

    def _estimate_start_time(self, run_path: Path) -> Optional[datetime]:
        """Estimate when the scraper started"""
        # Find the oldest file in the run directory
        oldest_time = None
        
        for file_path in run_path.rglob("*"):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if not oldest_time or mtime < oldest_time:
                    oldest_time = mtime
        
        return oldest_time

    def _check_warnings(self, status: Dict, project_path: Path) -> List[str]:
        """Check for warning conditions"""
        warnings = []
        
        # Stalled process warning
        if status.get("last_activity"):
            last_activity = datetime.fromisoformat(status["last_activity"])
            stall_time = (datetime.now() - last_activity).seconds / 60
            
            if stall_time > self.thresholds["stall_minutes"]:
                warnings.append(f"Stalled for {int(stall_time)} minutes")
        
        # High resource usage
        if status.get("memory_mb", 0) > self.thresholds["high_memory_mb"]:
            warnings.append(f"High memory: {status['memory_mb']:.0f}MB")
        
        if status.get("cpu_percent", 0) > self.thresholds["high_cpu_percent"]:
            warnings.append(f"High CPU: {status['cpu_percent']:.1f}%")
        
        # Long ETA warning
        if status.get("estimated_completion"):
            try:
                eta = datetime.fromisoformat(status["estimated_completion"])
                hours_remaining = (eta - datetime.now()).total_seconds() / 3600
                
                if hours_remaining > self.thresholds["eta_warning_hours"]:
                    warnings.append(f"Long ETA: {hours_remaining:.1f}h")
            except Exception:
                pass
        
        # Check for error logs
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = project_path / today
        
        if log_path.exists():
            error_count = self._count_log_errors(log_path)
            if error_count > 10:
                warnings.append(f"{error_count} errors in logs")
        
        return warnings

    def _count_log_errors(self, run_path: Path) -> int:
        """Count errors in log files"""
        error_count = 0
        error_patterns = ["error", "exception", "failed", "timeout", "blocked"]
        
        for log_file in run_path.glob("**/*.log"):
            try:
                with open(log_file) as f:
                    content = f.read().lower()
                    for pattern in error_patterns:
                        error_count += content.count(pattern)
            except Exception:
                pass
        
        return error_count

    def _update_scraper_status(self, status: Dict):
        """Update scraper status in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scraper_status 
                (project_name, status, phase, progress_percent, providers_count,
                 start_time, last_activity, estimated_completion, pid, memory_mb, cpu_percent, warnings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                status["name"],
                status["status"],
                status["phase"],
                status["progress_percent"],
                status["providers_count"],
                status.get("start_time"),
                status.get("last_activity"),
                status.get("estimated_completion"),
                status.get("pid"),
                status["memory_mb"],
                status["cpu_percent"],
                json.dumps(status["warnings"])
            ))
            
            # Add alerts for warnings
            for warning in status["warnings"]:
                if "stalled" in warning.lower() or "high" in warning.lower():
                    severity = "high" if "stalled" in warning.lower() else "medium"
                    
                    conn.execute("""
                        INSERT INTO alert_history (project_name, alert_type, severity, message)
                        VALUES (?, ?, ?, ?)
                    """, (status["name"], "performance", severity, warning))

    def _get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts from database"""
        with sqlite3.connect(self.db_path) as conn:
            cutoff = datetime.now() - timedelta(hours=hours)
            cursor = conn.execute("""
                SELECT project_name, alert_type, severity, message, created_at
                FROM alert_history
                WHERE created_at > ? AND NOT resolved
                ORDER BY created_at DESC
            """, (cutoff.isoformat(),))
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    "project_name": row[0],
                    "alert_type": row[1],
                    "severity": row[2], 
                    "message": row[3],
                    "created_at": row[4]
                })
            
            return alerts

    def export_metrics(self, hours: int = 24) -> Dict:
        """Export monitoring metrics"""
        logger.info(f"Exporting metrics for last {hours} hours")
        
        with sqlite3.connect(self.db_path) as conn:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Get performance metrics
            cursor = conn.execute("""
                SELECT project_name, metric_name, AVG(metric_value), COUNT(*)
                FROM performance_metrics
                WHERE timestamp > ?
                GROUP BY project_name, metric_name
            """, (cutoff.isoformat(),))
            
            metrics = defaultdict(dict)
            for row in cursor.fetchall():
                project, metric_name, avg_value, count = row
                metrics[project][metric_name] = {
                    "average": avg_value,
                    "samples": count
                }
            
            # Get alert summary
            cursor = conn.execute("""
                SELECT alert_type, severity, COUNT(*)
                FROM alert_history
                WHERE created_at > ?
                GROUP BY alert_type, severity
            """, (cutoff.isoformat(),))
            
            alert_summary = {}
            for row in cursor.fetchall():
                alert_type, severity, count = row
                key = f"{alert_type}_{severity}"
                alert_summary[key] = count
            
            return {
                "time_period": f"last_{hours}_hours",
                "metrics": dict(metrics),
                "alert_summary": alert_summary,
                "export_timestamp": datetime.now().isoformat()
            }

    def _start_background_monitoring(self):
        """Start background monitoring without dashboard"""
        logger.info("Starting background monitoring")
        
        while self.running:
            try:
                status = self.check_all_scrapers()
                
                # Log summary
                summary = status.get("summary", {})
                logger.info(f"Fleet status: {summary['running']} running, "
                          f"{summary['warning']} warnings, {summary['error']} errors")
                
                # Log alerts
                recent_alerts = status.get("recent_alerts", [])
                high_alerts = [a for a in recent_alerts if a.get("severity") == "high"]
                if high_alerts:
                    for alert in high_alerts[:5]:  # Log top 5 high-severity alerts
                        logger.warning(f"ALERT: {alert['project_name']} - {alert['message']}")
                
                # Sleep before next check
                time.sleep(60)  # Check every minute in background mode
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                time.sleep(60)

def main():
    parser = argparse.ArgumentParser(description="Scraper Pulse Monitor - Real-time Fleet Monitoring")
    parser.add_argument("--dashboard", action="store_true", help="Start interactive dashboard")
    parser.add_argument("--check-all", action="store_true", help="Check all scrapers once")
    parser.add_argument("--export-metrics", action="store_true", help="Export performance metrics")
    parser.add_argument("--alert-thresholds", action="store_true", help="Show alert thresholds")
    parser.add_argument("--hours", type=int, default=24, help="Hours of history for metrics")
    parser.add_argument("--output", default="console", choices=["console", "json"])
    
    args = parser.parse_args()
    
    monitor = ScraperPulseMonitor()
    
    if args.dashboard:
        monitor.start_monitoring(dashboard_mode=True)
    elif args.check_all:
        result = monitor.check_all_scrapers()
        if args.output == "json":
            print(json.dumps(result, indent=2))
        else:
            _print_status_summary(result)
    elif args.export_metrics:
        metrics = monitor.export_metrics(args.hours)
        if args.output == "json":
            print(json.dumps(metrics, indent=2))
        else:
            _print_metrics_summary(metrics)
    elif args.alert_thresholds:
        _print_thresholds(monitor.thresholds)
    else:
        # Default to background monitoring
        monitor.start_monitoring(dashboard_mode=False)

def _print_status_summary(result: Dict):
    """Print status summary in console format"""
    summary = result.get("summary", {})
    print(f"\n🚀 SCRAPER FLEET STATUS")
    print(f"Total Projects: {summary.get('total', 0)}")
    print(f"🟢 Running: {summary.get('running', 0)}")
    print(f"🟡 Warning: {summary.get('warning', 0)}")
    print(f"🔴 Error: {summary.get('error', 0)}")
    print(f"⚪ Idle: {summary.get('idle', 0)}")
    
    # Show active scrapers
    active = [s for s in result.get("scrapers", []) if s.get("status") != "idle"]
    if active:
        print(f"\n📊 ACTIVE SCRAPERS ({len(active)}):")
        for scraper in sorted(active, key=lambda x: x.get("progress_percent", 0), reverse=True):
            status_icon = "🟢" if scraper["status"] == "running" else "🟡" if scraper["status"] == "warning" else "🔴"
            progress = scraper.get("progress_percent", 0)
            warnings = len(scraper.get("warnings", []))
            warning_text = f" ({warnings} alerts)" if warnings > 0 else ""
            
            print(f"  {status_icon} {scraper['name']}: {progress:.1f}% - {scraper.get('phase', 'unknown')}{warning_text}")

def _print_metrics_summary(metrics: Dict):
    """Print metrics summary in console format"""
    print(f"\n📊 PERFORMANCE METRICS ({metrics.get('time_period', 'unknown')})")
    
    project_metrics = metrics.get("metrics", {})
    if project_metrics:
        print(f"\nProject Performance (averages):")
        for project, data in sorted(project_metrics.items())[:10]:  # Top 10
            print(f"  {project}:")
            for metric, values in data.items():
                print(f"    {metric}: {values['average']:.2f} (n={values['samples']})")
    
    alert_summary = metrics.get("alert_summary", {})
    if alert_summary:
        print(f"\nAlert Summary:")
        for alert_type, count in alert_summary.items():
            print(f"  {alert_type}: {count}")

def _print_thresholds(thresholds: Dict):
    """Print current alert thresholds"""
    print(f"\n⚙️  ALERT THRESHOLDS")
    print(f"Stall detection: {thresholds['stall_minutes']} minutes")
    print(f"Slow progress: {thresholds['slow_progress']*100}% per hour")
    print(f"High memory: {thresholds['high_memory_mb']} MB")
    print(f"High CPU: {thresholds['high_cpu_percent']}%")
    print(f"Long ETA warning: {thresholds['eta_warning_hours']} hours")

if __name__ == "__main__":
    main()