"""
User & Permission System - Advanced Edition
Realistic Unix-like permission model with advanced security features
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
import random
import string
from collections import deque
import re


class UserRole(Enum):
    """User privilege levels"""
    ADMIN = "admin"          # Full system access
    POWER_USER = "power_user"  # Extended permissions
    USER = "user"            # Standard user
    GUEST = "guest"          # Limited read-only access


class FilePermission(Enum):
    """Unix-style file permissions"""
    READ = 4      # r
    WRITE = 2     # w
    EXECUTE = 1   # x


class User:
    """Represents a system user"""
    
    def __init__(self, username, uid, gid, home_dir, shell="/bin/bash"):
        self.username = username
        self.uid = uid  # User ID
        self.gid = gid  # Group ID
        self.home_dir = home_dir
        self.shell = shell
        self.created_at = datetime.now()
        self.password_hash = ""  # Will be hashed
        self.password_salt = ""  # Salt for password hashing
        self.groups = [gid]
        self.last_login = None
        self.failed_login_attempts = 0
        self.account_locked = False
        self.locked_until = None
        self.password_expiry = None
        self.session_start = None
        self.roles = []  # RBAC roles
        
    def set_password(self, password):
        """Set user password with hashing"""
        self.password_salt = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        self.password_hash = self._hash_password(password)
        self.password_expiry = datetime.now() + timedelta(days=90)  # Default 90 days
        
    def _hash_password(self, password):
        """Hash password with salt"""
        combined = password + self.password_salt
        return hashlib.sha256(combined.encode()).hexdigest()
        
    def verify_password(self, password):
        """Verify password"""
        if not self.password_hash:
            return False
        return self._hash_password(password) == self.password_hash
        
    def is_password_expired(self):
        """Check if password is expired"""
        return self.password_expiry and datetime.now() > self.password_expiry
        
    def record_login_attempt(self, success):
        """Record login attempt"""
        if success:
            self.last_login = datetime.now()
            self.failed_login_attempts = 0
            self.account_locked = False
            self.locked_until = None
            self.session_start = datetime.now()
        else:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 3:  # Lock account after 3 failed attempts
                self.account_locked = True
                self.locked_until = datetime.now() + timedelta(minutes=30)
                
    def is_account_locked(self):
        """Check if account is locked"""
        if not self.account_locked:
            return False
        if self.locked_until and datetime.now() > self.locked_until:
            self.account_locked = False
            self.locked_until = None
            return False
        return True
        
    def is_session_expired(self):
        """Check if user session is expired"""
        if not self.session_start:
            return False
        return (datetime.now() - self.session_start).total_seconds() > 3600  # 1 hour
        
    def to_dict(self):
        return {
            "username": self.username,
            "uid": self.uid,
            "gid": self.gid,
            "home_dir": self.home_dir,
            "shell": self.shell,
            "created_at": self.created_at.isoformat(),
            "groups": self.groups,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "failed_login_attempts": self.failed_login_attempts,
            "account_locked": self.account_locked,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            "password_expiry": self.password_expiry.isoformat() if self.password_expiry else None,
            "roles": self.roles
        }


class Group:
    """Represents a system group"""
    
    def __init__(self, groupname, gid):
        self.groupname = groupname
        self.gid = gid
        self.members = []
        self.created_at = datetime.now()
        
    def to_dict(self):
        return {
            "groupname": self.groupname,
            "gid": self.gid,
            "members": self.members,
            "created_at": self.created_at.isoformat()
        }


class FilePermissions:
    """Unix-style file permissions (rwxrwxrwx)"""
    
    def __init__(self, owner_perm=7, group_perm=5, other_perm=5):
        self.owner = owner_perm  # 0-7
        self.group = group_perm  # 0-7
        self.other = other_perm  # 0-7
        
    def can_read(self, user, group, is_owner, is_group_member):
        """Check if user can read"""
        if is_owner:
            return (self.owner & FilePermission.READ.value) != 0
        elif is_group_member:
            return (self.group & FilePermission.READ.value) != 0
        else:
            return (self.other & FilePermission.READ.value) != 0
    
    def can_write(self, is_owner, is_group_member):
        """Check if user can write"""
        if is_owner:
            return (self.owner & FilePermission.WRITE.value) != 0
        elif is_group_member:
            return (self.group & FilePermission.WRITE.value) != 0
        else:
            return (self.other & FilePermission.WRITE.value) != 0
    
    def can_execute(self, is_owner, is_group_member):
        """Check if user can execute"""
        if is_owner:
            return (self.owner & FilePermission.EXECUTE.value) != 0
        elif is_group_member:
            return (self.group & FilePermission.EXECUTE.value) != 0
        else:
            return (self.other & FilePermission.EXECUTE.value) != 0
    
    def to_string(self):
        """Convert to rwx string format"""
        def perm_to_str(perm):
            r = "r" if (perm & 4) else "-"
            w = "w" if (perm & 2) else "-"
            x = "x" if (perm & 1) else "-"
            return r + w + x
        
        return perm_to_str(self.owner) + perm_to_str(self.group) + perm_to_str(self.other)
    
    def to_octal(self):
        """Convert to octal format"""
        return f"{self.owner}{self.group}{self.other}"


class AccessControlList:
    """Advanced ACL for fine-grained permissions"""
    
    def __init__(self):
        self.entries = []  # List of (user/group, permissions, type)
        
    def add_entry(self, target, permissions, entry_type="user"):
        """Add ACL entry"""
        self.entries.append({
            'target': target,  # username or gid
            'permissions': permissions,  # FilePermissions object
            'type': entry_type  # 'user' or 'group'
        })
        
    def check_permission(self, user, group, permission_type):
        """Check if user has specific permission"""
        # Check user-specific entries first
        for entry in self.entries:
            if entry['type'] == 'user' and entry['target'] == user.username:
                if permission_type == 'read':
                    return entry['permissions'].can_read(user, group, True, True)
                elif permission_type == 'write':
                    return entry['permissions'].can_write(True, True)
                elif permission_type == 'execute':
                    return entry['permissions'].can_execute(True, True)
        
        # Check group entries
        for entry in self.entries:
            if entry['type'] == 'group' and entry['target'] in user.groups:
                if permission_type == 'read':
                    return entry['permissions'].can_read(user, group, False, True)
                elif permission_type == 'write':
                    return entry['permissions'].can_write(False, True)
                elif permission_type == 'execute':
                    return entry['permissions'].can_execute(False, True)
        
        return False


class SecurityPolicy:
    """Security policies for password and access control"""
    
    def __init__(self):
        self.min_password_length = 8
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special_chars = True
        self.password_expiry_days = 90
        self.max_login_attempts = 3
        self.lockout_duration_minutes = 30
        self.session_timeout_minutes = 60
        
    def validate_password(self, password):
        """Validate password against policy"""
        errors = []
        
        if len(password) < self.min_password_length:
            errors.append(f"Password must be at least {self.min_password_length} characters")
            
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain uppercase letters")
            
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain lowercase letters")
            
        if self.require_digits and not re.search(r'\d', password):
            errors.append("Password must contain digits")
            
        if self.require_special_chars and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain special characters")
            
        return errors
    
    def generate_password(self):
        """Generate a compliant password"""
        chars = ""
        password = []
        
        if self.require_lowercase:
            chars += string.ascii_lowercase
            password.append(random.choice(string.ascii_lowercase))
            
        if self.require_uppercase:
            chars += string.ascii_uppercase
            password.append(random.choice(string.ascii_uppercase))
            
        if self.require_digits:
            chars += string.digits
            password.append(random.choice(string.digits))
            
        if self.require_special_chars:
            special = "!@#$%^&*(),.?\":{}|<>"
            chars += special
            password.append(random.choice(special))
        
        # Fill remaining length
        remaining = self.min_password_length - len(password)
        for _ in range(remaining):
            password.append(random.choice(chars))
        
        # Shuffle
        random.shuffle(password)
        return ''.join(password)


class RoleBasedAccessControl:
    """RBAC system for advanced permission management"""
    
    def __init__(self):
        self.roles = {}  # role_name -> permissions
        self.user_roles = {}  # username -> [roles]
        self.role_hierarchy = {}  # role -> parent_roles
        
        # Define default roles
        self._setup_default_roles()
        
    def _setup_default_roles(self):
        """Setup default RBAC roles"""
        self.roles = {
            'admin': ['user.create', 'user.delete', 'group.create', 'group.delete', 
                     'file.read', 'file.write', 'file.execute', 'system.admin'],
            'power_user': ['user.read', 'group.read', 'file.read', 'file.write', 'file.execute'],
            'user': ['user.read', 'file.read', 'file.write'],
            'guest': ['file.read']
        }
        
        self.role_hierarchy = {
            'admin': ['power_user', 'user', 'guest'],
            'power_user': ['user', 'guest'],
            'user': ['guest']
        }
        
    def assign_role(self, username, role):
        """Assign role to user"""
        if username not in self.user_roles:
            self.user_roles[username] = []
        if role not in self.user_roles[username]:
            self.user_roles[username].append(role)
            
    def revoke_role(self, username, role):
        """Revoke role from user"""
        if username in self.user_roles and role in self.user_roles[username]:
            self.user_roles[username].remove(role)
            
    def get_user_permissions(self, username):
        """Get all permissions for user"""
        if username not in self.user_roles:
            return set()
            
        permissions = set()
        for role in self.user_roles[username]:
            permissions.update(self.roles.get(role, []))
            # Add inherited permissions
            for parent_role in self.role_hierarchy.get(role, []):
                permissions.update(self.roles.get(parent_role, []))
                
        return permissions
    
    def check_permission(self, username, permission):
        """Check if user has specific permission"""
        user_permissions = self.get_user_permissions(username)
        return permission in user_permissions
    
    def can_execute(self, is_owner, is_group_member):
        """Check if user can execute"""
        if is_owner:
            return (self.owner & FilePermission.EXECUTE.value) != 0
        elif is_group_member:
            return (self.group & FilePermission.EXECUTE.value) != 0
        else:
            return (self.other & FilePermission.EXECUTE.value) != 0
    
    def to_string(self):
        """Convert to rwxrwxrwx format"""
        def perm_to_str(p):
            s = ""
            s += "r" if (p & FilePermission.READ.value) else "-"
            s += "w" if (p & FilePermission.WRITE.value) else "-"
            s += "x" if (p & FilePermission.EXECUTE.value) else "-"
            return s
        
        return perm_to_str(self.owner) + perm_to_str(self.group) + perm_to_str(self.other)
    
    @staticmethod
    def from_string(perm_str):
        """Parse rwxrwxrwx format"""
        owner = int(perm_str[0:3].replace('r', '4').replace('w', '2').replace('x', '1').replace('-', '0'), 8) if len(perm_str) >= 3 else 7
        group = int(perm_str[3:6].replace('r', '4').replace('w', '2').replace('x', '1').replace('-', '0'), 8) if len(perm_str) >= 6 else 5
        other = int(perm_str[6:9].replace('r', '4').replace('w', '2').replace('x', '1').replace('-', '0'), 8) if len(perm_str) >= 9 else 5
        return FilePermissions(owner, group, other)


class UserManager:
    """Manages users and groups"""
    
    def __init__(self):
        self.users = {}
        self.groups = {}
        self.next_uid = 1000
        self.next_gid = 1000
        self.rbac = RoleBasedAccessControl()
        self.security_policy = SecurityPolicy()
        self.audit_log = deque(maxlen=1000)
        
        # Create default users and groups
        self._create_system_defaults()
        
    def _create_system_defaults(self):
        """Create default system users and groups"""
        # Create root user
        root = User("root", 0, 0, "/root", "/bin/bash")
        root.set_password("RootPass123!")
        root.roles = ['admin']
        self.users["root"] = root
        
        # Create common groups
        self.groups[0] = Group("root", 0)
        self.groups[1] = Group("users", 1)
        self.groups[4] = Group("adm", 4)
        self.groups[27] = Group("sudo", 27)
        
        # Create regular user
        user = User("user", 1000, 1, "/home/user", "/bin/bash")
        user.set_password("UserPass123!")
        user.roles = ['user']
        self.users["user"] = user
        self.groups[1].members.append(user.username)
        
    def create_user(self, username, gid=1, home_dir=None, password=None):
        """Create a new user"""
        if username in self.users:
            return None
        
        if home_dir is None:
            home_dir = f"/home/{username}"
        
        uid = self.next_uid
        self.next_uid += 1
        
        user = User(username, uid, gid, home_dir)
        
        # Set password if provided, otherwise generate one
        if password:
            validation_errors = self.security_policy.validate_password(password)
            if validation_errors:
                raise ValueError(f"Password validation failed: {'; '.join(validation_errors)}")
            user.set_password(password)
        else:
            generated_password = self.security_policy.generate_password()
            user.set_password(generated_password)
            
        # Assign default role
        user.roles = ['user']
        self.rbac.assign_role(username, 'user')
        
        self.users[username] = user
        
        if gid in self.groups:
            self.groups[gid].members.append(username)
        
        self._audit_log(f"User created: {username} (UID: {uid})")
        return user
    
    def authenticate_user(self, username, password):
        """Authenticate user"""
        user = self.get_user(username)
        if not user:
            return False, "User not found"
            
        if user.is_account_locked():
            return False, "Account is locked"
            
        if user.is_password_expired():
            return False, "Password expired"
            
        if user.verify_password(password):
            user.record_login_attempt(True)
            self._audit_log(f"User login successful: {username}")
            return True, "Login successful"
        else:
            user.record_login_attempt(False)
            self._audit_log(f"User login failed: {username}")
            return False, f"Invalid password. {3 - user.failed_login_attempts} attempts remaining"
    
    def change_password(self, username, old_password, new_password):
        """Change user password"""
        user = self.get_user(username)
        if not user:
            return False, "User not found"
            
        if not user.verify_password(old_password):
            return False, "Current password incorrect"
            
        validation_errors = self.security_policy.validate_password(new_password)
        if validation_errors:
            return False, f"New password invalid: {'; '.join(validation_errors)}"
            
        user.set_password(new_password)
        self._audit_log(f"Password changed for user: {username}")
        return True, "Password changed successfully"
        
    def assign_role(self, username, role):
        """Assign RBAC role to user"""
        if username not in self.users:
            return False
            
        self.rbac.assign_role(username, role)
        self.users[username].roles.append(role)
        self._audit_log(f"Role {role} assigned to user: {username}")
        return True
        
    def revoke_role(self, username, role):
        """Revoke RBAC role from user"""
        if username not in self.users:
            return False
            
        self.rbac.revoke_role(username, role)
        if role in self.users[username].roles:
            self.users[username].roles.remove(role)
        self._audit_log(f"Role {role} revoked from user: {username}")
        return True
        
    def check_permission(self, username, permission):
        """Check if user has permission"""
        return self.rbac.check_permission(username, permission)
        
    def get_user_permissions(self, username):
        """Get all permissions for user"""
        return self.rbac.get_user_permissions(username)
        
    def _audit_log(self, message):
        """Log audit event"""
        self.audit_log.append({
            'timestamp': datetime.now(),
            'message': message
        })
    
    def create_group(self, groupname):
        """Create a new group"""
        gid = self.next_gid
        self.next_gid += 1
        
        group = Group(groupname, gid)
        self.groups[gid] = group
        return group
    
    def add_user_to_group(self, username, gid):
        """Add user to group"""
        if username not in self.users or gid not in self.groups:
            return False
        
        user = self.users[username]
        group = self.groups[gid]
        
        if username not in group.members:
            group.members.append(username)
            if gid not in user.groups:
                user.groups.append(gid)
            return True
        return False
    
    def get_user(self, username):
        """Get user by username"""
        return self.users.get(username)
    
    def get_group(self, gid):
        """Get group by GID"""
        return self.groups.get(gid)
    
    def list_users(self):
        """List all users"""
        return list(self.users.values())
    
    def list_groups(self):
        """List all groups"""
        return list(self.groups.values())


class UserPermissionUI:
    """UI for User and Permission Management"""
    
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        
        self.colors = {
            "bg": "#1e1e2e",
            "card": "#313244",
            "accent": "#f7a400",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "danger": "#f38ba8",
            "text": "#cdd6f4",
            "text_muted": "#6c7086"
        }
        
        self.um = UserManager()
        self.setup_ui()
        self.load_saved_state()
        
    def setup_ui(self):
        """Setup the UI"""
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", pady=(20, 10), padx=20)
        
        tk.Label(header, text="👥 User & Permission Manager", font=("Segoe UI", 24, "bold"),
                bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        tk.Label(header, text=f"Device: {self.device.name}",
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w")
        
        content = tk.Frame(self.main_frame, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Notebook for tabs
        notebook = ttk.Notebook(content)
        notebook.pack(fill="both", expand=True)
        
        # Users tab
        users_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(users_frame, text="👥 Users")
        self._setup_users_tab(users_frame)
        
        # Groups tab
        groups_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(groups_frame, text="👥 Groups")
        self._setup_groups_tab(groups_frame)
        
        # Permissions tab
        perms_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(perms_frame, text="🔒 Permissions")
        self._setup_permissions_tab(perms_frame)
        
        # RBAC tab
        rbac_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(rbac_frame, text="🛡️ RBAC")
        self._setup_rbac_tab(rbac_frame)
        
        # Security tab
        security_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(security_frame, text="🔐 Security")
        self._setup_security_tab(security_frame)
        
        # Audit tab
        audit_frame = tk.Frame(notebook, bg=self.colors["card"])
        notebook.add(audit_frame, text="📋 Audit Log")
        self._setup_audit_tab(audit_frame)
        
        # Back button
        button_frame = tk.Frame(content, bg=self.colors["bg"])
        button_frame.pack(fill="x", pady=10)
        tk.Button(button_frame, text="Back", command=self.go_back,
                 bg=self.colors["text_muted"], fg="#000000").pack(side="right", padx=5)
        
    def _setup_users_tab(self, parent):
        """Setup users management tab"""
        # Create user section
        create_frame = tk.LabelFrame(parent, text="Create User", bg=self.colors["card"],
                                    fg=self.colors["text"])
        create_frame.pack(fill="x", padx=10, pady=10)
        
        input_frame = tk.Frame(create_frame, bg=self.colors["card"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(input_frame, text="Username:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.username_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.username_entry.pack(fill="x", pady=(0, 10))
        
        tk.Button(input_frame, text="Create User", command=self.create_user,
                 bg=self.colors["accent"], fg="#000000").pack(fill="x")
        
        # Users list
        list_frame = tk.LabelFrame(parent, text="System Users", bg=self.colors["card"],
                                  fg=self.colors["text"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Username", "UID", "GID", "Home Dir")
        self.users_tree = ttk.Treeview(list_frame, columns=columns, height=10)
        
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=120)
        
        self.users_tree.pack(fill="both", expand=True)
        self.refresh_users_list()
        
    def _setup_groups_tab(self, parent):
        """Setup groups management tab"""
        # Create group section
        create_frame = tk.LabelFrame(parent, text="Create Group", bg=self.colors["card"],
                                    fg=self.colors["text"])
        create_frame.pack(fill="x", padx=10, pady=10)
        
        input_frame = tk.Frame(create_frame, bg=self.colors["card"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(input_frame, text="Group Name:", bg=self.colors["card"],
                fg=self.colors["text"]).pack(anchor="w")
        self.groupname_entry = tk.Entry(input_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.groupname_entry.pack(fill="x", pady=(0, 10))
        
        tk.Button(input_frame, text="Create Group", command=self.create_group,
                 bg=self.colors["accent"], fg="#000000").pack(fill="x")
        
        # Groups list
        list_frame = tk.LabelFrame(parent, text="System Groups", bg=self.colors["card"],
                                  fg=self.colors["text"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Group Name", "GID", "Members")
        self.groups_tree = ttk.Treeview(list_frame, columns=columns, height=10)
        
        for col in columns:
            self.groups_tree.heading(col, text=col)
            self.groups_tree.column(col, width=150)
        
        self.groups_tree.pack(fill="both", expand=True)
        self.refresh_groups_list()
        
    def _setup_permissions_tab(self, parent):
        """Setup file permissions tab"""
        # Unix permissions section
        unix_frame = tk.LabelFrame(parent, text="Unix File Permissions", bg=self.colors["card"],
                                  fg=self.colors["text"])
        unix_frame.pack(fill="x", padx=10, pady=10)
        
        info_text = tk.Label(unix_frame, text=
            "Unix permissions use rwx format:\n"
            "r (read) = 4, w (write) = 2, x (execute) = 1\n\n"
            "Format: Owner Group Other (e.g., 755 = rwxr-xr-x)\n\n"
            "This simulates standard Unix file permissions with\n"
            "support for owner, group, and other access levels.",
            bg=self.colors["card"], fg=self.colors["text"], justify="left")
        info_text.pack(padx=10, pady=10)
        
        # Permission calculator
        calc_frame = tk.LabelFrame(parent, text="Permission Calculator", bg=self.colors["card"],
                                  fg=self.colors["text"])
        calc_frame.pack(fill="x", padx=10, pady=10)
        
        # Owner permissions
        owner_frame = tk.Frame(calc_frame, bg=self.colors["card"])
        owner_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(owner_frame, text="Owner:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        
        self.owner_read = tk.BooleanVar()
        self.owner_write = tk.BooleanVar()
        self.owner_execute = tk.BooleanVar()
        
        tk.Checkbutton(owner_frame, text="Read", variable=self.owner_read, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        tk.Checkbutton(owner_frame, text="Write", variable=self.owner_write, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        tk.Checkbutton(owner_frame, text="Execute", variable=self.owner_execute, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        
        # Group permissions
        group_frame = tk.Frame(calc_frame, bg=self.colors["card"])
        group_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(group_frame, text="Group:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        
        self.group_read = tk.BooleanVar()
        self.group_write = tk.BooleanVar()
        self.group_execute = tk.BooleanVar()
        
        tk.Checkbutton(group_frame, text="Read", variable=self.group_read, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        tk.Checkbutton(group_frame, text="Write", variable=self.group_write, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        tk.Checkbutton(group_frame, text="Execute", variable=self.group_execute, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        
        # Other permissions
        other_frame = tk.Frame(calc_frame, bg=self.colors["card"])
        other_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(other_frame, text="Other:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        
        self.other_read = tk.BooleanVar()
        self.other_write = tk.BooleanVar()
        self.other_execute = tk.BooleanVar()
        
        tk.Checkbutton(other_frame, text="Read", variable=self.other_read, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        tk.Checkbutton(other_frame, text="Write", variable=self.other_write, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        tk.Checkbutton(other_frame, text="Execute", variable=self.other_execute, bg=self.colors["card"], fg=self.colors["text"], command=self._update_permission_display).pack(side="left", padx=5)
        
        # Result display
        result_frame = tk.Frame(calc_frame, bg=self.colors["card"])
        result_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(result_frame, text="Octal:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.octal_label = tk.Label(result_frame, text="755", bg=self.colors["card"], fg=self.colors["accent"], font=("Courier", 12, "bold"))
        self.octal_label.pack(side="left", padx=10)
        
        tk.Label(result_frame, text="Symbolic:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=20)
        self.symbolic_label = tk.Label(result_frame, text="rwxr-xr-x", bg=self.colors["card"], fg=self.colors["accent"], font=("Courier", 12, "bold"))
        self.symbolic_label.pack(side="left", padx=10)
        
    def _setup_rbac_tab(self, parent):
        """Setup RBAC management tab"""
        # Role assignment section
        assign_frame = tk.LabelFrame(parent, text="Role Assignment", bg=self.colors["card"],
                                    fg=self.colors["text"])
        assign_frame.pack(fill="x", padx=10, pady=10)
        
        # User selection
        user_frame = tk.Frame(assign_frame, bg=self.colors["card"])
        user_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(user_frame, text="User:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.rbac_user_var = tk.StringVar()
        self.rbac_user_combo = ttk.Combobox(user_frame, textvariable=self.rbac_user_var, state="readonly")
        self.rbac_user_combo.pack(side="left", padx=10, fill="x", expand=True)
        self.rbac_user_combo.bind("<<ComboboxSelected>>", self._update_user_roles)
        
        # Role selection
        role_frame = tk.Frame(assign_frame, bg=self.colors["card"])
        role_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(role_frame, text="Role:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.rbac_role_var = tk.StringVar()
        self.rbac_role_combo = ttk.Combobox(role_frame, textvariable=self.rbac_role_var, 
                                           values=["admin", "power_user", "user", "guest"], state="readonly")
        self.rbac_role_combo.pack(side="left", padx=10, fill="x", expand=True)
        
        # Buttons
        btn_frame = tk.Frame(assign_frame, bg=self.colors["card"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        tk.Button(btn_frame, text="Assign Role", command=self._assign_role,
                 bg=self.colors["success"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Revoke Role", command=self._revoke_role,
                 bg=self.colors["danger"], fg="#ffffff").pack(side="left", padx=5)
        
        # Current roles display
        roles_frame = tk.LabelFrame(parent, text="Current User Roles", bg=self.colors["card"],
                                   fg=self.colors["text"])
        roles_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.roles_text = scrolledtext.ScrolledText(roles_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                                   height=10, font=("Consolas", 9))
        self.roles_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Role permissions display
        perm_frame = tk.LabelFrame(parent, text="Role Permissions", bg=self.colors["card"],
                                  fg=self.colors["text"])
        perm_frame.pack(fill="x", padx=10, pady=10)
        
        self.permissions_text = scrolledtext.ScrolledText(perm_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                                        height=8, font=("Consolas", 9))
        self.permissions_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._update_rbac_users()
        
    def _setup_security_tab(self, parent):
        """Setup security policies tab"""
        # Password policy section
        policy_frame = tk.LabelFrame(parent, text="Password Policy", bg=self.colors["card"],
                                    fg=self.colors["text"])
        policy_frame.pack(fill="x", padx=10, pady=10)
        
        # Policy settings
        settings_frame = tk.Frame(policy_frame, bg=self.colors["card"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        # Minimum length
        len_frame = tk.Frame(settings_frame, bg=self.colors["card"])
        len_frame.pack(fill="x", pady=2)
        tk.Label(len_frame, text="Min Length:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.min_len_var = tk.IntVar(value=self.um.security_policy.min_password_length)
        tk.Spinbox(len_frame, from_=6, to=20, textvariable=self.min_len_var, width=5).pack(side="right")
        
        # Requirements
        req_frame = tk.Frame(settings_frame, bg=self.colors["card"])
        req_frame.pack(fill="x", pady=5)
        
        self.req_upper = tk.BooleanVar(value=self.um.security_policy.require_uppercase)
        self.req_lower = tk.BooleanVar(value=self.um.security_policy.require_lowercase)
        self.req_digits = tk.BooleanVar(value=self.um.security_policy.require_digits)
        self.req_special = tk.BooleanVar(value=self.um.security_policy.require_special_chars)
        
        tk.Checkbutton(req_frame, text="Uppercase", variable=self.req_upper, bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=10)
        tk.Checkbutton(req_frame, text="Lowercase", variable=self.req_lower, bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=10)
        tk.Checkbutton(req_frame, text="Digits", variable=self.req_digits, bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=10)
        tk.Checkbutton(req_frame, text="Special Chars", variable=self.req_special, bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=10)
        
        # Password operations
        pwd_frame = tk.LabelFrame(parent, text="Password Management", bg=self.colors["card"],
                                 fg=self.colors["text"])
        pwd_frame.pack(fill="x", padx=10, pady=10)
        
        # User selection for password change
        user_frame = tk.Frame(pwd_frame, bg=self.colors["card"])
        user_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(user_frame, text="User:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.pwd_user_var = tk.StringVar()
        self.pwd_user_combo = ttk.Combobox(user_frame, textvariable=self.pwd_user_var, state="readonly")
        self.pwd_user_combo.pack(side="left", padx=10, fill="x", expand=True)
        
        # New password
        pwd_entry_frame = tk.Frame(pwd_frame, bg=self.colors["card"])
        pwd_entry_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(pwd_entry_frame, text="New Password:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.new_pwd_entry = tk.Entry(pwd_entry_frame, bg=self.colors["bg"], fg=self.colors["text"], show="*")
        self.new_pwd_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Buttons
        btn_frame = tk.Frame(pwd_frame, bg=self.colors["card"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        tk.Button(btn_frame, text="Change Password", command=self._change_password,
                 bg=self.colors["warning"], fg="#000000").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Generate Password", command=self._generate_password,
                 bg=self.colors["info"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Update Policy", command=self._update_policy,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        
        # Account status
        status_frame = tk.LabelFrame(parent, text="Account Status", bg=self.colors["card"],
                                    fg=self.colors["text"])
        status_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                                   height=10, font=("Consolas", 9))
        self.status_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._update_security_users()
        
    def _setup_audit_tab(self, parent):
        """Setup audit log tab"""
        # Audit log display
        log_frame = tk.LabelFrame(parent, text="Security Audit Log", bg=self.colors["card"],
                                 fg=self.colors["text"])
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.audit_text = scrolledtext.ScrolledText(log_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                                  height=20, font=("Consolas", 9))
        self.audit_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Controls
        ctrl_frame = tk.Frame(parent, bg=self.colors["bg"])
        ctrl_frame.pack(fill="x", pady=10, padx=20)
        
        tk.Button(ctrl_frame, text="Refresh Log", command=self._refresh_audit_log,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="Clear Log", command=self._clear_audit_log,
                 bg=self.colors["warning"], fg="#000000").pack(side="left", padx=5)
        
    def create_user(self):
        """Create a new user"""
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Username is required")
            return
        
        user = self.um.create_user(username)
        if user:
            self.log(f"User created: {username} (UID: {user.uid})")
            self.username_entry.delete(0, tk.END)
            self.refresh_users_list()
        else:
            messagebox.showerror("Error", "User already exists")
            return
        self.save_state()
            
    def create_group(self):
        """Create a new group"""
        groupname = self.groupname_entry.get().strip()
        if not groupname:
            messagebox.showerror("Error", "Group name is required")
            return
        
        group = self.um.create_group(groupname)
        self.log(f"Group created: {groupname} (GID: {group.gid})")
        self.groupname_entry.delete(0, tk.END)
        self.refresh_groups_list()
        self.save_state()
        
    def refresh_users_list(self):
        """Refresh users list display"""
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        for user in self.um.list_users():
            self.users_tree.insert("", "end", text="",
                                 values=(user.username, user.uid, user.gid, user.home_dir))
            
    def refresh_groups_list(self):
        """Refresh groups list display"""
        for item in self.groups_tree.get_children():
            self.groups_tree.delete(item)
        
        for group in self.um.list_groups():
            members_str = ", ".join(group.members) if group.members else "-"
            self.groups_tree.insert("", "end", text="",
                                  values=(group.groupname, group.gid, members_str))

    def load_saved_state(self):
        saved = getattr(self.device, 'extra_state', {}).get('user_manager_state', {})
        if not saved:
            return
        self.um = UserManager()
        self.um.users = {}
        self.um.groups = {}

        for udata in saved.get('users', []):
            user = User(udata['username'], udata['uid'], udata['gid'], udata['home_dir'], udata.get('shell', '/bin/bash'))
            user.created_at = datetime.fromisoformat(udata['created_at']) if udata.get('created_at') else user.created_at
            user.groups = udata.get('groups', [])
            self.um.users[user.username] = user

        for gdata in saved.get('groups', []):
            group = Group(gdata['groupname'], gdata['gid'])
            group.members = gdata.get('members', [])
            group.created_at = datetime.fromisoformat(gdata['created_at']) if gdata.get('created_at') else group.created_at
            self.um.groups[group.gid] = group

        self.um.next_uid = saved.get('next_uid', max((u.uid for u in self.um.users.values()), default=1000) + 1)
        self.um.next_gid = saved.get('next_gid', max(self.um.groups.keys(), default=1000) + 1)
        self.refresh_users_list()
        self.refresh_groups_list()

    def save_state(self):
        data = {
            'users': [user.to_dict() for user in self.um.list_users()],
            'groups': [group.to_dict() for group in self.um.list_groups()],
            'next_uid': self.um.next_uid,
            'next_gid': self.um.next_gid
        }
        self.device_manager.update_device_state(self.device, {'user_manager_state': data})

    def _update_permission_display(self):
        """Update permission display based on checkboxes"""
        owner_perm = (self.owner_read.get() * 4 + self.owner_write.get() * 2 + self.owner_execute.get() * 1)
        group_perm = (self.group_read.get() * 4 + self.group_write.get() * 2 + self.group_execute.get() * 1)
        other_perm = (self.other_read.get() * 4 + self.other_write.get() * 2 + self.other_execute.get() * 1)
        
        octal = f"{owner_perm}{group_perm}{other_perm}"
        symbolic = self._octal_to_symbolic(octal)
        
        self.octal_label.config(text=octal)
        self.symbolic_label.config(text=symbolic)
        
    def _octal_to_symbolic(self, octal):
        """Convert octal permission to symbolic format"""
        def perm_to_str(perm):
            r = "r" if (perm & 4) else "-"
            w = "w" if (perm & 2) else "-"
            x = "x" if (perm & 1) else "-"
            return r + w + x
        
        return perm_to_str(int(octal[0])) + perm_to_str(int(octal[1])) + perm_to_str(int(octal[2]))
        
    def _update_rbac_users(self):
        """Update RBAC user list"""
        users = [user.username for user in self.um.list_users()]
        self.rbac_user_combo['values'] = users
        if users:
            self.rbac_user_combo.set(users[0])
            self._update_user_roles()
            
    def _update_user_roles(self, event=None):
        """Update user roles display"""
        username = self.rbac_user_var.get()
        if not username:
            return
            
        user = self.um.get_user(username)
        if not user:
            return
            
        # Display current roles
        roles_text = f"Current roles for {username}:\n"
        roles_text += ", ".join(user.roles) if user.roles else "No roles assigned"
        roles_text += "\n\nAll permissions:\n"
        
        permissions = self.um.get_user_permissions(username)
        if permissions:
            for perm in sorted(permissions):
                roles_text += f"  - {perm}\n"
        else:
            roles_text += "  No permissions"
            
        self.roles_text.delete(1.0, tk.END)
        self.roles_text.insert(tk.END, roles_text)
        
        # Display role permissions
        perm_text = "Role Permissions:\n\n"
        for role in self.um.rbac.roles:
            perm_text += f"{role.upper()}:\n"
            for perm in self.um.rbac.roles[role]:
                perm_text += f"  - {perm}\n"
            perm_text += "\n"
            
        self.permissions_text.delete(1.0, tk.END)
        self.permissions_text.insert(tk.END, perm_text)
        
    def _assign_role(self):
        """Assign role to user"""
        username = self.rbac_user_var.get()
        role = self.rbac_role_var.get()
        
        if not username or not role:
            messagebox.showerror("Error", "Please select user and role")
            return
            
        if self.um.assign_role(username, role):
            self.log(f"Role {role} assigned to {username}")
            self._update_user_roles()
            messagebox.showinfo("Success", f"Role {role} assigned to {username}")
        else:
            messagebox.showerror("Error", "Failed to assign role")
            
    def _revoke_role(self):
        """Revoke role from user"""
        username = self.rbac_user_var.get()
        role = self.rbac_role_var.get()
        
        if not username or not role:
            messagebox.showerror("Error", "Please select user and role")
            return
            
        if self.um.revoke_role(username, role):
            self.log(f"Role {role} revoked from {username}")
            self._update_user_roles()
            messagebox.showinfo("Success", f"Role {role} revoked from {username}")
        else:
            messagebox.showerror("Error", "Failed to revoke role")
            
    def _update_security_users(self):
        """Update security user list"""
        users = [user.username for user in self.um.list_users()]
        self.pwd_user_combo['values'] = users
        if users:
            self.pwd_user_combo.set(users[0])
            
        self._update_account_status()
        
    def _change_password(self):
        """Change user password"""
        username = self.pwd_user_var.get()
        new_password = self.new_pwd_entry.get()
        
        if not username or not new_password:
            messagebox.showerror("Error", "Please select user and enter new password")
            return
            
        # For admin password change, we don't need old password
        success, message = self.um.change_password(username, "", new_password)
        if success:
            self.log(f"Password changed for {username}")
            self.new_pwd_entry.delete(0, tk.END)
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
            
    def _generate_password(self):
        """Generate a compliant password"""
        password = self.um.security_policy.generate_password()
        self.new_pwd_entry.delete(0, tk.END)
        self.new_pwd_entry.insert(0, password)
        messagebox.showinfo("Generated Password", f"Generated password: {password}\n\nPlease change it after first login.")
        
    def _update_policy(self):
        """Update security policy"""
        self.um.security_policy.min_password_length = self.min_len_var.get()
        self.um.security_policy.require_uppercase = self.req_upper.get()
        self.um.security_policy.require_lowercase = self.req_lower.get()
        self.um.security_policy.require_digits = self.req_digits.get()
        self.um.security_policy.require_special_chars = self.req_special.get()
        
        self.log("Security policy updated")
        messagebox.showinfo("Success", "Security policy updated")
        
    def _update_account_status(self):
        """Update account status display"""
        status_text = "Account Status:\n\n"
        
        for user in self.um.list_users():
            status_text += f"User: {user.username}\n"
            status_text += f"  UID: {user.uid}\n"
            status_text += f"  Locked: {'Yes' if user.is_account_locked() else 'No'}\n"
            status_text += f"  Password Expired: {'Yes' if user.is_password_expired() else 'No'}\n"
            status_text += f"  Failed Attempts: {user.failed_login_attempts}\n"
            status_text += f"  Last Login: {user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never'}\n"
            status_text += f"  Roles: {', '.join(user.roles)}\n\n"
            
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, status_text)
        
    def _refresh_audit_log(self):
        """Refresh audit log display"""
        log_text = "Security Audit Log:\n\n"
        
        for entry in reversed(list(self.um.audit_log)):
            timestamp = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            log_text += f"[{timestamp}] {entry['message']}\n"
            
        self.audit_text.delete(1.0, tk.END)
        self.audit_text.insert(tk.END, log_text)
        
    def _clear_audit_log(self):
        """Clear audit log"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the audit log?"):
            self.um.audit_log.clear()
            self._refresh_audit_log()
            self.log("Audit log cleared")

    def go_back(self):
        self.save_state()
        self.main_frame.destroy()
        self.back()
