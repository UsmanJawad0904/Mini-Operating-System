"""
Memory Management Module - With Persistent Device Support
"""

import tkinter as tk
from tkinter import ttk, messagebox


class MemoryUI:
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        
        self.colors = {"bg": "#1e1e2e", "card": "#313244", "accent": "#a6e3a1", "success": "#a6e3a1",
                       "warning": "#f9e2af", "danger": "#f38ba8", "text": "#cdd6f4", "text_muted": "#6c7086"}
        
        self.setup_ui()
        self.load_saved_state()
        
    def load_saved_state(self):
        if hasattr(self.device, 'memory_blocks') and self.device.memory_blocks:
            self.memory_blocks = self.device.memory_blocks
            blocks_str = ", ".join(str(b["size"]) for b in self.memory_blocks)
            self.blocks_entry.delete(0, tk.END)
            self.blocks_entry.insert(0, blocks_str)
            self.display_current_allocation()
            self.log(f"Loaded {len(self.memory_blocks)} memory blocks")
        else:
            self.init_default_memory()
            
    def init_default_memory(self):
        mem = self.device.memory_size
        sizes = [mem//10, mem//8, mem//6, mem//5, mem//4, mem//3]
        self.memory_blocks = [{"size": s, "allocated": None, "fragmentation": 0} for s in sizes if s > 0]
        blocks_str = ", ".join(str(b["size"]) for b in self.memory_blocks)
        self.blocks_entry.delete(0, tk.END)
        self.blocks_entry.insert(0, blocks_str)
        
    def save_state(self):
        self.device.memory_blocks = self.memory_blocks
        self.device_manager.update_device_state(self.device, {"memory_blocks": self.memory_blocks})
        
    def display_current_allocation(self):
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert("1.0", "="*60 + "\nCURRENT MEMORY STATE\n" + "="*60 + "\n\n")
        self.results_text.insert("end", f"{'Block':<10} {'Size':<10} {'Allocated':<12} {'Fragmentation':<12}\n" + "-"*60 + "\n")
        total_frag = 0
        for i, b in enumerate(self.memory_blocks):
            status = b['allocated'] if b['allocated'] else "Free"
            total_frag += b['fragmentation']
            self.results_text.insert("end", f"Block {i:<6} {b['size']:<10} {status:<12} {b['fragmentation']:<12}\n")
        self.results_text.insert("end", "\n" + "="*60 + f"\n📊 Total Fragmentation: {total_frag}\n")
        
    def setup_ui(self):
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10))
        tk.Label(header, text="💾 Memory Management", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack()
        tk.Label(header, text=f"Device: {self.device.name} | Total RAM: {self.device.memory_size}MB", 
                font=("Segoe UI", 12), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack()
        
        content = tk.Frame(self.main_frame, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        left = tk.Frame(content, bg=self.colors["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        block_card = tk.Frame(left, bg=self.colors["card"])
        block_card.pack(fill="x", pady=10)
        tk.Label(block_card, text="📦 Memory Blocks", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        tk.Label(block_card, text="Block sizes (comma-separated):", bg=self.colors["card"], fg=self.colors["text_muted"]).pack()
        self.blocks_entry = tk.Entry(block_card, bg="#0f172a", fg=self.colors["text"], width=40, font=("Consolas", 11))
        self.blocks_entry.pack(pady=10, padx=20)
        
        proc_card = tk.Frame(left, bg=self.colors["card"])
        proc_card.pack(fill="x", pady=10)
        tk.Label(proc_card, text="📋 Processes", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        tk.Label(proc_card, text="Process sizes (comma-separated):", bg=self.colors["card"], fg=self.colors["text_muted"]).pack()
        self.proc_entry = tk.Entry(proc_card, bg="#0f172a", fg=self.colors["text"], width=40, font=("Consolas", 11))
        self.proc_entry.pack(pady=10, padx=20)
        self.proc_entry.insert(0, "80, 120, 50, 180, 90, 70, 200")
        
        algo_card = tk.Frame(left, bg=self.colors["card"])
        algo_card.pack(fill="x", pady=10)
        tk.Label(algo_card, text="🎯 Allocation Algorithm", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        self.algo_var = tk.StringVar(value="First Fit")
        for algo in ["First Fit", "Best Fit", "Worst Fit"]:
            tk.Radiobutton(algo_card, text=algo, variable=self.algo_var, value=algo,
                          bg=self.colors["card"], fg=self.colors["text"], selectcolor=self.colors["card"]).pack(anchor="w", padx=30, pady=5)
        
        btn_frame = tk.Frame(left, bg=self.colors["bg"])
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="▶ Allocate", command=self.allocate,
                 bg=self.colors["accent"], fg="white", font=("Segoe UI", 11, "bold"), cursor="hand2", padx=20).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑 Reset", command=self.reset,
                 bg=self.colors["warning"], fg="white", cursor="hand2", padx=20).pack(side="left", padx=5)
        tk.Button(btn_frame, text="💾 Save", command=self.save_state,
                 bg=self.colors["success"], fg="white", cursor="hand2", padx=20).pack(side="left", padx=5)
        
        right = tk.Frame(content, bg=self.colors["bg"])
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        results_card = tk.Frame(right, bg=self.colors["card"])
        results_card.pack(fill="both", expand=True, pady=10)
        tk.Label(results_card, text="📊 Allocation Results", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        text_frame = tk.Frame(results_card, bg=self.colors["card"])
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.results_text = tk.Text(text_frame, bg="#0f172a", fg=self.colors["text"], font=("Consolas", 10), wrap="word", height=15)
        scroll = tk.Scrollbar(text_frame, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scroll.set)
        self.results_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        back_btn = tk.Button(self.main_frame, text="← Back to Dashboard", command=self.go_back,
                            bg=self.colors["text_muted"], fg="white", cursor="hand2", padx=20, pady=8)
        back_btn.pack(pady=20)
        
    def allocate(self):
        try:
            blocks = list(map(int, self.blocks_entry.get().split(',')))
            procs = list(map(int, self.proc_entry.get().split(',')))
            algo = self.algo_var.get()
            
            allocation = [-1] * len(procs)
            used = [False] * len(blocks)
            frag = [0] * len(blocks)
            
            for i, ps in enumerate(procs):
                if algo == "First Fit":
                    for j, bs in enumerate(blocks):
                        if not used[j] and bs >= ps:
                            allocation[i], used[j], frag[j] = j, True, bs - ps
                            break
                elif algo == "Best Fit":
                    best, best_frag = -1, float('inf')
                    for j, bs in enumerate(blocks):
                        if not used[j] and bs >= ps:
                            f = bs - ps
                            if f < best_frag:
                                best_frag, best = f, j
                    if best != -1:
                        allocation[i], used[best], frag[best] = best, True, best_frag
                else:  # Worst Fit
                    worst, worst_frag = -1, -1
                    for j, bs in enumerate(blocks):
                        if not used[j] and bs >= ps:
                            f = bs - ps
                            if f > worst_frag:
                                worst_frag, worst = f, j
                    if worst != -1:
                        allocation[i], used[worst], frag[worst] = worst, True, worst_frag
            
            self.memory_blocks = []
            for j, bs in enumerate(blocks):
                alloc = None
                for i, a in enumerate(allocation):
                    if a == j:
                        alloc = f"P{i+1}({procs[i]})"
                        break
                self.memory_blocks.append({"size": bs, "allocated": alloc, "fragmentation": frag[j] if alloc else 0})
            
            self.display_results(procs, blocks, allocation, frag)
            self.save_state()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            
    def display_results(self, procs, blocks, allocation, frag):
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert("1.0", "="*60 + "\nALLOCATION RESULTS\n" + "="*60 + "\n\n")
        self.results_text.insert("end", f"{'Process':<10} {'Size':<10} {'Block':<10} {'Fragmentation':<12}\n" + "-"*60 + "\n")
        total_frag = 0
        for i, ps in enumerate(procs):
            if allocation[i] != -1:
                total_frag += frag[allocation[i]]
                self.results_text.insert("end", f"P{i+1:<9} {ps:<10} Block {allocation[i]:<6} {frag[allocation[i]]:<12}\n")
            else:
                self.results_text.insert("end", f"P{i+1:<9} {ps:<10} {'NOT ALLOCATED':<10} {'-':<12}\n")
        total_mem = sum(blocks)
        alloc_mem = sum(ps for i, ps in enumerate(procs) if allocation[i] != -1)
        self.results_text.insert("end", "\n" + "="*60 + f"\n📊 Total Fragmentation: {total_frag}\n📊 Memory Utilization: {(alloc_mem/total_mem*100):.1f}%\n")
        
    def reset(self):
        self.init_default_memory()
        self.proc_entry.delete(0, tk.END)
        self.proc_entry.insert(0, "80, 120, 50, 180, 90, 70, 200")
        self.results_text.delete(1.0, tk.END)
        self.save_state()
        
    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()