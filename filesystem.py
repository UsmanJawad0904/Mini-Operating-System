"""
File System Module - With Persistent Device Support
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime


class FileSystemUI:
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager, refresh_callback=None):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        self.refresh_callback = refresh_callback
        
        self.colors = {"bg": "#1e1e2e", "card": "#313244", "accent": "#f9e2af", "success": "#a6e3a1",
                       "danger": "#f38ba8", "info": "#89dceb", "text": "#cdd6f4", "text_muted": "#6c7086"}
        
        if hasattr(self.device, 'file_system') and self.device.file_system:
            self.file_system = self.device.file_system
        else:
            self.file_system = self.create_default_fs()
            self.device.file_system = self.file_system
            
        self.current_path = ["root"]
        self.setup_ui()
        
    def create_default_fs(self):
        return {
            "root": {
                "type": "folder",
                "size": 4096,
                "children": {},
                "created": datetime.now().isoformat()
            }
        }
        
    def save_state(self):
        self.device.file_system = self.file_system
        self.device_manager.update_device_state(self.device, {"file_system": self.file_system})
        if callable(self.refresh_callback):
            self.refresh_callback()
        
    def get_current_node(self):
        node = self.file_system
        for p in self.current_path:
            node = node[p] if p == "root" else node["children"].get(p, {})
            if not node:
                return None
        return node
        
    def get_human_size(self, size):
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def refresh_content(self):
        self.content_listbox.delete(0, tk.END)
        node = self.get_current_node()
        if node and node.get("type") == "folder":
            for name, data in sorted(node.get("children", {}).items()):
                icon = "📁" if data["type"] == "folder" else "📄"
                size = ""
                if "size" in data:
                    size = f" ({self.get_human_size(data['size'])})"
                self.content_listbox.insert(tk.END, f"{icon} {name}{size}")
                
    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        def add(parent, node):
            for name, data in node.get("children", {}).items():
                if data.get("type") == "folder":
                    item = self.tree.insert(parent, "end", text=f"📁 {name}")
                    add(item, data)
        add("", self.file_system["root"])
        
    def update_path(self):
        path = "/" + "/".join(self.current_path[1:])
        self.path_label.config(text=f"📍 {path}")
        
    def setup_ui(self):
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10))
        tk.Label(header, text="📁 File System", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack()
        tk.Label(header, text=f"Device: {self.device.name} | Storage: {self.device.storage_size}MB", 
                font=("Segoe UI", 12), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack()
        self.path_label = tk.Label(header, text="📍 /root", font=("Segoe UI", 11),
                                   bg=self.colors["bg"], fg=self.colors["accent"])
        self.path_label.pack(pady=5)
        
        content = tk.Frame(self.main_frame, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        left = tk.Frame(content, bg=self.colors["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0,10))
        
        tree_card = tk.Frame(left, bg=self.colors["card"])
        tree_card.pack(fill="both", expand=True)
        tk.Label(tree_card, text="📂 Directory Tree", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        tree_frame = tk.Frame(tree_card, bg=self.colors["card"])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree = ttk.Treeview(tree_frame)
        scroll = tk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        right = tk.Frame(content, bg=self.colors["bg"])
        right.pack(side="right", fill="both", expand=True, padx=(10,0))
        
        actions = tk.Frame(right, bg=self.colors["card"])
        actions.pack(fill="x", pady=10)
        tk.Label(actions, text="⚡ Quick Actions", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        input_frame = tk.Frame(actions, bg=self.colors["card"])
        input_frame.pack(pady=10)
        self.name_entry = tk.Entry(input_frame, bg="#0f172a", fg=self.colors["text"], width=25, font=("Segoe UI", 11))
        self.name_entry.pack(side="left", padx=5)
        self.name_entry.bind("<Return>", lambda e: self.create_item())
        tk.Button(input_frame, text="📁 New Folder", command=lambda: self.create_item("folder"),
                 bg=self.colors["success"], fg="white", cursor="hand2").pack(side="left", padx=2)
        tk.Button(input_frame, text="📄 New File", command=lambda: self.create_item("file"),
                 bg=self.colors["info"], fg="white", cursor="hand2").pack(side="left", padx=2)
        
        ops = tk.Frame(actions, bg=self.colors["card"])
        ops.pack(pady=10)
        for text, cmd, color in [("✏ Rename", self.rename_item, self.colors["accent"]),
                                  ("🗑 Delete", self.delete_item, self.colors["danger"]),
                                  ("🔍 Search", self.search_items, self.colors["info"])]:
            tk.Button(ops, text=text, command=cmd, bg=color, fg="white", width=10, cursor="hand2").pack(side="left", padx=5)
        
        content_card = tk.Frame(right, bg=self.colors["card"])
        content_card.pack(fill="both", expand=True, pady=10)
        tk.Label(content_card, text="📋 Directory Contents", font=("Segoe UI", 14, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(pady=10)
        
        list_frame = tk.Frame(content_card, bg=self.colors["card"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.content_listbox = tk.Listbox(list_frame, bg="#0f172a", fg=self.colors["text"], font=("Consolas", 11), height=12)
        scroll = tk.Scrollbar(list_frame, orient="vertical", command=self.content_listbox.yview)
        self.content_listbox.configure(yscrollcommand=scroll.set)
        self.content_listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.content_listbox.bind("<Double-Button-1>", self.on_double_click)
        
        nav = tk.Frame(right, bg=self.colors["bg"])
        nav.pack(fill="x", pady=5)
        tk.Button(nav, text="⬆ Up", command=self.go_up, bg=self.colors["text_muted"], fg="white", width=10, cursor="hand2").pack(side="left", padx=5)
        tk.Button(nav, text="🏠 Home", command=self.go_home, bg=self.colors["text_muted"], fg="white", width=10, cursor="hand2").pack(side="left", padx=5)
        
        btn_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="💾 Save State", command=self.save_state,
                 bg=self.colors["success"], fg="white", cursor="hand2", padx=20).pack(side="left", padx=5)
        tk.Button(btn_frame, text="← Back to Dashboard", command=self.go_back,
                 bg=self.colors["text_muted"], fg="white", cursor="hand2", padx=20).pack(side="left", padx=5)
        
        self.refresh_tree()
        self.refresh_content()
        self.update_path()
        
    def on_tree_select(self, e):
        sel = self.tree.selection()
        if sel:
            name = self.tree.item(sel[0])["text"][2:]
            node = self.get_current_node()
            if node and name in node.get("children", {}) and node["children"][name]["type"] == "folder":
                self.current_path.append(name)
                self.update_path()
                self.refresh_content()
                self.refresh_tree()
                
    def on_double_click(self, e):
        sel = self.content_listbox.curselection()
        if sel:
            text = self.content_listbox.get(sel[0])
            name = text.split()[1] if " " in text else text[2:]
            name = name.split("(")[0]
            node = self.get_current_node()
            if node and name in node.get("children", {}):
                if node["children"][name]["type"] == "folder":
                    self.current_path.append(name)
                    self.update_path()
                    self.refresh_content()
                    self.refresh_tree()
                else:
                    content = node["children"][name].get("content", "No content")
                    messagebox.showinfo(f"File: {name}", content)
                    
    def go_up(self):
        if len(self.current_path) > 1:
            self.current_path.pop()
            self.update_path()
            self.refresh_content()
            self.refresh_tree()
            
    def go_home(self):
        self.current_path = ["root"]
        self.update_path()
        self.refresh_content()
        self.refresh_tree()
        
    def create_item(self, item_type="folder"):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Enter a name!")
            return
        node = self.get_current_node()
        if not node:
            messagebox.showerror("Error", "Invalid location!")
            return
        if name in node.get("children", {}):
            messagebox.showerror("Error", "Already exists!")
            return
        if item_type == "folder":
            node["children"][name] = {"type": "folder", "children": {}, "created": datetime.now().isoformat(), "size": 1024 * 1024}
        else:
            node["children"][name] = {"type": "file", "size": 2 * 1024 * 1024, "content": f"New file {name}", "created": datetime.now().isoformat()}
        self.name_entry.delete(0, tk.END)
        self.refresh_content()
        self.refresh_tree()
        self.save_state()
        
    def rename_item(self):
        sel = self.content_listbox.curselection()
        if not sel:
            messagebox.showerror("Error", "Select an item!")
            return
        old = self.content_listbox.get(sel[0]).split()[1] if " " in self.content_listbox.get(sel[0]) else self.content_listbox.get(sel[0])[2:]
        old = old.split("(")[0]
        new = simpledialog.askstring("Rename", f"Rename '{old}' to:")
        if new:
            node = self.get_current_node()
            if node and old in node.get("children", {}):
                node["children"][new] = node["children"].pop(old)
                self.refresh_content()
                self.refresh_tree()
                self.save_state()
                
    def delete_item(self):
        sel = self.content_listbox.curselection()
        if not sel:
            messagebox.showerror("Error", "Select an item!")
            return
        name = self.content_listbox.get(sel[0]).split()[1] if " " in self.content_listbox.get(sel[0]) else self.content_listbox.get(sel[0])[2:]
        name = name.split("(")[0]
        if messagebox.askyesno("Confirm", f"Delete '{name}'?"):
            node = self.get_current_node()
            if node and name in node.get("children", {}):
                del node["children"][name]
                self.refresh_content()
                self.refresh_tree()
                self.save_state()
                
    def search_items(self):
        query = simpledialog.askstring("Search", "Enter search term:")
        if query:
            results = []
            def search(node, path):
                for name, data in node.get("children", {}).items():
                    if query.lower() in name.lower():
                        results.append("/".join(path + [name]))
                    if data.get("type") == "folder":
                        search(data, path + [name])
            search(self.file_system["root"], ["root"])
            if results:
                win = tk.Toplevel()
                win.title("Search Results")
                win.geometry("500x400")
                win.configure(bg=self.colors["bg"])
                tk.Label(win, text=f"Found {len(results)} items:", font=("Segoe UI", 12, "bold"),
                        bg=self.colors["bg"], fg=self.colors["text"]).pack(pady=10)
                lb = tk.Listbox(win, bg="#0f172a", fg=self.colors["text"], font=("Consolas", 10))
                lb.pack(fill="both", expand=True, padx=10, pady=10)
                for r in results:
                    lb.insert(tk.END, r)
                tk.Button(win, text="Close", command=win.destroy, bg=self.colors["accent"], fg="white").pack(pady=10)
            else:
                messagebox.showinfo("Search", "No items found!")
                
    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()