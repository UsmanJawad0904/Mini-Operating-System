#!/usr/bin/env python3
"""
MiniOS Ultimate CLI Edition - Complete Operating System Simulator
Advanced features: Persistent devices, Real-time monitoring, Full OS simulation
"""

import sys
import os
import time
import random
import json
import shutil
import subprocess
import threading
from datetime import datetime
from collections import deque
from pathlib import Path
import uuid

# Try to import colorama for colored output
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = BLACK = RESET = ''
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''

# ============================================================================
# DEVICE MANAGEMENT SYSTEM
# ============================================================================

class Device:
    """Persistent device with full state"""
    def __init__(self, device_id, name, memory_size, storage_size, cpu_cores=2):
        self.device_id = device_id
        self.name = name
        self.memory_size = memory_size
        self.storage_size = storage_size
        self.cpu_cores = cpu_cores
        self.created_date = datetime.now()
        self.last_used = datetime.now()
        
        # Device state
        self.memory_blocks = []
        self.processes = []
        self.file_system = {}
        self.scheduling_history = []
        self.command_history = []
        self.current_directory = ""
        self.settings = {"theme": "dark", "default_scheduler": "FCFS"}
        
    def to_dict(self):
        return {
            "device_id": self.device_id, "name": self.name,
            "memory_size": self.memory_size, "storage_size": self.storage_size,
            "cpu_cores": self.cpu_cores,
            "created_date": self.created_date.isoformat(),
            "last_used": self.last_used.isoformat(),
            "memory_blocks": self.memory_blocks,
            "processes": self.processes,
            "file_system": self.file_system,
            "scheduling_history": self.scheduling_history,
            "command_history": self.command_history,
            "current_directory": self.current_directory,
            "settings": self.settings
        }
    
    @classmethod
    def from_dict(cls, data):
        device = cls(data["device_id"], data["name"], data["memory_size"], 
                     data["storage_size"], data.get("cpu_cores", 2))
        device.created_date = datetime.fromisoformat(data["created_date"])
        device.last_used = datetime.fromisoformat(data["last_used"])
        device.memory_blocks = data.get("memory_blocks", [])
        device.processes = data.get("processes", [])
        device.file_system = data.get("file_system", {})
        device.scheduling_history = data.get("scheduling_history", [])
        device.command_history = data.get("command_history", [])
        device.current_directory = data.get("current_directory", "")
        device.settings = data.get("settings", {})
        return device


class DeviceManager:
    """Manages persistent devices"""
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
        return {"last_device": None, "total_devices": 0, "version": "2.0"}
    
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
                "children": {
                    "Documents": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "Downloads": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "Pictures": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "Videos": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "Music": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "readme.txt": {
                        "type": "file", "size": 1024,
                        "content": f"Welcome to {device_name}!\nCreated: {datetime.now()}\nStorage: {self.current_device.storage_size if self.current_device else 'N/A'}MB",
                        "created": datetime.now().isoformat()
                    }
                },
                "created": datetime.now().isoformat()
            }
        }
    
    def create_default_memory_blocks(self, memory_size):
        sizes = [memory_size//10, memory_size//8, memory_size//6, memory_size//5, memory_size//4, memory_size//3]
        return [{"size": s, "allocated": None, "fragmentation": 0} for s in sizes if s > 0]
    
    def save_device(self, device):
        with open(self.devices_dir / f"{device.device_id}.json", 'w') as f:
            json.dump(device.to_dict(), f, indent=2)
    
    def load_device(self, device_id):
        file_path = self.devices_dir / f"{device_id}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
            device = Device.from_dict(data)
            device.last_used = datetime.now()
            self.current_device = device
            self.save_device(device)
            return device
        return None
    
    def get_all_devices(self):
        devices = []
        for f in self.devices_dir.glob("*.json"):
            with open(f, 'r') as file:
                data = json.load(file)
                devices.append({
                    "id": data["device_id"], "name": data["name"],
                    "memory_size": data["memory_size"], "storage_size": data["storage_size"],
                    "cpu_cores": data.get("cpu_cores", 2),
                    "last_used": data["last_used"], "created_date": data["created_date"]
                })
        return sorted(devices, key=lambda x: x["last_used"], reverse=True)
    
    def delete_device(self, device_id):
        file_path = self.devices_dir / f"{device_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def update_device_state(self, device, state_data):
        if "memory_blocks" in state_data:
            device.memory_blocks = state_data["memory_blocks"]
        if "processes" in state_data:
            device.processes = state_data["processes"]
        if "file_system" in state_data:
            device.file_system = state_data["file_system"]
        if "command_history" in state_data:
            device.command_history = state_data["command_history"]
        device.last_used = datetime.now()
        self.save_device(device)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title, char='='):
    print(f"\n{Fore.CYAN}{char*70}")
    print(f"{Fore.YELLOW}{title.center(70)}")
    print(f"{Fore.CYAN}{char*70}{Style.RESET_ALL}\n")

def print_success(msg):
    print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")

def print_error(msg):
    print(f"{Fore.RED}❌ {msg}{Style.RESET_ALL}")

def print_info(msg):
    print(f"{Fore.BLUE}ℹ️  {msg}{Style.RESET_ALL}")

def print_warning(msg):
    print(f"{Fore.YELLOW}⚠️  {msg}{Style.RESET_ALL}")

def print_table(headers, rows, min_width=12):
    if not rows:
        print_info("No data to display")
        return
    col_widths = [max(len(str(h)), min_width) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    total_width = sum(col_widths) + (len(headers) * 3)
    print(f"\n{Fore.CYAN}{'─'*total_width}{Style.RESET_ALL}")
    header_line = ""
    for i, h in enumerate(headers):
        header_line += f"{Fore.CYAN}{str(h):<{col_widths[i]}}{Style.RESET_ALL} │ "
    print(header_line[:-3])
    print(f"{Fore.CYAN}{'─'*total_width}{Style.RESET_ALL}")
    for row in rows:
        line = ""
        for i, cell in enumerate(row):
            line += f"{str(cell):<{col_widths[i]}} │ "
        print(line[:-3])
    print(f"{Fore.CYAN}{'─'*total_width}{Style.RESET_ALL}\n")

def progress_bar(percentage, width=30, color=Fore.GREEN):
    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"{color}{bar}{Style.RESET_ALL}"

def get_input(prompt, default=None, input_type=str, valid_range=None, choices=None):
    while True:
        try:
            if default:
                user_input = input(f"{Fore.YELLOW}{prompt} [{default}]: {Style.RESET_ALL}").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{Fore.YELLOW}{prompt}: {Style.RESET_ALL}").strip()
            if choices and user_input not in choices:
                print_error(f"Choose from: {', '.join(choices)}")
                continue
            if input_type == int:
                value = int(user_input)
                if valid_range and not (valid_range[0] <= value <= valid_range[1]):
                    print_error(f"Value must be between {valid_range[0]} and {valid_range[1]}")
                    continue
                return value
            return user_input
        except ValueError:
            print_error(f"Invalid input! Enter a valid {input_type.__name__}")


# ============================================================================
# CPU SCHEDULING MODULE
# ============================================================================

class CPUScheduler:
    @staticmethod
    def fcfs(processes):
        time = 0
        results = []
        gantt = []
        for p in processes:
            if time < p['arrival']:
                time = p['arrival']
            start = time
            time += p['burst']
            ct, tat, wt = time, time - p['arrival'], time - p['arrival'] - p['burst']
            results.append({'name': p['name'], 'arrival': p['arrival'], 'burst': p['burst'],
                           'completion': ct, 'turnaround': tat, 'waiting': wt})
            gantt.append((p['name'], start, time))
        return results, gantt
    
    @staticmethod
    def sjf(processes):
        time = 0
        results = []
        gantt = []
        remaining = processes.copy()
        while remaining:
            available = [p for p in remaining if p['arrival'] <= time]
            if not available:
                time = min(p['arrival'] for p in remaining)
                continue
            shortest = min(available, key=lambda x: x['burst'])
            start = time
            time += shortest['burst']
            ct, tat, wt = time, time - shortest['arrival'], time - shortest['arrival'] - shortest['burst']
            results.append({'name': shortest['name'], 'arrival': shortest['arrival'], 'burst': shortest['burst'],
                           'completion': ct, 'turnaround': tat, 'waiting': wt})
            gantt.append((shortest['name'], start, time))
            remaining.remove(shortest)
        return results, gantt
    
    @staticmethod
    def priority_scheduling(processes):
        time = 0
        results = []
        gantt = []
        remaining = processes.copy()
        while remaining:
            available = [p for p in remaining if p['arrival'] <= time]
            if not available:
                time = min(p['arrival'] for p in remaining)
                continue
            highest = min(available, key=lambda x: (x['priority'], x['arrival']))
            start = time
            time += highest['burst']
            ct, tat, wt = time, time - highest['arrival'], time - highest['arrival'] - highest['burst']
            results.append({'name': highest['name'], 'arrival': highest['arrival'], 'burst': highest['burst'],
                           'priority': highest['priority'], 'completion': ct, 'turnaround': tat, 'waiting': wt})
            gantt.append((highest['name'], start, time))
            remaining.remove(highest)
        return results, gantt
    
    @staticmethod
    def round_robin(processes, quantum):
        time = 0
        results = {}
        gantt = []
        queue = deque()
        remaining = {p['name']: p['burst'] for p in processes}
        arrival = {p['name']: p['arrival'] for p in processes}
        for p in processes:
            if p['arrival'] == 0:
                queue.append(p['name'])
        completed = set()
        while len(completed) < len(processes):
            for p in processes:
                if p['arrival'] <= time and p['name'] not in queue and p['name'] not in completed:
                    queue.append(p['name'])
            if not queue:
                time += 1
                continue
            current = queue.popleft()
            exec_time = min(quantum, remaining[current])
            start = time
            time += exec_time
            remaining[current] -= exec_time
            gantt.append((current, start, time))
            if remaining[current] == 0:
                ct = time
                tat = ct - arrival[current]
                burst = next(p['burst'] for p in processes if p['name'] == current)
                wt = tat - burst
                results[current] = {'name': current, 'arrival': arrival[current], 'burst': burst,
                                   'completion': ct, 'turnaround': tat, 'waiting': wt}
                completed.add(current)
            else:
                queue.append(current)
        return list(results.values()), gantt
    
    @staticmethod
    def display_results(results, gantt):
        if not results:
            print_error("No results")
            return
        avg_tat = sum(r['turnaround'] for r in results) / len(results)
        avg_wt = sum(r['waiting'] for r in results) / len(results)
        headers = ['Process', 'Arrival', 'Burst', 'Completion', 'Turnaround', 'Waiting']
        rows = [[r['name'], r['arrival'], r['burst'], r['completion'], 
                f"{r['turnaround']:.2f}", f"{r['waiting']:.2f}"] for r in results]
        print_table(headers, rows)
        print(f"{Fore.GREEN}📊 Average Turnaround: {avg_tat:.2f}")
        print(f"📊 Average Waiting: {avg_wt:.2f}")
        print(f"📊 Total Time: {max(r['completion'] for r in results)}{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}📈 Gantt Chart:{Style.RESET_ALL}")
        print(" " + "".join([f"+{'-'*8}+" for _ in gantt]))
        print(" " + "".join([f"| {p:^6} " for p, _, _ in gantt]) + "|")
        print(" " + "".join([f"+{'-'*8}+" for _ in gantt]))
        print(" " + "".join([f"{s:^4}    " for _, s, _ in gantt]) + f"{gantt[-1][2]}")


# ============================================================================
# MEMORY MANAGEMENT MODULE
# ============================================================================

class MemoryManager:
    @staticmethod
    def first_fit(blocks, processes):
        allocation = [-1] * len(processes)
        used = [False] * len(blocks)
        frag = [0] * len(blocks)
        for i, ps in enumerate(processes):
            for j, bs in enumerate(blocks):
                if not used[j] and bs >= ps:
                    allocation[i], used[j], frag[j] = j, True, bs - ps
                    break
        return allocation, used, frag
    
    @staticmethod
    def best_fit(blocks, processes):
        allocation = [-1] * len(processes)
        used = [False] * len(blocks)
        frag = [0] * len(blocks)
        for i, ps in enumerate(processes):
            best, best_frag = -1, float('inf')
            for j, bs in enumerate(blocks):
                if not used[j] and bs >= ps:
                    f = bs - ps
                    if f < best_frag:
                        best_frag, best = f, j
            if best != -1:
                allocation[i], used[best], frag[best] = best, True, best_frag
        return allocation, used, frag
    
    @staticmethod
    def worst_fit(blocks, processes):
        allocation = [-1] * len(processes)
        used = [False] * len(blocks)
        frag = [0] * len(blocks)
        for i, ps in enumerate(processes):
            worst, worst_frag = -1, -1
            for j, bs in enumerate(blocks):
                if not used[j] and bs >= ps:
                    f = bs - ps
                    if f > worst_frag:
                        worst_frag, worst = f, j
            if worst != -1:
                allocation[i], used[worst], frag[worst] = worst, True, worst_frag
        return allocation, used, frag
    
    @staticmethod
    def display_results(blocks, processes, allocation, frag):
        print(f"\n{Fore.CYAN}📦 Memory Blocks:{Style.RESET_ALL}")
        for i, b in enumerate(blocks):
            status = f"{Fore.RED}Allocated{Style.RESET_ALL}" if allocation[i] != -1 else f"{Fore.GREEN}Free{Style.RESET_ALL}"
            print(f"  Block {i}: {b}MB - {status} (Frag: {frag[i] if allocation[i] != -1 else 0}MB)")
        print(f"\n{Fore.CYAN}📋 Process Allocation:{Style.RESET_ALL}")
        headers = ['Process', 'Size', 'Block', 'Fragmentation']
        rows, total_frag = [], 0
        for i, ps in enumerate(processes):
            if allocation[i] != -1:
                total_frag += frag[allocation[i]]
                rows.append([f"P{i+1}", f"{ps}MB", f"Block {allocation[i]}", f"{frag[allocation[i]]}MB"])
            else:
                rows.append([f"P{i+1}", f"{ps}MB", f"{Fore.RED}NOT ALLOCATED{Style.RESET_ALL}", "-"])
        print_table(headers, rows)
        total_mem = sum(blocks)
        alloc_mem = sum(ps for i, ps in enumerate(processes) if allocation[i] != -1)
        util = (alloc_mem / total_mem * 100) if total_mem > 0 else 0
        print(f"{Fore.GREEN}📊 Total Fragmentation: {total_frag}MB")
        print(f"📊 Memory Utilization: {util:.1f}%")
        print(f"📊 Allocated: {alloc_mem}/{total_mem}MB{Style.RESET_ALL}")


# ============================================================================
# FILE SYSTEM MODULE
# ============================================================================

class FileSystemCLI:
    def __init__(self, device=None, device_manager=None):
        self.device = device
        self.device_manager = device_manager
        if device and hasattr(device, 'file_system') and device.file_system:
            self.fs = device.file_system
        else:
            self.fs = self.create_default_fs()
        self.current_path = ["root"]
    
    def create_default_fs(self):
        return {
            "root": {
                "type": "folder",
                "children": {
                    "Documents": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "Downloads": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "Pictures": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "Videos": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "Music": {"type": "folder", "children": {}, "created": datetime.now().isoformat()},
                    "readme.txt": {"type": "file", "size": 1024, "content": "Welcome to MiniOS!", "created": datetime.now().isoformat()}
                },
                "created": datetime.now().isoformat()
            }
        }
    
    def save_state(self):
        if self.device and self.device_manager:
            self.device.file_system = self.fs
            self.device_manager.update_device_state(self.device, {"file_system": self.fs})
    
    def get_node(self):
        node = self.fs
        for p in self.current_path:
            node = node[p] if p == "root" else node["children"].get(p, {})
            if not node:
                return None
        return node
    
    def get_path(self):
        return "/" + "/".join(self.current_path[1:])
    
    def list_contents(self):
        node = self.get_node()
        if not node or node.get("type") != "folder":
            print_error("Invalid directory")
            return
        items = node.get("children", {})
        if not items:
            print_info("Directory is empty")
            return
        print(f"\n{Fore.CYAN}📁 Contents of {self.get_path()}:{Style.RESET_ALL}")
        headers = ['Name', 'Type', 'Size', 'Created']
        rows = []
        for name, data in sorted(items.items()):
            icon = "📁" if data["type"] == "folder" else "📄"
            size = f"{data.get('size', 0)}B" if data["type"] == "file" else "-"
            created = data.get('created', datetime.now().isoformat())[:10]
            rows.append([f"{icon} {name}", data["type"], size, created])
        print_table(headers, rows)
    
    def change_dir(self, name):
        if name == "..":
            if len(self.current_path) > 1:
                self.current_path.pop()
                print_success(f"Changed to {self.get_path()}")
            else:
                print_error("Already at root")
            return
        node = self.get_node()
        if node and name in node.get("children", {}):
            if node["children"][name]["type"] == "folder":
                self.current_path.append(name)
                print_success(f"Changed to {self.get_path()}")
            else:
                print_error(f"'{name}' is a file")
        else:
            print_error(f"Directory '{name}' not found")
    
    def create_folder(self, name):
        node = self.get_node()
        if not node:
            print_error("Invalid location")
            return
        if name in node.get("children", {}):
            print_error(f"'{name}' already exists")
            return
        node["children"][name] = {"type": "folder", "children": {}, "created": datetime.now().isoformat()}
        print_success(f"Folder '{name}' created")
        self.save_state()
    
    def create_file(self, name, content=""):
        node = self.get_node()
        if not node:
            print_error("Invalid location")
            return
        if name in node.get("children", {}):
            print_error(f"'{name}' already exists")
            return
        if not content:
            content = f"File created at {datetime.now()}"
        node["children"][name] = {"type": "file", "size": len(content), "content": content, "created": datetime.now().isoformat()}
        print_success(f"File '{name}' created")
        self.save_state()
    
    def delete_item(self, name):
        node = self.get_node()
        if not node:
            print_error("Invalid location")
            return
        if name not in node.get("children", {}):
            print_error(f"'{name}' not found")
            return
        if get_input(f"Delete '{name}'? (y/n)", "n").lower() == 'y':
            del node["children"][name]
            print_success(f"'{name}' deleted")
            self.save_state()
    
    def rename_item(self, old, new):
        node = self.get_node()
        if not node:
            print_error("Invalid location")
            return
        if old not in node.get("children", {}):
            print_error(f"'{old}' not found")
            return
        if new in node.get("children", {}):
            print_error(f"'{new}' already exists")
            return
        node["children"][new] = node["children"].pop(old)
        print_success(f"Renamed '{old}' → '{new}'")
        self.save_state()
    
    def view_file(self, name):
        node = self.get_node()
        if not node:
            print_error("Invalid location")
            return
        if name not in node.get("children", {}):
            print_error(f"'{name}' not found")
            return
        item = node["children"][name]
        if item["type"] == "folder":
            print_error(f"'{name}' is a folder")
            return
        print(f"\n{Fore.CYAN}📄 File: {name}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(item.get("content", "No content"))
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    def search(self, query):
        results = []
        def search_rec(node, path):
            for name, data in node.get("children", {}).items():
                if query.lower() in name.lower():
                    icon = "📁" if data["type"] == "folder" else "📄"
                    results.append(f"{icon} {'/'.join(path + [name])}")
                if data.get("type") == "folder":
                    search_rec(data, path + [name])
        search_rec(self.fs["root"], ["root"])
        if results:
            print(f"\n{Fore.GREEN}🔍 Found {len(results)} items:{Style.RESET_ALL}")
            for r in results:
                print(f"  {r}")
        else:
            print_info(f"No items found matching '{query}'")
    
    def show_info(self):
        node = self.get_node()
        if node:
            items = len(node.get("children", {}))
            folders = sum(1 for d in node.get("children", {}).values() if d["type"] == "folder")
            files = items - folders
            created = node.get('created', datetime.now().isoformat())[:10]
            print(f"\n{Fore.CYAN}📊 Directory Info:{Style.RESET_ALL}")
            print(f"  Path: {self.get_path()}")
            print(f"  Items: {items} (📁 {folders}, 📄 {files})")
            print(f"  Created: {created}")


# ============================================================================
# MAIN CLI APPLICATION
# ============================================================================

class MiniOSCLI:
    def __init__(self):
        self.device_manager = DeviceManager()
        self.current_device = None
        self.running = True
    
    def display_banner(self):
        clear_screen()
        banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║     ███╗   ███╗██╗███╗   ██╗██╗ ██████╗ ███████╗                            ║
║     ████╗ ████║██║████╗  ██║██║██╔═══██╗██╔════╝                            ║
║     ██╔████╔██║██║██╔██╗ ██║██║██║   ██║███████╗                            ║
║     ██║╚██╔╝██║██║██║╚██╗██║██║██║   ██║╚════██║                            ║
║     ██║ ╚═╝ ██║██║██║ ╚████║██║╚██████╔╝███████║                            ║
║     ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝ ╚══════╝                            ║
║                                                                               ║
║                    MiniOS Ultimate CLI Edition v3.0                          ║
║                 Advanced Operating System Simulator                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)
        print(f"{Fore.YELLOW}💡 Welcome to MiniOS! Type 'help' for commands | 'exit' to quit{Style.RESET_ALL}\n")
    
    def show_device_menu(self):
        while True:
            clear_screen()
            print_header("💾 DEVICE MANAGER")
            devices = self.device_manager.get_all_devices()
            if devices:
                print(f"{Fore.CYAN}📱 Available Devices:{Style.RESET_ALL}")
                for i, d in enumerate(devices, 1):
                    print(f"  {i}. {Fore.GREEN}{d['name']}{Style.RESET_ALL} | RAM: {d['memory_size']}MB | Storage: {d['storage_size']}MB")
                print(f"\n  {len(devices)+1}. Create New Device")
                print(f"  {len(devices)+2}. Delete Device")
                print(f"  {len(devices)+3}. Exit")
                choice = get_input("\nSelect device", default=1, input_type=int, 
                                   valid_range=(1, len(devices)+3))
                if 1 <= choice <= len(devices):
                    device = self.device_manager.load_device(devices[choice-1]["id"])
                    if device:
                        self.current_device = device
                        print_success(f"Loaded device: {device.name}")
                        time.sleep(1)
                        return
                elif choice == len(devices)+1:
                    self.create_new_device()
                elif choice == len(devices)+2:
                    self.delete_device_prompt(devices)
                else:
                    self.running = False
                    return
            else:
                print_info("No devices found. Create one to begin!")
                self.create_new_device()
                return
    
    def create_new_device(self):
        print_header("✨ CREATE NEW DEVICE")
        name = get_input("Device Name", "My MiniOS Device")
        print_info("Memory Size Options: 512MB, 1024MB, 2048MB, 4096MB, 8192MB")
        memory = get_input("Memory Size (MB)", 2048, int, (512, 8192))
        print_info("Storage Size Options: 1024MB, 2048MB, 4096MB, 8192MB, 16384MB, 32768MB")
        storage = get_input("Storage Size (MB)", 8192, int, (1024, 32768))
        cpu = get_input("CPU Cores", 2, int, (1, 8))
        device = self.device_manager.create_device(name, memory, storage, cpu)
        self.current_device = device
        print_success(f"Device '{name}' created successfully!")
        print_info(f"ID: {device.device_id} | RAM: {memory}MB | Storage: {storage}MB | CPU: {cpu} cores")
        time.sleep(2)
    
    def delete_device_prompt(self, devices):
        if not devices:
            print_error("No devices to delete")
            time.sleep(1)
            return
        print_header("🗑 DELETE DEVICE")
        for i, d in enumerate(devices, 1):
            print(f"  {i}. {d['name']}")
        choice = get_input("Select device to delete", input_type=int, valid_range=(1, len(devices)))
        if get_input(f"Delete '{devices[choice-1]['name']}' permanently? (y/n)", "n").lower() == 'y':
            self.device_manager.delete_device(devices[choice-1]["id"])
            print_success("Device deleted")
            time.sleep(1)
    
    def show_device_info(self):
        if not self.current_device:
            return
        stats = self.get_device_stats()
        print(f"\n{Fore.CYAN}📊 Device: {self.current_device.name}{Style.RESET_ALL}")
        print(f"  🆔 ID: {self.current_device.device_id}")
        print(f"  💾 RAM: {stats['used_memory']}/{stats['total_memory']}MB ({progress_bar(stats['memory_percent'])})")
        print(f"  📀 Storage: {stats['used_storage']//1024}/{stats['total_storage']//1024}MB ({progress_bar(stats['storage_percent'])})")
        print(f"  ⚙️ CPU: {self.current_device.cpu_cores} Cores")
        print(f"  📈 Processes: {len(self.current_device.processes)}")
        print(f"  📅 Created: {self.current_device.created_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"  🕐 Last Used: {self.current_device.last_used.strftime('%Y-%m-%d %H:%M')}")
    
    def get_device_stats(self):
        used_memory = sum(b["size"] for b in self.current_device.memory_blocks if b["allocated"])
        def calc_usage(node):
            total = 0
            if node.get("type") == "folder":
                for child in node.get("children", {}).values():
                    total += calc_usage(child)
            else:
                total += node.get("size", 0)
            return total
        used_storage = calc_usage(self.current_device.file_system)
        return {
            "total_memory": self.current_device.memory_size,
            "used_memory": used_memory,
            "memory_percent": (used_memory / self.current_device.memory_size * 100),
            "total_storage": self.current_device.storage_size,
            "used_storage": used_storage,
            "storage_percent": (used_storage / self.current_device.storage_size * 100)
        }
    
    def run_scheduler(self):
        print_header("⚡ CPU SCHEDULING")
        processes = []
        print_info("Enter process details (blank name to finish)")
        while True:
            name = get_input(f"Process {len(processes)+1} Name", "").strip()
            if not name:
                break
            arrival = get_input("Arrival Time", 0, int, (0, 100))
            burst = get_input("Burst Time", 5, int, (1, 100))
            priority = get_input("Priority (1=highest)", 2, int, (1, 10))
            processes.append({"name": name, "arrival": arrival, "burst": burst, "priority": priority})
            print_success(f"Added {name}")
        if not processes:
            print_error("No processes added")
            return
        print(f"\n{Fore.CYAN}Algorithms: 1.FCFS 2.SJF 3.Priority 4.Round Robin{Style.RESET_ALL}")
        algo = get_input("Choose algorithm", 1, int, (1, 4))
        quantum = None
        if algo == 4:
            quantum = get_input("Time Quantum", 2, int, (1, 10))
        if algo == 1:
            results, gantt = CPUScheduler.fcfs(processes)
        elif algo == 2:
            results, gantt = CPUScheduler.sjf(processes)
        elif algo == 3:
            results, gantt = CPUScheduler.priority_scheduling(processes)
        else:
            results, gantt = CPUScheduler.round_robin(processes, quantum)
        CPUScheduler.display_results(results, gantt)
        self.current_device.processes = processes
        self.device_manager.update_device_state(self.current_device, {"processes": processes})
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def run_memory(self):
        print_header("💾 MEMORY MANAGEMENT")
        blocks = list(map(int, get_input("Memory blocks (comma-separated)", "100,200,300,400,500").split(',')))
        processes = list(map(int, get_input("Process sizes (comma-separated)", "80,120,50,180,90,70").split(',')))
        print(f"\n{Fore.CYAN}Algorithms: 1.First Fit 2.Best Fit 3.Worst Fit{Style.RESET_ALL}")
        algo = get_input("Choose algorithm", 1, int, (1, 3))
        if algo == 1:
            allocation, used, frag = MemoryManager.first_fit(blocks, processes)
        elif algo == 2:
            allocation, used, frag = MemoryManager.best_fit(blocks, processes)
        else:
            allocation, used, frag = MemoryManager.worst_fit(blocks, processes)
        MemoryManager.display_results(blocks, processes, allocation, frag)
        self.current_device.memory_blocks = [{"size": b, "allocated": allocation[i] != -1, "fragmentation": frag[i] if allocation[i] != -1 else 0} 
                                              for i, b in enumerate(blocks)]
        self.device_manager.update_device_state(self.current_device, {"memory_blocks": self.current_device.memory_blocks})
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def run_filesystem(self):
        fs = FileSystemCLI(self.current_device, self.device_manager)
        print_header("📁 FILE SYSTEM")
        print_info("Commands: ls, pwd, cd <dir>, mkdir, touch, rm, mv, cat, search, info, exit\n")
        while True:
            try:
                cmd = input(f"{Fore.GREEN}fs{self.current_device.name}>{Style.RESET_ALL} ").strip().split()
                if not cmd:
                    continue
                if cmd[0] == "exit":
                    break
                elif cmd[0] == "ls":
                    fs.list_contents()
                elif cmd[0] == "pwd":
                    print(f"Current: {fs.get_path()}")
                elif cmd[0] == "cd" and len(cmd) > 1:
                    fs.change_dir(cmd[1])
                elif cmd[0] == "mkdir" and len(cmd) > 1:
                    fs.create_folder(cmd[1])
                elif cmd[0] == "touch" and len(cmd) > 1:
                    fs.create_file(cmd[1])
                elif cmd[0] == "rm" and len(cmd) > 1:
                    fs.delete_item(cmd[1])
                elif cmd[0] == "mv" and len(cmd) > 2:
                    fs.rename_item(cmd[1], cmd[2])
                elif cmd[0] == "cat" and len(cmd) > 1:
                    fs.view_file(cmd[1])
                elif cmd[0] == "search" and len(cmd) > 1:
                    fs.search(" ".join(cmd[1:]))
                elif cmd[0] == "info":
                    fs.show_info()
                elif cmd[0] == "help":
                    print(f"\n{Fore.CYAN}Commands:{Style.RESET_ALL}")
                    print("  ls           - List contents")
                    print("  pwd          - Show path")
                    print("  cd <dir>     - Change directory")
                    print("  mkdir <name> - Create folder")
                    print("  touch <name> - Create file")
                    print("  rm <name>    - Delete item")
                    print("  mv <old> <new>- Rename")
                    print("  cat <file>   - View file")
                    print("  search <term>- Search")
                    print("  info         - Directory info")
                    print("  exit         - Exit")
                else:
                    print_error(f"Unknown: {cmd[0]}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print_error(f"Error: {e}")
    
    def run_process_simulator(self):
        print_header("⚡ REAL-TIME PROCESS SIMULATOR")
        print_info("Simulating processes... Press Ctrl+C to stop\n")
        try:
            for i in range(15):
                pid = random.randint(1000, 9999)
                burst = random.randint(2, 12)
                mem = random.randint(10, 100)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {Fore.GREEN}Process P{pid} created{Style.RESET_ALL} | Burst: {burst}ms | Memory: {mem}MB")
                time.sleep(random.uniform(0.5, 1))
            print(f"\n{Fore.CYAN}Simulation Complete!{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Simulation stopped{Style.RESET_ALL}")
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def run_bankers(self):
        print_header("🔒 BANKER'S ALGORITHM")
        available = [10, 5, 7]
        max_need = [[7,5,3], [3,2,2], [9,0,2], [2,2,2], [4,3,3]]
        allocation = [[0,1,0], [2,0,0], [3,0,2], [2,1,1], [0,0,2]]
        need = [[max_need[i][j] - allocation[i][j] for j in range(3)] for i in range(5)]
        print(f"{Fore.CYAN}Available Resources: {available}{Style.RESET_ALL}")
        headers = ["Process", "Max Need", "Allocated", "Need"]
        rows = [[f"P{i}", str(max_need[i]), str(allocation[i]), str(need[i])] for i in range(5)]
        print_table(headers, rows)
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
            print(f"{Fore.GREEN}✅ System is in SAFE state!{Style.RESET_ALL}")
            print(f"Safe Sequence: {' → '.join(safe_seq)}")
        else:
            print(f"{Fore.RED}❌ Deadlock detected! Unsafe processes: {[f'P{i}' for i, f in enumerate(finish) if not f]}{Style.RESET_ALL}")
        input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def run_monitor(self):
        print_header("📊 PERFORMANCE MONITOR")
        print_info("Real-time monitoring (Press Ctrl+C to stop)\n")
        try:
            while True:
                clear_screen()
                print_header("📊 SYSTEM PERFORMANCE MONITOR", '─')
                stats = self.get_device_stats()
                print(f"{Fore.CYAN}Device: {self.current_device.name}{Style.RESET_ALL}\n")
                print(f"💾 Memory Usage:     {progress_bar(stats['memory_percent'])} {stats['memory_percent']:.1f}%")
                print(f"📀 Storage Usage:    {progress_bar(stats['storage_percent'])} {stats['storage_percent']:.1f}%")
                cpu_sim = random.randint(10, 85)
                print(f"⚙️  CPU Usage:        {progress_bar(cpu_sim)} {cpu_sim}%")
                print(f"\n{Fore.CYAN}📈 Active Processes: {len(self.current_device.processes)}")
                print(f"📊 Total Memory:     {stats['total_memory']}MB")
                print(f"🎯 Used Memory:      {stats['used_memory']}MB")
                print(f"💿 Total Storage:    {stats['total_storage']//1024}MB")
                print(f"📁 Used Storage:     {stats['used_storage']//1024}MB{Style.RESET_ALL}")
                time.sleep(2)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Monitoring stopped{Style.RESET_ALL}")
    
    def show_help(self):
        print_header("📚 AVAILABLE COMMANDS")
        commands = [
            ("scheduler", "CPU Scheduling (FCFS, SJF, Priority, RR)"),
            ("memory", "Memory Management (First/Best/Worst Fit)"),
            ("filesystem", "File System Explorer"),
            ("process", "Real-time Process Simulator"),
            ("banker", "Banker's Algorithm - Deadlock Detection"),
            ("monitor", "Performance Monitor"),
            ("info", "Show Device Information"),
            ("clear", "Clear Screen"),
            ("help", "Show this menu"),
            ("exit", "Exit MiniOS"),
        ]
        for cmd, desc in commands:
            print(f"  {Fore.GREEN}{cmd:<12}{Style.RESET_ALL} {desc}")
        print()
    
    def run(self):
        self.show_device_menu()
        if not self.running:
            return
        while self.running:
            try:
                if not self.current_device:
                    self.show_device_menu()
                    if not self.running:
                        break
                clear_screen()
                print_header(f"🐧 MINIOS - {self.current_device.name}")
                self.show_device_info()
                print(f"\n{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Commands: scheduler | memory | filesystem | process | banker | monitor | info | clear | help | exit{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
                cmd = input(f"\n{Fore.GREEN}{self.current_device.name}> {Style.RESET_ALL}").strip().lower()
                if cmd == "exit":
                    print_success("Goodbye!")
                    self.running = False
                elif cmd == "scheduler":
                    self.run_scheduler()
                elif cmd == "memory":
                    self.run_memory()
                elif cmd == "filesystem":
                    self.run_filesystem()
                elif cmd == "process":
                    self.run_process_simulator()
                elif cmd == "banker":
                    self.run_bankers()
                elif cmd == "monitor":
                    self.run_monitor()
                elif cmd == "info":
                    self.show_device_info()
                    input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
                elif cmd == "clear":
                    clear_screen()
                elif cmd == "help":
                    self.show_help()
                    input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
                elif cmd:
                    print_error(f"Unknown command: {cmd}")
                    print_info("Type 'help' for available commands")
                    time.sleep(1)
            except KeyboardInterrupt:
                print_success("\nGoodbye!")
                self.running = False
            except Exception as e:
                print_error(f"Error: {e}")
                time.sleep(1)


if __name__ == "__main__":
    if not COLORS_AVAILABLE:
        print("For best experience install colorama: pip install colorama")
    cli = MiniOSCLI()
    cli.run()