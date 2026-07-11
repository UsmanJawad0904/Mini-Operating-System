"""
Ubuntu-Style Shell Terminal - Windows Compatible
All commands handled properly
"""

import tkinter as tk
from tkinter import font, simpledialog
import subprocess
import os
import platform
import shlex
from datetime import datetime


class UltimateShell:
    def __init__(self, parent, back_callback, log_callback, device, device_manager, refresh_callback=None):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        self.refresh_callback = refresh_callback
        
        self.os_type = platform.system()
        self.username = os.getenv("USER") or os.getenv("USERNAME") or "minios"
        self.hostname = platform.node() or "minios"
        self.home_dir = os.path.expanduser("~")
        self.current_dir = self.home_dir if os.path.exists(self.home_dir) else os.getcwd()
        
        self.colors = {"bg": "#1e1e2e", "text": "#cdd6f4", "prompt": "#a6e3a1", "error": "#f38ba8", "success": "#a6e3a1"}
        
        # Load command history from device
        if hasattr(self.device, 'command_history') and self.device.command_history:
            self.command_history = self.device.command_history
        else:
            self.command_history = []
        self.history_index = -1
        
        # Virtual device filesystem and current device path
        if not hasattr(self.device, 'file_system') or not self.device.file_system:
            self.device.file_system = self.create_default_fs()
        saved_path = getattr(self.device, 'current_directory', None)
        if saved_path:
            self.current_path = [seg for seg in saved_path.split("/") if seg]
        else:
            self.current_path = ["root"]
        if not self.current_path or self.current_path[0] != "root":
            self.current_path = ["root"]
        self.current_dir = self.get_dir_display()
        self.save_state()
        self.first_pwd = True
        
        # Command aliases (Linux to Windows mapping)
        self.aliases = {
            "ll": "ls -la" if self.os_type != "Windows" else "dir /w",
            "la": "ls -la" if self.os_type != "Windows" else "dir /a",
            "cls": "clear" if self.os_type != "Windows" else "cls",
        }
        
        # Built-in commands (handled internally, not sent to system)
        self.builtin_commands = {
            "cd": self.cd_command,
            "pwd": self.pwd_command,
            "ls": self.ls_command,
            "dir": self.ls_command,
            "echo": self.echo_command,
            "type": self.type_command,
            "cat": self.cat_command,
            "mkdir": self.mkdir_command,
            "rm": self.rm_command,
            "del": self.rm_command,
            "clear": self.clear_terminal,
            "exit": self.exit_shell,
            "help": self.show_help,
            "minios": self.show_info,
            "about": self.show_about,
            "neofetch": self.neofetch,
            "touch": self.touch_command,
            "write": self.write_command,
            "edit": self.edit_command,
            "storage": self.show_storage,
            "meminfo": self.show_memory_info,
            "sysinfo": self.show_info,
            "scheduler": self.launch_scheduler,
            "memory": self.launch_memory,
            "filesystem": self.launch_filesystem,
            "advanced": self.launch_advanced,
            "dashboard": self.launch_dashboard,
        }
        
        self.setup_ui()
        self.print_banner()
        self.input_entry.focus()
        
    def setup_ui(self):
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        header = tk.Frame(self.main_frame, bg="#313244", height=40)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🐧 MiniOS Terminal", font=("Segoe UI", 11, "bold"),
                bg="#313244", fg=self.colors["text"]).pack(side="left", padx=15, pady=10)
        
        os_text = "Windows Mode" if self.os_type == "Windows" else "Linux Mode"
        tk.Label(header, text=f"[{os_text}]", font=("Segoe UI", 9),
                bg="#313244", fg=self.colors["success"]).pack(side="left", padx=5)
        
        tk.Label(header, text=f"📁 {self.device.name}:{self.current_dir}", font=("Segoe UI", 9),
                bg="#313244", fg=self.colors["success"]).pack(side="right", padx=15)
        
        term_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        term_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.output_text = tk.Text(term_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                   font=("Consolas", 11), wrap="word", insertbackground="white")
        scroll = tk.Scrollbar(term_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scroll.set)
        self.output_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        input_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        input_frame.pack(fill="x", padx=5, pady=(0,5))
        
        self.prompt_label = tk.Label(input_frame, text=self.get_prompt(), font=("Consolas", 11, "bold"),
                                     bg=self.colors["bg"], fg=self.colors["prompt"])
        self.prompt_label.pack(side="left")
        
        self.input_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                    font=("Consolas", 11), insertbackground="white", relief="flat")
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(5,0))
        self.input_entry.bind("<Return>", self.execute)
        self.input_entry.bind("<Up>", self.history_up)
        self.input_entry.bind("<Down>", self.history_down)
        
        btn_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="← Exit to Dashboard", command=self.go_back,
                 bg="#45475a", fg="white", cursor="hand2", padx=20).pack()
        
    def get_prompt(self):
        cur = self.current_dir.replace(self.home_dir, "~") if self.current_dir.startswith(self.home_dir) else self.current_dir
        return f"{self.username}@{self.hostname}:{cur}$ "
        
    def update_prompt(self):
        self.prompt_label.config(text=self.get_prompt())
        
    def append(self, text, is_error=False):
        if is_error:
            self.output_text.insert(tk.END, text, "error")
            self.output_text.tag_config("error", foreground=self.colors["error"])
        else:
            self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        
    def save_history(self):
        self.device.command_history = self.command_history[-100:]
        self.device.current_directory = "/".join(self.current_path)
        self.device_manager.update_device_state(self.device, {
            "command_history": self.device.command_history,
            "current_directory": self.device.current_directory
        })
        
    def print_banner(self):
        mode = "Windows Compatibility Mode" if self.os_type == "Windows" else "Native Linux Mode"
        banner = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                         MiniOS Ultimate Shell                             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Device: {self.device.name} | RAM: {self.device.memory_size}MB | Storage: {self.device.storage_size}MB
║  Mode: {mode}
║  Commands: ls, cd, pwd, mkdir, rm, cat, echo, clear, help, exit
║  Type 'help' for all commands
╚═══════════════════════════════════════════════════════════════════════════╝
"""
        self.append(banner)
        
    # ========================================================================
    # BUILT-IN COMMANDS (Handled internally)
    # ========================================================================
    
    def get_dir_display(self):
        if len(self.current_path) == 1:
            return "/"
        return "/" + "/".join(self.current_path[1:])

    def normalize_path(self, path):
        if path.startswith("/"):
            segments = [seg for seg in path.strip("/").split("/") if seg]
            normalized = ["root"] + segments
        else:
            segments = [seg for seg in path.split("/") if seg]
            normalized = list(self.current_path)
            for seg in segments:
                if seg == ".":
                    continue
                if seg == "..":
                    if len(normalized) > 1:
                        normalized.pop()
                    continue
                normalized.append(seg)
        if not normalized:
            normalized = ["root"]
        if normalized[0] != "root":
            normalized.insert(0, "root")
        return normalized

    def get_node(self, path=None):
        if path is None:
            path = self.current_path
        node = self.device.file_system.get("root", {})
        if not path or path[0] != "root":
            return None
        for segment in path[1:]:
            if node.get("type") != "folder":
                return None
            node = node.get("children", {}).get(segment)
            if node is None:
                return None
        return node

    def save_state(self):
        self.device.current_directory = "/".join(self.current_path)
        self.device.file_system = self.device.file_system
        self.device.command_history = self.command_history[-100:]
        self.device_manager.update_device_state(self.device, {
            "current_directory": self.device.current_directory,
            "file_system": self.device.file_system,
            "command_history": self.device.command_history
        })
        if callable(self.refresh_callback):
            self.refresh_callback()

    def create_default_fs(self):
        return {
            "root": {
                "type": "folder",
                "size": 4096,
                "children": {},
                "created": datetime.now().isoformat()
            }
        }

    def cd_command(self, args):
        """Change directory - built-in"""
        if not args:
            new_path = ["root"]
        else:
            new_path = self.normalize_path(args[0])
        node = self.get_node(new_path)
        if node and node.get("type") == "folder":
            self.current_path = new_path
            self.current_dir = self.get_dir_display()
            self.update_prompt()
            self.append(f"Changed to {self.current_dir}\n")
        else:
            self.append(f"cd: {args[0]}: No such directory\n", is_error=True)

    def pwd_command(self, args):
        """Print working directory - built-in"""
        if self.first_pwd:
            self.append(f"{self.device.name}:{self.current_dir}\n")
            self.first_pwd = False
        else:
            self.append(f"{self.current_dir}\n")

    def echo_command(self, args):
        """Echo text to terminal"""
        self.append(" ".join(args) + "\n")

    def type_command(self, args):
        """Windows-style cat alias"""
        self.cat_command(args)

    def format_size(self, size):
        if size >= 1024**3:
            return f"{size / 1024**3:.2f} GB"
        if size >= 1024**2:
            return f"{size / 1024**2:.2f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def ls_command(self, args):
        """List directory contents - built-in"""
        try:
            target_path = list(self.current_path)
            show_all = False
            long_format = False
            remaining = []
            for arg in args:
                if arg == "-a" or arg == "--all":
                    show_all = True
                elif arg == "-l":
                    long_format = True
                else:
                    remaining.append(arg)
            if remaining:
                target_path = self.normalize_path(remaining[-1])
            node = self.get_node(target_path)
            if not node:
                self.append(f"ls: {remaining[-1] if remaining else self.current_dir}: No such file or directory\n", is_error=True)
                return
            if node.get("type") != "folder":
                self.append(f"{remaining[-1]}\n")
                return
            items = sorted(node.get("children", {}).items())
            if not show_all:
                items = [(name, data) for name, data in items if not name.startswith('.')]
            if long_format:
                self.append(f"\n{'Type':<8} {'Size':<12} {'Created':<20} {'Name'}\n")
                self.append("-" * 70 + "\n")
                for name, data in items:
                    dtype = "DIR" if data["type"] == "folder" else "FILE"
                    size = self.format_size(data.get("size", 0))
                    created = data.get("created", "-")
                    self.append(f"{dtype:<8} {size:<12} {created:<20} {name}\n")
            else:
                cols = 4
                names = [name + ("/" if data["type"] == "folder" else "") for name, data in items]
                for i in range(0, len(names), cols):
                    row = names[i:i+cols]
                    self.append("  ".join(f"{item:<20}" for item in row) + "\n")
            self.append("\n")
        except Exception as e:
            self.append(f"ls: {e}\n", is_error=True)

    def touch_command(self, args):
        """Create an empty file in the current device filesystem"""
        if not args:
            self.append("touch: missing file operand\n", is_error=True)
            return
        node = self.get_node(self.current_path)
        if not node or node.get("type") != "folder":
            self.append("touch: current directory invalid\n", is_error=True)
            return
        for filename in args:
            if filename in node.get("children", {}):
                self.append(f"touch: cannot create file '{filename}': File exists\n", is_error=True)
                continue
            stats = self.device_manager.get_device_stats(self.device)
            file_size = 2 * 1024 * 1024
            if stats["free_storage"] < file_size:
                self.append(f"touch: cannot create file '{filename}': No space left on device\n", is_error=True)
                continue
            node["children"][filename] = {
                "type": "file",
                "size": file_size,
                "content": "",
                "created": datetime.now().isoformat()
            }
            self.save_state()
            self.append(f"Created file: {filename} ({file_size // (1024 * 1024)}MB)\n")

    def write_command(self, args):
        """Write text into a file in the current device filesystem"""
        if len(args) < 2:
            self.append("write: usage: write <filename> <text>\n", is_error=True)
            return
        filename = args[0]
        text = " ".join(args[1:])
        node = self.get_node(self.current_path)
        if not node or node.get("type") != "folder":
            self.append("write: current directory invalid\n", is_error=True)
            return
        child = node.get("children", {}).get(filename)
        old_size = 0
        if child:
            if child.get("type") == "folder":
                self.append(f"write: {filename}: Is a directory\n", is_error=True)
                return
            old_size = child.get("size", 0)
        content_bytes = text.encode("utf-8")
        new_size = len(content_bytes)
        stats = self.device_manager.get_device_stats(self.device)
        if stats["free_storage"] + old_size < new_size:
            self.append(f"write: cannot write to {filename}: No space left on device\n", is_error=True)
            return
        node["children"][filename] = {
            "type": "file",
            "size": new_size,
            "content": text,
            "created": datetime.now().isoformat()
        }
        self.save_state()
        self.append(f"Written to file: {filename}\n")

    def edit_command(self, args):
        """Open a simple edit dialog for a file in the current device filesystem"""
        if len(args) != 1:
            self.append("edit: usage: edit <filename>\n", is_error=True)
            return
        filename = args[0]
        node = self.get_node(self.current_path)
        if not node or node.get("type") != "folder":
            self.append("edit: current directory invalid\n", is_error=True)
            return
        child = node.get("children", {}).get(filename)
        if child and child.get("type") == "folder":
            self.append(f"edit: {filename}: Is a directory\n", is_error=True)
            return
        current_text = child.get("content", "") if child else ""
        new_text = simpledialog.askstring("Edit File", f"Edit contents of {filename}:", initialvalue=current_text)
        if new_text is None:
            self.append("edit: cancelled\n")
            return
        old_size = child.get("size", 0) if child else 0
        new_size = len(new_text.encode("utf-8"))
        stats = self.device_manager.get_device_stats(self.device)
        if stats["free_storage"] + old_size < new_size:
            self.append(f"edit: cannot save {filename}: No space left on device\n", is_error=True)
            return
        node["children"][filename] = {
            "type": "file",
            "size": new_size,
            "content": new_text,
            "created": datetime.now().isoformat()
        }
        self.save_state()
        self.append(f"Edited file: {filename}\n")

    def cat_command(self, args):
        """Display file content - built-in"""
        if not args:
            self.append("cat: missing file operand\n", is_error=True)
            return
        for filename in args:
            target = self.get_node(self.normalize_path(filename))
            if not target:
                self.append(f"cat: {filename}: No such file\n", is_error=True)
                continue
            if target.get("type") == "folder":
                self.append(f"cat: {filename}: Is a directory\n", is_error=True)
                continue
            self.append(target.get("content", "") + "\n")

    def mkdir_command(self, args):
        """Create directory - built-in"""
        if not args:
            self.append("mkdir: missing operand\n", is_error=True)
            return
        node = self.get_node(self.current_path)
        if not node or node.get("type") != "folder":
            self.append("mkdir: current directory invalid\n", is_error=True)
            return
        for dirname in args:
            if dirname in node.get("children", {}):
                self.append(f"mkdir: cannot create directory '{dirname}': File exists\n", is_error=True)
                continue
            stats = self.device_manager.get_device_stats(self.device)
            folder_size = 1 * 1024 * 1024
            if stats["free_storage"] < folder_size:
                self.append(f"mkdir: cannot create directory '{dirname}': No space left on device\n", is_error=True)
                continue
            node["children"][dirname] = {
                "type": "folder",
                "children": {},
                "size": folder_size,
                "created": datetime.now().isoformat()
            }
            self.save_state()
            self.append(f"Directory created: {dirname} ({folder_size // (1024 * 1024)}MB)\n")

    def rm_command(self, args):
        """Remove file or directory - built-in"""
        if not args:
            self.append("rm: missing operand\n", is_error=True)
            return
        recursive = False
        if args[0] == "-r":
            recursive = True
            args = args[1:]
        if not args:
            self.append("rm: missing operand\n", is_error=True)
            return
        for target in args:
            path = self.normalize_path(target)
            if len(path) == 1:
                self.append("rm: cannot remove root directory\n", is_error=True)
                continue
            parent = self.get_node(path[:-1])
            name = path[-1]
            if not parent or parent.get("type") != "folder" or name not in parent.get("children", {}):
                self.append(f"rm: {target}: No such file or directory\n", is_error=True)
                continue
            child = parent["children"][name]
            if child.get("type") == "folder" and not recursive:
                self.append(f"rm: cannot remove '{target}': Is a directory\n", is_error=True)
                continue
            del parent["children"][name]
            self.save_state()
            self.append(f"Removed: {target}\n")
    
    # ========================================================================
    # CUSTOM MINIOS COMMANDS
    # ========================================================================
    
    def execute(self, e=None):
        cmd_line = self.input_entry.get().strip()
        if not cmd_line:
            self.input_entry.delete(0, tk.END)
            self.update_prompt()
            return
        
        self.command_history.append(cmd_line)
        self.history_index = -1
        self.append(f"\n{self.get_prompt()}{cmd_line}\n")
        
        # Parse command
        parts = shlex.split(cmd_line) if cmd_line else []
        cmd = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        
        # Check alias
        if cmd in self.aliases:
            alias_cmd = self.aliases[cmd]
            self.append(f"→ {alias_cmd}\n")
            parts = shlex.split(alias_cmd)
            cmd = parts[0].lower() if parts else ""
            args = parts[1:] if len(parts) > 1 else []
        
        # Check if built-in command
        if cmd in self.builtin_commands:
            self.builtin_commands[cmd](args)
        else:
            # Try to run as system command
            self.run_system_command(cmd_line)
        
        self.input_entry.delete(0, tk.END)
        self.update_prompt()
        self.save_history()
    
    def run_system_command(self, cmd):
        """Run external system command"""
        try:
            if self.os_type == "Windows":
                # Use cmd.exe for Windows
                process = subprocess.Popen(cmd, shell=True, 
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         text=True, cwd=self.current_dir,
                                         executable='cmd.exe')
            else:
                process = subprocess.Popen(cmd, shell=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         text=True, cwd=self.current_dir)
            
            out, err = process.communicate(timeout=30)
            if out:
                self.append(out)
            if err:
                self.append(err, is_error=True)
                
        except subprocess.TimeoutExpired:
            self.append("Command timed out\n", is_error=True)
        except FileNotFoundError:
            self.append(f"Command not found: {cmd.split()[0]}\n", is_error=True)
        except Exception as e:
            self.append(f"Error: {e}\n", is_error=True)
    
    def history_up(self, e):
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, self.command_history[-(self.history_index+1)])
        return "break"
    
    def history_down(self, e):
        if self.history_index > 0:
            self.history_index -= 1
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, self.command_history[-(self.history_index+1)])
        elif self.history_index == 0:
            self.history_index = -1
            self.input_entry.delete(0, tk.END)
        return "break"
    
    def clear_terminal(self, args):
        """Clear terminal screen"""
        self.output_text.delete(1.0, tk.END)
        self.print_banner()
    
    def exit_shell(self, args):
        """Exit shell"""
        self.append("Goodbye! Exiting MiniOS Shell...\n")
        self.go_back()
    
    def show_help(self, args):
        help_text = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                         AVAILABLE COMMANDS                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  📁 FILE SYSTEM COMMANDS:                                                 ║
║    ls [path]     - List directory contents                                ║
║    cd [path]     - Change directory                                       ║
║    pwd           - Print working directory                                ║
║    mkdir [name]  - Create directory                                       ║
║    touch [file]  - Create empty file                                      ║
║    write [file]  - Write text to a file                                   ║
║    edit [file]   - Edit file contents                                     ║
║    rm [file]     - Remove file/directory                                  ║
║    rm -r [dir]   - Remove directory recursively                           ║
║    cat [file]    - Display file contents                                  ║
║    echo [text]   - Print text                                             ║
║                                                                           ║
║  🚀 MINIOS MODULES:                                                       ║
║    scheduler     - Launch CPU Scheduler                                   ║
║    memory        - Launch Memory Manager                                  ║
║    filesystem    - Launch File System                                     ║
║    advanced      - Launch Advanced Features                               ║
║    dashboard     - Return to main dashboard                               ║
║                                                                           ║
║  🔧 UTILITIES:                                                            ║
║    neofetch      - Display system info                                    ║
║    minios        - Show MiniOS information                                ║
║    sysinfo       - Show MiniOS information                                ║
║    storage       - Show MiniOS storage status                             ║
║    meminfo       - Show MiniOS memory status                              ║
║    about         - Show about MiniOS                                      ║
║    clear         - Clear screen                                           ║
║    help          - Show this help                                         ║
║    exit          - Exit shell                                             ║
║                                                                           ║
║  💡 TIPS:                                                                 ║
║    • Use ↑/↓ arrows for command history                                   ║
║    • 'ls' and 'dir' both work                                             ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
        self.append(help_text)
    
    def show_info(self, args):
        info = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                         MINIOS INFORMATION                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Device: {self.device.name}
║  RAM: {self.device.memory_size}MB | Storage: {self.device.storage_size}MB | CPU: {self.device.cpu_cores} Cores
║  OS: {platform.system()} {platform.release()}
║  Python: {platform.python_version()}
║  Current Directory: {self.current_dir}
║  Commands in history: {len(self.command_history)}
╚═══════════════════════════════════════════════════════════════════════════╝
"""
        self.append(info)
    
    def format_bytes(self, size):
        if size >= 1024**3:
            return f"{size / 1024**3:.2f} GB"
        if size >= 1024**2:
            return f"{size / 1024**2:.2f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def show_storage(self, args):
        stats = self.device_manager.get_device_stats(self.device)
        used = stats["used_storage"]
        free = stats["free_storage"]
        total = int(self.device.storage_size * 1024 * 1024)
        self.append("\n╔═══════════════════════════════════════════════════════════════════════════╗\n")
        self.append("║                        MINIOS STORAGE STATUS                             ║\n")
        self.append("╠═══════════════════════════════════════════════════════════════════════════╣\n")
        self.append(f"║  Total Storage: {self.format_bytes(total):<34}              ║\n")
        self.append(f"║  Used Storage:  {self.format_bytes(used):<34}              ║\n")
        self.append(f"║  Free Storage:  {self.format_bytes(free):<34}              ║\n")
        self.append("╚═══════════════════════════════════════════════════════════════════════════╝\n")

    def show_memory_info(self, args):
        stats = self.device_manager.get_device_stats(self.device)
        self.append("\n╔═══════════════════════════════════════════════════════════════════════════╗\n")
        self.append("║                       MINIOS MEMORY STATUS                              ║\n")
        self.append("╠═══════════════════════════════════════════════════════════════════════════╣\n")
        self.append(f"║  Total RAM: {stats['total_memory']} MB{'':<36}║\n")
        self.append(f"║  Used RAM:  {stats['used_memory']} MB{'':<36}║\n")
        self.append(f"║  Free RAM:  {stats['free_memory']} MB{'':<36}║\n")
        self.append(f"║  Processes: {stats['total_processes']}{'':<41}║\n")
        self.append("╚═══════════════════════════════════════════════════════════════════════════╝\n")
    
    def neofetch(self, args):
        logo = """
        ╔══════════════╗
        ║     ███╗     ║
        ║     ████╗    ║
        ║     ██╔██╗   ║
        ║     ██║╚██╗  ║
        ║     ██║ ╚██╗ ║
        ║     ╚═╝  ╚═╝ ║
        ╚══════════════╝
"""
        sys_info = f"""
        {self.username}@{self.hostname}
        ------------------------
        OS: MiniOS Ultimate {platform.system()}
        Shell: MiniOS Terminal v3.0
        Terminal: MiniOS Console
        Python: {platform.python_version()}
        Mode: {'Windows Mode' if self.os_type == 'Windows' else 'Linux Mode'}
"""
        self.append(f"{logo}{sys_info}")
    
    def show_about(self, args):
        about = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                         ABOUT MINIOS SHELL                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  MiniOS Ultimate Shell v3.0                                               ║
║  Ubuntu-style terminal emulator with Windows/Linux support                ║
║                                                                           ║
║  Features:                                                                ║
║  • Built-in commands (cd, ls, pwd, mkdir, rm, cat)                       ║
║  • Command history with ↑/↓ arrows                                        ║
║  • Persistent storage across sessions                                     ║
║  • Launch MiniOS modules from shell                                       ║
║                                                                           ║
║  Version: 6.0 - Ultimate Edition                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
        self.append(about)
    
    def launch_scheduler(self, args):
        self.append("Launching CPU Scheduler...\n")
        self.parent.after(100, lambda: self.back())
        self.parent.after(200, lambda: self.parent.master.open_scheduler())
    
    def launch_memory(self, args):
        self.append("Launching Memory Manager...\n")
        self.parent.after(100, lambda: self.back())
        self.parent.after(200, lambda: self.parent.master.open_memory())
    
    def launch_filesystem(self, args):
        self.append("Launching File System...\n")
        self.parent.after(100, lambda: self.back())
        self.parent.after(200, lambda: self.parent.master.open_filesystem())
    
    def launch_advanced(self, args):
        self.append("Launching Advanced Features...\n")
        self.parent.after(100, lambda: self.back())
        self.parent.after(200, lambda: self.parent.master.open_advanced())
    
    def launch_dashboard(self, args):
        self.append("Returning to dashboard...\n")
        self.go_back()
    
    def go_back(self):
        self.save_history()
        self.main_frame.destroy()
        self.back()