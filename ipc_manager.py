"""
Inter-Process Communication (IPC) Module
Implements pipes, message queues, and shared memory
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from collections import deque
from datetime import datetime
import threading


class Pipe:
    """Represents a pipe for inter-process communication"""
    
    def __init__(self, name, owner_pid):
        self.name = name
        self.owner_pid = owner_pid
        self.read_end = None
        self.write_end = None
        self.buffer = deque(maxlen=100)  # Max 100 messages
        self.created_at = datetime.now()
        self.messages_sent = 0
        self.messages_received = 0
        
    def write(self, data, sender=None):
        """Write data to pipe"""
        self.buffer.append({
            "data": data,
            "timestamp": datetime.now(),
            "sender": sender or self.write_end
        })
        self.messages_sent += 1
        return True
    
    def read(self):
        """Read data from pipe"""
        if self.buffer:
            msg = self.buffer.popleft()
            self.messages_received += 1
            return msg
        return None
    
    def peek(self, count=10):
        """Peek current messages in buffer"""
        return list(self.buffer)[:count]
    
    def is_empty(self):
        """Check if pipe is empty"""
        return len(self.buffer) == 0
    
    def get_statistics(self):
        """Get pipe statistics"""
        return {
            "name": self.name,
            "owner": self.owner_pid,
            "messages_in_buffer": len(self.buffer),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "created_at": self.created_at.isoformat()
        }


class MessageQueue:
    """Represents a message queue"""
    
    def __init__(self, name, creator_pid):
        self.name = name
        self.creator_pid = creator_pid
        self.messages = deque()
        self.created_at = datetime.now()
        self.subscribers = []
        
    def enqueue(self, message, priority=0, sender=None):
        """Add message to queue"""
        self.messages.append({
            "content": message,
            "priority": priority,
            "timestamp": datetime.now(),
            "sender": sender
        })
        self._sort_by_priority()
        return True
    
    def dequeue(self):
        """Get highest-priority message from queue"""
        if self.messages:
            best_index = min(range(len(self.messages)), key=lambda i: (-self.messages[i]["priority"], self.messages[i]["timestamp"]))
            return self.messages.pop(best_index)
        return None
    
    def peek(self, count=10):
        """Peek current queue messages"""
        return list(self.messages)[:count]
    
    def _sort_by_priority(self):
        self.messages = deque(sorted(self.messages, key=lambda x: (-x["priority"], x["timestamp"])))
    
    def subscribe(self, pid):
        """Subscribe to queue"""
        if pid not in self.subscribers:
            self.subscribers.append(pid)
            return True
        return False
    
    def get_size(self):
        """Get queue size"""
        return len(self.messages)


class SharedMemory:
    """Simulates shared memory for IPC"""
    
    def __init__(self, name, creator_pid, size=4096):
        self.name = name
        self.creator_pid = creator_pid
        self.size = size
        self.data = {}
        self.access_list = [creator_pid]
        self.created_at = datetime.now()
        
    def write(self, offset, data):
        """Write data to shared memory"""
        self.data[offset] = data
        return True
    
    def read(self, offset):
        """Read data from shared memory"""
        return self.data.get(offset, None)
    
    def grant_access(self, pid):
        """Grant access to another process"""
        if pid not in self.access_list:
            self.access_list.append(pid)
            return True
        return False
    
    def get_statistics(self):
        """Get shared memory statistics"""
        return {
            "name": self.name,
            "creator": self.creator_pid,
            "size": self.size,
            "used_bytes": len(self.data) * 8,  # Approximate
            "access_count": len(self.access_list)
        }


class IPCManager:
    """Manages all IPC mechanisms"""
    
    def __init__(self):
        self.pipes = {}
        self.message_queues = {}
        self.shared_memory = {}
        
    def create_pipe(self, name, owner_pid):
        """Create a new pipe"""
        if name not in self.pipes:
            pipe = Pipe(name, owner_pid)
            self.pipes[name] = pipe
            return pipe
        return None
    
    def create_message_queue(self, name, creator_pid):
        """Create a message queue"""
        if name not in self.message_queues:
            mq = MessageQueue(name, creator_pid)
            self.message_queues[name] = mq
            return mq
        return None
    
    def create_shared_memory(self, name, creator_pid, size=4096):
        """Create shared memory"""
        if name not in self.shared_memory:
            shm = SharedMemory(name, creator_pid, size)
            self.shared_memory[name] = shm
            return shm
        return None
    
    def delete_message_queue(self, name):
        if name in self.message_queues:
            del self.message_queues[name]
            return True
        return False
    
    def delete_shared_memory(self, name):
        if name in self.shared_memory:
            del self.shared_memory[name]
            return True
        return False
    
    def get_pipe(self, name):
        """Get pipe by name"""
        return self.pipes.get(name)
    
    def delete_pipe(self, name):
        """Delete a pipe"""
        if name in self.pipes:
            del self.pipes[name]
            return True
        return False
    
    def get_all_pipes(self):
        """Get all pipes"""
        return list(self.pipes.values())
    
    def get_all_message_queues(self):
        """Get all message queues"""
        return list(self.message_queues.values())
    
    def get_all_shared_memory(self):
        """Get all shared memory"""
        return list(self.shared_memory.values())


class IPCManagerUI:
    """UI for IPC Management"""
    
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        
        self.colors = {
            "bg": "#1e1e2e",
            "card": "#313244",
            "accent": "#b4befe",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "danger": "#f38ba8",
            "text": "#cdd6f4",
            "text_muted": "#6c7086"
        }
        
        self.ipc = IPCManager()
        self.selected_pipe = None
        self.selected_queue = None
        self.selected_shm = None
        self.pipe_owner_var = tk.StringVar()
        self.pipe_sender_var = tk.StringVar()
        self.mq_sender_var = tk.StringVar()
        self.mq_subscriber_var = tk.StringVar()
        self.shm_access_var = tk.StringVar()
        self.process_options = [p.get('name') for p in getattr(self.device, 'processes', []) if isinstance(p, dict)]
        self.load_saved_state()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI"""
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10), padx=20)
        
        tk.Label(header, text="🔗 Inter-Process Communication (IPC)", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        tk.Label(header, text=f"Device: {self.device.name}",
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w")
        
        content = tk.Frame(self.main_frame, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Notebook for tabs
        notebook = ttk.Notebook(content)
        notebook.pack(fill="both", expand=True)
        
        # Pipes tab
        pipes_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(pipes_frame, text="Pipes")
        self._setup_pipes_tab(pipes_frame)
        
        # Message Queues tab
        mq_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(mq_frame, text="Message Queues")
        self._setup_mq_tab(mq_frame)
        
        # Shared Memory tab
        shm_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(shm_frame, text="Shared Memory")
        self._setup_shm_tab(shm_frame)
        
        # Back button
        button_frame = tk.Frame(content, bg=self.colors["bg"])
        button_frame.pack(fill="x", pady=10)
        tk.Button(button_frame, text="Back", command=self.go_back,
                 bg=self.colors["text_muted"], fg="#000000").pack(side="right", padx=5)
        
    def _setup_pipes_tab(self, parent):
        """Setup pipes management tab"""
        create_frame = tk.LabelFrame(parent, text="Create Pipe", bg=self.colors["card"],
                                    fg=self.colors["text"])
        create_frame.pack(fill="x", padx=10, pady=10)
        
        input_frame = tk.Frame(create_frame, bg=self.colors["card"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(input_frame, text="Pipe Name:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.pipe_name_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.pipe_name_entry.pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Pipe Owner:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        owner_values = self.process_options or ["proc_001"]
        self.pipe_owner_cb = ttk.Combobox(input_frame, values=owner_values,
                                          textvariable=self.pipe_owner_var, state="readonly")
        self.pipe_owner_cb.pack(fill="x", pady=(0, 10))
        if owner_values:
            self.pipe_owner_cb.current(0)
        
        tk.Button(input_frame, text="Create Pipe", command=self.create_pipe,
                 bg=self.colors["accent"], fg="#000000").pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Send Message:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w", pady=(10, 0))
        self.pipe_msg_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.pipe_msg_entry.pack(fill="x", pady=(0, 10))

        tk.Label(input_frame, text="Sender Process:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        sender_values = self.process_options or ["proc_001"]
        self.pipe_sender_cb = ttk.Combobox(input_frame, values=sender_values,
                                           textvariable=self.pipe_sender_var, state="readonly")
        self.pipe_sender_cb.pack(fill="x", pady=(0, 10))
        if sender_values:
            self.pipe_sender_cb.current(0)
        
        tk.Button(input_frame, text="Send Message", command=self.send_pipe_message,
                 bg=self.colors["success"], fg="#000000").pack(fill="x", pady=(0, 10))

        action_frame = tk.Frame(create_frame, bg=self.colors["card"])
        action_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Button(action_frame, text="Read Message", command=self.read_pipe_message,
                 bg=self.colors["warning"], fg="#000000").pack(side="left", expand=True, fill="x", padx=(0, 5))
        tk.Button(action_frame, text="Delete Pipe", command=self.delete_pipe,
                 bg=self.colors["danger"], fg="#ffffff").pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        self.pipe_log = scrolledtext.ScrolledText(create_frame, height=6, bg="#0f172a", fg=self.colors["text"], wrap="word")
        self.pipe_log.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self.pipe_log.insert(tk.END, "IPC pipe activity log...\n")
        self.pipe_log.configure(state="disabled")
        
        list_frame = tk.LabelFrame(parent, text="Active Pipes", bg=self.colors["card"],
                                  fg=self.colors["text"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Pipe Name", "Owner", "Buffer Size", "Sent", "Received")
        self.pipes_tree = ttk.Treeview(list_frame, columns=columns, height=10)
        self.pipes_tree.bind("<<TreeviewSelect>>", self.on_pipe_select)
        
        for col in columns:
            self.pipes_tree.heading(col, text=col)
            self.pipes_tree.column(col, width=120)
        
        self.pipes_tree.pack(fill="both", expand=True)
        self.refresh_pipes_list()
        
    def _setup_mq_tab(self, parent):
        """Setup message queues tab"""
        create_frame = tk.LabelFrame(parent, text="Create Message Queue", bg=self.colors["card"],
                                    fg=self.colors["text"])
        create_frame.pack(fill="x", padx=10, pady=10)
        
        input_frame = tk.Frame(create_frame, bg=self.colors["card"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(input_frame, text="Queue Name:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.mq_name_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.mq_name_entry.pack(fill="x", pady=(0, 10))
        
        tk.Button(input_frame, text="Create Queue", command=self.create_mq,
                 bg=self.colors["accent"], fg="#000000").pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Publish Message:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w", pady=(10, 0))
        self.mq_message_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.mq_message_entry.pack(fill="x", pady=(0, 10))
        
        self.mq_priority_entry = tk.Spinbox(input_frame, from_=-5, to=10, width=5,
                                            bg=self.colors["bg"], fg=self.colors["text"])
        tk.Label(input_frame, text="Priority:", bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w")
        self.mq_priority_entry.pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Sender Process:", bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w")
        sender_values = self.process_options or ["proc_001"]
        self.mq_sender_cb = ttk.Combobox(input_frame, values=sender_values,
                                         textvariable=self.mq_sender_var, state="readonly")
        self.mq_sender_cb.pack(fill="x", pady=(0, 10))
        if sender_values:
            self.mq_sender_cb.current(0)
        
        tk.Button(input_frame, text="Publish Message", command=self.publish_mq_message,
                 bg=self.colors["success"], fg="#000000").pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Subscriber Process:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        subscriber_values = self.process_options or ["proc_001"]
        self.mq_subscriber_cb = ttk.Combobox(input_frame, values=subscriber_values,
                                             textvariable=self.mq_subscriber_var, state="readonly")
        self.mq_subscriber_cb.pack(fill="x", pady=(0, 10))
        if subscriber_values:
            self.mq_subscriber_cb.current(0)
        
        tk.Button(input_frame, text="Subscribe", command=self.subscribe_mq,
                 bg=self.colors["warning"], fg="#000000").pack(fill="x", pady=(0, 10))
        
        tk.Button(input_frame, text="Dequeue Message", command=self.dequeue_mq,
                 bg=self.colors["danger"], fg="#ffffff").pack(fill="x", pady=(0, 10))
        
        list_frame = tk.LabelFrame(parent, text="Message Queues", bg=self.colors["card"],
                                  fg=self.colors["text"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Queue Name", "Creator", "Size", "Subscribers")
        self.mq_tree = ttk.Treeview(list_frame, columns=columns, height=10)
        self.mq_tree.bind("<<TreeviewSelect>>", self.on_mq_select)
        
        for col in columns:
            self.mq_tree.heading(col, text=col)
            self.mq_tree.column(col, width=150)
        
        self.mq_tree.pack(fill="both", expand=True)
        self.mq_message_log = scrolledtext.ScrolledText(list_frame, height=6, bg="#0f172a", fg=self.colors["text"], wrap="word")
        self.mq_message_log.pack(fill="both", expand=True, pady=(10, 0), padx=5)
        self.mq_message_log.insert(tk.END, "Queue contents will appear here after selection.\n")
        self.mq_message_log.configure(state="disabled")
        self.refresh_mq_list()
        
    def _setup_shm_tab(self, parent):
        """Setup shared memory tab"""
        create_frame = tk.LabelFrame(parent, text="Create Shared Memory", bg=self.colors["card"],
                                    fg=self.colors["text"])
        create_frame.pack(fill="x", padx=10, pady=10)
        
        input_frame = tk.Frame(create_frame, bg=self.colors["card"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(input_frame, text="Memory Name:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.shm_name_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.shm_name_entry.pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Size (bytes):", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.shm_size_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.shm_size_entry.insert(0, "4096")
        self.shm_size_entry.pack(fill="x", pady=(0, 10))
        
        tk.Button(input_frame, text="Create Memory", command=self.create_shm,
                 bg=self.colors["accent"], fg="#000000").pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Offset / Key:", bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w")
        self.shm_offset_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.shm_offset_entry.pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Value:", bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w")
        self.shm_value_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.shm_value_entry.pack(fill="x", pady=(0, 10))
        
        tk.Button(input_frame, text="Write to Shared Memory", command=self.write_shm,
                 bg=self.colors["success"], fg="#000000").pack(fill="x", pady=(0, 10))
        tk.Button(input_frame, text="Read from Shared Memory", command=self.read_shm,
                 bg=self.colors["warning"], fg="#000000").pack(fill="x", pady=(0, 10))
        
        tk.Label(input_frame, text="Grant Access to Process:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w", pady=(10, 0))
        access_values = self.process_options or ["proc_001"]
        self.shm_access_cb = ttk.Combobox(input_frame, values=access_values,
                                          textvariable=self.shm_access_var, state="readonly")
        self.shm_access_cb.pack(fill="x", pady=(0, 10))
        if access_values:
            self.shm_access_cb.current(0)
        tk.Button(input_frame, text="Grant Access", command=self.grant_shm_access,
                 bg=self.colors["accent"], fg="#000000").pack(fill="x", pady=(0, 10))

        list_frame = tk.LabelFrame(parent, text="Shared Memory Segments", bg=self.colors["card"],
                                  fg=self.colors["text"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Memory Name", "Creator", "Size", "Used")
        self.shm_tree = ttk.Treeview(list_frame, columns=columns, height=10)
        self.shm_tree.bind("<<TreeviewSelect>>", self.on_shm_select)
        
        for col in columns:
            self.shm_tree.heading(col, text=col)
            self.shm_tree.column(col, width=150)
        
        self.shm_tree.pack(fill="both", expand=True)
        self.shm_data_log = scrolledtext.ScrolledText(list_frame, height=6, bg="#0f172a", fg=self.colors["text"], wrap="word")
        self.shm_data_log.pack(fill="both", expand=True, pady=(10, 0), padx=5)
        self.shm_data_log.insert(tk.END, "Shared memory contents will appear here after selection.\n")
        self.shm_data_log.configure(state="disabled")
        self.refresh_shm_list()
        
    def create_pipe(self):
        """Create a new pipe"""
        name = self.pipe_name_entry.get().strip()
        owner = self.pipe_owner_var.get() or "proc_001"
        if not name:
            messagebox.showerror("Error", "Pipe name is required")
            return
        
        pipe = self.ipc.create_pipe(name, owner)
        if pipe:
            self.log(f"Pipe created: {name} (owner: {owner})")
            self.pipe_name_entry.delete(0, tk.END)
            self.refresh_pipes_list()
            self.save_state()
        else:
            messagebox.showerror("Error", "Pipe already exists")
            
    def send_pipe_message(self):
        """Send message through selected pipe"""
        pipe = self.get_selected_pipe()
        if not pipe:
            messagebox.showerror("Error", "Select a pipe first")
            return
        
        msg = self.pipe_msg_entry.get().strip()
        sender = self.pipe_sender_var.get() or self.pipe_owner_var.get() or pipe.owner_pid
        if not msg:
            messagebox.showerror("Error", "Message is required")
            return
        
        pipe.write(msg, sender=sender)
        self.log(f"Message sent through {pipe.name}: {msg}")
        self.log_pipe(f"Sent => {msg} (sender: {sender})")
        self.pipe_msg_entry.delete(0, tk.END)
        self.refresh_pipes_list()
        self.save_state()
        self.update_pipe_log()
        
    def read_pipe_message(self):
        """Read message from selected pipe"""
        pipe = self.get_selected_pipe()
        if not pipe:
            messagebox.showerror("Error", "Select a pipe first")
            return
        
        msg = pipe.read()
        if not msg:
            messagebox.showinfo("Empty", "No message in this pipe")
            return
        self.log(f"Message received from {pipe.name}: {msg['data']}")
        self.log_pipe(f"Read <= {msg['data']} (sender: {msg['sender']})")
        self.refresh_pipes_list()
        self.save_state()
        self.update_pipe_log()
        
    def delete_pipe(self):
        """Delete the selected pipe"""
        pipe = self.get_selected_pipe()
        if not pipe:
            messagebox.showerror("Error", "Select a pipe first")
            return
        self.ipc.delete_pipe(pipe.name)
        self.selected_pipe = None
        self.log(f"Deleted pipe: {pipe.name}")
        self.refresh_pipes_list()
        self.save_state()
        self.update_pipe_log()
        
    def get_selected_pipe(self):
        selection = self.pipes_tree.selection()
        if not selection:
            return None
        row_values = self.pipes_tree.item(selection[0])['values']
        if not row_values:
            return None
        name = row_values[0]
        return self.ipc.get_pipe(name)
    
    def on_pipe_select(self, event=None):
        self.selected_pipe = self.get_selected_pipe()
        self.update_pipe_log()
    
    def log_pipe(self, message):
        self.pipe_log.configure(state="normal")
        self.pipe_log.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.pipe_log.configure(state="disabled")
        self.pipe_log.see(tk.END)
    
    def update_pipe_log(self):
        self.pipe_log.configure(state="normal")
        self.pipe_log.delete(1.0, tk.END)
        if self.selected_pipe:
            self.pipe_log.insert(tk.END, f"Selected pipe: {self.selected_pipe.name}\nOwner: {self.selected_pipe.owner_pid}\n\n")
            for msg in self.selected_pipe.peek(20):
                self.pipe_log.insert(tk.END, f"{msg['timestamp'].strftime('%H:%M:%S')} | {msg['sender']} => {msg['data']}\n")
        else:
            self.pipe_log.insert(tk.END, "IPC pipe activity log...\n")
        self.pipe_log.configure(state="disabled")
    
    def create_mq(self):
        """Create message queue"""
        name = self.mq_name_entry.get().strip()
        creator = self.mq_sender_var.get() or (self.process_options[0] if self.process_options else "proc_001")
        if not name:
            messagebox.showerror("Error", "Queue name is required")
            return
        
        mq = self.ipc.create_message_queue(name, creator)
        if mq:
            self.log(f"Message queue created: {name} (creator: {creator})")
            self.mq_name_entry.delete(0, tk.END)
            self.refresh_mq_list()
            self.save_state()
        else:
            messagebox.showerror("Error", "Queue already exists")
            
    def publish_mq_message(self):
        """Publish a message to the selected queue"""
        mq = self.get_selected_queue()
        if not mq:
            messagebox.showerror("Error", "Select a queue first")
            return
        content = self.mq_message_entry.get().strip()
        if not content:
            messagebox.showerror("Error", "Message content is required")
            return
        try:
            priority = int(self.mq_priority_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Priority must be a number")
            return
        sender = self.mq_sender_var.get() or "proc_001"
        mq.enqueue(content, priority=priority, sender=sender)
        self.log(f"Published to queue {mq.name}: {content} (priority: {priority})")
        self.mq_message_entry.delete(0, tk.END)
        self.refresh_mq_list()
        self.save_state()
        self.update_mq_message_log()
        
    def subscribe_mq(self):
        """Add a subscriber to the selected message queue"""
        mq = self.get_selected_queue()
        if not mq:
            messagebox.showerror("Error", "Select a queue first")
            return
        subscriber = self.mq_subscriber_var.get() or "proc_001"
        if mq.subscribe(subscriber):
            self.log(f"Subscriber {subscriber} added to queue {mq.name}")
            self.refresh_mq_list()
            self.save_state()
        else:
            messagebox.showinfo("Info", "Subscriber already registered")
        self.update_mq_message_log()
        
    def dequeue_mq(self):
        """Dequeue a message from the selected queue"""
        mq = self.get_selected_queue()
        if not mq:
            messagebox.showerror("Error", "Select a queue first")
            return
        msg = mq.dequeue()
        if not msg:
            messagebox.showinfo("Empty", "No messages in this queue")
            return
        self.log(f"Dequeued from {mq.name}: {msg['content']} (sender: {msg['sender']})")
        self.refresh_mq_list()
        self.save_state()
        self.update_mq_message_log()
        
    def get_selected_queue(self):
        selection = self.mq_tree.selection()
        if not selection:
            return None
        values = self.mq_tree.item(selection[0])['values']
        if not values:
            return None
        return self.ipc.message_queues.get(values[0])
    
    def on_mq_select(self, event=None):
        self.selected_queue = self.get_selected_queue()
        self.update_mq_message_log()
    
    def update_mq_message_log(self):
        self.mq_message_log.configure(state="normal")
        self.mq_message_log.delete(1.0, tk.END)
        if self.selected_queue:
            self.mq_message_log.insert(tk.END, f"Queue: {self.selected_queue.name}\nCreator: {self.selected_queue.creator_pid}\nSubscribers: {', '.join(self.selected_queue.subscribers) or '-'}\n\n")
            for idx, msg in enumerate(self.selected_queue.peek(50), 1):
                self.mq_message_log.insert(tk.END, f"{idx}. [{msg['priority']}] {msg['sender'] or 'unknown'} => {msg['content']}\n")
        else:
            self.mq_message_log.insert(tk.END, "Queue contents will appear here after selection.\n")
        self.mq_message_log.configure(state="disabled")
        self.mq_message_log.see(tk.END)
    
    def create_shm(self):
        """Create shared memory"""
        name = self.shm_name_entry.get().strip()
        size_str = self.shm_size_entry.get().strip()
        creator = self.process_options[0] if self.process_options else "proc_001"
        
        if not name or not size_str:
            messagebox.showerror("Error", "All fields required")
            return
        
        try:
            size = int(size_str)
            shm = self.ipc.create_shared_memory(name, creator, size)
            if shm:
                self.log(f"Shared memory created: {name} ({size} bytes)")
                self.shm_name_entry.delete(0, tk.END)
                self.refresh_shm_list()
                self.save_state()
            else:
                messagebox.showerror("Error", "Memory segment already exists")
        except ValueError:
            messagebox.showerror("Error", "Invalid size")
            
    def write_shm(self):
        shm = self.get_selected_shm()
        if not shm:
            messagebox.showerror("Error", "Select a shared memory segment first")
            return
        offset = self.shm_offset_entry.get().strip()
        data = self.shm_value_entry.get().strip()
        if not offset:
            messagebox.showerror("Error", "Offset/key is required")
            return
        shm.write(offset, data)
        self.log(f"Wrote to shared memory {shm.name}: {offset} => {data}")
        self.save_state()
        self.refresh_shm_list()
        self.update_shm_data_log()
        
    def read_shm(self):
        shm = self.get_selected_shm()
        if not shm:
            messagebox.showerror("Error", "Select a shared memory segment first")
            return
        offset = self.shm_offset_entry.get().strip()
        if not offset:
            messagebox.showerror("Error", "Offset/key is required")
            return
        value = shm.read(offset)
        if value is None:
            messagebox.showinfo("Empty", "No value found at this offset")
            return
        self.log(f"Read from shared memory {shm.name}: {offset} => {value}")
        self.shm_data_log.configure(state="normal")
        self.shm_data_log.insert(tk.END, f"Read {offset} => {value}\n")
        self.shm_data_log.configure(state="disabled")
        self.shm_data_log.see(tk.END)
        
    def grant_shm_access(self):
        shm = self.get_selected_shm()
        if not shm:
            messagebox.showerror("Error", "Select a shared memory segment first")
            return
        pid = self.shm_access_var.get() or "proc_001"
        if shm.grant_access(pid):
            self.log(f"Granted access to {pid} for {shm.name}")
            self.save_state()
            self.update_shm_data_log()
        else:
            messagebox.showinfo("Info", "Process already has access")
        
    def get_selected_shm(self):
        selection = self.shm_tree.selection()
        if not selection:
            return None
        values = self.shm_tree.item(selection[0])['values']
        if not values:
            return None
        return self.ipc.shared_memory.get(values[0])
    
    def on_shm_select(self, event=None):
        self.selected_shm = self.get_selected_shm()
        self.update_shm_data_log()
    
    def update_shm_data_log(self):
        self.shm_data_log.configure(state="normal")
        self.shm_data_log.delete(1.0, tk.END)
        if self.selected_shm:
            self.shm_data_log.insert(tk.END, f"Segment: {self.selected_shm.name}\nCreator: {self.selected_shm.creator_pid}\nSize: {self.selected_shm.size} B\nAccess: {', '.join(self.selected_shm.access_list)}\n\n")
            if self.selected_shm.data:
                for key, value in self.selected_shm.data.items():
                    self.shm_data_log.insert(tk.END, f"{key} => {value}\n")
            else:
                self.shm_data_log.insert(tk.END, "No stored values yet.\n")
        else:
            self.shm_data_log.insert(tk.END, "Shared memory contents will appear here after selection.\n")
        self.shm_data_log.configure(state="disabled")
        self.shm_data_log.see(tk.END)
        
    def refresh_pipes_list(self):
        """Refresh pipes list display"""
        for item in self.pipes_tree.get_children():
            self.pipes_tree.delete(item)
        
        for pipe in self.ipc.get_all_pipes():
            stats = pipe.get_statistics()
            self.pipes_tree.insert("", "end", text="",
                                 values=(stats["name"], stats["owner"],
                                        stats["messages_in_buffer"],
                                        stats["messages_sent"],
                                        stats["messages_received"]))
        self.update_pipe_log()
            
    def refresh_mq_list(self):
        """Refresh message queues list"""
        for item in self.mq_tree.get_children():
            self.mq_tree.delete(item)
        
        for mq in self.ipc.get_all_message_queues():
            self.mq_tree.insert("", "end", text="",
                              values=(mq.name, mq.creator_pid, mq.get_size(),
                                     len(mq.subscribers)))
        self.update_mq_message_log()
            
    def refresh_shm_list(self):
        """Refresh shared memory list"""
        for item in self.shm_tree.get_children():
            self.shm_tree.delete(item)
        
        for shm in self.ipc.get_all_shared_memory():
            stats = shm.get_statistics()
            self.shm_tree.insert("", "end", text="",
                               values=(stats["name"], stats["creator"],
                                      f"{stats['size']} B",
                                      f"{stats['used_bytes']} B"))
        self.update_shm_data_log()

    def load_saved_state(self):
        saved = getattr(self.device, 'extra_state', {}).get('ipc_state', {})
        if not saved:
            return

        for pipe_data in saved.get('pipes', []):
            pipe = self.ipc.create_pipe(pipe_data['name'], pipe_data['owner_pid'])
            if pipe:
                pipe.messages_sent = pipe_data.get('messages_sent', 0)
                pipe.messages_received = pipe_data.get('messages_received', 0)
                buffer_data = pipe_data.get('buffer', [])
                # Convert timestamp strings back to datetime objects
                for msg in buffer_data:
                    if 'timestamp' in msg and isinstance(msg['timestamp'], str):
                        msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
                pipe.buffer = deque(buffer_data, maxlen=100)

        for mq_data in saved.get('message_queues', []):
            mq = self.ipc.create_message_queue(mq_data['name'], mq_data['creator_pid'])
            if mq:
                messages_data = mq_data.get('messages', [])
                # Convert timestamp strings back to datetime objects
                for msg in messages_data:
                    if 'timestamp' in msg and isinstance(msg['timestamp'], str):
                        msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
                mq.messages = deque(messages_data)
                mq.subscribers = mq_data.get('subscribers', [])

        for shm_data in saved.get('shared_memory', []):
            shm = self.ipc.create_shared_memory(shm_data['name'], shm_data['creator_pid'], shm_data.get('size', 4096))
            if shm:
                shm.data = shm_data.get('data', {})
                shm.access_list = shm_data.get('access_list', [])

    def save_state(self):
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        state = {
            'pipes': [
                {
                    'name': pipe.name,
                    'owner_pid': pipe.owner_pid,
                    'messages_sent': pipe.messages_sent,
                    'messages_received': pipe.messages_received,
                    'buffer': [
                        {
                            'data': msg['data'],
                            'timestamp': serialize_datetime(msg['timestamp']),
                            'sender': msg['sender']
                        }
                        for msg in pipe.buffer
                    ]
                }
                for pipe in self.ipc.get_all_pipes()
            ],
            'message_queues': [
                {
                    'name': mq.name,
                    'creator_pid': mq.creator_pid,
                    'messages': [
                        {
                            'content': msg['content'],
                            'priority': msg['priority'],
                            'timestamp': serialize_datetime(msg['timestamp']),
                            'sender': msg['sender']
                        }
                        for msg in mq.messages
                    ],
                    'subscribers': mq.subscribers
                }
                for mq in self.ipc.get_all_message_queues()
            ],
            'shared_memory': [
                {
                    'name': shm.name,
                    'creator_pid': shm.creator_pid,
                    'size': shm.size,
                    'data': shm.data,
                    'access_list': shm.access_list
                }
                for shm in self.ipc.get_all_shared_memory()
            ]
        }
        self.device_manager.update_device_state(self.device, {'ipc_state': state})

    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()
