"""
Device Manager - Persistent Storage for MiniOS
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import uuid


class Device:
    """Represents a virtual device with persistent storage"""
    
    def __init__(self, device_id, name, memory_size, storage_size, cpu_cores=2):
        self.device_id = device_id
        self.name = name
        self.memory_size = memory_size
        self.storage_size = storage_size
        self.cpu_cores = cpu_cores
        self.created_date = datetime.now()
        self.last_used = datetime.now()
        
        self.memory_blocks = []
        self.processes = []
        self.file_system = {}
        self.scheduling_history = []
        self.command_history = []
        self.current_directory = ""
        self.settings = {"theme": "dark", "default_scheduler": "FCFS", "auto_save": True}
        self.extra_state = {}
        
    def to_dict(self):
        return {
            "device_id": self.device_id,
            "name": self.name,
            "memory_size": self.memory_size,
            "storage_size": self.storage_size,
            "cpu_cores": self.cpu_cores,
            "created_date": self.created_date.isoformat(),
            "last_used": self.last_used.isoformat(),
            "memory_blocks": self.memory_blocks,
            "processes": self.processes,
            "file_system": self.file_system,
            "scheduling_history": self.scheduling_history,
            "command_history": self.command_history,
            "current_directory": self.current_directory,
            "settings": self.settings,
            "extra_state": self.extra_state
        }
    
    @classmethod
    def from_dict(cls, data):
        device = cls(data["device_id"], data["name"], data["memory_size"], data["storage_size"], data.get("cpu_cores", 2))
        device.created_date = datetime.fromisoformat(data["created_date"])
        device.last_used = datetime.fromisoformat(data["last_used"])
        device.memory_blocks = data.get("memory_blocks", [])
        device.processes = data.get("processes", [])
        device.file_system = data.get("file_system", {})
        device.scheduling_history = data.get("scheduling_history", [])
        device.command_history = data.get("command_history", [])
        device.current_directory = data.get("current_directory", "")
        device.settings = data.get("settings", {})
        device.extra_state = data.get("extra_state", {})
        
        # Recursively convert any ISO datetime strings back to datetime objects in extra_state
        def convert_datetimes(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and len(value) >= 19:  # ISO format minimum length
                        try:
                            # Try to parse as ISO datetime
                            datetime.fromisoformat(value)
                            obj[key] = datetime.fromisoformat(value)
                        except (ValueError, TypeError):
                            pass  # Not a datetime string, leave as is
                    elif isinstance(value, (dict, list)):
                        convert_datetimes(value)
            elif isinstance(obj, list):
                for item in obj:
                    convert_datetimes(item)
        
        convert_datetimes(device.extra_state)
        return device


class DeviceManager:
    """Manages all virtual devices"""
    
    def __init__(self, data_dir="MiniOS_Devices"):
        self.data_dir = Path(data_dir)
        self.devices_dir = self.data_dir / "devices"
        self.config_file = self.data_dir / "config.json"
        
        self.devices_dir.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()
        self.current_device = None
        
    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {"last_device": None, "total_devices": 0, "version": "1.0"}
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def create_device(self, name, memory_size, storage_size, cpu_cores=2):
        device_id = str(uuid.uuid4())[:8]
        device = Device(device_id, name, memory_size, storage_size, cpu_cores)
        device.file_system = self.create_default_filesystem(name)
        device.memory_blocks = self.create_default_memory_blocks(memory_size)
        self.save_device(device)
        self.config["total_devices"] += 1
        self.config["last_device"] = device_id
        self.save_config()
        return device
    
    def create_default_filesystem(self, device_name):
        return {
            "root": {
                "type": "folder",
                "size": 4096,
                "children": {},
                "created": datetime.now().isoformat()
            }
        }
    
    def create_default_memory_blocks(self, memory_size):
        block_sizes = [memory_size // 10, memory_size // 8, memory_size // 6, memory_size // 5, memory_size // 4, memory_size // 3]
        return [{"size": size, "allocated": None, "fragmentation": 0} for size in block_sizes if size > 0]
    
    def save_device(self, device):
        device_file = self.devices_dir / f"{device.device_id}.json"
        
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)
        
        with open(device_file, 'w') as f:
            json.dump(device.to_dict(), f, indent=2, cls=DateTimeEncoder)
    
    def load_device(self, device_id):
        device_file = self.devices_dir / f"{device_id}.json"
        if device_file.exists():
            with open(device_file, 'r') as f:
                data = json.load(f)
            device = Device.from_dict(data)
            device.last_used = datetime.now()
            self.current_device = device
            self.save_device(device)
            return device
        return None
    
    def get_all_devices(self):
        devices = []
        for device_file in self.devices_dir.glob("*.json"):
            with open(device_file, 'r') as f:
                data = json.load(f)
                devices.append({
                    "id": data["device_id"], "name": data["name"],
                    "memory_size": data["memory_size"], "storage_size": data["storage_size"],
                    "cpu_cores": data.get("cpu_cores", 2),
                    "last_used": data["last_used"], "created_date": data["created_date"]
                })
        return sorted(devices, key=lambda x: x["last_used"], reverse=True)
    
    def delete_device(self, device_id):
        device_file = self.devices_dir / f"{device_id}.json"
        if device_file.exists():
            device_file.unlink()
            return True
        return False
    
    def update_device_state(self, device, state_data):
        for key, value in state_data.items():
            if hasattr(device, key):
                setattr(device, key, value)
            else:
                device.extra_state[key] = value
        device.last_used = datetime.now()
        self.save_device(device)
    
    def get_device_stats(self, device):
        used_storage = self.calculate_storage_usage(device.file_system)
        total_storage_bytes = int(device.storage_size * 1024 * 1024)
        free_storage = max(total_storage_bytes - used_storage, 0)
        used_memory = sum(b["size"] for b in device.memory_blocks if b["allocated"] is not None)
        used_memory = min(used_memory, device.memory_size)
        return {
            "total_memory": device.memory_size, "used_memory": used_memory, "free_memory": device.memory_size - used_memory,
            "total_storage": device.storage_size, "used_storage": used_storage, "free_storage": free_storage,
            "cpu_cores": device.cpu_cores, "total_processes": len(device.processes),
            "total_scheduling_runs": len(device.scheduling_history), "total_commands": len(device.command_history)
        }
    
    def calculate_storage_usage(self, node):
        total = 0
        if isinstance(node, dict):
            if node.get("type") == "folder":
                total += node.get("size", 0)
                for child in node.get("children", {}).values():
                    total += self.calculate_storage_usage(child)
            else:
                total += node.get("size", 0)
        return total


class DeviceSelectionUI:
    """Device selection screen UI"""
    
    def __init__(self, parent, on_device_selected, colors):
        self.parent = parent
        self.on_device_selected = on_device_selected
        self.colors = colors
        self.device_manager = DeviceManager()
        self.setup_ui()
        
    def setup_ui(self):
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(50, 30))
        tk.Label(header, text="💾 MiniOS Device Manager", font=("Segoe UI", 32, "bold"),
                bg=self.colors["bg"], fg=self.colors["accent"]).pack()
        tk.Label(header, text="Choose a device or create a new one", font=("Segoe UI", 14),
                bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(pady=10)
        
        content = tk.Frame(self.main_frame, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=50, pady=20)
        
        # Left panel - Device list
        left_panel = tk.Frame(content, bg=self.colors["bg"])
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 20))
        tk.Label(left_panel, text="📱 Your Devices", font=("Segoe UI", 16, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=10)
        
        list_frame = tk.Frame(left_panel, bg=self.colors["card"])
        list_frame.pack(fill="both", expand=True)
        
        self.device_listbox = tk.Listbox(list_frame, bg=self.colors["card"], fg=self.colors["text"],
                                         font=("Segoe UI", 11), selectbackground=self.colors["accent"], height=15)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.device_listbox.yview)
        self.device_listbox.configure(yscrollcommand=scrollbar.set)
        self.device_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        self.device_listbox.bind("<Double-Button-1>", self.load_selected_device)
        
        btn_frame = tk.Frame(left_panel, bg=self.colors["bg"])
        btn_frame.pack(fill="x", pady=10)
        tk.Button(btn_frame, text="▶ Load Selected", command=self.load_selected_device,
                 bg=self.colors["success"], fg="white", font=("Segoe UI", 11), cursor="hand2", padx=20).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑 Delete Selected", command=self.delete_selected_device,
                 bg=self.colors["danger"], fg="white", font=("Segoe UI", 11), cursor="hand2", padx=20).pack(side="left", padx=5)
        
        # Right panel - Create new device
        right_panel = tk.Frame(content, bg=self.colors["bg"])
        right_panel.pack(side="right", fill="both", expand=True, padx=(20, 0))
        tk.Label(right_panel, text="✨ Create New Device", font=("Segoe UI", 16, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=10)
        
        form_frame = tk.Frame(right_panel, bg=self.colors["card"])
        form_frame.pack(fill="both", expand=True, pady=10)
        
        # Device Name
        name_frame = tk.Frame(form_frame, bg=self.colors["card"])
        name_frame.pack(fill="x", pady=10, padx=20)
        tk.Label(name_frame, text="Device Name:", font=("Segoe UI", 11),
                bg=self.colors["card"], fg=self.colors["text"], width=18, anchor="w").pack(side="left")
        self.name_entry = tk.Entry(name_frame, bg="#0f172a", fg=self.colors["text"], font=("Segoe UI", 11), width=25)
        self.name_entry.insert(0, "My MiniOS Device")
        self.name_entry.pack(side="left", padx=10)
        
        # Memory Size
        mem_frame = tk.Frame(form_frame, bg=self.colors["card"])
        mem_frame.pack(fill="x", pady=10, padx=20)
        tk.Label(mem_frame, text="Memory Size (MB):", font=("Segoe UI", 11),
                bg=self.colors["card"], fg=self.colors["text"], width=18, anchor="w").pack(side="left")
        self.mem_scale = tk.Scale(mem_frame, from_=512, to=8192, orient="horizontal", length=200,
                                  bg=self.colors["card"], fg=self.colors["text"], highlightbackground=self.colors["card"])
        self.mem_scale.set(2048)
        self.mem_scale.pack(side="left", padx=10)
        self.mem_value = tk.Label(mem_frame, text="2048 MB", bg=self.colors["card"], fg=self.colors["accent"])
        self.mem_value.pack(side="left", padx=5)
        self.mem_scale.configure(command=lambda v: self.mem_value.config(text=f"{int(float(v))} MB"))
        
        # Storage Size
        storage_frame = tk.Frame(form_frame, bg=self.colors["card"])
        storage_frame.pack(fill="x", pady=10, padx=20)
        tk.Label(storage_frame, text="Storage Size (MB):", font=("Segoe UI", 11),
                bg=self.colors["card"], fg=self.colors["text"], width=18, anchor="w").pack(side="left")
        self.storage_scale = tk.Scale(storage_frame, from_=1024, to=32768, orient="horizontal", length=200,
                                      bg=self.colors["card"], fg=self.colors["text"], highlightbackground=self.colors["card"])
        self.storage_scale.set(8192)
        self.storage_scale.pack(side="left", padx=10)
        self.storage_value = tk.Label(storage_frame, text="8192 MB", bg=self.colors["card"], fg=self.colors["accent"])
        self.storage_value.pack(side="left", padx=5)
        self.storage_scale.configure(command=lambda v: self.storage_value.config(text=f"{int(float(v))} MB"))
        
        # CPU Cores
        cpu_frame = tk.Frame(form_frame, bg=self.colors["card"])
        cpu_frame.pack(fill="x", pady=10, padx=20)
        tk.Label(cpu_frame, text="CPU Cores:", font=("Segoe UI", 11),
                bg=self.colors["card"], fg=self.colors["text"], width=18, anchor="w").pack(side="left")
        self.cpu_spinbox = tk.Spinbox(cpu_frame, from_=1, to=8, width=10, font=("Segoe UI", 11),
                                      bg="#0f172a", fg=self.colors["text"])
        self.cpu_spinbox.delete(0, tk.END)
        self.cpu_spinbox.insert(0, "2")
        self.cpu_spinbox.pack(side="left", padx=10)
        
        # Create button
        create_btn = tk.Button(form_frame, text="🚀 Create Device", command=self.create_new_device,
                               bg=self.colors["accent"], fg="white", font=("Segoe UI", 13, "bold"),
                               cursor="hand2", padx=30, pady=10)
        create_btn.pack(pady=(20, 10))
        
        self.refresh_device_list()
        
    def refresh_device_list(self):
        self.device_listbox.delete(0, tk.END)
        devices = self.device_manager.get_all_devices()
        if not devices:
            self.device_listbox.insert(tk.END, "  No devices found. Create one!")
            self.device_listbox.itemconfig(0, fg=self.colors["warning"])
            return
        for device in devices:
            created = datetime.fromisoformat(device["created_date"]).strftime("%Y-%m-%d")
            display_text = f"📱 {device['name']} | RAM: {device['memory_size']}MB | Storage: {device['storage_size']}MB | Created: {created}"
            self.device_listbox.insert(tk.END, display_text)
    
    def get_selected_device_id(self):
        selection = self.device_listbox.curselection()
        if selection:
            devices = self.device_manager.get_all_devices()
            if devices and selection[0] < len(devices):
                return devices[selection[0]]["id"]
        return None
    
    def load_selected_device(self, event=None):
        device_id = self.get_selected_device_id()
        if device_id:
            device = self.device_manager.load_device(device_id)
            if device:
                self.on_device_selected(device)
    
    def delete_selected_device(self):
        device_id = self.get_selected_device_id()
        if device_id:
            if messagebox.askyesno("Confirm Delete", "Delete this device? All data will be lost!"):
                self.device_manager.delete_device(device_id)
                self.refresh_device_list()
    
    def create_new_device(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a device name!")
            return
        memory_size = int(self.mem_scale.get())
        storage_size = int(self.storage_scale.get())
        cpu_cores = int(self.cpu_spinbox.get())
        device = self.device_manager.create_device(name, memory_size, storage_size, cpu_cores)
        messagebox.showinfo("Success", f"Device '{name}' created successfully!")
        self.refresh_device_list()
        self.on_device_selected(device)