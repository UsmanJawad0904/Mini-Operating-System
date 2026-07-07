"""
Advanced Features Module - Ultra Advanced Edition
Real-time Process Simulation, Banker's Algorithm Visualization, Live Performance Monitoring
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random
from datetime import datetime
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from collections import deque

try:
    import psutil
except ImportError:
    psutil = None


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
    
    def get_content_frame(self):
        return self.scrollable_frame
class AdvancedFeaturesUI:
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager, colors):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        self.colors = colors
        self.sim_running = False
        self.process_count = 0
        self.processes_data = []
        self.process_queue = deque()
        self.process_log = deque(maxlen=120)
        self.cpu_usage = 0
        self.memory_usage = 0
        self.performance_score = 100.0
        self.monitoring = True
        self.quantum = 4
        self.schedule_var = tk.StringVar(value="FCFS")
        self.sim_thread = None
        self.graph_timer_id = None  # Store after() ID for cleanup
        self.setup_ui()
        self.load_saved_state()
        
    def setup_ui(self):
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header with device info
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10))
        
        tk.Label(header, text="🚀 Advanced Features", font=("Segoe UI", 28, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack()
        tk.Label(header, text=f"Device: {self.device.name} | CPU: {self.device.cpu_cores} Cores | RAM: {self.device.memory_size}MB", 
                font=("Segoe UI", 12), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Tab 1: Process Simulator
        self.create_process_sim_tab(notebook)
        
        # Tab 2: Banker's Algorithm Visual
        self.create_bankers_tab(notebook)
        
        # Tab 3: Performance Monitor with Graphs
        self.create_monitor_tab(notebook)
        
        # Tab 4: System Analyzer
        self.create_analyzer_tab(notebook)
        
        self.notebook = notebook
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Back button
        back_btn = tk.Button(self.main_frame, text="← Back to Dashboard", command=self.go_back,
                            bg=self.colors["text_muted"], fg="white", font=("Segoe UI", 11),
                            cursor="hand2", padx=20, pady=8)
        back_btn.pack(pady=20)
        
    def create_process_sim_tab(self, notebook):
        """Advanced Process Simulator Tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="⚡ Process Simulator")
        
        # Control panel
        control_frame = tk.Frame(tab, bg=self.colors["bg"])
        control_frame.pack(fill="x", pady=10, padx=20)
        
        scheduler_frame = tk.Frame(control_frame, bg=self.colors["card"])
        scheduler_frame.pack(fill="x", pady=10)
        tk.Label(scheduler_frame, text="Scheduler:", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=(10, 10))
        self.schedule_cb = ttk.Combobox(scheduler_frame, values=["FCFS", "SJF", "Priority", "Round Robin"],
                                        textvariable=self.schedule_var, state="readonly", width=16)
        self.schedule_cb.pack(side="left", padx=(0, 10))
        self.schedule_cb.current(0)
        tk.Label(scheduler_frame, text="Quantum:", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=(10, 10))
        self.quantum_entry = tk.Entry(scheduler_frame, width=4, bg="#0f172a", fg=self.colors["text"])
        self.quantum_entry.insert(0, str(self.quantum))
        self.quantum_entry.pack(side="left", padx=(0, 10))
        self.quantum_note = tk.Label(scheduler_frame, text="Round Robin uses quantum", bg=self.colors["card"], fg=self.colors["warning"], font=("Segoe UI", 9))
        self.quantum_note.pack(side="left", padx=(10, 10))
        
        # Statistics display
        stats_frame = tk.Frame(tab, bg=self.colors["card"])
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        stats = ["Total Processes", "Avg Burst", "Avg Memory", "CPU Load"]
        self.stats_labels = {}
        
        for i, stat in enumerate(stats):
            frame = tk.Frame(stats_frame, bg=self.colors["card"])
            frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            tk.Label(frame, text=stat, font=("Segoe UI", 10), bg=self.colors["card"], fg=self.colors["text_muted"]).pack()
            lbl = tk.Label(frame, text="0", font=("Segoe UI", 18, "bold"), bg=self.colors["card"], fg=self.colors["success"])
            lbl.pack()
            self.stats_labels[stat] = lbl
        
        stats_frame.grid_columnconfigure(list(range(4)), weight=1)
        
        list_frame = tk.Frame(tab, bg=self.colors["bg"])
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(list_frame, text="📋 Process Activity Log", font=("Segoe UI", 12, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        
        self.process_listbox = tk.Listbox(list_frame, bg="#0f172a", fg=self.colors["text"],
                                          font=("Consolas", 10), height=12)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.process_listbox.yview)
        self.process_listbox.configure(yscrollcommand=scrollbar.set)
        self.process_listbox.pack(side="left", fill="both", expand=True, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        btn_frame = tk.Frame(tab, bg=self.colors["bg"])
        btn_frame.pack(pady=10)
        
        def add_process():
            pid = random.randint(1000, 9999)
            burst = random.randint(2, 15)
            memory = random.randint(10, 100)
            priority = random.randint(1, 5)
            display = f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 P{pid} | Burst:{burst}ms | Mem:{memory}MB | Priority:{priority}"
            process = {"pid": pid, "burst": burst, "memory": memory, "priority": priority, "display": display}
            self.process_count += 1
            self.processes_data.append(process)
            self.process_listbox.insert("end", display)
            self.process_listbox.see("end")
            self.log(f"Process P{pid} created with burst {burst}ms")
            self.update_process_stats()
            self.save_state()
        
        def start_simulation():
            self.sim_running = True
            self.log("Process simulation started")
        
        def stop_simulation():
            self.sim_running = False
            self.log("Process simulation stopped")
        
        def clear_processes():
            self.process_listbox.delete(0, tk.END)
            self.process_count = 0
            self.processes_data = []
            self.update_process_stats()
            self.log("Cleared all processes")
            self.save_state()
        
        btn_start = tk.Button(btn_frame, text="▶ Start Auto-Sim", command=start_simulation,
                             bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"),
                             cursor="hand2", padx=15)
        btn_start.pack(side="left", padx=5)
        
        btn_stop = tk.Button(btn_frame, text="⏸ Stop", command=stop_simulation,
                            bg=self.colors["danger"], fg="white", font=("Segoe UI", 10, "bold"),
                            cursor="hand2", padx=15)
        btn_stop.pack(side="left", padx=5)
        
        btn_add = tk.Button(btn_frame, text="➕ Add Process", command=add_process,
                           bg=self.colors.get("info", self.colors["accent"]), fg="white", font=("Segoe UI", 10, "bold"),
                           cursor="hand2", padx=15)
        btn_add.pack(side="left", padx=5)
        
        btn_clear = tk.Button(btn_frame, text="🗑 Clear All", command=clear_processes,
                             bg=self.colors["warning"], fg="white", font=("Segoe UI", 10, "bold"),
                             cursor="hand2", padx=15)
        btn_clear.pack(side="left", padx=5)
        
        def auto_simulate():
            while True:
                if self.sim_running:
                    self.process_listbox.after(0, self.step_simulation)
                time.sleep(2)
        
        self.sim_thread = threading.Thread(target=auto_simulate, daemon=True)
        self.sim_thread.start()

    def refresh_process_list(self):
        self.process_listbox.delete(0, tk.END)
        for proc in self.processes_data:
            self.process_listbox.insert("end", proc.get("display", ""))
        self.process_listbox.see("end")

    def update_process_stats(self):
        active = len(self.processes_data)
        avg_burst = sum(p["burst"] for p in self.processes_data) / active if active else 0
        avg_memory = sum(p["memory"] for p in self.processes_data) / active if active else 0
        sys_cpu = psutil.cpu_percent(interval=None) if psutil else 0
        cpu_load = min(100, int(active * 5 + avg_memory / 2 + sys_cpu * 0.15))
        self.performance_score = max(0, 100 - cpu_load * 0.3)
        self.stats_labels["Total Processes"].config(text=str(self.process_count))
        self.stats_labels["Avg Burst"].config(text=f"{avg_burst:.1f}ms")
        self.stats_labels["Avg Memory"].config(text=f"{avg_memory:.0f}MB")
        self.stats_labels["CPU Load"].config(text=f"{cpu_load}%")
        self.process_listbox.configure(bg="#0f172a")

    def step_simulation(self):
        if not self.processes_data:
            return
        active = self.processes_data
        algo = self.schedule_var.get()
        if algo == "FCFS":
            proc = active[0]
        elif algo == "SJF":
            proc = min(active, key=lambda p: p["burst"])
        elif algo == "Priority":
            proc = min(active, key=lambda p: p["priority"])
        else:
            proc = min(active, key=lambda p: p["burst"])
        try:
            quantum = int(self.quantum_entry.get())
        except Exception:
            quantum = self.quantum
        consumed = min(quantum, proc["burst"])
        proc["burst"] -= consumed
        proc["display"] = f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 P{proc['pid']} | Burst:{proc['burst']}ms | Mem:{proc['memory']}MB | Pri:{proc['priority']}"
        self.log(f"Simulated {algo} for P{proc['pid']} (-{consumed}ms)")
        if proc["burst"] <= 0:
            self.processes_data.remove(proc)
            self.process_listbox.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Completed P{proc['pid']}")
        self.refresh_process_list()
        self.update_process_stats()
        self.save_state()

    def load_saved_state(self):
        saved = getattr(self.device, 'extra_state', {}).get('advanced_features_state', {})
        if not saved:
            return
        self.process_count = saved.get('process_count', 0)
        self.processes_data = saved.get('processes_data', [])
        for proc in self.processes_data:
            self.process_listbox.insert('end', proc.get('display', ''))
        self.schedule_var.set(saved.get('scheduler', 'FCFS'))
        if hasattr(self, 'schedule_cb'):
            self.schedule_cb.set(self.schedule_var.get())
        self.quantum_entry.delete(0, tk.END)
        self.quantum_entry.insert(0, str(saved.get('quantum', self.quantum)))
        self.stats_labels['Total Processes'].config(text=str(self.process_count))
        self.stats_labels['Avg Burst'].config(text=saved.get('avg_burst', '0'))
        self.stats_labels['Avg Memory'].config(text=saved.get('avg_memory', '0'))
        self.stats_labels['CPU Load'].config(text=saved.get('cpu_load', '0'))
        if 'performance_score' in saved and 'Performance Score' in self.monitor_labels:
            self.monitor_labels['Performance Score'].config(text=str(saved.get('performance_score', '100')))

    def save_state(self):
        state = {
            'process_count': self.process_count,
            'processes_data': self.processes_data,
            'scheduler': self.schedule_var.get(),
            'quantum': self.quantum_entry.get(),
            'avg_burst': self.stats_labels['Avg Burst'].cget('text'),
            'avg_memory': self.stats_labels['Avg Memory'].cget('text'),
            'cpu_load': self.stats_labels['CPU Load'].cget('text'),
            'performance_score': getattr(self, 'performance_score', 100)
        }
        self.device_manager.update_device_state(self.device, {'advanced_features_state': state})

    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()
        
    def create_bankers_tab(self, notebook):
        """Advanced Banker's Algorithm Visualization Tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="🔒 Banker's Algorithm")
        
        # Main container
        main_container = tk.Frame(tab, bg=self.colors["bg"])
        main_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Available resources display
        avail_frame = tk.Frame(main_container, bg=self.colors["card"])
        avail_frame.pack(fill="x", pady=10)
        
        tk.Label(avail_frame, text="📊 Available Resources", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        self.avail_vars = []
        avail_values = [10, 5, 7]
        resources = ["Resource A", "Resource B", "Resource C"]
        
        for i, (res, val) in enumerate(zip(resources, avail_values)):
            frame = tk.Frame(avail_frame, bg=self.colors["card"])
            frame.pack(side="left", expand=True, padx=20, pady=10)
            tk.Label(frame, text=res, font=("Segoe UI", 11), bg=self.colors["card"], fg=self.colors["text_muted"]).pack()
            var = tk.StringVar(value=str(val))
            self.avail_vars.append(var)
            tk.Label(frame, textvariable=var, font=("Segoe UI", 20, "bold"),
                    bg=self.colors["card"], fg=self.colors["success"]).pack()
        
        # Process table
        table_frame = tk.Frame(main_container, bg=self.colors["card"])
        table_frame.pack(fill="both", expand=True, pady=10)
        
        tk.Label(table_frame, text="📋 Process Allocation Table", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        # Treeview for process data
        columns = ("Process", "Max_A", "Max_B", "Max_C", "Alloc_A", "Alloc_B", "Alloc_C", "Need_A", "Need_B", "Need_C")
        self.process_tree = ttk.Treeview(table_frame, columns=columns, height=6, show="headings")
        
        col_widths = {"Process": 70, "Max_A": 60, "Max_B": 60, "Max_C": 60,
                      "Alloc_A": 60, "Alloc_B": 60, "Alloc_C": 60,
                      "Need_A": 60, "Need_B": 60, "Need_C": 60}
        
        for col in columns:
            self.process_tree.heading(col, text=col)
            self.process_tree.column(col, width=col_widths.get(col, 70), anchor="center")
        
        scrollbar = tk.Scrollbar(table_frame, orient="vertical", command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)
        
        self.process_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Sample data
        self.process_data = [
            ("P0", 7, 5, 3, 0, 1, 0),
            ("P1", 3, 2, 2, 2, 0, 0),
            ("P2", 9, 0, 2, 3, 0, 2),
            ("P3", 2, 2, 2, 2, 1, 1),
            ("P4", 4, 3, 3, 0, 0, 2),
        ]
        
        for data in self.process_data:
            name, ma, mb, mc, aa, ab, ac = data
            need = [ma - aa, mb - ab, mc - ac]
            self.process_tree.insert("", "end", values=(name, ma, mb, mc, aa, ab, ac, need[0], need[1], need[2]))
        
        # Control buttons
        btn_frame = tk.Frame(main_container, bg=self.colors["bg"])
        btn_frame.pack(pady=10)
        
        def check_safe():
            """Check if system is in safe state"""
            available = [10, 5, 7]
            max_need = [[7,5,3], [3,2,2], [9,0,2], [2,2,2], [4,3,3]]
            allocation = [[0,1,0], [2,0,0], [3,0,2], [2,1,1], [0,0,2]]
            need = [[max_need[i][j] - allocation[i][j] for j in range(3)] for i in range(5)]
            
            work = available.copy()
            finish = [False] * 5
            safe_seq = []
            
            while len(safe_seq) < 5:
                found = False
                for i in range(5):
                    if not finish[i] and all(need[i][j] <= work[j] for j in range(3)):
                        for j in range(3):
                            work[j] += allocation[i][j]
                        finish[i] = True
                        safe_seq.append(f"P{i}")
                        found = True
                        break
                if not found:
                    break
            
            if len(safe_seq) == 5:
                messagebox.showinfo("Safe State", f"✅ System is SAFE!\n\nSafe Sequence: {' → '.join(safe_seq)}")
            else:
                messagebox.showwarning("Unsafe State", "❌ System is UNSAFE! Deadlock possible!")
        
        def reset_system():
            """Reset to default state"""
            for i, data in enumerate(self.process_data):
                self.process_tree.item(self.process_tree.get_children()[i], 
                                       values=(data[0], data[1], data[2], data[3], data[4], data[5], data[6],
                                              data[1]-data[4], data[2]-data[5], data[3]-data[6]))
            for i, var in enumerate(self.avail_vars):
                var.set([10, 5, 7][i])
            messagebox.showinfo("Reset", "System reset to default state")
        
        btn_check = tk.Button(btn_frame, text="🔍 Check Safe State", command=check_safe,
                             bg=self.colors["info"], fg="white", font=("Segoe UI", 11, "bold"),
                             cursor="hand2", padx=20)
        btn_check.pack(side="left", padx=10)
        
        btn_reset = tk.Button(btn_frame, text="🔄 Reset System", command=reset_system,
                             bg=self.colors["warning"], fg="white", font=("Segoe UI", 11, "bold"),
                             cursor="hand2", padx=20)
        btn_reset.pack(side="left", padx=10)
        
        # Info text
        info_frame = tk.Frame(main_container, bg=self.colors["card"])
        info_frame.pack(fill="x", pady=10)
        
        info_text = """
        💡 Banker's Algorithm - Deadlock Avoidance
        
        The system is in a SAFE state if there exists a sequence where all processes can complete.
        Current safe sequence: P1 → P3 → P4 → P0 → P2
        """
        
        info_label = tk.Label(info_frame, text=info_text, font=("Segoe UI", 10),
                             bg=self.colors["card"], fg=self.colors["text_muted"], justify="left")
        info_label.pack(pady=10, padx=20)
        
    def create_monitor_tab(self, notebook):
        """Advanced Performance Monitor with Live Graphs"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="📊 Performance Monitor")
        self.monitor_tab = tab
        
        # Statistics cards
        stats_frame = tk.Frame(tab, bg=self.colors["bg"])
        stats_frame.pack(fill="x", pady=10, padx=20)
        
        stats = [
            ("CPU Usage", "0%", self.colors["accent"]),
            ("Memory Usage", "0%", self.colors["success"]),
            ("Active Processes", "0", self.colors["warning"]),
            ("Response Time", "0ms", self.colors["info"]),
            ("Throughput", "0/s", self.colors["purple"]),
            ("System Load", "0.00", self.colors["cyan"]),
            ("Performance Score", "100", self.colors["success"])
        ]
        
        self.monitor_labels = {}
        
        for i, (label, val, color) in enumerate(stats):
            frame = tk.Frame(stats_frame, bg=self.colors["card"])
            frame.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew", ipadx=20, ipady=10)
            tk.Label(frame, text=label, font=("Segoe UI", 10), bg=self.colors["card"], fg=self.colors["text_muted"]).pack()
            lbl = tk.Label(frame, text=val, font=("Segoe UI", 20, "bold"), bg=self.colors["card"], fg=color)
            lbl.pack()
            self.monitor_labels[label] = lbl
        
        for i in range(3):
            stats_frame.grid_rowconfigure(i, weight=1)
        for i in range(3):
            stats_frame.grid_columnconfigure(i, weight=1)
        
        # Live graph
        graph_frame = tk.Frame(tab, bg=self.colors["bg"])
        graph_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(graph_frame, text="📈 Real-time Performance Graph", font=("Segoe UI", 14, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        
        # Matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(10, 3), facecolor=self.colors["bg"])
        self.ax.set_facecolor(self.colors["card"])
        self.ax.set_xlabel('Time (seconds)', color=self.colors["text"])
        self.ax.set_ylabel('Usage (%)', color=self.colors["text"])
        self.ax.tick_params(colors=self.colors["text"])
        self.ax.set_ylim(0, 100)
        
        self.cpu_data = deque(maxlen=50)
        self.mem_data = deque(maxlen=50)
        self.time_data = deque(maxlen=50)
        
        self.cpu_line, = self.ax.plot([], [], 'r-', label='CPU', linewidth=2)
        self.mem_line, = self.ax.plot([], [], 'b-', label='Memory', linewidth=2)
        self.ax.legend(loc='upper right', facecolor=self.colors["card"], labelcolor=self.colors["text"])
        
        canvas = FigureCanvasTkAgg(self.fig, graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)
        
        self.monitoring = True
        self.monitor_visible = False
        self.current_monitor_metrics = None
        
        def update_graph():
            metrics = self.generate_monitor_metrics()
            self.current_monitor_metrics = metrics
            self.cpu_data.append(metrics["cpu"])
            self.mem_data.append(metrics["mem"])
            self.time_data.append(len(self.time_data))
            
            if self.monitoring:
                self.cpu_line.set_data(range(len(self.cpu_data)), list(self.cpu_data))
                self.mem_line.set_data(range(len(self.mem_data)), list(self.mem_data))
                self.ax.set_xlim(0, max(50, len(self.cpu_data)))
                self.apply_monitor_metrics(metrics)
                self.fig.canvas.draw_idle()
                self.fig.canvas.flush_events()
            
            self.graph_timer_id = tab.after(1000, update_graph)
        
        update_graph()
        
        def stop_monitoring():
            self.monitoring = False
            self.log("Performance monitoring paused")
            messagebox.showinfo("Monitor", "Performance monitoring paused")
            
        stop_btn = tk.Button(tab, text="⏹ Pause Monitoring", command=stop_monitoring,
                            bg=self.colors["danger"], fg="white", font=("Segoe UI", 11, "bold"),
                            cursor="hand2", padx=20, pady=5)
        stop_btn.pack(pady=10)

    def generate_monitor_metrics(self):
        sys_cpu = psutil.cpu_percent(interval=None) if psutil else random.randint(5, 80)
        sys_mem = psutil.virtual_memory().percent if psutil else random.randint(10, 85)
        active = len(self.processes_data)
        total_burst = sum(p["burst"] for p in self.processes_data) if self.processes_data else 0
        total_memory = sum(p["memory"] for p in self.processes_data) if self.processes_data else 0
        workload_cpu = min(80, active * 4 + total_burst / 8)
        workload_mem = min(85, active * 3 + total_memory / 25)
        cpu = min(100, max(5, int(sys_cpu * 0.65 + workload_cpu * 0.35 + random.uniform(-4, 4))))
        mem = min(100, max(10, int(sys_mem * 0.6 + workload_mem * 0.4 + random.uniform(-4, 4))))
        response_time = max(15, int(80 + active * 5 + cpu * 0.35 + mem * 0.18 - total_memory * 0.02))
        throughput = max(1, int(active * 1.4 + (100 - cpu) * 0.06 + random.uniform(-1, 1)))
        performance_score = max(0, min(100, 100 - (cpu * 0.28 + mem * 0.18 + active * 1.2)))
        system_load = max(0.50, min(10.0, (cpu / 25 + mem / 40 + active * 0.18)))
        return {
            "cpu": cpu,
            "mem": mem,
            "active": active,
            "response_time": response_time,
            "throughput": throughput,
            "performance_score": performance_score,
            "system_load": system_load
        }

    def apply_monitor_metrics(self, metrics):
        self.monitor_labels["CPU Usage"].config(text=f"{metrics['cpu']}%")
        self.monitor_labels["Memory Usage"].config(text=f"{metrics['mem']}%")
        self.monitor_labels["Active Processes"].config(text=f"{metrics['active']}")
        self.monitor_labels["Response Time"].config(text=f"{metrics['response_time']}ms")
        self.monitor_labels["Throughput"].config(text=f"{metrics['throughput']}/s")
        self.monitor_labels["System Load"].config(text=f"{metrics['system_load']:.2f}")
        self.monitor_labels["Performance Score"].config(text=f"{metrics['performance_score']:.0f}")
        self.performance_score = metrics['performance_score']

    def on_tab_changed(self, event):
        selected = event.widget.select()
        if selected == str(self.monitor_tab):
            self.monitor_visible = True
            if self.current_monitor_metrics and self.monitoring:
                self.apply_monitor_metrics(self.current_monitor_metrics)
        else:
            self.monitor_visible = False

    def create_analyzer_tab(self, notebook):
        """System Analyzer Tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="🔍 System Analyzer")
        
        # System health check
        health_frame = tk.Frame(tab, bg=self.colors["card"])
        health_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(health_frame, text="🏥 System Health Check", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        health_items = [
            ("Memory Status", "Optimal", self.colors["success"]),
            ("CPU Status", "Normal", self.colors["success"]),
            ("Storage Status", "Healthy", self.colors["success"]),
            ("Process Load", "Moderate", self.colors["warning"]),
        ]
        
        for i, (item, status, color) in enumerate(health_items):
            frame = tk.Frame(health_frame, bg=self.colors["card"])
            frame.pack(fill="x", pady=5, padx=20)
            tk.Label(frame, text=item, font=("Segoe UI", 11), bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
            tk.Label(frame, text=status, font=("Segoe UI", 11, "bold"), bg=self.colors["card"], fg=color).pack(side="right")
        
        # Recommendations
        rec_frame = tk.Frame(tab, bg=self.colors["card"])
        rec_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(rec_frame, text="💡 System Recommendations", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        recommendations = [
            "• Monitor CPU usage - consider upgrading if consistently above 80%",
            "• Memory usage is optimal - no action needed",
            "• Process count is normal for current workload",
            "• System stability is good"
        ]
        
        for rec in recommendations:
            tk.Label(rec_frame, text=rec, font=("Segoe UI", 10), bg=self.colors["card"],
                    fg=self.colors["text_muted"], anchor="w").pack(fill="x", padx=20, pady=2)
        
        # Device info
        info_frame = tk.Frame(tab, bg=self.colors["card"])
        info_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(info_frame, text="🖥️ Device Configuration", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        stats = self.device_manager.get_device_stats(self.device)
        
        config_items = [
            (f"Device Name: {self.device.name}", self.colors["accent"]),
            (f"Total Memory: {stats['total_memory']} MB", self.colors["success"]),
            (f"Storage Capacity: {stats['total_storage'] // 1024} MB", self.colors["warning"]),
            (f"CPU Cores: {self.device.cpu_cores}", self.colors["info"]),
            (f"Created: {self.device.created_date.strftime('%Y-%m-%d')}", self.colors["purple"]),
            (f"Last Used: {self.device.last_used.strftime('%Y-%m-%d %H:%M')}", self.colors["cyan"])
        ]
        
        for text, color in config_items:
            tk.Label(info_frame, text=text, font=("Segoe UI", 11), bg=self.colors["card"],
                    fg=color, anchor="w").pack(fill="x", padx=20, pady=3)
        
    def cleanup_timers(self):
        """Cancel any running timers"""
        if self.graph_timer_id:
            try:
                self.main_frame.after_cancel(self.graph_timer_id)
            except:
                pass  # Timer might already be cancelled
        
    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()