"""
Virtual Memory & Paging System
Simulates page tables, virtual memory, and paging with realistic page faults
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import random


class PageTable:
    """Represents a page table for a process"""
    
    def __init__(self, process_pid, page_size=4096, num_pages=256):
        self.process_pid = process_pid
        self.page_size = page_size  # 4KB typical
        self.num_pages = num_pages
        self.pages = {}
        self.page_faults = 0
        self.page_hits = 0
        
        # Each page entry: {page_num: {valid: bool, frame: int, dirty: bool, accessed: datetime}}
        for i in range(num_pages):
            self.pages[i] = {
                "valid": False,
                "frame": None,
                "dirty": False,
                "accessed": None,
                "created": datetime.now()
            }
    
    def access_page(self, page_num):
        """Access a page, returns True if hit, False if fault"""
        if page_num >= self.num_pages:
            return False
        
        page = self.pages[page_num]
        if page["valid"]:
            page["accessed"] = datetime.now()
            self.page_hits += 1
            return True
        else:
            self.page_faults += 1
            return False
    
    def load_page(self, page_num, frame_num):
        """Load a page into memory"""
        if page_num < self.num_pages:
            self.pages[page_num]["valid"] = True
            self.pages[page_num]["frame"] = frame_num
            self.pages[page_num]["accessed"] = datetime.now()
            return True
        return False
    
    def mark_dirty(self, page_num):
        """Mark a page as dirty (modified)"""
        if page_num < self.num_pages:
            self.pages[page_num]["dirty"] = True
    
    def get_statistics(self):
        """Get page table statistics"""
        total_accesses = self.page_hits + self.page_faults
        hit_ratio = (self.page_hits / total_accesses * 100) if total_accesses > 0 else 0
        loaded_pages = sum(1 for p in self.pages.values() if p["valid"])
        
        return {
            "total_pages": self.num_pages,
            "loaded_pages": loaded_pages,
            "page_hits": self.page_hits,
            "page_faults": self.page_faults,
            "hit_ratio": hit_ratio
        }


class VirtualMemoryManager:
    """Manages virtual memory for all processes"""
    
    def __init__(self, physical_ram_size=1024, page_size=4096):
        self.physical_ram_size = physical_ram_size  # MB
        self.page_size = page_size  # bytes
        self.total_frames = (physical_ram_size * 1024 * 1024) // page_size
        self.frames = [None] * self.total_frames  # frame[i] = pid or None
        self.page_tables = {}  # pid -> PageTable
        self.swap_disk = {}  # page_id -> data (simulated)
        self.page_replacement_algorithm = "LRU"  # LRU, FIFO, Random
        
    def create_page_table(self, process_pid, num_pages=256):
        """Create a page table for a process"""
        pt = PageTable(process_pid, self.page_size, num_pages)
        self.page_tables[process_pid] = pt
        return pt
    
    def allocate_frame(self, process_pid):
        """Allocate a free frame or trigger page replacement"""
        # Find a free frame
        for i, frame in enumerate(self.frames):
            if frame is None:
                self.frames[i] = process_pid
                return i
        
        # No free frames, perform page replacement
        if self.page_replacement_algorithm == "FIFO":
            victim_frame = self._fifo_replacement()
        elif self.page_replacement_algorithm == "LRU":
            victim_frame = self._lru_replacement()
        else:
            victim_frame = random.randint(0, self.total_frames - 1)
        
        # Save to swap disk
        if self.frames[victim_frame]:
            self.swap_disk[f"{self.frames[victim_frame]}_page_{victim_frame}"] = True
        
        self.frames[victim_frame] = process_pid
        return victim_frame
    
    def _fifo_replacement(self):
        """FIFO page replacement"""
        for i, frame in enumerate(self.frames):
            if frame is not None:
                return i
        return 0
    
    def _lru_replacement(self):
        """LRU page replacement"""
        oldest_time = datetime.now()
        oldest_frame = 0
        
        for pid in self.page_tables:
            pt = self.page_tables[pid]
            for page_num, page in pt.pages.items():
                if page["valid"] and page["accessed"]:
                    if page["accessed"] < oldest_time:
                        oldest_time = page["accessed"]
                        oldest_frame = page["frame"]
        
        return oldest_frame
    
    def access_virtual_address(self, process_pid, virtual_address):
        """Access a virtual address, handle page faults"""
        if process_pid not in self.page_tables:
            return False
        
        # Calculate page number
        page_num = virtual_address // self.page_size
        
        pt = self.page_tables[process_pid]
        
        # Try to access the page
        if not pt.access_page(page_num):
            # Page fault - need to load page
            frame = self.allocate_frame(process_pid)
            pt.load_page(page_num, frame)
            return False  # Return False to indicate page fault
        
        return True  # Return True for page hit
    
    def get_statistics(self):
        """Get memory statistics"""
        free_frames = sum(1 for f in self.frames if f is None)
        used_frames = self.total_frames - free_frames
        
        stats = {
            "total_frames": self.total_frames,
            "used_frames": used_frames,
            "free_frames": free_frames,
            "utilization": (used_frames / self.total_frames * 100),
            "swap_pages": len(self.swap_disk),
            "page_tables": len(self.page_tables)
        }
        
        return stats


class VirtualMemoryUI:
    """UI for Virtual Memory Management"""
    
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        
        self.colors = {
            "bg": "#1e1e2e",
            "card": "#313244",
            "accent": "#f5c211",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "danger": "#f38ba8",
            "text": "#cdd6f4",
            "text_muted": "#6c7086"
        }
        
        self.vm = VirtualMemoryManager(device.memory_size)
        self.setup_ui()
        self.load_saved_state()
        
    def setup_ui(self):
        """Setup the UI"""
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10), padx=20)
        
        tk.Label(header, text="💾 Virtual Memory Manager", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        tk.Label(header, text=f"RAM: {self.device.memory_size}MB | Page Size: 4KB",
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w")
        
        content = tk.Frame(self.main_frame, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Memory Statistics
        stats_frame = tk.LabelFrame(content, text="Memory Statistics", bg=self.colors["card"],
                                   fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        stats_frame.pack(fill="x", pady=10)
        
        stats_info = tk.Frame(stats_frame, bg=self.colors["card"])
        stats_info.pack(fill="x", padx=10, pady=10)
        
        self.stats_label = tk.Label(stats_info, text="", bg=self.colors["card"],
                                   fg=self.colors["text"], justify="left")
        self.stats_label.pack(anchor="w")
        
        # Page Replacement Algorithm
        algo_frame = tk.LabelFrame(content, text="Page Replacement Algorithm", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        algo_frame.pack(fill="x", pady=10)
        
        self.algo_var = tk.StringVar(value="LRU")
        for algo in ["LRU", "FIFO", "Random"]:
            tk.Radiobutton(algo_frame, text=algo, variable=self.algo_var, value=algo,
                          bg=self.colors["card"], fg=self.colors["text"],
                          selectcolor=self.colors["accent"]).pack(anchor="w", padx=10, pady=5)
        
        # Simulation
        sim_frame = tk.LabelFrame(content, text="Memory Access Simulation", bg=self.colors["card"],
                                 fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        sim_frame.pack(fill="both", expand=True, pady=10)
        
        self.simulation_text = tk.Text(sim_frame, height=10, bg=self.colors["bg"],
                                      fg=self.colors["text"], wrap="word")
        self.simulation_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Buttons
        button_frame = tk.Frame(content, bg=self.colors["bg"])
        button_frame.pack(fill="x", pady=10)
        
        tk.Button(button_frame, text="Run Simulation", command=self.run_simulation,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        tk.Button(button_frame, text="Update Stats", command=lambda: [self.update_statistics(), self.save_state()],
                 bg=self.colors["success"], fg="#000000").pack(side="left", padx=5)
        tk.Button(button_frame, text="Back", command=self.go_back,
                 bg=self.colors["text_muted"], fg="#000000").pack(side="right", padx=5)
        
        self.update_statistics()
        
    def update_statistics(self):
        """Update memory statistics display"""
        stats = self.vm.get_statistics()
        stats_text = (
            f"Total Frames: {stats['total_frames']}\n"
            f"Used Frames: {stats['used_frames']}\n"
            f"Free Frames: {stats['free_frames']}\n"
            f"Memory Utilization: {stats['utilization']:.1f}%\n"
            f"Swapped Pages: {stats['swap_pages']}\n"
            f"Active Page Tables: {stats['page_tables']}"
        )
        self.stats_label.config(text=stats_text)
        
    def load_saved_state(self):
        saved = getattr(self.device, 'extra_state', {}).get('virtual_memory', {})
        if saved:
            self.algo_var.set(saved.get('algorithm', 'LRU'))
            self.simulation_text.delete(1.0, tk.END)
            self.simulation_text.insert(tk.END, saved.get('last_output', ''))
            self.vm.page_replacement_algorithm = saved.get('algorithm', 'LRU')
            self.update_statistics()

    def save_state(self):
        state = {
            'algorithm': self.algo_var.get(),
            'last_output': self.simulation_text.get(1.0, tk.END).strip(),
            'stats': self.vm.get_statistics()
        }
        self.device_manager.update_device_state(self.device, {'virtual_memory': state})

    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()

    def run_simulation(self):
        """Run a memory access simulation"""
        algo = self.algo_var.get()
        self.vm.page_replacement_algorithm = algo
        
        self.simulation_text.delete(1.0, tk.END)
        self.simulation_text.insert("end", f"Running Memory Access Simulation ({algo} Algorithm)\n")
        self.simulation_text.insert("end", "=" * 50 + "\n\n")
        
        # Create a virtual page table
        test_pid = "proc_001"
        pt = self.vm.create_page_table(test_pid, 64)
        
        # Simulate random memory accesses
        for i in range(20):
            virtual_addr = random.randint(0, 65536)
            is_hit = self.vm.access_virtual_address(test_pid, virtual_addr)
            hit_str = "HIT ✓" if is_hit else "FAULT ✗"
            self.simulation_text.insert("end",
                f"Access {i+1}: Address {virtual_addr} -> {hit_str}\n")
        
        stats = pt.get_statistics()
        self.simulation_text.insert("end", "\n" + "=" * 50 + "\n")
        self.simulation_text.insert("end",
            f"Page Hits: {stats['page_hits']}\n"
            f"Page Faults: {stats['page_faults']}\n"
            f"Hit Ratio: {stats['hit_ratio']:.1f}%\n")
        
        self.log(f"Simulation completed with {algo} algorithm")
        self.update_statistics()
