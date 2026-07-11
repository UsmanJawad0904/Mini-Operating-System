"""
MiniOS Competition Edition - Ultimate Edition
Complete Operating System Simulator with Device Management
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import sys
import os

# Import modules
from device_manager import DeviceManager, DeviceSelectionUI
from scheduler import SchedulerUI
from memory import MemoryUI
from filesystem import FileSystemUI
from adv_features import AdvancedFeaturesUI
from shell import UltimateShell
from process_manager import ProcessManagerUI
from virtual_memory import VirtualMemoryUI
from user_permissions import UserPermissionUI
from ipc_manager import IPCManagerUI
from system_logger import SystemLoggerUI
from file_sharing import FileSharingUI


class MiniOSApp:
    """Main application class with device management"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("MiniOS v6.0 - Ultimate Edition 🐧")
        
        # Get screen dimensions for fullscreen
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Set to fullscreen
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.root.attributes('-fullscreen', True)
        
        # Color scheme - Ubuntu Dark Theme
        self.colors = {
            "bg": "#1e1e2e",
            "sidebar": "#181825",
            "card": "#313244",
            "card_hover": "#45475a",
            "accent": "#cba6f7",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "danger": "#f38ba8",
            "info": "#89b4fa",
            "purple": "#cba6f7",
            "cyan": "#89dceb",
            "text": "#cdd6f4",
            "text_muted": "#6c7086",
            "border": "#45475a",
            "terminal_bg": "#1e1e2e",
            "terminal_text": "#a6e3a1"
        }
        
        # Session tracking
        self.session_start = datetime.now()
        self.current_module = None
        self.fullscreen = True
        self.session_timer_id = None  # Store after() ID for cleanup
        
        # Device management
        self.device_manager = DeviceManager()
        self.current_device = None
        
        # Setup UI
        self.setup_ui()
        
        # Show device selection screen first
        self.show_device_selection()
        
        # Bind keyboard shortcuts
        self.bind_shortcuts()
        
        # Bind F11 for fullscreen toggle
        self.root.bind('<F11>', self.toggle_fullscreen)
        self.root.bind('<Escape>', self.exit_fullscreen)
        
    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)
        
    def exit_fullscreen(self, event=None):
        """Exit fullscreen"""
        self.root.attributes('-fullscreen', False)
        
    def setup_ui(self):
        """Setup main UI structure"""
        # Top Navigation Bar
        self.top_bar = tk.Frame(self.root, bg=self.colors["sidebar"], height=50)
        self.top_bar.pack(fill="x")
        self.top_bar.pack_propagate(False)
        
        # Logo and Title
        title_frame = tk.Frame(self.top_bar, bg=self.colors["sidebar"])
        title_frame.pack(side="left", padx=20, pady=10)
        
        tk.Label(title_frame, text="🐧", font=("Segoe UI", 20), 
                bg=self.colors["sidebar"]).pack(side="left")
        tk.Label(title_frame, text="MiniOS", font=("Segoe UI", 18, "bold"), 
                bg=self.colors["sidebar"], fg=self.colors["accent"]).pack(side="left", padx=8)
        tk.Label(title_frame, text="Ultimate Edition", font=("Segoe UI", 10), 
                bg=self.colors["sidebar"], fg=self.colors["text_muted"]).pack(side="left", padx=5)
        
        # Device indicator
        self.device_label = tk.Label(title_frame, text="", font=("Segoe UI", 9, "bold"),
                                     bg=self.colors["sidebar"], fg=self.colors["success"])
        self.device_label.pack(side="left", padx=15)
        
        # Right side - Session Info
        right_frame = tk.Frame(self.top_bar, bg=self.colors["sidebar"])
        right_frame.pack(side="right", padx=20)
        
        self.session_label = tk.Label(right_frame, font=("Segoe UI", 10), 
                                      bg=self.colors["sidebar"], fg=self.colors["accent"])
        self.session_label.pack()
        self.update_session_timer()
        
        # Fullscreen indicator
        tk.Label(right_frame, text="[F11] Fullscreen", font=("Segoe UI", 9),
                bg=self.colors["sidebar"], fg=self.colors["text_muted"]).pack()
        
        # Main Container (Sidebar + Content)
        main_container = tk.Frame(self.root, bg=self.colors["bg"])
        main_container.pack(fill="both", expand=True)
        
        # LEFT SIDEBAR
        self.create_sidebar(main_container)
        
        # RIGHT CONTENT AREA
        self.content_container = tk.Frame(main_container, bg=self.colors["bg"])
        self.content_container.pack(side="right", fill="both", expand=True)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(self.content_container, bg=self.colors["bg"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.content_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["bg"])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.content_frame = self.scrollable_frame
        
    def create_sidebar(self, parent):
        """Create navigation sidebar"""
        sidebar = tk.Frame(parent, bg=self.colors["sidebar"], width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        tk.Label(sidebar, text="Navigation", font=("Segoe UI", 13, "bold"),
                bg=self.colors["sidebar"], fg=self.colors["text"]).pack(pady=20)
        
        nav_items = [
            ("🏠 Dashboard", self.show_dashboard),
            ("⚡ CPU Scheduling", self.open_scheduler),
            ("💾 Memory Management", self.open_memory),
            ("📁 File System", self.open_filesystem),
            ("🚀 Advanced Features", self.open_advanced),
            ("🐚 Shell Terminal", self.open_shell),
            ("─────────────────────", None),
            ("⚙️ Process Manager", self.open_process_manager),
            ("💾 Virtual Memory", self.open_virtual_memory),
            ("👥 User & Permissions", self.open_user_permissions),
            ("🔗 IPC Manager", self.open_ipc_manager),
            ("📋 System Logger", self.open_system_logger),
            ("📤 File Sharing", self.open_file_sharing),
            ("─────────────────────", None),
            ("🔄 Switch Device", self.show_device_selection),
        ]
        
        for text, command in nav_items:
            if command is None:
                tk.Label(sidebar, text=text, bg=self.colors["sidebar"],
                        fg=self.colors["text_muted"], font=("Segoe UI", 8)).pack(fill="x", pady=8)
            else:
                btn = tk.Button(sidebar, text=text, command=command,
                               bg=self.colors["sidebar"], fg=self.colors["text_muted"],
                               font=("Segoe UI", 10), anchor="w", padx=20,
                               relief="flat", cursor="hand2")
                btn.pack(fill="x", pady=3)
                
                def on_enter(e, b=btn):
                    b.config(bg=self.colors["card_hover"], fg=self.colors["text"])
                def on_leave(e, b=btn):
                    b.config(bg=self.colors["sidebar"], fg=self.colors["text_muted"])
                btn.bind("<Enter>", on_enter)
                btn.bind("<Leave>", on_leave)
        
        tk.Frame(sidebar, bg=self.colors["border"], height=1).pack(fill="x", pady=20)
        
        # Device stats
        self.stats_frame = tk.Frame(sidebar, bg=self.colors["sidebar"])
        self.stats_frame.pack(side="bottom", fill="x", pady=20)
        self.update_device_stats()
        
    def update_device_stats(self):
        """Update device statistics display"""
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        if self.current_device:
            stats = self.device_manager.get_device_stats(self.current_device)
            total_storage_mb = stats['total_storage']
            
            tk.Label(self.stats_frame, text="📊 Device Stats", font=("Segoe UI", 10, "bold"),
                    bg=self.colors["sidebar"], fg=self.colors["text"]).pack()
            
            tk.Label(self.stats_frame, text=f"💾 RAM: {stats['used_memory']}/{stats['total_memory']}MB", 
                    font=("Segoe UI", 8), bg=self.colors["sidebar"], fg=self.colors["text_muted"]).pack()
            tk.Label(self.stats_frame, text=f"📀 Disk: {self.format_storage_display(stats['used_storage'])}/{total_storage_mb:.2f}MB", 
                    font=("Segoe UI", 8), bg=self.colors["sidebar"], fg=self.colors["text_muted"]).pack()
            tk.Label(self.stats_frame, text=f"Free: {self.format_storage_display(stats['free_storage'])}", 
                    font=("Segoe UI", 8), bg=self.colors["sidebar"], fg=self.colors["text_muted"]).pack()
            tk.Label(self.stats_frame, text=f"⚙️ CPU: {stats['cpu_cores']} Cores", 
                    font=("Segoe UI", 8), bg=self.colors["sidebar"], fg=self.colors["text_muted"]).pack()
            tk.Label(self.stats_frame, text=f"📈 Processes: {stats['total_processes']}", 
                    font=("Segoe UI", 8), bg=self.colors["sidebar"], fg=self.colors["text_muted"]).pack()
        else:
            tk.Label(self.stats_frame, text="No device loaded", font=("Segoe UI", 10),
                    bg=self.colors["sidebar"], fg=self.colors["warning"]).pack()
            tk.Label(self.stats_frame, text="Select or create a device", font=("Segoe UI", 8),
                    bg=self.colors["sidebar"], fg=self.colors["text_muted"]).pack()
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def format_storage_display(self, bytes_value, precision=2):
        if bytes_value < 1024 * 1024:
            kb_value = bytes_value / 1024
            return f"{kb_value:.0f}KB"
        mb_value = bytes_value / (1024 * 1024)
        return f"{mb_value:.{precision}f}MB"
        
    def update_session_timer(self):
        elapsed = datetime.now() - self.session_start
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.session_label.config(text=f"Session: {hours:02d}:{minutes:02d}:{seconds:02d}")
        self.session_timer_id = self.root.after(1000, self.update_session_timer)
        
    def bind_shortcuts(self):
        self.root.bind('<F1>', lambda e: self.open_scheduler())
        self.root.bind('<F2>', lambda e: self.open_memory())
        self.root.bind('<F3>', lambda e: self.open_filesystem())
        self.root.bind('<F4>', lambda e: self.open_advanced())
        self.root.bind('<F5>', lambda e: self.open_shell())
        self.root.bind('<F6>', lambda e: self.show_dashboard())
        self.root.bind('<F7>', lambda e: self.open_process_manager())
        self.root.bind('<F8>', lambda e: self.open_virtual_memory())
        self.root.bind('<F9>', lambda e: self.open_user_permissions())
        self.root.bind('<Control-p>', lambda e: self.open_ipc_manager())
        self.root.bind('<Control-l>', lambda e: self.open_system_logger())
        
        # Bind window close event to cleanup timers
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        """Cleanup before closing the application"""
        # Cancel session timer
        if self.session_timer_id:
            self.root.after_cancel(self.session_timer_id)
        # Cancel any module-specific timers
        if self.current_module and hasattr(self.current_module, 'cleanup_timers'):
            self.current_module.cleanup_timers()
        # Destroy the window
        self.root.destroy()
        
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
    def on_device_selected(self, device):
        """Handle device selection"""
        self.current_device = device
        self.device_label.config(text=f"📱 {device.name}")
        self.update_device_stats()
        self.show_dashboard()
        
    def show_device_selection(self):
        """Show device selection screen"""
        self.clear_content()
        self.current_module = "device_selection"
        DeviceSelectionUI(self.content_frame, self.on_device_selected, self.colors)
        
    def show_dashboard(self):
        """Show main dashboard"""
        if not self.current_device:
            self.show_device_selection()
            return
            
        self.clear_content()
        self.current_module = "dashboard"
        self.create_dashboard()
        
    def create_dashboard(self):
        """Create dashboard with device info"""
        header_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        header_frame.pack(fill="x", pady=(20, 30))
        
        tk.Label(header_frame, text=f"Welcome to {self.current_device.name}", 
                font=("Segoe UI", 32, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack()
        
        tk.Label(header_frame, text=f"Device: {self.current_device.name} | RAM: {self.current_device.memory_size}MB | Storage: {self.current_device.storage_size}MB | CPU: {self.current_device.cpu_cores} Cores", 
                font=("Segoe UI", 12), 
                bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(pady=5)
        
        # Device stats cards
        stats = self.device_manager.get_device_stats(self.current_device)
        
        stats_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        stats_frame.pack(fill="x", pady=20)
        
        used_storage_mb = stats['used_storage'] / (1024 * 1024)
        free_storage_mb = stats['free_storage'] / (1024 * 1024)
        total_storage_mb = stats['total_storage']
        stat_items = [
            ("💾 Memory", f"{stats['used_memory']}/{stats['total_memory']} MB", f"Free: {stats['free_memory']}MB"),
            ("📀 Storage", f"{self.format_storage_display(stats['used_storage'])}/{total_storage_mb:.2f} MB", f"Free: {self.format_storage_display(stats['free_storage'])}"),
            ("⚙️ CPU", f"{stats['cpu_cores']} Cores", "Available"),
            ("📈 Processes", str(stats['total_processes']), "Running")
        ]
        
        for i, (label, value, extra) in enumerate(stat_items):
            card = tk.Frame(stats_frame, bg=self.colors["card"], relief="flat")
            card.grid(row=0, column=i, padx=15, pady=10, sticky="nsew")
            
            tk.Label(card, text=label, font=("Segoe UI", 12),
                    bg=self.colors["card"], fg=self.colors["text_muted"]).pack(pady=(15, 5))
            tk.Label(card, text=value, font=("Segoe UI", 20, "bold"),
                    bg=self.colors["card"], fg=self.colors["accent"]).pack()
            tk.Label(card, text=extra, font=("Segoe UI", 9),
                    bg=self.colors["card"], fg=self.colors["success"]).pack(pady=(5, 15))
        
        for i in range(4):
            stats_frame.grid_columnconfigure(i, weight=1)
        
        # Modules
        modules_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        modules_frame.pack(fill="both", expand=True, pady=20)
        
        modules = [
            {"icon": "⚡", "title": "CPU Scheduling", "color": self.colors["accent"], "cmd": self.open_scheduler},
            {"icon": "💾", "title": "Memory Management", "color": self.colors["success"], "cmd": self.open_memory},
            {"icon": "📁", "title": "File System", "color": self.colors["warning"], "cmd": self.open_filesystem},
            {"icon": "🚀", "title": "Advanced Features", "color": self.colors["danger"], "cmd": self.open_advanced},
            {"icon": "🐚", "title": "Shell Terminal", "color": self.colors["purple"], "cmd": self.open_shell},
            {"icon": "⚙️", "title": "Process Manager", "color": self.colors["cyan"], "cmd": self.open_process_manager},
            {"icon": "💾", "title": "Virtual Memory", "color": self.colors["accent"], "cmd": self.open_virtual_memory},
            {"icon": "👥", "title": "User & Permissions", "color": self.colors["success"], "cmd": self.open_user_permissions},
            {"icon": "🔗", "title": "IPC Manager", "color": self.colors["warning"], "cmd": self.open_ipc_manager},
            {"icon": "📋", "title": "System Logger", "color": self.colors["danger"], "cmd": self.open_system_logger},
        ]
        
        for i, module in enumerate(modules):
            row = i // 3
            col = i % 3
            
            card = tk.Frame(modules_frame, bg=self.colors["card"], relief="flat", bd=1)
            card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            
            inner = tk.Frame(card, bg=self.colors["card"])
            inner.pack(fill="both", expand=True, padx=25, pady=25)
            
            tk.Label(inner, text=module["icon"], font=("Segoe UI", 40), 
                    bg=self.colors["card"]).pack()
            tk.Label(inner, text=module["title"], font=("Segoe UI", 16, "bold"), 
                    bg=self.colors["card"], fg=module["color"]).pack(pady=10)
            
            btn = tk.Button(inner, text="Launch →", command=module["cmd"],
                           bg=module["color"], fg="white", font=("Segoe UI", 11, "bold"),
                           cursor="hand2", padx=25, pady=8)
            btn.pack(pady=(15, 0))
        
        for i in range(4):
            modules_frame.grid_rowconfigure(i, weight=1)
        for i in range(3):
            modules_frame.grid_columnconfigure(i, weight=1)
            
    def open_scheduler(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            from scheduler import SchedulerUI
            SchedulerUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager)
        except ImportError as e:
            self.show_error(f"Scheduler module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading Scheduler: {e}")
        
    def open_memory(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            from memory import MemoryUI
            MemoryUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager)
        except ImportError as e:
            self.show_error(f"Memory module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading Memory Manager: {e}")
        
    def open_filesystem(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            from filesystem import FileSystemUI
            FileSystemUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager, self.update_device_stats)
        except ImportError as e:
            self.show_error(f"FileSystem module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading File System: {e}")
        
    def open_advanced(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            from adv_features import AdvancedFeaturesUI
            AdvancedFeaturesUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager, self.colors)
        except ImportError as e:
            self.show_error(f"AdvancedFeatures module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading Advanced Features: {e}")
        
    def open_shell(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            from shell import UltimateShell
            # UltimateShell expects: parent, back_callback, log_callback, device, device_manager, refresh_callback
            UltimateShell(self.content_frame, self.show_dashboard, self.log_action, self.current_device, self.device_manager, self.update_device_stats)
        except ImportError as e:
            self.show_error(f"Shell module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading Shell: {e}")
    
    def open_process_manager(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            ProcessManagerUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager)
        except ImportError as e:
            self.show_error(f"Process Manager module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading Process Manager: {e}")
    
    def open_virtual_memory(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            VirtualMemoryUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager)
        except ImportError as e:
            self.show_error(f"Virtual Memory module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading Virtual Memory: {e}")
    
    def open_user_permissions(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            UserPermissionUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager)
        except ImportError as e:
            self.show_error(f"User & Permissions module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading User & Permissions: {e}")
    
    def open_ipc_manager(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            IPCManagerUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager)
        except ImportError as e:
            self.show_error(f"IPC Manager module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading IPC Manager: {e}")
    
    def open_system_logger(self):
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            SystemLoggerUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager)
        except ImportError as e:
            self.show_error(f"System Logger module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading System Logger: {e}")
    
    def open_file_sharing(self):
        """Open Advanced File Sharing module"""
        if not self.current_device:
            self.show_device_selection()
            return
        self.clear_content()
        try:
            FileSharingUI(self.content_frame, self.show_dashboard, True, self.log_action, self.current_device, self.device_manager)
        except ImportError as e:
            self.show_error(f"File Sharing module not found: {e}")
        except Exception as e:
            self.show_error(f"Error loading File Sharing: {e}")
        
    def show_error(self, message):
        frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="❌ Error", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["danger"]).pack(pady=50)
        tk.Label(frame, text=message, font=("Segoe UI", 12),
                bg=self.colors["bg"], fg=self.colors["text"]).pack()
        tk.Button(frame, text="← Back", command=self.show_dashboard,
                 bg=self.colors["accent"], fg="white", font=("Segoe UI", 11),
                 cursor="hand2", padx=20, pady=8).pack(pady=30)
        
    def log_action(self, action):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {action}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MiniOSApp(root)
    root.mainloop()