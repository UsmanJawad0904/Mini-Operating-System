"""
System Logging Module
Comprehensive logging system similar to syslog
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class LogLevel(Enum):
    """Log levels"""
    DEBUG = 0
    INFO = 1
    NOTICE = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5
    ALERT = 6
    EMERGENCY = 7


class LogEntry:
    """Represents a system log entry"""
    
    def __init__(self, level, facility, message, pid="system", user="root"):
        self.timestamp = datetime.now()
        self.level = level
        self.facility = facility
        self.message = message
        self.pid = pid
        self.user = user
        
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "facility": self.facility,
            "message": self.message,
            "pid": self.pid,
            "user": self.user
        }
    
    def __str__(self):
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp_str}] [{self.level.name}] [{self.facility}] {self.message} (PID: {self.pid}, User: {self.user})"


class SystemLogger:
    """Manages system logs"""
    
    def __init__(self, max_entries=10000):
        self.logs = []
        self.max_entries = max_entries
        self.facilities = {}
        self.log_file = None
        
    def log(self, level, facility, message, pid="system", user="root"):
        """Add a log entry"""
        entry = LogEntry(level, facility, message, pid, user)
        self.logs.append(entry)
        
        # Keep only recent logs
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]
        
        # Track facility statistics
        if facility not in self.facilities:
            self.facilities[facility] = {
                "count": 0,
                "errors": 0,
                "warnings": 0
            }
        
        self.facilities[facility]["count"] += 1
        if level == LogLevel.ERROR:
            self.facilities[facility]["errors"] += 1
        elif level == LogLevel.WARNING:
            self.facilities[facility]["warnings"] += 1
        
        return entry
    
    def get_logs(self, facility=None, level=None, limit=100):
        """Get logs with optional filtering"""
        results = self.logs
        
        if facility:
            results = [l for l in results if l.facility == facility]
        
        if level:
            results = [l for l in results if l.level == level or l.level.value >= level.value]
        
        return results[-limit:]
    
    def get_statistics(self):
        """Get logging statistics"""
        return {
            "total_entries": len(self.logs),
            "facilities": self.facilities,
            "levels": self._count_by_level()
        }
    
    def _count_by_level(self):
        """Count logs by level"""
        counts = {level.name: 0 for level in LogLevel}
        for log in self.logs:
            counts[log.level.name] += 1
        return counts
    
    def export_logs(self, filename):
        """Export logs to JSON file"""
        data = [log.to_dict() for log in self.logs]
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    
    def clear_logs(self):
        """Clear all logs"""
        self.logs = []
        return True


class SystemLoggerUI:
    """UI for System Logging"""
    
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager):
        self.parent = parent
        self.back = back_callback
        self.log_callback = log_callback
        self.device = device
        self.device_manager = device_manager
        
        self.colors = {
            "bg": "#1e1e2e",
            "card": "#313244",
            "accent": "#74c7ec",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "danger": "#f38ba8",
            "text": "#cdd6f4",
            "text_muted": "#6c7086",
            "debug": "#94e2d5",
            "error": "#f38ba8",
            "critical": "#f38ba8"
        }
        
        self.logger = SystemLogger()
        self.load_saved_state()
        if not self.logger.logs:
            self._add_sample_logs()
        self.setup_ui()
        
    def _add_sample_logs(self):
        """Add sample logs for demonstration"""
        self.logger.log(LogLevel.INFO, "KERNEL", "System started successfully", "0", "root")
        self.logger.log(LogLevel.INFO, "SYSTEM", "Initializing device manager", "1", "root")
        self.logger.log(LogLevel.INFO, "MEMORY", "Memory subsystem initialized", "2", "root")
        self.logger.log(LogLevel.WARNING, "PROCESS", "High memory usage detected", "3", "root")
        self.logger.log(LogLevel.INFO, "FILESYSTEM", "Filesystem mounted", "4", "root")
        self.logger.log(LogLevel.ERROR, "NETWORK", "Failed to initialize network interface", "5", "root")
        
    def setup_ui(self):
        """Setup the UI"""
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10), padx=20)
        
        tk.Label(header, text="📋 System Logger (Syslog)", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        tk.Label(header, text=f"Device: {self.device.name}",
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w")
        
        content = tk.Frame(self.main_frame, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Controls frame
        controls = tk.Frame(content, bg=self.colors["bg"])
        controls.pack(fill="x", pady=(0, 10))
        
        tk.Label(controls, text="Filter by Level:", bg=self.colors["bg"],
                fg=self.colors["text"]).pack(side="left", padx=(0, 10))
        
        self.level_var = tk.StringVar(value="INFO")
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            tk.Radiobutton(controls, text=level, variable=self.level_var, value=level,
                          bg=self.colors["bg"], fg=self.colors["text"],
                          selectcolor=self.colors["accent"]).pack(side="left", padx=5)
        
        tk.Button(controls, text="Filter", command=self.refresh_logs,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=10)
        
        # Logs display
        log_frame = tk.LabelFrame(content, text="System Logs", bg=self.colors["card"],
                                 fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        log_frame.pack(fill="both", expand=True, pady=10)
        
        self.logs_text = scrolledtext.ScrolledText(log_frame, height=20, bg=self.colors["bg"],
                                                   fg=self.colors["text"], wrap="word",
                                                   font=("Courier New", 9))
        self.logs_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure text tags for colors
        self.logs_text.tag_config("DEBUG", foreground=self.colors["debug"])
        self.logs_text.tag_config("INFO", foreground=self.colors["success"])
        self.logs_text.tag_config("WARNING", foreground=self.colors["warning"])
        self.logs_text.tag_config("ERROR", foreground=self.colors["danger"])
        self.logs_text.tag_config("CRITICAL", foreground=self.colors["critical"])
        
        # Statistics frame
        stats_frame = tk.LabelFrame(content, text="Statistics", bg=self.colors["card"],
                                   fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        stats_frame.pack(fill="x", pady=10)
        
        self.stats_label = tk.Label(stats_frame, text="", bg=self.colors["card"],
                                   fg=self.colors["text"], justify="left")
        self.stats_label.pack(padx=10, pady=10, anchor="w")
        
        # Buttons
        button_frame = tk.Frame(content, bg=self.colors["bg"])
        button_frame.pack(fill="x", pady=10)
        
        tk.Button(button_frame, text="Add Test Log", command=self.add_test_log,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        tk.Button(button_frame, text="Clear Logs", command=self.clear_logs,
                 bg=self.colors["danger"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(button_frame, text="Export", command=self.export_logs,
                 bg=self.colors["success"], fg="#000000").pack(side="left", padx=5)
        tk.Button(button_frame, text="Back", command=self.go_back,
                 bg=self.colors["text_muted"], fg="#000000").pack(side="right", padx=5)
        
        self.refresh_logs()
        
    def refresh_logs(self):
        """Refresh logs display"""
        self.logs_text.delete(1.0, tk.END)
        
        # Get filtered logs
        level_str = self.level_var.get()
        level = LogLevel[level_str]
        logs = self.logger.get_logs(level=level, limit=200)
        
        for log in logs:
            self.logs_text.insert("end", f"{log}\n", log.level.name)
        
        # Update statistics
        stats = self.logger.get_statistics()
        stats_text = f"Total Entries: {stats['total_entries']}\n"
        for level_name, count in stats['levels'].items():
            stats_text += f"{level_name}: {count}\n"
        
        self.stats_label.config(text=stats_text)
        
    def add_test_log(self):
        """Add a test log entry"""
        test_messages = [
            ("KERNEL", LogLevel.INFO, "System heartbeat"),
            ("PROCESS", LogLevel.INFO, "New process spawned"),
            ("MEMORY", LogLevel.WARNING, "Memory usage above threshold"),
            ("FILESYSTEM", LogLevel.INFO, "File I/O operation completed"),
            ("NETWORK", LogLevel.DEBUG, "Packet sent to interface eth0"),
        ]
        
        import random
        facility, level, msg = random.choice(test_messages)
        self.logger.log(level, facility, msg, f"proc_{random.randint(1000, 9999)}", "root")
        self.save_state()
        self.log_callback("Log entry added")
        self.refresh_logs()
        
    def clear_logs(self):
        """Clear all logs"""
        self.logger.clear_logs()
        self.save_state()
        self.log_callback("All logs cleared")
        self.refresh_logs()
        
    def export_logs(self):
        """Export logs to file"""
        filename = f"minios_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.logger.export_logs(filename)
        self.log_callback(f"Logs exported to {filename}")

    def load_saved_state(self):
        saved = getattr(self.device, 'extra_state', {}).get('system_logs', {})
        if not saved:
            return
        self.logger.logs = []
        self.logger.facilities = {}
        self.logger.max_entries = saved.get('max_entries', self.logger.max_entries)
        for entry_data in saved.get('logs', []):
            entry = LogEntry(
                LogLevel[entry_data['level']],
                entry_data['facility'],
                entry_data['message'],
                entry_data.get('pid', 'system'),
                entry_data.get('user', 'root')
            )
            entry.timestamp = datetime.fromisoformat(entry_data['timestamp'])
            self.logger.logs.append(entry)
            facility = entry.facility
            if facility not in self.logger.facilities:
                self.logger.facilities[facility] = {'count': 0, 'errors': 0, 'warnings': 0}
            self.logger.facilities[facility]['count'] += 1
            if entry.level == LogLevel.ERROR:
                self.logger.facilities[facility]['errors'] += 1
            elif entry.level == LogLevel.WARNING:
                self.logger.facilities[facility]['warnings'] += 1
        self.logger.logs = self.logger.logs[-self.logger.max_entries:]

    def save_state(self):
        state = {
            'logs': [log.to_dict() for log in self.logger.logs],
            'max_entries': self.logger.max_entries
        }
        self.device_manager.update_device_state(self.device, {'system_logs': state})

    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()
