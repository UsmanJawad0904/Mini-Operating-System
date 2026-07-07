"""
CPU Scheduling Module - Enhanced with Persistent Device Support
Modern UI matching ProcessManager style with improved data persistence
"""

import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import json


class SchedulerUI:
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        
        self.colors = {"bg": "#1e1e2e", "card": "#313244", "accent": "#cba6f7", "success": "#a6e3a1",
                       "warning": "#f9e2af", "danger": "#f38ba8", "text": "#cdd6f4", "text_muted": "#6c7086"}
        
        self.setup_ui()
        self.load_saved_state()
        
    def load_saved_state(self):
        scheduler_state = getattr(self.device, 'extra_state', {}).get('scheduler_state', {})
        if scheduler_state:
            self.algo_var.set(scheduler_state.get('algorithm', 'FCFS'))
            self.on_algo_change()
            self.quantum_entry.delete(0, tk.END)
            self.quantum_entry.insert(0, scheduler_state.get('quantum', '2'))
            saved_results = scheduler_state.get('last_results', '')
            if saved_results:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, saved_results)

        if hasattr(self.device, 'processes') and self.device.processes:
            for process in self.device.processes:
                self.tree.insert("", "end", text=process['name'], 
                                values=(process['arrival'], process['burst'], process['priority']))
            self.log(f"Loaded {len(self.device.processes)} saved processes")
        
    def save_state(self):
        self.device.processes = self.get_processes()
        if not hasattr(self.device, 'scheduling_history'):
            self.device.scheduling_history = []
        self.device.scheduling_history.append({
            'timestamp': datetime.now().isoformat(),
            'algorithm': self.algo_var.get(),
            'process_count': len(self.device.processes)
        })
        self.device_manager.update_device_state(self.device, {
            "processes": self.device.processes,
            "scheduler_state": {
                "algorithm": self.algo_var.get(),
                "quantum": self.quantum_entry.get(),
                "last_results": self.results_text.get(1.0, tk.END).strip()
            },
            "scheduling_history": self.device.scheduling_history
        })
        
    def setup_ui(self):
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10), padx=20)
        tk.Label(header, text="⚡ CPU Scheduler", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        tk.Label(header, text=f"Device: {self.device.name} | RAM: {self.device.memory_size}MB | CPU: {self.device.cpu_cores} Cores", 
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(4, 0))
        
        content = tk.Frame(self.main_frame, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        top_row = tk.Frame(content, bg=self.colors["bg"])
        top_row.pack(fill="both", expand=False)
        bottom_row = tk.Frame(content, bg=self.colors["bg"])
        bottom_row.pack(fill="both", expand=True, pady=(10, 0))
        
        input_card = tk.LabelFrame(top_row, text="Add New Process", bg=self.colors["card"],
                                   fg=self.colors["text"], font=("Segoe UI", 12, "bold"))
        input_card.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        
        fields = ["Process Name:", "Arrival Time:", "Burst Time:", "Priority:"]
        self.entries = {}
        for label in fields:
            frame = tk.Frame(input_card, bg=self.colors["card"])
            frame.pack(fill="x", pady=6, padx=15)
            tk.Label(frame, text=label, width=14, anchor="w", bg=self.colors["card"], fg=self.colors["text_muted"]).pack(side="left")
            entry = tk.Entry(frame, bg="#0f172a", fg=self.colors["text"], width=20)
            entry.pack(side="left", padx=10)
            self.entries[label] = entry
        
        tk.Button(input_card, text="➕ Add Process", command=self.add_process,
                 bg=self.colors["success"], fg="#000000", font=("Segoe UI", 11, "bold"), cursor="hand2").pack(pady=10)
        
        list_card = tk.LabelFrame(bottom_row, text="Process List", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 12, "bold"))
        list_card.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        
        tree_frame = tk.Frame(list_card, bg=self.colors["card"])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Arrival", "Burst", "Priority"), height=10)
        self.tree.heading("#0", text="Process")
        self.tree.heading("Arrival", text="Arrival")
        self.tree.heading("Burst", text="Burst")
        self.tree.heading("Priority", text="Priority")
        self.tree.column("#0", width=100)
        self.tree.column("Arrival", width=80, anchor="center")
        self.tree.column("Burst", width=80, anchor="center")
        self.tree.column("Priority", width=80, anchor="center")
        scrollbar = tk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        tk.Button(list_card, text="Clear All", command=self.clear_processes,
                 bg=self.colors["danger"], fg="white", cursor="hand2").pack(pady=(0, 10))
        
        right = tk.Frame(top_row, bg=self.colors["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        algo_card = tk.LabelFrame(right, text="Scheduling Options", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 12, "bold"))
        algo_card.pack(fill="both", expand=True, pady=10)
        
        self.algo_var = tk.StringVar(value="FCFS")
        tk.Label(algo_card, text="Select Algorithm:", font=("Segoe UI", 12),
                bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w", padx=15, pady=(12, 4))
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Dark.TCombobox", fieldbackground="#0f172a", background="#0f172a",
                        foreground=self.colors["text"], selectforeground=self.colors["text"], selectbackground="#0f172a")
        self.algo_select = ttk.Combobox(algo_card, values=["FCFS", "SJF", "Priority", "Round Robin"],
                                       textvariable=self.algo_var, state="readonly", font=("Segoe UI", 11), style="Dark.TCombobox")
        self.algo_select.pack(fill="x", padx=15)
        self.algo_select.current(0)
        
        self.algo_description = tk.Label(algo_card, text="Choose an algorithm to simulate CPU scheduling behavior.",
                                         bg=self.colors["card"], fg=self.colors["text_muted"], wraplength=280, justify="left")
        self.algo_description.pack(fill="x", padx=15, pady=(8, 10))
        
        quantum_frame = tk.Frame(algo_card, bg=self.colors["card"])
        quantum_frame.pack(fill="x", padx=15, pady=(0, 10))
        tk.Label(quantum_frame, text="Time Quantum:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.quantum_entry = tk.Entry(quantum_frame, width=6, bg="#0f172a", fg=self.colors["text"])
        self.quantum_entry.pack(side="left", padx=8)
        self.quantum_entry.insert(0, "2")
        
        self.quantum_note = tk.Label(algo_card, text="Quantum only applies to Round Robin.",
                                     bg=self.colors["card"], fg=self.colors["warning"], font=("Segoe UI", 9))
        self.quantum_note.pack(anchor="w", padx=15, pady=(0, 10))
        
        self.algo_var.trace_add("write", self.on_algo_change)
        self.on_algo_change()
        
        tk.Button(algo_card, text="▶ RUN SIMULATION", command=self.run_scheduler,
                 bg=self.colors["accent"], fg="white", font=("Segoe UI", 13, "bold"), cursor="hand2", padx=30, pady=10).pack(pady=(0, 15))
        
        results_card = tk.LabelFrame(bottom_row, text="Results", bg=self.colors["card"],
                                     fg=self.colors["text"], font=("Segoe UI", 12, "bold"))
        results_card.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        
        text_frame = tk.Frame(results_card, bg=self.colors["card"])
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.results_text = tk.Text(text_frame, bg="#0f172a", fg=self.colors["text"], font=("Consolas", 10), wrap="word", height=14)
        scroll_y = tk.Scrollbar(text_frame, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scroll_y.set)
        self.results_text.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        
        footer = tk.Frame(self.main_frame, bg=self.colors["bg"])
        footer.pack(fill="x", pady=10, padx=20)
        tk.Button(footer, text="💾 Save State", command=self.save_state,
                 bg=self.colors["success"], fg="#000000", cursor="hand2").pack(side="right", padx=5)
        tk.Button(footer, text="← Back", command=self.go_back,
                 bg=self.colors["text_muted"], fg="#000000", cursor="hand2").pack(side="right", padx=5)
        
        self.add_sample_processes()
        
    def add_process(self):
        name = self.entries["Process Name:"].get().strip()
        arrival = self.entries["Arrival Time:"].get().strip()
        burst = self.entries["Burst Time:"].get().strip()
        priority = self.entries["Priority:"].get().strip()
        if not name or not arrival or not burst:
            messagebox.showerror("Error", "Please fill all fields!")
            return
        try:
            self.tree.insert("", "end", text=name, values=(int(arrival), int(burst), int(priority) if priority else 1))
            for e in self.entries.values():
                e.delete(0, tk.END)
            self.log(f"Added process: {name}")
            self.save_state()
        except ValueError:
            messagebox.showerror("Error", "Invalid numbers!")
            
    def add_sample_processes(self):
        if not self.tree.get_children():
            for name, arr, burst, pri in [("P1",0,6,2),("P2",1,4,1),("P3",2,2,3),("P4",3,5,2)]:
                self.tree.insert("", "end", text=name, values=(arr, burst, pri))
            self.save_state()
            
    def clear_processes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results_text.delete(1.0, tk.END)
        self.save_state()
        
    def on_algo_change(self, *args):
        algorithm = self.algo_var.get()
        if algorithm == "Round Robin":
            self.quantum_entry.configure(state="normal")
            self.quantum_note.configure(text="Quantum only applies to Round Robin.")
        else:
            self.quantum_entry.configure(state="disabled")
            self.quantum_note.configure(text="Quantum is disabled for the selected algorithm.")

    def get_processes(self):
        processes = []
        for item in self.tree.get_children():
            v = self.tree.item(item)['values']
            processes.append({'name': self.tree.item(item)['text'], 'arrival': v[0], 'burst': v[1], 'priority': v[2]})
        return sorted(processes, key=lambda x: x['arrival'])
    
    def run_scheduler(self):
        procs = self.get_processes()
        if not procs:
            messagebox.showerror("Error", "No processes!")
            return
        algo = self.algo_var.get()
        if algo == "FCFS":
            self.fcfs(procs)
        elif algo == "SJF":
            self.sjf(procs)
        elif algo == "Priority":
            self.priority_sched(procs)
        elif algo == "Round Robin":
            try:
                self.round_robin(procs, int(self.quantum_entry.get()))
            except:
                messagebox.showerror("Error", "Invalid quantum!")
        self.log(f"Executed {algo}")
        self.save_state()
        
    def fcfs(self, procs):
        time = 0
        results = []
        for p in procs:
            if time < p['arrival']:
                time = p['arrival']
            start = time
            time += p['burst']
            ct, tat, wt = time, time - p['arrival'], time - p['arrival'] - p['burst']
            results.append((p['name'], p['arrival'], p['burst'], ct, tat, wt))
        self.display_results(results)
        
    def sjf(self, procs):
        time = 0
        results = []
        remaining = procs.copy()
        while remaining:
            avail = [p for p in remaining if p['arrival'] <= time]
            if not avail:
                time = min(p['arrival'] for p in remaining)
                continue
            short = min(avail, key=lambda x: x['burst'])
            start = time
            time += short['burst']
            ct, tat, wt = time, time - short['arrival'], time - short['arrival'] - short['burst']
            results.append((short['name'], short['arrival'], short['burst'], ct, tat, wt))
            remaining.remove(short)
        self.display_results(results)
        
    def priority_sched(self, procs):
        time = 0
        results = []
        remaining = procs.copy()
        while remaining:
            avail = [p for p in remaining if p['arrival'] <= time]
            if not avail:
                time = min(p['arrival'] for p in remaining)
                continue
            high = min(avail, key=lambda x: x['priority'])
            start = time
            time += high['burst']
            ct, tat, wt = time, time - high['arrival'], time - high['arrival'] - high['burst']
            results.append((high['name'], high['arrival'], high['burst'], ct, tat, wt))
            remaining.remove(high)
        self.display_results(results)
        
    def round_robin(self, procs, quantum):
        time = 0
        results = {}
        queue = deque()
        remaining = {p['name']: p['burst'] for p in procs}
        arrival = {p['name']: p['arrival'] for p in procs}
        for p in procs:
            if p['arrival'] == 0:
                queue.append(p['name'])
        completed = set()
        gantt = []
        while len(completed) < len(procs):
            for p in procs:
                if p['arrival'] <= time and p['name'] not in queue and p['name'] not in completed:
                    queue.append(p['name'])
            if not queue:
                time += 1
                continue
            curr = queue.popleft()
            exec_t = min(quantum, remaining[curr])
            start = time
            time += exec_t
            remaining[curr] -= exec_t
            gantt.append((curr, start, time))
            if remaining[curr] == 0:
                ct = time
                tat = ct - arrival[curr]
                burst = next(p['burst'] for p in procs if p['name'] == curr)
                wt = tat - burst
                results[curr] = (curr, arrival[curr], burst, ct, tat, wt)
                completed.add(curr)
            else:
                queue.append(curr)
        self.display_results(list(results.values()))
        self.draw_gantt(gantt)
        
    def display_results(self, results):
        self.results_text.delete(1.0, tk.END)
        if not results:
            return
        avg_tat = sum(r[4] for r in results) / len(results)
        avg_wt = sum(r[5] for r in results) / len(results)
        self.results_text.insert("1.0", "="*70 + "\nSCHEDULING RESULTS\n" + "="*70 + "\n\n")
        self.results_text.insert("end", f"{'Process':<10} {'Arrival':<10} {'Burst':<10} {'Completion':<12} {'Turnaround':<12} {'Waiting':<10}\n")
        self.results_text.insert("end", "-"*70 + "\n")
        for r in results:
            self.results_text.insert("end", f"{r[0]:<10} {r[1]:<10} {r[2]:<10} {r[3]:<12} {r[4]:<12.2f} {r[5]:<10.2f}\n")
        self.results_text.insert("end", "\n" + "="*70 + f"\n📊 Avg Turnaround: {avg_tat:.2f}\n📊 Avg Waiting: {avg_wt:.2f}\n")
        
    def draw_gantt(self, gantt):
        try:
            fig, ax = plt.subplots(figsize=(12, 3))
            colors = plt.cm.Set3(np.linspace(0, 1, len(set(p[0] for p in gantt))))
            cmap = {proc: colors[i] for i, proc in enumerate(set(p[0] for p in gantt))}
            for proc, start, end in gantt:
                ax.barh(0, end-start, left=start, color=cmap[proc], edgecolor='black')
                ax.text((start+end)/2, 0, proc, ha='center', va='center', fontsize=10, fontweight='bold')
            ax.set_xlabel('Time'), ax.set_title('Gantt Chart'), ax.set_yticks([]), ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()
        except:
            pass
        
    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()