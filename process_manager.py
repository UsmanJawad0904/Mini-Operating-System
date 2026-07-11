"""
Process Manager - Advanced Edition
Realistic Process Management with Scheduling, Monitoring, and IPC
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from enum import Enum
import uuid
import time
import threading
import random
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class ProcessState(Enum):
    """Process states in a realistic OS"""
    NEW = "New"
    READY = "Ready"
    RUNNING = "Running"
    WAITING = "Waiting"
    TERMINATED = "Terminated"
    SUSPENDED = "Suspended"


class ProcessSignal(Enum):
    """Process signals"""
    SIGTERM = "SIGTERM"  # Termination
    SIGKILL = "SIGKILL"  # Force kill
    SIGSTOP = "SIGSTOP"  # Stop
    SIGCONT = "SIGCONT"  # Continue
    SIGHUP = "SIGHUP"   # Hangup


class Process:
    """Represents a process in the OS with advanced features"""
    
    def __init__(self, name, priority=5, memory_required=512, owner="root", parent_pid=None):
        self.pid = str(uuid.uuid4())[:8]
        self.name = name
        self.priority = priority  # 1-10, higher is more important
        self.memory_required = memory_required
        self.owner = owner
        self.state = ProcessState.NEW
        self.created_at = datetime.now()
        self.started_at = None
        self.ended_at = None
        self.cpu_time = 0  # milliseconds
        self.io_operations = 0
        self.page_faults = 0
        self.parent_pid = parent_pid
        self.children_pids = []
        self.file_descriptors = []
        self.environment = {}
        self.nice_value = 0  # Process niceness (-20 to 19)
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.threads = 1
        self.open_files = []
        self.signals_received = []
        self.scheduling_policy = "SCHED_OTHER"
        self.affinity_mask = 0xFF  # CPU affinity
        self.resource_limits = {
            'cpu_time': None,
            'memory': None,
            'file_descriptors': 1024,
            'processes': 1024
        }
        
    def to_dict(self):
        return {
            "pid": self.pid,
            "name": self.name,
            "priority": self.priority,
            "memory_required": self.memory_required,
            "owner": self.owner,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "cpu_time": self.cpu_time,
            "io_operations": self.io_operations,
            "page_faults": self.page_faults,
            "parent_pid": self.parent_pid,
            "children_pids": self.children_pids,
            "nice_value": self.nice_value,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "threads": self.threads,
            "scheduling_policy": self.scheduling_policy,
            "resource_limits": self.resource_limits
        }


class ProcessManager:
    """Advanced Process Manager with Scheduling and Monitoring"""
    
    def __init__(self):
        self.processes = {}
        self.process_queue = {
            "ready": deque(),
            "waiting": deque(),
            "running": None
        }
        self.next_pid = 1
        self.scheduling_algorithm = "FCFS"
        self.quantum = 100  # Time quantum for round robin
        self.total_cpu_time = 0
        self.context_switches = 0
        self.process_history = deque(maxlen=1000)
        self.system_load = 0.0
        self.monitoring_active = False
        
    def create_process(self, name, priority=5, memory_required=512, owner="root", parent_pid=None):
        """Create a new process"""
        process = Process(name, priority, memory_required, owner, parent_pid)
        self.processes[process.pid] = process
        
        # Add to parent's children if parent exists
        if parent_pid and parent_pid in self.processes:
            self.processes[parent_pid].children_pids.append(process.pid)
        
        self.process_queue["ready"].append(process.pid)
        self.log_process_event(process.pid, "created")
        return process
        
    def fork_process(self, parent_pid, child_name=None):
        """Fork a process (create child process)"""
        parent = self.get_process(parent_pid)
        if not parent:
            return None
            
        child_name = child_name or f"{parent.name}_child"
        child = self.create_process(child_name, parent.priority, parent.memory_required, parent.owner, parent_pid)
        return child
        
    def get_process(self, pid):
        """Get process by PID"""
        return self.processes.get(pid)
        
    def terminate_process(self, pid, signal=ProcessSignal.SIGTERM):
        """Terminate a process"""
        process = self.processes.get(pid)
        if process:
            process.state = ProcessState.TERMINATED
            process.ended_at = datetime.now()
            process.signals_received.append({
                'signal': signal.value,
                'timestamp': datetime.now()
            })
            
            # Remove from queues
            if pid in self.process_queue["ready"]:
                self.process_queue["ready"].remove(pid)
            elif pid in self.process_queue["waiting"]:
                self.process_queue["waiting"].remove(pid)
            elif self.process_queue["running"] == pid:
                self.process_queue["running"] = None
                
            # Terminate children
            for child_pid in process.children_pids[:]:
                self.terminate_process(child_pid, ProcessSignal.SIGHUP)
                
            self.log_process_event(pid, f"terminated by {signal.value}")
            return True
        return False
        
    def suspend_process(self, pid):
        """Suspend a process"""
        process = self.processes.get(pid)
        if process and process.state == ProcessState.RUNNING:
            process.state = ProcessState.SUSPENDED
            self.process_queue["running"] = None
            self.process_queue["waiting"].append(pid)
            self.log_process_event(pid, "suspended")
            return True
        return False
        
    def resume_process(self, pid):
        """Resume a suspended process"""
        process = self.processes.get(pid)
        if process and process.state == ProcessState.SUSPENDED:
            process.state = ProcessState.READY
            if pid in self.process_queue["waiting"]:
                self.process_queue["waiting"].remove(pid)
            self.process_queue["ready"].append(pid)
            self.log_process_event(pid, "resumed")
            return True
        return False
        
    def send_signal(self, pid, signal):
        """Send a signal to a process"""
        process = self.processes.get(pid)
        if process:
            process.signals_received.append({
                'signal': signal.value,
                'timestamp': datetime.now()
            })
            
            if signal == ProcessSignal.SIGTERM:
                self.terminate_process(pid, signal)
            elif signal == ProcessSignal.SIGKILL:
                self.terminate_process(pid, signal)
            elif signal == ProcessSignal.SIGSTOP:
                self.suspend_process(pid)
            elif signal == ProcessSignal.SIGCONT:
                self.resume_process(pid)
                
            self.log_process_event(pid, f"received {signal.value}")
            return True
        return False
        
    def schedule_next_process(self):
        """Schedule next process based on current algorithm"""
        if not self.process_queue["ready"]:
            return None
            
        if self.scheduling_algorithm == "FCFS":
            next_pid = self.process_queue["ready"].popleft()
        elif self.scheduling_algorithm == "SJF":
            # Shortest Job First
            ready_processes = [(pid, self.processes[pid]) for pid in self.process_queue["ready"]]
            ready_processes.sort(key=lambda x: x[1].cpu_time)
            next_pid = ready_processes[0][0]
            self.process_queue["ready"].remove(next_pid)
        elif self.scheduling_algorithm == "Priority":
            # Highest priority first
            ready_processes = [(pid, self.processes[pid]) for pid in self.process_queue["ready"]]
            ready_processes.sort(key=lambda x: x[1].priority, reverse=True)
            next_pid = ready_processes[0][0]
            self.process_queue["ready"].remove(next_pid)
        elif self.scheduling_algorithm == "Round Robin":
            next_pid = self.process_queue["ready"].popleft()
        else:
            next_pid = self.process_queue["ready"].popleft()
            
        # Context switch
        if self.process_queue["running"]:
            old_process = self.processes[self.process_queue["running"]]
            old_process.state = ProcessState.READY
            self.process_queue["ready"].append(self.process_queue["running"])
            self.context_switches += 1
            
        self.process_queue["running"] = next_pid
        process = self.processes[next_pid]
        process.state = ProcessState.RUNNING
        if not process.started_at:
            process.started_at = datetime.now()
            
        self.log_process_event(next_pid, "scheduled")
        return process
        
    def update_process_stats(self):
        """Update process statistics and simulate execution"""
        if self.process_queue["running"]:
            pid = self.process_queue["running"]
            process = self.processes[pid]
            
            # Simulate CPU usage
            cpu_increment = random.randint(1, 10)
            process.cpu_time += cpu_increment
            self.total_cpu_time += cpu_increment
            
            # Simulate memory usage variation
            process.memory_usage = min(100.0, max(0.0, process.memory_required / 1024.0 * 100 + random.uniform(-5, 5)))
            
            # Simulate CPU usage percentage
            process.cpu_usage = min(100.0, random.uniform(0, 20) + process.priority * 2)
            
            # Simulate I/O operations
            if random.random() < 0.1:  # 10% chance
                process.io_operations += 1
                # Process goes to waiting state during I/O
                process.state = ProcessState.WAITING
                self.process_queue["running"] = None
                self.process_queue["waiting"].append(pid)
                
                # Schedule next process
                self.schedule_next_process()
                
            # Check if process should finish
            if process.cpu_time > random.randint(500, 2000):  # Random completion time
                self.terminate_process(pid)
                self.schedule_next_process()
                
        # Wake up waiting processes
        for pid in list(self.process_queue["waiting"]):
            if random.random() < 0.3:  # 30% chance to wake up
                process = self.processes[pid]
                process.state = ProcessState.READY
                self.process_queue["waiting"].remove(pid)
                self.process_queue["ready"].append(pid)
                
    def schedule_processes(self):
        """Run scheduling cycle"""
        # Update current running process
        self.update_process_stats()
        
        # Schedule next process if needed
        if not self.process_queue["running"] and self.process_queue["ready"]:
            self.schedule_next_process()
            
    def set_scheduling_algorithm(self, algorithm, quantum=None):
        """Set scheduling algorithm"""
        self.scheduling_algorithm = algorithm
        if quantum is not None:
            self.quantum = quantum
        self.log_system_event(f"Scheduling algorithm changed to {algorithm}")
        
    def get_process_list(self, state=None):
        """Get all processes or filtered by state"""
        if state:
            return [p for p in self.processes.values() if p.state == state]
        return list(self.processes.values())
        
    def get_process_tree(self, root_pid=None):
        """Get process hierarchy tree"""
        def build_tree(pid, level=0):
            process = self.processes.get(pid)
            if not process:
                return []
                
            tree = [{"process": process, "level": level}]
            for child_pid in process.children_pids:
                tree.extend(build_tree(child_pid, level + 1))
            return tree
            
        if root_pid:
            return build_tree(root_pid)
        else:
            # Find root processes (no parent)
            roots = [p for p in self.processes.values() if not p.parent_pid]
            tree = []
            for root in roots:
                tree.extend(build_tree(root.pid))
            return tree
            
    def get_system_stats(self):
        """Get system-wide statistics"""
        total_processes = len(self.processes)
        running = len([p for p in self.processes.values() if p.state == ProcessState.RUNNING])
        ready = len([p for p in self.processes.values() if p.state == ProcessState.READY])
        waiting = len([p for p in self.processes.values() if p.state == ProcessState.WAITING])
        terminated = len([p for p in self.processes.values() if p.state == ProcessState.TERMINATED])
        
        avg_cpu_time = sum(p.cpu_time for p in self.processes.values()) / total_processes if total_processes > 0 else 0
        avg_memory = sum(p.memory_required for p in self.processes.values()) / total_processes if total_processes > 0 else 0
        
        return {
            'total_processes': total_processes,
            'running': running,
            'ready': ready,
            'waiting': waiting,
            'terminated': terminated,
            'context_switches': self.context_switches,
            'total_cpu_time': self.total_cpu_time,
            'system_load': self.system_load,
            'avg_cpu_time': avg_cpu_time,
            'avg_memory': avg_memory,
            'scheduling_algorithm': self.scheduling_algorithm
        }
        
    def log_process_event(self, pid, event):
        """Log process event"""
        self.process_history.append({
            'timestamp': datetime.now(),
            'pid': pid,
            'event': event,
            'process_name': self.processes[pid].name if pid in self.processes else 'unknown'
        })
        
    def log_system_event(self, event):
        """Log system event"""
        self.process_history.append({
            'timestamp': datetime.now(),
            'pid': None,
            'event': event,
            'process_name': 'system'
        })


class ProcessManagerUI:
    """Advanced UI for Process Management with Scheduling and Monitoring"""
    
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        
        self.colors = {
            "bg": "#1e1e2e",
            "card": "#313244",
            "card_hover": "#45475a",
            "accent": "#89dceb",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "danger": "#f38ba8",
            "info": "#89b4fa",
            "purple": "#cba6f7",
            "text": "#cdd6f4",
            "text_muted": "#6c7086"
        }
        
        # Initialize process manager
        self.pm = ProcessManager()
        self.monitoring_active = False
        self.monitor_thread = None
        self.scheduling_active = False
        self.auto_schedule_var = tk.BooleanVar(value=False)
        
        # UI components that will be initialized in setup methods
        self.start_sched_btn = None
        self.sched_display_frame = None
        self.start_mon_btn = None
        self.cpu_ax = None
        self.mem_ax = None
        self.proc_ax = None
        self.cpu_canvas = None
        self.mem_canvas = None
        self.proc_canvas = None
        self.stats_labels = {}
        self.process_tree = None
        
        self.setup_ui()
        self.load_saved_state()
        
    def setup_ui(self):
        """Setup the advanced UI"""
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10), padx=20)
        
        tk.Label(header, text="⚙️ Advanced Process Manager", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        tk.Label(header, text=f"Device: {self.device.name} | Scheduling: {self.pm.scheduling_algorithm}",
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Process Management Tab
        self.setup_process_tab(notebook)
        
        # Scheduling Tab
        self.setup_scheduling_tab(notebook)
        
        # Monitoring Tab
        self.setup_monitoring_tab(notebook)
        
        # Process Tree Tab
        self.setup_tree_tab(notebook)
        
        # Back button
        back_btn = tk.Button(self.main_frame, text="← Back to Dashboard", command=self.go_back,
                            bg=self.colors["text_muted"], fg="white", font=("Segoe UI", 11),
                            cursor="hand2", padx=20, pady=8)
        back_btn.pack(pady=20)
        
    def setup_process_tab(self, notebook):
        """Setup process management tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="⚡ Processes")
        
        # Process creation section
        create_frame = tk.LabelFrame(tab, text="Create Process", bg=self.colors["card"],
                                    fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        create_frame.pack(fill="x", pady=10, padx=20)
        
        input_frame = tk.Frame(create_frame, bg=self.colors["card"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        # Process name
        tk.Label(input_frame, text="Process Name:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.name_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.name_entry.pack(fill="x", pady=(0, 10))
        
        # Priority and Memory in same row
        params_frame = tk.Frame(input_frame, bg=self.colors["card"])
        params_frame.pack(fill="x", pady=(0, 10))
        
        # Priority
        priority_frame = tk.Frame(params_frame, bg=self.colors["card"])
        priority_frame.pack(side="left", expand=True, padx=(0, 5))
        tk.Label(priority_frame, text="Priority (1-10):", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.priority_var = tk.IntVar(value=5)
        priority_scale = tk.Scale(priority_frame, from_=1, to=10, orient="horizontal",
                                 bg=self.colors["bg"], fg=self.colors["accent"], variable=self.priority_var)
        priority_scale.pack(fill="x")
        
        # Memory required
        memory_frame = tk.Frame(params_frame, bg=self.colors["card"])
        memory_frame.pack(side="left", expand=True, padx=(5, 0))
        tk.Label(memory_frame, text="Memory (MB):", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.memory_entry = tk.Entry(memory_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.memory_entry.insert(0, "512")
        self.memory_entry.pack(fill="x")
        
        # Owner
        tk.Label(input_frame, text="Owner:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.owner_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.owner_entry.insert(0, "root")
        self.owner_entry.pack(fill="x", pady=(0, 10))

        # Advanced creation options
        advanced_toggle_frame = tk.Frame(input_frame, bg=self.colors["card"])
        advanced_toggle_frame.pack(fill="x", pady=(0, 10))
        self.advanced_var = tk.BooleanVar(value=False)
        tk.Checkbutton(advanced_toggle_frame, text="Show advanced options",
                       variable=self.advanced_var, command=self.toggle_advanced_options,
                       bg=self.colors["card"], fg=self.colors["text"], selectcolor=self.colors["card"]).pack(anchor="w")

        self.advanced_frame = tk.Frame(input_frame, bg=self.colors["card"])
        self.advanced_frame.pack(fill="x", pady=(0, 10))
        self.advanced_frame.pack_forget()

        adv_params_frame = tk.Frame(self.advanced_frame, bg=self.colors["card"])
        adv_params_frame.pack(fill="x", pady=(0, 10))

        nice_frame = tk.Frame(adv_params_frame, bg=self.colors["card"])
        nice_frame.pack(side="left", expand=True, padx=(0, 5))
        tk.Label(nice_frame, text="Nice Value (-20 to 19):", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.nice_var = tk.IntVar(value=0)
        tk.Scale(nice_frame, from_=-20, to=19, orient="horizontal",
                 bg=self.colors["bg"], fg=self.colors["accent"], variable=self.nice_var).pack(fill="x")

        threads_frame = tk.Frame(adv_params_frame, bg=self.colors["card"])
        threads_frame.pack(side="left", expand=True, padx=(5, 0))
        tk.Label(threads_frame, text="Threads:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.threads_var = tk.IntVar(value=1)
        tk.Spinbox(threads_frame, from_=1, to=64, textvariable=self.threads_var,
                   bg=self.colors["bg"], fg=self.colors["text"], width=6).pack(fill="x")

        policy_frame = tk.Frame(self.advanced_frame, bg=self.colors["card"])
        policy_frame.pack(fill="x", pady=(0, 10))
        tk.Label(policy_frame, text="Scheduling Policy:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.policy_var = tk.StringVar(value="SCHED_OTHER")
        policy_combo = ttk.Combobox(policy_frame, textvariable=self.policy_var,
                                    values=["SCHED_OTHER", "SCHED_FIFO", "SCHED_RR"], state="readonly")
        policy_combo.pack(fill="x")

        affinity_frame = tk.Frame(self.advanced_frame, bg=self.colors["card"])
        affinity_frame.pack(fill="x")
        tk.Label(affinity_frame, text="CPU Affinity Mask:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.affinity_entry = tk.Entry(affinity_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.affinity_entry.insert(0, "0xFF")
        self.affinity_entry.pack(fill="x", pady=(0, 10))

        # Create and Fork buttons
        btn_frame = tk.Frame(input_frame, bg=self.colors["card"])
        btn_frame.pack(fill="x")
        
        tk.Button(btn_frame, text="➕ Create Process", command=self.create_process,
                 bg=self.colors["accent"], fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔀 Fork Selected", command=self.fork_selected,
                 bg=self.colors["info"], fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        
        # Process list section
        list_frame = tk.LabelFrame(tab, text="Running Processes", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        list_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        # Create treeview
        columns = ("PID", "Name", "State", "Priority", "Memory", "CPU%", "Owner", "Nice", "Policy", "CPU Time")
        self.tree = ttk.Treeview(list_frame, columns=columns, height=15)
        
        # Set column headings
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=0)
        col_widths = {"PID": 80, "Name": 120, "State": 80, "Priority": 70, "Memory": 80, "CPU%": 60, "Owner": 80, "Nice": 70, "Policy": 100, "CPU Time": 80}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 100))
        
        # Add scrollbar
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = tk.Frame(tab, bg=self.colors["bg"])
        button_frame.pack(fill="x", pady=10, padx=20)
        
        tk.Button(button_frame, text="🔄 Refresh", command=self.refresh_process_list,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        tk.Button(button_frame, text="🛑 Terminate", command=self.terminate_selected,
                 bg=self.colors["danger"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(button_frame, text="⏸ Suspend", command=self.suspend_selected,
                 bg=self.colors["warning"], fg="#000000").pack(side="left", padx=5)
        tk.Button(button_frame, text="▶ Resume", command=self.resume_selected,
                 bg=self.colors["success"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(button_frame, text="📡 Send Signal", command=self.send_signal_dialog,
                 bg=self.colors["info"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(button_frame, text="🗑 Clear Terminated", command=self.clear_terminated,
                 bg=self.colors["text_muted"], fg="#ffffff").pack(side="left", padx=5)
        
    def setup_scheduling_tab(self, notebook):
        """Setup scheduling controls tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="⏰ Scheduling")
        
        # Algorithm selection
        algo_frame = tk.LabelFrame(tab, text="Scheduling Algorithm", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        algo_frame.pack(fill="x", pady=10, padx=20)
        
        algo_inner = tk.Frame(algo_frame, bg=self.colors["card"])
        algo_inner.pack(fill="x", padx=10, pady=10)
        
        tk.Label(algo_inner, text="Algorithm:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.algo_var = tk.StringVar(value=self.pm.scheduling_algorithm)
        algo_combo = ttk.Combobox(algo_inner, textvariable=self.algo_var, 
                                 values=["FCFS", "SJF", "Priority", "Round Robin"], state="readonly")
        algo_combo.pack(side="left", padx=10)
        algo_combo.bind("<<ComboboxSelected>>", self.change_algorithm)
        
        # Quantum setting (for Round Robin)
        quantum_frame = tk.Frame(algo_inner, bg=self.colors["card"])
        quantum_frame.pack(side="left", padx=20)
        tk.Label(quantum_frame, text="Quantum (ms):", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.quantum_var = tk.StringVar(value=str(self.pm.quantum))
        quantum_entry = tk.Entry(quantum_frame, textvariable=self.quantum_var, width=8, bg=self.colors["bg"], fg=self.colors["text"])
        quantum_entry.pack(side="left", padx=5)
        tk.Button(quantum_frame, text="Set", command=self.set_quantum, bg=self.colors["accent"], fg="#000000").pack(side="left")
        
        # Manual scheduling
        manual_frame = tk.LabelFrame(tab, text="Manual Control", bg=self.colors["card"],
                                    fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        manual_frame.pack(fill="x", pady=10, padx=20)
        
        manual_inner = tk.Frame(manual_frame, bg=self.colors["card"])
        manual_inner.pack(fill="x", padx=10, pady=10)
        
        self.start_sched_btn = tk.Button(manual_inner, text="▶️ Start Scheduling", command=self.start_scheduling,
                                        bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold"))
        self.start_sched_btn.pack(side="left", padx=5)
        
        tk.Button(manual_inner, text="⏭️ Step Once", command=self.manual_schedule,
                  bg=self.colors["info"], fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Checkbutton(manual_inner, text="Auto Schedule", variable=self.auto_schedule_var,
                       command=self.toggle_auto_schedule, bg=self.colors["card"], fg=self.colors["text"], selectcolor=self.colors["card"]).pack(side="left", padx=10)
        
        # Queue status
        queue_frame = tk.LabelFrame(tab, text="Queue Status", bg=self.colors["card"],
                                   fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        queue_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        queue_inner = tk.Frame(queue_frame, bg=self.colors["card"])
        queue_inner.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Ready queue
        ready_frame = tk.Frame(queue_inner, bg=self.colors["card"])
        ready_frame.pack(fill="x", pady=5)
        tk.Label(ready_frame, text="Ready Queue:", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
        self.ready_label = tk.Label(ready_frame, text="Empty", bg=self.colors["card"], fg=self.colors["warning"])
        self.ready_label.pack(side="left", padx=10)
        
        # Waiting queue
        waiting_frame = tk.Frame(queue_inner, bg=self.colors["card"])
        waiting_frame.pack(fill="x", pady=5)
        tk.Label(waiting_frame, text="Waiting Queue:", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
        self.waiting_label = tk.Label(waiting_frame, text="Empty", bg=self.colors["card"], fg=self.colors["info"])
        self.waiting_label.pack(side="left", padx=10)
        
        # Running process
        running_frame = tk.Frame(queue_inner, bg=self.colors["card"])
        running_frame.pack(fill="x", pady=5)
        tk.Label(running_frame, text="Running:", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
        self.running_label = tk.Label(running_frame, text="None", bg=self.colors["card"], fg=self.colors["success"])
        self.running_label.pack(side="left", padx=10)
        
        # Statistics
        stats_frame = tk.LabelFrame(queue_inner, text="Scheduling Statistics", bg=self.colors["card"],
                                   fg=self.colors["text"])
        stats_frame.pack(fill="both", expand=True, pady=10)
        
        self.stats_labels = {}
        stats = [
            ("Context Switches", "0"),
            ("Total CPU Time", "0ms"),
            ("System Load", "0.0%"),
            ("Avg Response Time", "0ms")
        ]
        
        for i, (label, value) in enumerate(stats):
            frame = tk.Frame(stats_frame, bg=self.colors["card"])
            frame.pack(fill="x", pady=2)
            tk.Label(frame, text=f"{label}:", bg=self.colors["card"], fg=self.colors["text_muted"]).pack(side="left")
            lbl = tk.Label(frame, text=value, bg=self.colors["card"], fg=self.colors["accent"])
            lbl.pack(side="right")
            self.stats_labels[label] = lbl
        
        # Scheduling display
        self.sched_display_frame = tk.LabelFrame(queue_inner, text="Current Scheduling Status", bg=self.colors["card"],
                                                fg=self.colors["text"])
        self.sched_display_frame.pack(fill="both", expand=True, pady=10)
        
    def setup_monitoring_tab(self, notebook):
        """Setup monitoring tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="📊 Monitoring")
        
        # Control panel
        control_frame = tk.Frame(tab, bg=self.colors["bg"])
        control_frame.pack(fill="x", pady=10, padx=20)
        
        self.start_mon_btn = tk.Button(control_frame, text="▶ Start Monitoring", command=self.start_monitoring,
                                      bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold"))
        self.start_mon_btn.pack(side="left", padx=5)
        
        # System stats
        stats_frame = tk.LabelFrame(tab, text="System Statistics", bg=self.colors["card"],
                                   fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        stats_frame.pack(fill="x", pady=10, padx=20)
        
        self.monitor_labels = {}
        stats = [
            ("Total Processes", "0", self.colors["info"]),
            ("Running", "0", self.colors["success"]),
            ("Ready", "0", self.colors["warning"]),
            ("Waiting", "0", self.colors["purple"]),
            ("Terminated", "0", self.colors["danger"]),
            ("Context Switches", "0", self.colors["cyan"]),
            ("System Load", "0.0%", self.colors["accent"]),
            ("Avg CPU Time", "0ms", self.colors["success"])
        ]
        
        for i, (label, value, color) in enumerate(stats):
            frame = tk.Frame(stats_frame, bg=self.colors["card"])
            frame.grid(row=i//4, column=i%4, padx=10, pady=5, sticky="nsew")
            tk.Label(frame, text=label, bg=self.colors["card"], fg=self.colors["text_muted"], font=("Segoe UI", 9)).pack()
            lbl = tk.Label(frame, text=value, bg=self.colors["card"], fg=color, font=("Segoe UI", 14, "bold"))
            lbl.pack()
            self.monitor_labels[label] = lbl
        
        for i in range(2):
            stats_frame.grid_rowconfigure(i, weight=1)
        for i in range(4):
            stats_frame.grid_columnconfigure(i, weight=1)
        
        # Charts section
        charts_frame = tk.LabelFrame(tab, text="Performance Charts", bg=self.colors["card"],
                                    fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        charts_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        # Create matplotlib figures
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        
        # CPU chart
        cpu_frame = tk.Frame(charts_frame, bg=self.colors["card"])
        cpu_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        cpu_fig = plt.Figure(figsize=(4, 3), dpi=100, facecolor=self.colors["card"])
        self.cpu_ax = cpu_fig.add_subplot(111)
        self.cpu_ax.set_facecolor(self.colors["bg"])
        self.cpu_ax.tick_params(colors=self.colors["text"])
        for spine in self.cpu_ax.spines.values():
            spine.set_edgecolor(self.colors["text"])
        self.cpu_canvas = FigureCanvasTkAgg(cpu_fig, master=cpu_frame)
        self.cpu_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Memory chart
        mem_frame = tk.Frame(charts_frame, bg=self.colors["card"])
        mem_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        mem_fig = plt.Figure(figsize=(4, 3), dpi=100, facecolor=self.colors["card"])
        self.mem_ax = mem_fig.add_subplot(111)
        self.mem_ax.set_facecolor(self.colors["bg"])
        self.mem_ax.tick_params(colors=self.colors["text"])
        for spine in self.mem_ax.spines.values():
            spine.set_edgecolor(self.colors["text"])
        self.mem_canvas = FigureCanvasTkAgg(mem_fig, master=mem_frame)
        self.mem_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Process state chart
        proc_frame = tk.Frame(charts_frame, bg=self.colors["card"])
        proc_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        proc_fig = plt.Figure(figsize=(4, 3), dpi=100, facecolor=self.colors["card"])
        self.proc_ax = proc_fig.add_subplot(111)
        self.proc_ax.set_facecolor(self.colors["bg"])
        self.proc_ax.tick_params(colors=self.colors["text"])
        for spine in self.proc_ax.spines.values():
            spine.set_edgecolor(self.colors["text"])
        self.proc_canvas = FigureCanvasTkAgg(proc_fig, master=proc_frame)
        self.proc_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Process activity log
        log_frame = tk.LabelFrame(tab, text="Process Activity Log", bg=self.colors["card"],
                                 fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        log_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                                 font=("Consolas", 9), height=15)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Auto-scroll to bottom
        self.log_text.see("end")
        
    def setup_tree_tab(self, notebook):
        """Setup process tree tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="🌳 Process Tree")
        
        # Tree view
        tree_frame = tk.LabelFrame(tab, text="Process Hierarchy", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        tree_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        # Create treeview for hierarchy
        columns = ("PID", "Name", "State", "CPU%", "Memory")
        self.process_tree = ttk.Treeview(tree_frame, columns=columns, height=20)
        
        self.process_tree.heading("#0", text="")
        self.process_tree.column("#0", width=0)
        col_widths = {"PID": 80, "Name": 150, "State": 80, "CPU%": 60, "Memory": 80}
        for col in columns:
            self.process_tree.heading(col, text=col)
            self.process_tree.column(col, width=col_widths.get(col, 100))
        
        scrollbar = tk.Scrollbar(tree_frame, orient="vertical", command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)
        
        self.process_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        btn_frame = tk.Frame(tab, bg=self.colors["bg"])
        btn_frame.pack(fill="x", pady=10, padx=20)
        
        tk.Button(btn_frame, text="🔄 Refresh Tree", command=self.refresh_process_tree,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        tk.Button(btn_frame, text="📋 Show Details", command=self.show_process_details,
                 bg=self.colors["info"], fg="#ffffff").pack(side="left", padx=5)
        
    def create_process(self):
        """Create a new process"""
        try:
            name = self.name_entry.get()
            if not name:
                messagebox.showerror("Error", "Process name is required")
                return
            
            priority = self.priority_var.get()
            memory = int(self.memory_entry.get())
            owner = self.owner_entry.get()
            
            process = self.pm.create_process(name, priority, memory, owner)
            if self.advanced_var.get():
                process.nice_value = self.nice_var.get()
                process.threads = self.threads_var.get()
                process.scheduling_policy = self.policy_var.get()
                try:
                    process.affinity_mask = int(self.affinity_entry.get(), 0)
                except ValueError:
                    process.affinity_mask = 0xFF
            self.log(f"Process created: {name} (PID: {process.pid})")
            self.name_entry.delete(0, tk.END)
            self.refresh_process_list()
            self.refresh_process_tree()
            self.update_scheduling_display()
            self.update_monitoring()
            self.save_state()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create process: {str(e)}")
            
    def toggle_advanced_options(self):
        """Show or hide advanced process creation fields"""
        if self.advanced_var.get():
            self.advanced_frame.pack(fill="x", pady=(0, 10))
        else:
            self.advanced_frame.pack_forget()

    def refresh_process_list(self):
        """Refresh the process list display"""
        if not getattr(self, 'tree', None):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for process in self.pm.get_process_list():
            cpu_percent = f"{process.cpu_usage:.1f}%"
            cpu_time = f"{process.cpu_time}ms"
            self.tree.insert("", "end", text="",
                           values=(process.pid, process.name, process.state.value,
                                  process.priority, f"{process.memory_required}MB",
                                  cpu_percent, process.owner, process.nice_value,
                                  process.scheduling_policy, cpu_time))
        
    def terminate_selected(self):
        """Terminate selected process"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a process")
            return
        
        for item in selection:
            pid = self.tree.item(item)['values'][0]
            if self.pm.terminate_process(pid):
                self.log(f"Process terminated: PID {pid}")
        
        self.refresh_process_list()
        self.refresh_process_tree()
        self.update_monitoring()
        self.save_state()

    def load_saved_state(self):
        saved = getattr(self.device, 'extra_state', {}).get('process_manager_state', {})
        processes = saved.get('processes', [])
        self.pm = ProcessManager()
        self.pm.process_queue = {"ready": deque(), "waiting": deque(), "running": None}
        self.pm.scheduling_algorithm = saved.get('scheduling_algorithm', self.pm.scheduling_algorithm)
        self.pm.quantum = saved.get('quantum', self.pm.quantum)

        for proc_data in processes:
            process = Process(proc_data['name'], proc_data.get('priority', 5), proc_data.get('memory_required', 512), proc_data.get('owner', 'root'))
            process.pid = proc_data.get('pid', process.pid)
            process.state = ProcessState(proc_data.get('state', 'New'))
            process.created_at = datetime.fromisoformat(proc_data.get('created_at')) if proc_data.get('created_at') else process.created_at
            process.started_at = datetime.fromisoformat(proc_data['started_at']) if proc_data.get('started_at') else None
            process.ended_at = datetime.fromisoformat(proc_data['ended_at']) if proc_data.get('ended_at') else None
            process.cpu_time = proc_data.get('cpu_time', 0)
            process.io_operations = proc_data.get('io_operations', 0)
            process.page_faults = proc_data.get('page_faults', 0)
            process.nice_value = proc_data.get('nice_value', 0)
            process.cpu_usage = proc_data.get('cpu_usage', 0.0)
            process.memory_usage = proc_data.get('memory_usage', 0.0)
            process.threads = proc_data.get('threads', 1)
            process.scheduling_policy = proc_data.get('scheduling_policy', 'SCHED_OTHER')
            process.affinity_mask = proc_data.get('affinity_mask', 0xFF)
            process.resource_limits = proc_data.get('resource_limits', process.resource_limits)
            self.pm.processes[process.pid] = process
            if process.state == ProcessState.READY:
                self.pm.process_queue['ready'].append(process.pid)
            elif process.state == ProcessState.WAITING:
                self.pm.process_queue['waiting'].append(process.pid)
            elif process.state == ProcessState.RUNNING:
                self.pm.process_queue['running'] = process.pid

        if hasattr(self, 'algo_var'):
            self.algo_var.set(self.pm.scheduling_algorithm)
        if hasattr(self, 'quantum_var'):
            self.quantum_var.set(str(self.pm.quantum))
        self.refresh_process_list()
        self.refresh_process_tree()
        self.update_scheduling_display()

    def fork_selected(self):
        """Fork the selected process"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a process to fork")
            return
        
        pid = self.tree.item(selection[0])['values'][0]
        parent = self.pm.get_process(pid)
        if not parent:
            messagebox.showerror("Error", "Process not found")
            return
            
        child = self.pm.fork_process(pid)
        if child:
            self.log(f"Process forked: {parent.name} -> {child.name} (PID: {child.pid})")
            self.refresh_process_list()
            self.refresh_process_tree()
            self.update_monitoring()
            self.save_state()
        else:
            messagebox.showerror("Error", "Failed to fork process")
            
    def suspend_selected(self):
        """Suspend selected process"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a process")
            return
        
        pid = self.tree.item(selection[0])['values'][0]
        if self.pm.suspend_process(pid):
            self.log(f"Process suspended: PID {pid}")
            self.refresh_process_list()
            self.update_monitoring()
            self.save_state()
        else:
            messagebox.showerror("Error", "Failed to suspend process")
            
    def resume_selected(self):
        """Resume selected process"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a process")
            return
        
        pid = self.tree.item(selection[0])['values'][0]
        if self.pm.resume_process(pid):
            self.log(f"Process resumed: PID {pid}")
            self.refresh_process_list()
            self.update_monitoring()
            self.save_state()
        else:
            messagebox.showerror("Error", "Failed to resume process")
            
    def send_signal_dialog(self):
        """Show signal sending dialog"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a process")
            return
        
        pid = self.tree.item(selection[0])['values'][0]
        process = self.pm.get_process(pid)
        if not process:
            return
            
        # Create signal dialog
        dialog = tk.Toplevel(self.main_frame)
        dialog.title("Send Signal")
        dialog.geometry("300x200")
        dialog.configure(bg=self.colors["bg"])
        
        tk.Label(dialog, text=f"Send signal to {process.name} (PID: {pid})",
                bg=self.colors["bg"], fg=self.colors["text"]).pack(pady=10)
        
        signal_var = tk.StringVar(value="SIGTERM")
        signals = ["SIGTERM", "SIGKILL", "SIGSTOP", "SIGCONT", "SIGHUP"]
        
        for signal in signals:
            tk.Radiobutton(dialog, text=signal, variable=signal_var, value=signal,
                          bg=self.colors["bg"], fg=self.colors["text"], selectcolor=self.colors["card"]).pack(anchor="w", padx=20)
        
        def send_signal():
            signal = ProcessSignal[signal_var.get()]
            if self.pm.send_signal(pid, signal):
                self.log(f"Signal {signal.value} sent to PID {pid}")
                self.refresh_process_list()
                self.update_monitoring()
                self.save_state()
            dialog.destroy()
            
        tk.Button(dialog, text="Send", command=send_signal, bg=self.colors["accent"], fg="#000000").pack(pady=10)
        
    def clear_terminated(self):
        """Clear terminated processes from display"""
        # Note: In a real system, we'd clean up terminated processes
        # For now, just refresh to show current state
        self.refresh_process_list()
        self.refresh_process_tree()
        self.update_monitoring()

    def change_algorithm(self):
        """Change scheduling algorithm"""
        algorithm = self.algo_var.get()
        self.pm.set_scheduling_algorithm(algorithm)
        self.log(f"Scheduling algorithm changed to: {algorithm}")
        self.update_scheduling_display()
        self.save_state()
        
    def start_scheduling(self):
        """Start the scheduling simulation"""
        if self.scheduling_active:
            self.stop_scheduling()
            return
            
        self.scheduling_active = True
        self.start_sched_btn.config(text="⏹️ Stop Scheduling")
        self.log("Scheduling simulation started")
        self.run_scheduling_cycle()
        
    def stop_scheduling(self):
        """Stop the scheduling simulation"""
        self.scheduling_active = False
        self.start_sched_btn.config(text="▶️ Start Scheduling")
        self.log("Scheduling simulation stopped")
        
    def run_scheduling_cycle(self):
        """Run one scheduling cycle"""
        if not self.scheduling_active:
            return
            
        # Run scheduling cycle
        self.pm.schedule_processes()
        
        # Update displays
        self.refresh_process_list()
        self.update_scheduling_display()
        self.update_monitoring()
        
        # Schedule next cycle
        if self.scheduling_active:
            self.main_frame.after(1000, self.run_scheduling_cycle)  # 1 second intervals
            
    def update_scheduling_display(self):
        """Update the scheduling display"""
        # Clear current display
        for widget in self.sched_display_frame.winfo_children():
            widget.destroy()
            
        # Update summary labels
        ready_len = len(self.pm.process_queue['ready'])
        waiting_len = len(self.pm.process_queue['waiting'])
        running_pid = self.pm.process_queue.get('running')
        running_text = "None"
        if running_pid:
            running_process = self.pm.get_process(running_pid)
            if running_process:
                running_text = f"{running_process.name} (PID: {running_pid})"

        self.ready_label.config(text=f"{ready_len} process(es)")
        self.waiting_label.config(text=f"{waiting_len} process(es)")
        self.running_label.config(text=running_text)
        self.stats_labels["Context Switches"].config(text=str(self.pm.context_switches))
        self.stats_labels["Total CPU Time"].config(text=f"{self.pm.total_cpu_time}ms")
        self.stats_labels["System Load"].config(text=f"{self.pm.system_load:.1f}%")
        self.stats_labels["Avg Response Time"].config(text=f"{(self.pm.total_cpu_time / max(1, ready_len + (1 if running_pid else 0))):.1f}ms")

        # Show current algorithm
        tk.Label(self.sched_display_frame, text=f"Current Algorithm: {self.pm.scheduling_algorithm}",
                bg=self.colors["card"], fg=self.colors["text"], font=("Arial", 10, "bold")).pack(pady=5)
        
        # Show ready queue
        ready_processes = [self.pm.get_process(pid) for pid in self.pm.process_queue['ready'] if self.pm.get_process(pid)]
        if ready_processes:
            tk.Label(self.sched_display_frame, text="Ready Queue:", bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w", padx=10)
            for process in ready_processes[:5]:  # Show first 5
                tk.Label(self.sched_display_frame, text=f"  {process.name} (PID: {process.pid}, Priority: {process.priority})",
                        bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w", padx=20)
        
        # Show running process
        if running_pid and running_process:
            tk.Label(self.sched_display_frame, text=f"Running: {running_text}",
                    bg=self.colors["card"], fg=self.colors["accent"], font=("Arial", 10, "bold")).pack(pady=5)
        
        # Show waiting queue
        waiting_processes = [self.pm.get_process(pid) for pid in self.pm.process_queue['waiting'] if self.pm.get_process(pid)]
        if waiting_processes:
            tk.Label(self.sched_display_frame, text="Waiting Queue:", bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w", padx=10)
            for process in waiting_processes[:3]:  # Show first 3
                tk.Label(self.sched_display_frame, text=f"  {process.name} (PID: {process.pid})",
                        bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w", padx=20)

    def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            self.stop_monitoring()
            return
            
        self.monitoring_active = True
        self.start_mon_btn.config(text="⏹️ Stop Monitoring")
        self.log("Performance monitoring started")
        self.update_monitoring()
        
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        self.start_mon_btn.config(text="📊 Start Monitoring")
        self.log("Performance monitoring stopped")
        
    def update_monitoring(self):
        """Update monitoring display"""
        if not self.monitoring_active:
            return
            
        # Update process metrics
        for process in self.pm.get_process_list():
            # Simulate CPU usage changes
            process.cpu_usage = random.uniform(0, 100)
            process.cpu_time += random.randint(1, 10)
        
        total_processes = len(self.pm.get_process_list())
        self.pm.system_load = sum(p.cpu_usage for p in self.pm.get_process_list()) / max(1, total_processes)
        
        # Update charts
        self.update_cpu_chart()
        self.update_memory_chart()
        self.update_process_chart()
        
        # Update statistics
        self.update_statistics()
        
        # Schedule next update
        if self.monitoring_active:
            self.main_frame.after(2000, self.update_monitoring)  # Update every 2 seconds
            
    def update_cpu_chart(self):
        """Update CPU usage chart"""
        self.cpu_ax.clear()
        processes = self.pm.get_process_list()
        if processes:
            names = [p.name for p in processes]
            cpu_usage = [p.cpu_usage for p in processes]
            self.cpu_ax.bar(names, cpu_usage, color='skyblue')
            self.cpu_ax.set_ylabel('CPU Usage (%)')
            self.cpu_ax.set_title('Process CPU Usage')
            self.cpu_ax.tick_params(axis='x', rotation=45)
        self.cpu_canvas.draw()
        
    def update_memory_chart(self):
        """Update memory usage chart"""
        self.mem_ax.clear()
        processes = self.pm.get_process_list()
        if processes:
            names = [p.name for p in processes]
            memory = [p.memory_required for p in processes]
            self.mem_ax.bar(names, memory, color='lightgreen')
            self.mem_ax.set_ylabel('Memory (MB)')
            self.mem_ax.set_title('Process Memory Usage')
            self.mem_ax.tick_params(axis='x', rotation=45)
        self.mem_canvas.draw()
        
    def update_process_chart(self):
        """Update process state chart"""
        self.proc_ax.clear()
        processes = self.pm.get_process_list()
        if processes:
            states = {}
            for process in processes:
                state = process.state.value
                states[state] = states.get(state, 0) + 1
            
            self.proc_ax.pie(states.values(), labels=states.keys(), autopct='%1.1f%%', startangle=90)
            self.proc_ax.set_title('Process States')
        self.proc_canvas.draw()
        
    def update_statistics(self):
        """Update statistics display"""
        processes = self.pm.get_process_list()
        total_processes = len(processes)
        running_processes = len([p for p in processes if p.state == ProcessState.RUNNING])
        ready_processes = len([p for p in processes if p.state == ProcessState.READY])
        waiting_processes = len([p for p in processes if p.state == ProcessState.WAITING])
        terminated_processes = len([p for p in processes if p.state == ProcessState.TERMINATED])
        
        total_cpu = sum(p.cpu_usage for p in processes)
        avg_cpu = total_cpu / total_processes if total_processes else 0
        
        self.monitor_labels["Total Processes"].config(text=str(total_processes))
        self.monitor_labels["Running"].config(text=str(running_processes))
        self.monitor_labels["Ready"].config(text=str(ready_processes))
        self.monitor_labels["Waiting"].config(text=str(waiting_processes))
        self.monitor_labels["Terminated"].config(text=str(terminated_processes))
        self.monitor_labels["Context Switches"].config(text=str(self.pm.context_switches))
        self.monitor_labels["System Load"].config(text=f"{self.pm.system_load:.1f}%")
        self.monitor_labels["Avg CPU Time"].config(text=f"{avg_cpu:.1f}ms")

    def refresh_process_tree(self):
        """Refresh the process tree display"""
        if not getattr(self, 'process_tree', None):
            return
        # Clear current tree
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
            
        # Build process tree
        root_processes = [p for p in self.pm.get_process_list() if p.parent_pid is None]
        
        for process in root_processes:
            self._add_process_to_tree(process)
            
    def _add_process_to_tree(self, process, parent_item=""):
        """Recursively add process to tree"""
        # Determine icon based on state
        if process.state == ProcessState.RUNNING:
            icon = "▶️"
        elif process.state == ProcessState.READY:
            icon = "⏸️"
        elif process.state == ProcessState.WAITING:
            icon = "⏳"
        elif process.state == ProcessState.TERMINATED:
            icon = "❌"
        elif process.state == ProcessState.SUSPENDED:
            icon = "⏯️"
        else:
            icon = "🆕"
            
        display_text = f"{icon} {process.name} (PID: {process.pid})"
        item = self.process_tree.insert(parent_item, "end", text=display_text,
                                      values=(process.pid, process.name, process.state.value,
                                              f"{process.cpu_usage:.1f}%", f"{process.memory_required}MB"))
        
        # Add children
        children = [p for p in self.pm.get_process_list() if p.parent_pid == process.pid]
        for child in children:
            self._add_process_to_tree(child, item)
            
    def show_process_details(self):
        """Show detailed information about selected process"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a process")
            return
        
        pid = self.tree.item(selection[0])['values'][0]
        process = self.pm.get_process(pid)
        if not process:
            return
            
        # Create details dialog
        dialog = tk.Toplevel(self.main_frame)
        dialog.title(f"Process Details - {process.name}")
        dialog.geometry("500x600")
        dialog.configure(bg=self.colors["bg"])
        
        # Create scrollable frame
        canvas = tk.Canvas(dialog, bg=self.colors["bg"])
        scrollbar = tk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Process information
        info_frame = tk.Frame(scrollable_frame, bg=self.colors["card"], relief="raised", bd=2)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(info_frame, text="Process Information", bg=self.colors["card"], fg=self.colors["text"],
                font=("Arial", 12, "bold")).pack(pady=5)
        
        details = [
            ("PID", process.pid),
            ("Name", process.name),
            ("State", process.state.value),
            ("Priority", process.priority),
            ("Owner", process.owner),
            ("Memory Required", f"{process.memory_required} MB"),
            ("CPU Usage", f"{process.cpu_usage:.1f}%"),
            ("CPU Time", f"{process.cpu_time} ms"),
            ("I/O Operations", process.io_operations),
            ("Page Faults", process.page_faults),
            ("Parent PID", process.parent_pid or "None"),
            ("Created", process.created_at.strftime("%Y-%m-%d %H:%M:%S") if process.created_at else "N/A"),
            ("Started", process.started_at.strftime("%Y-%m-%d %H:%M:%S") if process.started_at else "N/A"),
            ("Ended", process.ended_at.strftime("%Y-%m-%d %H:%M:%S") if process.ended_at else "N/A"),
        ]
        
        for label, value in details:
            frame = tk.Frame(info_frame, bg=self.colors["card"])
            frame.pack(fill="x", padx=10, pady=2)
            tk.Label(frame, text=f"{label}:", bg=self.colors["card"], fg=self.colors["text"], width=15, anchor="w").pack(side="left")
            tk.Label(frame, text=str(value), bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        
        # Close button
        tk.Button(scrollable_frame, text="Close", command=dialog.destroy, bg=self.colors["accent"], fg="#000000").pack(pady=10)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def manual_schedule(self):
        """Manually schedule next process"""
        self.pm.schedule_processes()
        self.refresh_process_list()
        self.update_scheduling_display()
        self.update_monitoring()
        self.log("Manual scheduling executed")
        
    def toggle_auto_schedule(self):
        """Toggle automatic scheduling"""
        if self.auto_schedule_var.get():
            self.log("Auto scheduling enabled")
            self.run_auto_schedule()
        else:
            self.log("Auto scheduling disabled")
            
    def run_auto_schedule(self):
        """Run automatic scheduling"""
        if self.auto_schedule_var.get():
            self.pm.schedule_processes()
            self.refresh_process_list()
            self.update_scheduling_display()
            self.update_monitoring()
            self.main_frame.after(2000, self.run_auto_schedule)  # Schedule every 2 seconds
            
    def set_quantum(self):
        """Set quantum for Round Robin scheduling"""
        try:
            quantum = int(self.quantum_var.get())
            if quantum > 0:
                self.pm.quantum = quantum
                self.log(f"Quantum set to {quantum}ms")
                self.save_state()
            else:
                messagebox.showerror("Error", "Quantum must be positive")
        except ValueError:
            messagebox.showerror("Error", "Invalid quantum value")
            
    def save_state(self):
        state = {
            'processes': [p.to_dict() for p in self.pm.get_process_list()],
            'scheduling_algorithm': self.pm.scheduling_algorithm,
            'quantum': self.pm.quantum
        }
        self.device_manager.update_device_state(self.device, {'process_manager_state': state})

    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()
