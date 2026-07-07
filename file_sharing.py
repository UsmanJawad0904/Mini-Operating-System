"""
Advanced File Sharing Module
Cross-Platform File Transfer between Windows and Linux/Ubuntu
Supports multiple protocols: SMB, SSH/SFTP, HTTP, Custom Socket Protocol
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime, timedelta
from enum import Enum
import os
import socket
import threading
import hashlib
import json
import subprocess
import shutil
from pathlib import Path
from collections import deque
import time
import struct
import zlib
import posixpath


class ProtocolType(Enum):
    """Supported file sharing protocols"""
    SMB = "SMB (Samba)"
    SSH_SFTP = "SSH/SFTP"
    HTTP = "HTTP"
    CUSTOM = "Custom Socket"
    NFS = "NFS"


class TransferStatus(Enum):
    """File transfer status"""
    PENDING = "Pending"
    TRANSFERRING = "Transferring"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    PAUSED = "Paused"


class FileShare:
    """Represents a shared file or folder"""
    
    def __init__(self, path, share_name=None, protocol=ProtocolType.CUSTOM,
                 host=None, username=None, password=None, port=None,
                 auth_method="password", direction="win2ubuntu", remote_path=None):
        self.path = Path(path)
        self.share_name = share_name or self.path.name
        self.protocol = protocol
        self.host = host
        self.username = username
        self.password = password
        self.port = port or (22 if protocol == ProtocolType.SSH_SFTP else 445)
        self.auth_method = auth_method
        self.direction = direction
        self.remote_path = remote_path or ""
        self.created_at = datetime.now()
        self.is_folder = self.path.is_dir()
        self.size = self._calculate_size()
        self.access_list = []  # List of allowed users/hosts
        self.read_only = False
        self.compressed = False
        self.encrypted = False
        self.password = password or ""
        
    def _calculate_size(self):
        """Calculate total size of file or folder"""
        if self.path.is_file():
            return self.path.stat().st_size
        elif self.path.is_dir():
            total = 0
            for entry in self.path.rglob('*'):
                if entry.is_file():
                    total += entry.stat().st_size
            return total
        return 0
        
    def get_file_tree(self):
        """Get tree structure of files"""
        if not self.path.is_dir():
            return []
            
        tree = []
        for item in self.path.rglob('*'):
            rel_path = item.relative_to(self.path)
            tree.append({
                'path': str(rel_path),
                'is_dir': item.is_dir(),
                'size': item.stat().st_size if item.is_file() else 0,
                'modified': datetime.fromtimestamp(item.stat().st_mtime)
            })
        return tree


class FileTransfer:
    """Manages individual file transfer"""
    
    def __init__(self, source, destination, transfer_id, share=None, direction="win2ubuntu", remote_path=None):
        self.transfer_id = transfer_id
        self.share = share
        self.source = Path(source) if source else None
        self.destination = Path(destination) if destination else None
        self.direction = direction
        self.remote_path = remote_path
        self.status = TransferStatus.PENDING
        self.progress = 0  # 0-100
        self.bytes_transferred = 0
        self.total_bytes = self._get_size()
        self.start_time = None
        self.end_time = None
        self.speed = 0  # bytes per second
        self.eta = 0  # seconds remaining
        self.checksum_source = ""
        self.checksum_dest = ""
        self.error_message = ""
        self.retry_count = 0
        self.max_retries = 3
        
    def _get_size(self):
        """Get total size to transfer"""
        try:
            if self.direction in ('win2ubuntu', 'win2win') and self.source:
                if self.source.is_file():
                    return self.source.stat().st_size
                elif self.source.is_dir():
                    total = 0
                    for item in self.source.rglob('*'):
                        if item.is_file():
                            total += item.stat().st_size
                    return total
            return 0
        except Exception:
            return 0
        
    def calculate_checksum(self, file_path, algorithm='sha256'):
        """Calculate file checksum"""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
        
    def update_progress(self, bytes_transferred):
        """Update transfer progress"""
        self.bytes_transferred = bytes_transferred
        self.progress = min(100, (self.bytes_transferred / self.total_bytes * 100) if self.total_bytes > 0 else 0)
        
        # Calculate speed and ETA
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                self.speed = self.bytes_transferred / elapsed
                if self.speed > 0:
                    self.eta = int((self.total_bytes - self.bytes_transferred) / self.speed)


class SMBShare:
    """SMB/Samba protocol handler"""
    
    def __init__(self, share):
        self.share = share
        self.mounted = False
        self.mount_point = None
        
    def connect(self, host, username, password):
        """Connect to SMB share"""
        try:
            # For Windows, use net use command
            # For Linux, use mount.cifs
            if os.name == 'nt':
                cmd = f'net use \\\\{host}\\{self.share.share_name} /user:{username} {password}'
                subprocess.run(cmd, shell=True, check=True)
            else:
                mount_point = f'/mnt/{self.share.share_name}'
                os.makedirs(mount_point, exist_ok=True)
                cmd = f'sudo mount -t cifs //{host}/{self.share.share_name} {mount_point} -o username={username},password={password}'
                subprocess.run(cmd, shell=True, check=True)
                self.mount_point = mount_point
                
            self.mounted = True
            return True
        except Exception as e:
            return False
            
    def disconnect(self):
        """Disconnect from SMB share"""
        try:
            if os.name == 'nt':
                subprocess.run(f'net use \\\\{self.share.share_name} /delete', shell=True)
            elif self.mount_point:
                subprocess.run(f'sudo umount {self.mount_point}', shell=True)
            self.mounted = False
            return True
        except:
            return False


class SSHSFTPShare:
    """SSH/SFTP protocol handler"""
    
    def __init__(self, share):
        self.share = share
        self.client = None
        self.sftp_client = None
        self.last_error = None
        
    def connect(self, host, username, password, port=22):
        """Connect via SSH/SFTP"""
        try:
            import paramiko
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.share.auth_method == "key":
                key_path = str(password) if password else None
                if not key_path or not os.path.exists(key_path):
                    raise ValueError(f"SSH key file not found: {key_path}")
                self.client.connect(
                    host,
                    port=port,
                    username=username,
                    key_filename=key_path,
                    look_for_keys=False,
                    allow_agent=False
                )
            else:
                self.client.connect(host, port=port, username=username, password=password)

            self.sftp_client = self.client.open_sftp()
            self.last_error = None
            return True
        except ImportError:
            self.last_error = "Paramiko is not installed"
            print("🔥 Paramiko is not installed")
            return False
        except Exception as e:
            self.last_error = str(e)
            print(f"🔥 SSH connection failed: {repr(e)}")
            return False
            
    def upload_file(self, local_path, remote_path, callback=None):
        """Upload file via SFTP with proper error handling"""
        if not self.sftp_client:
            print("🔥 SFTP client is not connected")
            return False
        try:
            local_path = str(local_path)
            remote_path = str(remote_path).replace("\\", "/")
            
            print(f"🔧 SFTP upload local_path={local_path}")
            print(f"🔧 SFTP upload remote_path={remote_path}")
            
            if not os.path.exists(local_path):
                print(f"🔥 Local file does not exist: {local_path}")
                return False
            
            remote_dir = posixpath.dirname(remote_path)
            if remote_dir:
                if not self._ensure_remote_dir_exists(remote_dir):
                    print(f"🔥 Failed to ensure remote directory exists: {remote_dir}")
                    return False
            
            try:
                self.sftp_client.chdir("/")
            except Exception:
                pass
            
            self.sftp_client.put(local_path, remote_path, callback=callback)
            print(f"✅ SFTP put succeeded: {remote_path}")
            return True
        except Exception as e:
            print(f"🔥 REAL SFTP ERROR: {repr(e)}")
            return False
    
    def _ensure_remote_dir_exists(self, remote_dir):
        """Ensure remote directory exists, creating it recursively"""
        remote_dir = remote_dir.rstrip("/")
        if not remote_dir or remote_dir == "/":
            return True
        try:
            self.sftp_client.stat(remote_dir)
            return True
        except IOError:
            try:
                parent_dir = posixpath.dirname(remote_dir)
                if parent_dir and parent_dir != "/":
                    self._ensure_remote_dir_exists(parent_dir)
                self.sftp_client.mkdir(remote_dir)
                return True
            except Exception:
                return False
            
    def download_file(self, remote_path, local_path, callback=None):
        """Download file via SFTP with proper error handling"""
        if not self.sftp_client:
            print("🔥 SFTP client is not connected")
            return False
        try:
            local_path = str(local_path)
            remote_path = str(remote_path).replace("\\", "/")
            
            print(f"🔧 SFTP download remote_path={remote_path}")
            print(f"🔧 SFTP download local_path={local_path}")
            
            try:
                self.sftp_client.stat(remote_path)
            except Exception as e:
                print(f"🔥 Remote file not found: {remote_path} - {repr(e)}")
                return False
            
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            self.sftp_client.get(remote_path, local_path, callback=callback)
            
            if os.path.exists(local_path):
                return True
            return False
        except Exception as e:
            print(f"🔥 REAL SFTP DOWNLOAD ERROR: {repr(e)}")
            return False
            
    def get_file_size(self, remote_path):
        """Get remote file size via SFTP"""
        if not self.sftp_client:
            return 0
        try:
            return self.sftp_client.stat(remote_path).st_size
        except:
            return 0
            
    def disconnect(self):
        """Disconnect SSH"""
        try:
            if self.sftp_client:
                self.sftp_client.close()
            if self.client:
                self.client.close()
            return True
        except:
            return False


class CustomSocketProtocol:
    """Custom socket-based file transfer protocol"""
    
    def __init__(self, host, port=9999):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.buffer_size = 1024 * 1024  # 1MB chunks
        
    def connect(self):
        """Connect to custom protocol server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except:
            return False
            
    def send_file(self, file_path, callback=None):
        """Send file using custom protocol"""
        if not self.connected:
            return False
            
        try:
            file_path = Path(file_path)
            file_size = file_path.stat().st_size
            file_name = file_path.name
            
            # Send file header
            header = {
                'type': 'file_transfer',
                'filename': file_name,
                'size': file_size,
                'timestamp': datetime.now().isoformat()
            }
            header_json = json.dumps(header).encode()
            header_len = struct.pack('!I', len(header_json))
            self.socket.sendall(header_len + header_json)
            
            # Send file data
            bytes_sent = 0
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(self.buffer_size)
                    if not chunk:
                        break
                    self.socket.sendall(chunk)
                    bytes_sent += len(chunk)
                    if callback:
                        callback(bytes_sent)
                        
            return True
        except Exception as e:
            return False
            
    def receive_file(self, destination, callback=None):
        """Receive file using custom protocol"""
        if not self.connected:
            return False
            
        try:
            # Receive header
            header_len_data = self.socket.recv(4)
            header_len = struct.unpack('!I', header_len_data)[0]
            header_json = self.socket.recv(header_len)
            header = json.loads(header_json.decode())
            
            file_size = header['size']
            file_name = header['filename']
            
            # Receive file data
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            bytes_received = 0
            with open(destination, 'wb') as f:
                while bytes_received < file_size:
                    chunk = self.socket.recv(self.buffer_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_received += len(chunk)
                    if callback:
                        callback(bytes_received)
                        
            return True
        except Exception as e:
            return False
            
    def disconnect(self):
        """Disconnect from server"""
        try:
            if self.socket:
                self.socket.close()
            self.connected = False
            return True
        except:
            return False


class NetworkDiscovery:
    """Discover available devices on network"""
    
    def __init__(self):
        self.devices = []
        self.scanning = False
        
    def scan_network(self, network_range="192.168.1.0/24", callback=None):
        """Scan network for active devices"""
        try:
            import ipaddress
            import concurrent.futures
            
            self.scanning = True
            self.devices = []
            
            network = ipaddress.ip_network(network_range, strict=False)
            
            def ping_host(ip):
                try:
                    if os.name == 'nt':
                        result = subprocess.run(['ping', '-n', '1', str(ip)], 
                                              capture_output=True, timeout=1)
                    else:
                        result = subprocess.run(['ping', '-c', '1', str(ip)], 
                                              capture_output=True, timeout=1)
                    return result.returncode == 0, str(ip)
                except:
                    return False, str(ip)
                    
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(ping_host, ip) for ip in network.hosts()]
                for future in concurrent.futures.as_completed(futures):
                    reachable, ip = future.result()
                    if reachable:
                        self.devices.append({
                            'ip': ip,
                            'hostname': self._get_hostname(ip),
                            'last_seen': datetime.now()
                        })
                        if callback:
                            callback(ip)
                            
            self.scanning = False
            return self.devices
        except:
            return []
            
    def _get_hostname(self, ip):
        """Get hostname from IP"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return "Unknown"


class FileShareManager:
    """Main manager for file sharing"""
    
    def __init__(self):
        self.shares = {}  # share_id -> FileShare
        self.transfers = {}  # transfer_id -> FileTransfer
        self.connections = {}  # host -> connection object
        self.discovery = NetworkDiscovery()
        self.transfer_history = deque(maxlen=100)
        self.next_share_id = 1000
        self.next_transfer_id = 2000
        
    def create_share(self, path, share_name=None, protocol=ProtocolType.CUSTOM,
                     host=None, username=None, password=None, port=None,
                     auth_method="password", direction="win2ubuntu",
                     remote_path=None):
        """Create a new shared resource"""
        share_id = self.next_share_id
        self.next_share_id += 1
        
        share = FileShare(path, share_name, protocol,
                          host=host, username=username, password=password,
                          port=port, auth_method=auth_method,
                          direction=direction, remote_path=remote_path)
        self.shares[share_id] = share
        return share_id, share
        
    def remove_share(self, share_id):
        """Remove a shared resource"""
        if share_id in self.shares:
            del self.shares[share_id]
            return True
        return False
        
    def initiate_transfer(self, share_id, source, destination, protocol=None):
        """Start a file transfer"""
        share = self.shares.get(share_id)
        transfer_id = self.next_transfer_id
        self.next_transfer_id += 1
        
        direction = share.direction if share else "win2ubuntu"
        remote_path = share.remote_path if share else None
        transfer = FileTransfer(source, destination, transfer_id,
                                share=share, direction=direction,
                                remote_path=remote_path)
        self.transfers[transfer_id] = transfer
        
        protocol = protocol or (share.protocol if share else ProtocolType.CUSTOM)
        
        # Start transfer in background thread
        thread = threading.Thread(
            target=self._execute_transfer,
            args=(transfer_id, protocol)
        )
        thread.daemon = True
        thread.start()
        
        return transfer_id
        
    def _execute_transfer(self, transfer_id, protocol):
        """Execute file transfer"""
        transfer = self.transfers.get(transfer_id)
        if not transfer:
            return
            
        transfer.status = TransferStatus.TRANSFERRING
        transfer.start_time = datetime.now()
        
        try:
            if protocol == ProtocolType.CUSTOM:
                self._transfer_custom_protocol(transfer)
            elif protocol == ProtocolType.SSH_SFTP:
                self._transfer_sftp(transfer)
            elif protocol == ProtocolType.SMB:
                self._transfer_smb(transfer)
                
            # Verify transfer
            if transfer.source and transfer.source.is_file() and transfer.destination and transfer.destination.exists():
                transfer.checksum_source = transfer.calculate_checksum(transfer.source)
                transfer.checksum_dest = transfer.calculate_checksum(transfer.destination)
                
                if transfer.checksum_source == transfer.checksum_dest:
                    transfer.status = TransferStatus.COMPLETED
                else:
                    transfer.status = TransferStatus.FAILED
                    transfer.error_message = "Checksum mismatch"
            else:
                transfer.status = TransferStatus.COMPLETED
                
        except Exception as e:
            transfer.status = TransferStatus.FAILED
            transfer.error_message = str(e)
            
        transfer.end_time = datetime.now()
        self.transfer_history.append(transfer)
        
    def _transfer_custom_protocol(self, transfer):
        """Transfer using custom socket protocol"""
        share = transfer.share
        host = share.host if share and share.host else "localhost"
        protocol = CustomSocketProtocol(host)
        if protocol.connect():
            if transfer.source and transfer.source.is_file():
                protocol.send_file(transfer.source,
                                   lambda b: transfer.update_progress(b))
            protocol.disconnect()
            
    def _transfer_sftp(self, transfer):
        """Transfer using SFTP"""
        share = transfer.share
        if not share:
            raise Exception("SFTP transfer missing share metadata")
        sftp = SSHSFTPShare(share)
        if not sftp.connect(share.host, share.username, share.password, share.port):
            error_text = sftp.last_error or "Unable to connect to SSH/SFTP host"
            raise Exception(f"Unable to connect to SSH/SFTP host: {error_text}")

        try:
            if share.direction == "win2ubuntu":
                if not transfer.source or not transfer.source.exists():
                    raise Exception("Source path does not exist")
                
                remote_base = share.remote_path or ""
                # Expand ~ to home directory
                if remote_base.startswith("~/"):
                    try:
                        home = sftp.sftp_client.normalize(".")
                        remote_base = remote_base.replace("~", home, 1)
                    except:
                        pass
                
                # Normalize to POSIX path
                remote_base = remote_base.replace("\\", "/").rstrip("/")
                
                if transfer.source.is_file():
                    remote_dest = posixpath.join(remote_base, transfer.source.name) if remote_base else transfer.source.name
                    success = sftp.upload_file(
                        str(transfer.source),
                        remote_dest,
                        callback=lambda transferred, total=None: transfer.update_progress(transferred)
                    )
                elif transfer.source.is_dir():
                    # Upload directory recursively
                    success = self._upload_directory_sftp(
                        sftp,
                        transfer.source,
                        remote_base,
                        callback=lambda transferred, total=None: transfer.update_progress(transferred)
                    )
                else:
                    raise Exception("Source is neither file nor directory")
                    
            elif share.direction == "ubuntu2win":
                if not transfer.destination:
                    raise Exception("Destination path is required for remote download")
                remote_source = share.remote_path or transfer.source.name if transfer.source else None
                # Expand ~ to home directory
                if remote_source and remote_source.startswith("~/"):
                    try:
                        home = sftp.sftp_client.normalize(".")
                        remote_source = remote_source.replace("~", home, 1)
                    except:
                        pass
                
                # Normalize to POSIX path
                remote_source = remote_source.replace("\\", "/") if remote_source else None
                
                if not remote_source:
                    raise Exception("Remote source path is required for download")
                
                # Check if remote source is a directory
                try:
                    sftp.sftp_client.listdir(remote_source)
                    is_remote_dir = True
                except:
                    is_remote_dir = False
                
                if is_remote_dir:
                    # Download directory recursively
                    transfer.total_bytes = self._get_directory_size_sftp(sftp, remote_source) or transfer.total_bytes
                    success = self._download_directory_sftp(
                        sftp,
                        remote_source,
                        transfer.destination,
                        callback=lambda transferred, total=None: transfer.update_progress(transferred)
                    )
                else:
                    transfer.total_bytes = sftp.get_file_size(remote_source) or transfer.total_bytes
                    if transfer.destination.is_dir():
                        local_dest = transfer.destination / Path(remote_source).name
                    else:
                        local_dest = transfer.destination
                    os.makedirs(local_dest.parent, exist_ok=True)
                    success = sftp.download_file(
                        remote_source,
                        str(local_dest),
                        callback=lambda transferred, total=None: transfer.update_progress(transferred)
                    )
            else:
                raise Exception("Unsupported SFTP transfer direction")
        finally:
            sftp.disconnect()
            
        if not success:
            raise Exception("SFTP transfer failed")
        
    def _upload_directory_sftp(self, sftp_client, local_dir, remote_base, callback=None):
        """Upload directory recursively via SFTP"""
        try:
            local_dir = Path(local_dir)
            remote_base = remote_base.rstrip("/") if remote_base else ""
            
            # Normalize remote_base to POSIX path
            remote_base = remote_base.replace("\\", "/")
            
            for root, dirs, files in os.walk(local_dir):
                root_path = Path(root)
                rel_path = root_path.relative_to(local_dir.parent)
                
                # Convert Windows path to POSIX path for SFTP
                rel_path_str = str(rel_path).replace("\\", "/")
                
                if remote_base:
                    remote_dir = posixpath.join(remote_base, rel_path_str)
                else:
                    remote_dir = rel_path_str
                
                # Ensure remote directory exists
                if not sftp_client._ensure_remote_dir_exists(remote_dir):
                    return False
                
                # Upload files
                for file in files:
                    local_file = root_path / file
                    # Use posixpath.join for SFTP paths
                    remote_file = posixpath.join(remote_dir, file)
                    if not sftp_client.upload_file(str(local_file), remote_file, callback=callback):
                        return False
                        
            return True
        except Exception as e:
            return False
            
    def _download_directory_sftp(self, sftp_client, remote_dir, local_base, callback=None):
        """Download directory recursively via SFTP"""
        try:
            local_base = Path(local_base)
            
            # Normalize remote path to POSIX
            remote_dir = remote_dir.rstrip("/").replace("\\", "/")
            remote_dir_name = posixpath.basename(remote_dir)
            local_dest = local_base / remote_dir_name
            local_dest.mkdir(parents=True, exist_ok=True)
            
            # Get list of files and directories
            def download_recursive(remote_path, local_path):
                try:
                    items = sftp_client.sftp_client.listdir_attr(remote_path)
                    for item in items:
                        remote_item = posixpath.join(remote_path, item.filename)
                        local_item = local_path / item.filename
                        
                        if item.st_mode & 0o40000:  # Directory
                            local_item.mkdir(exist_ok=True)
                            download_recursive(remote_item, local_item)
                        else:  # File
                            sftp_client.download_file(remote_item, str(local_item), callback=callback)
                except Exception:
                    pass
                    
            download_recursive(remote_dir, local_dest)
            return True
        except Exception as e:
            return False
            
    def _get_directory_size_sftp(self, sftp_client, remote_dir):
        """Get total size of remote directory"""
        try:
            total_size = 0
            
            # Normalize remote path
            remote_dir = remote_dir.rstrip("/").replace("\\", "/")
            
            def get_size_recursive(path):
                nonlocal total_size
                try:
                    items = sftp_client.sftp_client.listdir_attr(path)
                    for item in items:
                        item_path = posixpath.join(path, item.filename)
                        if item.st_mode & 0o40000:  # Directory
                            get_size_recursive(item_path)
                        else:  # File
                            total_size += item.st_size
                except:
                    pass
                    
            get_size_recursive(remote_dir)
            return total_size
        except:
            return 0
        
    def _transfer_smb(self, transfer):
        """Transfer using SMB"""
        share = transfer.share
        if not share:
            raise Exception("SMB transfer missing share metadata")
        smb = SMBShare(share)
        if not smb.connect(share.host, share.username, share.password):
            raise Exception("Unable to connect to SMB host")

        try:
            if os.name == 'nt':
                remote_root = Path(f"\\\\{share.host}\\{share.share_name}")
            else:
                remote_root = Path(smb.mount_point or f"/mnt/{share.share_name}")

            if share.remote_path:
                remote_dest = remote_root / Path(share.remote_path)
            else:
                remote_dest = remote_root / transfer.source.name

            if transfer.source and transfer.source.is_file():
                remote_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(transfer.source), str(remote_dest))
            elif transfer.source and transfer.source.is_dir():
                if remote_dest.exists():
                    shutil.rmtree(str(remote_dest))
                shutil.copytree(str(transfer.source), str(remote_dest))
            else:
                raise Exception("SMB source path is invalid")
        finally:
            smb.disconnect()
        
    def get_transfer_status(self, transfer_id):
        """Get status of transfer"""
        transfer = self.transfers.get(transfer_id)
        if transfer:
            return {
                'status': transfer.status.value,
                'progress': transfer.progress,
                'bytes_transferred': transfer.bytes_transferred,
                'total_bytes': transfer.total_bytes,
                'speed': transfer.speed,
                'eta': transfer.eta,
                'error': transfer.error_message
            }
        return None
        
    def pause_transfer(self, transfer_id):
        """Pause a transfer"""
        transfer = self.transfers.get(transfer_id)
        if transfer:
            transfer.status = TransferStatus.PAUSED
            return True
        return False
        
    def resume_transfer(self, transfer_id):
        """Resume a paused transfer"""
        transfer = self.transfers.get(transfer_id)
        if transfer and transfer.status == TransferStatus.PAUSED:
            transfer.status = TransferStatus.TRANSFERRING
            return True
        return False
        
    def cancel_transfer(self, transfer_id):
        """Cancel a transfer"""
        transfer = self.transfers.get(transfer_id)
        if transfer:
            transfer.status = TransferStatus.CANCELLED
            return True
        return False


class QuickSetupWizard:
    """Interactive wizard for setting up file sharing in 5 easy steps"""
    
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.result = None
        
        self.colors = {
            "bg": "#1e1e2e",
            "card": "#313244",
            "accent": "#89dceb",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "danger": "#f38ba8",
            "info": "#89b4fa",
            "text": "#cdd6f4",
            "text_muted": "#6c7086"
        }
        
        self.setup_wizard_ui()
        
    def setup_wizard_ui(self):
        """Create wizard window"""
        self.wizard_window = tk.Toplevel(self.parent)
        self.wizard_window.title("File Sharing Quick Setup Wizard")
        self.wizard_window.geometry("750x750")
        self.wizard_window.configure(bg=self.colors["bg"])
        
        self.scenario = tk.StringVar()
        self.path_var = tk.StringVar()
        self.share_name_var = tk.StringVar()
        self.remote_source_var = tk.StringVar()
        self.local_dest_var = tk.StringVar()
        self.target_host_var = tk.StringVar()
        self.smb_user_var = tk.StringVar()
        self.smb_pwd_var = tk.StringVar()
        self.ubuntu_ip_var = tk.StringVar()
        self.sftp_user_var = tk.StringVar()
        self.sftp_auth_var = tk.StringVar()
        self.remote_path_var = tk.StringVar()
        self.auth_method = tk.StringVar(value="password")
        self.compress_var = tk.BooleanVar(value=True)
        self.encrypt_var = tk.BooleanVar(value=True)
        self.verify_var = tk.BooleanVar(value=True)
        self.readonly_var = tk.BooleanVar(value=False)
        
        # Title
        title_frame = tk.Frame(self.wizard_window, bg=self.colors["card"])
        title_frame.pack(fill="x", padx=20, pady=20)
        tk.Label(title_frame, text="🚀 Quick Setup Wizard", font=("Segoe UI", 20, "bold"),
                bg=self.colors["card"], fg=self.colors["success"]).pack(anchor="w")
        tk.Label(title_frame, text="Get started with file sharing in 5 easy steps",
                font=("Segoe UI", 11), bg=self.colors["card"], fg=self.colors["text_muted"]).pack(anchor="w")
        
        # Scrollable content area
        canvas_frame = tk.Frame(self.wizard_window, bg=self.colors["bg"])
        canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["bg"])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Set content_frame to be the scrollable_frame
        self.content_frame = self.scrollable_frame
        
        # Button frame at bottom (fixed position)
        self.button_frame = tk.Frame(self.wizard_window, bg=self.colors["bg"])
        self.button_frame.pack(fill="x", padx=20, pady=20)
        
        self.step = 1
        self.data = {}
        self.show_step_1()
        
    def clear_content(self):
        """Clear content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        # Clear buttons too
        for widget in self.button_frame.winfo_children():
            widget.destroy()
            
    def show_step_1(self):
        """Step 1: Choose sharing scenario"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="Step 1 of 5: Choose Your Scenario",
                font=("Segoe UI", 14, "bold"), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=10)
        
        tk.Label(self.content_frame, text="What is your file sharing scenario?",
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(0, 15))
        
        self.scenario = tk.StringVar()
        
        scenarios = [
            ("💻 Windows to Windows (SMB)", "win2win"),
            ("🐧 Windows to Ubuntu/Linux (SSH/SFTP)", "win2ubuntu"),
            ("🐧 Ubuntu/Linux to Windows (SSH/SFTP)", "ubuntu2win"),
            ("🔄 Two-way Sync", "sync"),
            ("📡 Advanced Custom Setup", "custom")
        ]
        
        for text, value in scenarios:
            tk.Radiobutton(self.content_frame, text=text, variable=self.scenario, value=value,
                          bg=self.colors["bg"], fg=self.colors["text"], font=("Segoe UI", 11),
                          selectcolor=self.colors["card"]).pack(anchor="w", pady=8, padx=20)
        
        # Button frame
        tk.Button(self.button_frame, text="Cancel", command=self.wizard_window.destroy,
                 bg=self.colors["text_muted"], fg="white").pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Next →", command=self.next_step,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        
    def show_step_2(self):
        """Step 2: Select folder to share"""
        scenario = self.data.get('scenario')
        self.clear_content()
        
        if scenario == 'ubuntu2win':
            tk.Label(self.content_frame, text="Step 2 of 5: Choose Ubuntu Source and Windows Destination",
                    font=("Segoe UI", 14, "bold"), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=10)
            tk.Label(self.content_frame, text="Enter the source path on Ubuntu/Linux and the local Windows destination folder:",
                    font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(0, 15))

            source_frame = tk.Frame(self.content_frame, bg=self.colors["card"])
            source_frame.pack(fill="x", pady=10)
            tk.Label(source_frame, text="Ubuntu Source Path:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
            self.remote_source_var = tk.StringVar()
            tk.Entry(source_frame, textvariable=self.remote_source_var, bg=self.colors["bg"],
                    fg=self.colors["text"], font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, padx=10, pady=10)

            dest_frame = tk.Frame(self.content_frame, bg=self.colors["card"])
            dest_frame.pack(fill="x", pady=10)
            tk.Label(dest_frame, text="Local Destination Folder:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
            self.local_dest_var = tk.StringVar()
            tk.Entry(dest_frame, textvariable=self.local_dest_var, bg=self.colors["bg"],
                    fg=self.colors["text"], font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, padx=10, pady=10)
            tk.Button(dest_frame, text="📁 Browse", command=self._browse_destination,
                     bg=self.colors["accent"], fg="#000000", font=("Segoe UI", 9, "bold")).pack(side="right", padx=10, pady=10)
        else:
            tk.Label(self.content_frame, text="Step 2 of 5: Choose Folder to Share",
                    font=("Segoe UI", 14, "bold"), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=10)
            tk.Label(self.content_frame, text="Select a folder on your computer to share:",
                    font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(0, 15))
            
            path_frame = tk.Frame(self.content_frame, bg=self.colors["card"])
            path_frame.pack(fill="x", pady=10)
            
            self.path_var = tk.StringVar()
            tk.Entry(path_frame, textvariable=self.path_var, bg=self.colors["bg"],
                    fg=self.colors["text"], font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, padx=10, pady=10)
            tk.Button(path_frame, text="📁 Browse", command=self._browse_folder,
                     bg=self.colors["accent"], fg="#000000", font=("Segoe UI", 9, "bold")).pack(side="right", padx=10, pady=10)
            
            # Share name
            name_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
            name_frame.pack(fill="x", pady=10)
            tk.Label(name_frame, text="Share Name:", font=("Segoe UI", 10),
                    bg=self.colors["bg"], fg=self.colors["text"]).pack(side="left")
            self.share_name_var = tk.StringVar()
            tk.Entry(name_frame, textvariable=self.share_name_var, bg=self.colors["bg"],
                    fg=self.colors["text"], font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, padx=10)
        
        tk.Button(self.button_frame, text="← Back", command=self.prev_step,
                 bg=self.colors["text_muted"], fg="white").pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Next →", command=self.next_step,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        
    def show_step_3(self):
        """Step 3: Configure connection settings"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="Step 3 of 5: Configure Connection",
                font=("Segoe UI", 14, "bold"), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=10)
        
        scenario = self.data.get('scenario')
        if scenario == 'win2win':
            self._config_smb()
        elif scenario in ('win2ubuntu', 'ubuntu2win'):
            self._config_sftp()
        else:
            tk.Label(self.content_frame, text="Configure your connection settings",
                    font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w")
        
        tk.Button(self.button_frame, text="← Back", command=self.prev_step,
                 bg=self.colors["text_muted"], fg="white").pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Next →", command=self.next_step,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        
    def _config_smb(self):
        """SMB Configuration for Windows-to-Windows"""
        info = tk.Frame(self.content_frame, bg=self.colors["card"])
        info.pack(fill="x", pady=10, padx=20)
        
        tk.Label(info, text="Windows to Windows (SMB)", font=("Segoe UI", 12, "bold"),
                bg=self.colors["card"], fg=self.colors["success"]).pack(anchor="w", padx=10, pady=(10, 5))
        
        info_text = """
1. Enter the IP address or hostname of the target Windows computer
2. Provide Windows credentials (username and password)
3. Share will be accessible via \\\\hostname\\sharename
4. Both computers must be on the same network
        """
        tk.Label(info, text=info_text, font=("Segoe UI", 10),
                bg=self.colors["card"], fg=self.colors["text"], justify="left").pack(anchor="w", padx=10, pady=10)
        
        # Input fields
        fields_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        fields_frame.pack(fill="x", pady=20)
        
        # Target hostname
        tk.Label(fields_frame, text="Target Computer IP/Hostname:",
                font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 5))
        self.target_host_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.target_host_var, bg=self.colors["card"],
                fg=self.colors["text"]).pack(fill="x", pady=(0, 15))
        
        # Username
        tk.Label(fields_frame, text="Windows Username:",
                font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 5))
        self.smb_user_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.smb_user_var, bg=self.colors["card"],
                fg=self.colors["text"]).pack(fill="x", pady=(0, 15))
        
        # Password
        tk.Label(fields_frame, text="Password:",
                font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 5))
        self.smb_pwd_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.smb_pwd_var, bg=self.colors["card"],
                fg=self.colors["text"], show="*").pack(fill="x")
        
    def _config_sftp(self):
        """SFTP Configuration for Windows/Linux transfers"""
        scenario = self.data.get('scenario')
        info = tk.Frame(self.content_frame, bg=self.colors["card"])
        info.pack(fill="x", pady=10, padx=20)
        
        title_text = "Windows to Ubuntu/Linux (SSH/SFTP)" if scenario == 'win2ubuntu' else "Ubuntu/Linux to Windows (SSH/SFTP)"
        tk.Label(info, text=title_text, font=("Segoe UI", 12, "bold"),
                bg=self.colors["card"], fg=self.colors["success"]).pack(anchor="w", padx=10, pady=(10, 5))
        
        if scenario == 'win2ubuntu':
            info_text = """
1. Enter the Ubuntu/Linux server IP address
2. Provide SSH login credentials or SSH key path
3. OpenSSH must be installed on Ubuntu (sudo apt install openssh-server)
4. Ensure port 22 (SSH) is accessible
            """
        else:
            info_text = """
1. Enter the Windows host IP address or hostname
2. Provide SSH login credentials or SSH key path
3. OpenSSH Server must be enabled on Windows
4. Ensure port 22 (SSH) is accessible
            """
        tk.Label(info, text=info_text, font=("Segoe UI", 10),
                bg=self.colors["card"], fg=self.colors["text"], justify="left").pack(anchor="w", padx=10, pady=10)
        
        # Input fields
        fields_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        fields_frame.pack(fill="x", pady=20)
        
        # Host/IP
        host_label = "Ubuntu/Linux Server IP:" if scenario == 'win2ubuntu' else "Windows Host/IP:"
        tk.Label(fields_frame, text=host_label,
                font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 5))
        self.ubuntu_ip_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.ubuntu_ip_var, bg=self.colors["card"],
                fg=self.colors["text"]).pack(fill="x", pady=(0, 15))
        
        # Username
        tk.Label(fields_frame, text="SSH Username:",
                font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 5))
        self.sftp_user_var = tk.StringVar()
        tk.Entry(fields_frame, textvariable=self.sftp_user_var, bg=self.colors["card"],
                fg=self.colors["text"]).pack(fill="x", pady=(0, 15))
        
        # Auth method
        auth_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        auth_frame.pack(fill="x", pady=10)
        
        self.auth_method = tk.StringVar(value="password")
        tk.Radiobutton(auth_frame, text="Password Authentication", variable=self.auth_method,
                      value="password", bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=5)
        tk.Radiobutton(auth_frame, text="SSH Key", variable=self.auth_method,
                      value="key", bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=5)
        
        # Remote path
        path_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        path_frame.pack(fill="x", pady=10)
        label_text = "Remote destination path on Ubuntu/Linux:" if scenario == 'win2ubuntu' else "Remote source path on Ubuntu/Linux:"
        tk.Label(path_frame, text=label_text,
                font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 5))
        self.remote_path_var = tk.StringVar()
        tk.Entry(path_frame, textvariable=self.remote_path_var, bg=self.colors["card"],
                fg=self.colors["text"]).pack(fill="x")
        
        # Password field
        pwd_frame = tk.Frame(self.content_frame, bg=self.colors["bg"])
        pwd_frame.pack(fill="x", pady=10)
        tk.Label(pwd_frame, text="Password/Key Path:",
                font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=(0, 5))
        self.sftp_auth_var = tk.StringVar()
        tk.Entry(pwd_frame, textvariable=self.sftp_auth_var, bg=self.colors["card"],
                fg=self.colors["text"], show="*").pack(fill="x")
        
    def show_step_4(self):
        """Step 4: Security options"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="Step 4 of 5: Security Options",
                font=("Segoe UI", 14, "bold"), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=10)
        
        tk.Label(self.content_frame, text="Configure security settings for your share:",
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(0, 15))
        
        # Checkboxes
        self.compress_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.content_frame, text="🗜️  Enable Compression (faster for large files)",
                      variable=self.compress_var, bg=self.colors["bg"], fg=self.colors["text"],
                      font=("Segoe UI", 10), selectcolor=self.colors["card"]).pack(anchor="w", pady=8, padx=20)
        
        self.encrypt_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.content_frame, text="🔐 Enable Encryption (secure transfers)",
                      variable=self.encrypt_var, bg=self.colors["bg"], fg=self.colors["text"],
                      font=("Segoe UI", 10), selectcolor=self.colors["card"]).pack(anchor="w", pady=8, padx=20)
        
        self.verify_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.content_frame, text="✓ Verify Checksums (prevent corruption)",
                      variable=self.verify_var, bg=self.colors["bg"], fg=self.colors["text"],
                      font=("Segoe UI", 10), selectcolor=self.colors["card"]).pack(anchor="w", pady=8, padx=20)
        
        self.readonly_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.content_frame, text="🔒 Read-Only Mode (prevent modifications)",
                      variable=self.readonly_var, bg=self.colors["bg"], fg=self.colors["text"],
                      font=("Segoe UI", 10), selectcolor=self.colors["card"]).pack(anchor="w", pady=8, padx=20)
        
        tk.Button(self.button_frame, text="← Back", command=self.prev_step,
                 bg=self.colors["text_muted"], fg="white").pack(side="left", padx=5)
        tk.Button(self.button_frame, text="Next →", command=self.next_step,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
        
    def show_step_5(self):
        """Step 5: Review and create"""
        self.clear_content()
        
        tk.Label(self.content_frame, text="Step 5 of 5: Review & Create",
                font=("Segoe UI", 14, "bold"), bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=10)
        
        tk.Label(self.content_frame, text="Review your settings:",
                font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(anchor="w", pady=(0, 15))
        
        # Summary
        summary_frame = tk.Frame(self.content_frame, bg=self.colors["card"])
        summary_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        summary_text = scrolledtext.ScrolledText(summary_frame, bg=self.colors["bg"],
                                               fg=self.colors["text"], font=("Consolas", 10),
                                               height=12)
        summary_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Generate summary
        scenario_names = {
            "win2win": "Windows to Windows (SMB)",
            "win2ubuntu": "Windows to Ubuntu/Linux (SSH/SFTP)",
            "sync": "Two-way Sync",
            "custom": "Custom Setup"
        }
        
        summary = f"""
╔══════════════════════════════════════════╗
║     FILE SHARING CONFIGURATION SUMMARY   ║
╚══════════════════════════════════════════╝

Scenario: {scenario_names.get(self.data.get('scenario'), 'Unknown')}

Folder to Share: {self.path_var.get()}
Share Name: {self.share_name_var.get()}

Security Settings:
  • Compression: {'✅ Enabled' if self.compress_var.get() else '❌ Disabled'}
  • Encryption: {'✅ Enabled' if self.encrypt_var.get() else '❌ Disabled'}
  • Verify Checksums: {'✅ Enabled' if self.verify_var.get() else '❌ Disabled'}
  • Read-Only Mode: {'✅ Enabled' if self.readonly_var.get() else '❌ Disabled'}

Next Steps After Creation:
1. The share will be configured with your settings
2. Remote computers can access the share via the provided address
3. Monitor transfer progress in the Transfer Queue tab
4. Check the transfer history for completed transfers

Click 'Create Share' to complete setup!
        """
        
        summary_text.insert("1.0", summary)
        summary_text.config(state="disabled")
        
        tk.Button(self.button_frame, text="← Back", command=self.prev_step,
                 bg=self.colors["text_muted"], fg="white").pack(side="left", padx=5)
        tk.Button(self.button_frame, text="✅ Create Share", command=self.finish,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="right", padx=5)
        
    def _browse_folder(self):
        """Browse for folder"""
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
            if hasattr(self, 'share_name_var') and not self.share_name_var.get():
                self.share_name_var.set(os.path.basename(path))

    def _browse_destination(self):
        """Browse for destination folder"""
        path = filedialog.askdirectory()
        if path:
            self.local_dest_var.set(path)

    def next_step(self):
        """Go to next step"""
        if self.step == 1:
            if not self.scenario.get():
                messagebox.showwarning("Warning", "Please select a scenario")
                return
            self.data['scenario'] = self.scenario.get()
            self.step = 2
            self.show_step_2()
        elif self.step == 2:
            scenario = self.data.get('scenario')
            if scenario == 'ubuntu2win':
                if not self.remote_source_var.get() or not self.local_dest_var.get():
                    messagebox.showwarning("Warning", "Please enter the remote Ubuntu source and local destination")
                    return
                self.data['remote_source'] = self.remote_source_var.get()
                self.data['destination_folder'] = self.local_dest_var.get()
                self.step = 3
                self.show_step_3()
                return
            if not self.path_var.get() or not self.share_name_var.get():
                messagebox.showwarning("Warning", "Please enter folder and share name")
                return
            if not os.path.exists(self.path_var.get()):
                messagebox.showerror("Error", "Folder does not exist")
                return
            self.data['path'] = self.path_var.get()
            self.data['share_name'] = self.share_name_var.get()
            self.step = 3
            self.show_step_3()
        elif self.step == 3:
            scenario = self.data.get('scenario')
            if scenario in ('win2win', 'win2ubuntu', 'ubuntu2win'):
                if scenario == 'win2win' and not getattr(self, 'target_host_var', tk.StringVar()).get():
                    messagebox.showwarning("Warning", "Please enter the target host")
                    return
                if scenario in ('win2ubuntu', 'ubuntu2win') and not getattr(self, 'ubuntu_ip_var', tk.StringVar()).get():
                    messagebox.showwarning("Warning", "Please enter the remote host")
                    return
                if scenario in ('win2ubuntu', 'ubuntu2win') and not getattr(self, 'sftp_user_var', tk.StringVar()).get():
                    messagebox.showwarning("Warning", "Please enter the SSH username")
                    return
                self.data['host'] = self.target_host_var.get() if scenario == 'win2win' else self.ubuntu_ip_var.get()
                self.data['username'] = self.smb_user_var.get() if scenario == 'win2win' else self.sftp_user_var.get()
                self.data['password'] = self.smb_pwd_var.get() if scenario == 'win2win' else self.sftp_auth_var.get()
                self.data['auth_method'] = 'password' if self.auth_method.get() == 'password' else 'key'
                self.data['remote_path'] = self.remote_path_var.get()
            self.step = 4
            self.show_step_4()
        elif self.step == 4:
            self.data['compress'] = self.compress_var.get()
            self.data['encrypt'] = self.encrypt_var.get()
            self.step = 5
            self.show_step_5()
            
    def prev_step(self):
        """Go to previous step"""
        if self.step > 1:
            self.step -= 1
            if self.step == 1:
                self.show_step_1()
            elif self.step == 2:
                self.show_step_2()
            elif self.step == 3:
                self.show_step_3()
            elif self.step == 4:
                self.show_step_4()
                
    def finish(self):
        """Complete setup"""
        self.result = self.data
        self.callback(self.result)
        self.wizard_window.destroy()


class FileSharingUI:
    """UI for Advanced File Sharing"""
    
    def __init__(self, parent, back_callback, dark_mode, log_callback, device, device_manager):
        self.parent = parent
        self.back = back_callback
        self.log = log_callback
        self.device = device
        self.device_manager = device_manager
        
        self.colors = {
            "bg": "#1e1e2e",
            "card": "#313244",
            "accent": "#89dceb",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "danger": "#f38ba8",
            "info": "#89b4fa",
            "text": "#cdd6f4",
            "text_muted": "#6c7086"
        }
        
        self.fsm = FileShareManager()
        self.setup_ui()
        self.load_saved_state()
        
        # Auto-update timers
        self.update_timer_id = None
        self.start_auto_updates()
        
    def setup_ui(self):
        """Setup the UI"""
        self.main_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header with Quick Setup
        header = tk.Frame(self.main_frame, bg=self.colors["card"])
        header.pack(fill="x", pady=20, padx=20)
        
        left_header = tk.Frame(header, bg=self.colors["card"])
        left_header.pack(side="left", fill="both", expand=True)
        
        tk.Label(left_header, text="📁 Advanced File Sharing", font=("Segoe UI", 24, "bold"),
                bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w")
        tk.Label(left_header, text=f"Share files between Windows and Ubuntu/Linux - All Features Available",
                font=("Segoe UI", 11), bg=self.colors["card"], fg=self.colors["text_muted"]).pack(anchor="w")
        
        # Quick Setup Button
        tk.Button(header, text="🚀 Quick Setup\nWizard", command=self._launch_wizard,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold"),
                 padx=15, pady=10, cursor="hand2").pack(side="right", padx=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Dashboard Tab
        self.setup_dashboard_tab(notebook)
        
        # Shares Tab
        self.setup_shares_tab(notebook)
        
        # Transfers Tab
        self.setup_transfers_tab(notebook)
        
        # Network Discovery Tab
        self.setup_network_tab(notebook)
        
        # File Management Tab
        self.setup_file_management_tab(notebook)
        
        # Device Stats Tab
        self.setup_device_stats_tab(notebook)
        
        # Permissions Tab
        self.setup_permissions_tab(notebook)
        
        # System Monitor Tab
        self.setup_system_monitor_tab(notebook)
        
        # Transfer Logs Tab
        self.setup_logs_tab(notebook)
        
        # Settings Tab
        self.setup_settings_tab(notebook)
        
        # Back button
        back_btn = tk.Button(self.main_frame, text="← Back to Dashboard", command=self.go_back,
                            bg=self.colors["text_muted"], fg="white", font=("Segoe UI", 11),
                            cursor="hand2", padx=20, pady=8)
        back_btn.pack(pady=20)
        
    def setup_dashboard_tab(self, notebook):
        """Setup main dashboard tab with overview of all features"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="🎯 Dashboard")
        
        # Main overview frame
        canvas = tk.Canvas(tab, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["bg"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        tk.Label(scrollable_frame, text="File Sharing Dashboard", font=("Segoe UI", 18, "bold"),
                bg=self.colors["bg"], fg=self.colors["accent"]).pack(pady=20, padx=20, anchor="w")
        
        # Quick Stats
        stats_frame = tk.LabelFrame(scrollable_frame, text="Quick Overview", bg=self.colors["card"],
                                   fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        stats_grid = tk.Frame(stats_frame, bg=self.colors["card"])
        stats_grid.pack(fill="x", padx=10, pady=10)
        
        # Stat items
        stat_items = [
            ("📂 Active Shares", self._get_share_count, "0"),
            ("📤 Active Transfers", self._get_active_transfers, "0"),
            ("✅ Completed", self._get_completed_transfers, "0"),
            ("❌ Failed", self._get_failed_transfers, "0")
        ]
        
        for i, (label, func, default) in enumerate(stat_items):
            stat_card = tk.Frame(stats_grid, bg=self.colors["bg"], relief="flat")
            stat_card.grid(row=0, column=i, sticky="nsew", padx=10, pady=5)
            
            tk.Label(stat_card, text=label, font=("Segoe UI", 10),
                    bg=self.colors["bg"], fg=self.colors["text_muted"]).pack(pady=(5, 0))
            tk.Label(stat_card, text=default, font=("Segoe UI", 16, "bold"),
                    bg=self.colors["bg"], fg=self.colors["accent"]).pack()
        
        for i in range(4):
            stats_grid.grid_columnconfigure(i, weight=1)
        
        # Features Overview
        features_frame = tk.LabelFrame(scrollable_frame, text="Available Features", bg=self.colors["card"],
                                      fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        features_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        features_text = tk.Text(features_frame, bg=self.colors["bg"], fg=self.colors["text"],
                               height=14, font=("Segoe UI", 10), relief="flat")
        features_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        features_content = """
✅ FILE SHARING SUITE - All Features Available

📂 CORE FEATURES:
   • Shares Tab - Create and manage file shares
   • Transfers Tab - Monitor and control file transfers
   • File Manager - Browse and select files
   
🌐 NETWORK & CONNECTIVITY:
   • Network Discovery - Scan and find devices on network
   • Settings - Configure connection parameters
   • Multiple Protocols - SMB, SSH/SFTP, HTTP, Custom Socket, NFS
   
📊 MONITORING & ANALYTICS:
   • Device Stats - View system resources and usage
   • System Monitor - Real-time process and transfer monitoring
   • Activity Logs - Complete history of all sharing activities
   
🔐 SECURITY & PERMISSIONS:
   • Permissions Tab - Manage access controls
   • Encryption - Secure your transfers
   • Compression - Optimize transfer speed
   • Read-Only Mode - Protect shared files
   • Checksum Verification - Ensure data integrity
   
🚀 QUICK SETUP:
   • Wizard - 5-step guided setup process
   • Templates - Pre-configured scenarios (Win2Win, Win2Ubuntu, etc.)
   • Auto-Configuration - Automatic protocol detection
   
📋 UTILITIES:
   • Export Logs - Save activity history
   • File Properties - View detailed file information
   • Transfer History - Track all completed transfers
   • Error Recovery - Automatic retry and resume capability

👤 ACCESS CONTROL:
   • User/Host Permission Management
   • Role-based Access (Read-Only, Read-Write, Admin)
   • IP Whitelist/Blacklist Support
        """
        
        features_text.insert("1.0", features_content)
        features_text.config(state="disabled")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _get_share_count(self):
        """Get number of active shares"""
        return len(self.fsm.shares)
    
    def _get_active_transfers(self):
        """Get number of active transfers"""
        return len([t for t in self.fsm.transfers.values() if t.status == TransferStatus.TRANSFERRING])
    
    def _get_completed_transfers(self):
        """Get number of completed transfers"""
        return len([t for t in self.fsm.transfers.values() if t.status == TransferStatus.COMPLETED])
    
    def _get_failed_transfers(self):
        """Get number of failed transfers"""
        return len([t for t in self.fsm.transfers.values() if t.status == TransferStatus.FAILED])
        
    def setup_shares_tab(self, notebook):
        """Setup shares management tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="📂 Shares")
        
        # Create share section
        create_frame = tk.LabelFrame(tab, text="Create New Share", bg=self.colors["card"],
                                    fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        create_frame.pack(fill="x", pady=10, padx=20)
        
        input_frame = tk.Frame(create_frame, bg=self.colors["card"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        # Path selection
        path_frame = tk.Frame(input_frame, bg=self.colors["card"])
        path_frame.pack(fill="x", pady=(0, 10))
        tk.Label(path_frame, text="Path:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.path_entry = tk.Entry(path_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(10, 5))
        tk.Button(path_frame, text="Browse", command=self._browse_path,
                 bg=self.colors["accent"], fg="#000000").pack(side="left")
        
        # Share name
        name_frame = tk.Frame(input_frame, bg=self.colors["card"])
        name_frame.pack(fill="x", pady=(0, 10))
        tk.Label(name_frame, text="Share Name:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.share_name_entry = tk.Entry(name_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.share_name_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # Protocol selection
        proto_frame = tk.Frame(input_frame, bg=self.colors["card"])
        proto_frame.pack(fill="x", pady=(0, 10))
        tk.Label(proto_frame, text="Protocol:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.protocol_var = tk.StringVar(value="Custom Socket")
        proto_combo = ttk.Combobox(proto_frame, textvariable=self.protocol_var,
                                  values=[p.value for p in ProtocolType], state="readonly")
        proto_combo.pack(side="left", padx=10, fill="x", expand=True)
        
        # Options
        options_frame = tk.Frame(input_frame, bg=self.colors["card"])
        options_frame.pack(fill="x", pady=(0, 10))
        
        self.read_only_var = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="Read-Only", variable=self.read_only_var,
                      bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=5)
        
        self.compress_var = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="Compress", variable=self.compress_var,
                      bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=5)
        
        self.encrypt_var = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="Encrypt", variable=self.encrypt_var,
                      bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=5)
        
        # Create button
        tk.Button(input_frame, text="✅ Create Share", command=self._create_share,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(fill="x")
        
        # Shares list
        list_frame = tk.LabelFrame(tab, text="Active Shares", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        list_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        columns = ("ID", "Name", "Path", "Protocol", "Size", "Status")
        self.shares_tree = ttk.Treeview(list_frame, columns=columns, height=12)
        
        for col in columns:
            self.shares_tree.heading(col, text=col)
            self.shares_tree.column(col, width=100)
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.shares_tree.yview)
        self.shares_tree.configure(yscrollcommand=scrollbar.set)
        
        self.shares_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        ctrl_frame = tk.Frame(tab, bg=self.colors["bg"])
        ctrl_frame.pack(fill="x", pady=10, padx=20)
        
        tk.Button(ctrl_frame, text="🔄 Refresh", command=self._refresh_shares,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="🗑️ Remove Share", command=self._remove_share,
                 bg=self.colors["danger"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="📊 Share Details", command=self._show_share_details,
                 bg=self.colors["info"], fg="#ffffff").pack(side="left", padx=5)
        
    def setup_transfers_tab(self, notebook):
        """Setup file transfers tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="📤 Transfers")
        
        # Transfer controls
        ctrl_frame = tk.Frame(tab, bg=self.colors["bg"])
        ctrl_frame.pack(fill="x", pady=10, padx=20)
        
        tk.Button(ctrl_frame, text="➕ New Transfer", command=self._start_transfer,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="⏸️ Pause", command=self._pause_transfer,
                 bg=self.colors["warning"], fg="#000000").pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="▶️ Resume", command=self._resume_transfer,
                 bg=self.colors["info"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(ctrl_frame, text="❌ Cancel", command=self._cancel_transfer,
                 bg=self.colors["danger"], fg="#ffffff").pack(side="left", padx=5)
        
        # Transfers list
        list_frame = tk.LabelFrame(tab, text="Transfer Queue", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        list_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        columns = ("ID", "File", "Size", "Progress", "Status", "Speed", "ETA")
        self.transfers_tree = ttk.Treeview(list_frame, columns=columns, height=10)
        
        # Configure column widths for proper display
        col_widths = {"ID": 50, "File": 150, "Size": 100, "Progress": 80, "Status": 80, "Speed": 100, "ETA": 80}
        
        for col in columns:
            self.transfers_tree.heading(col, text=col)
            self.transfers_tree.column(col, width=col_widths.get(col, 100))
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.transfers_tree.yview)
        self.transfers_tree.configure(yscrollcommand=scrollbar.set)
        
        self.transfers_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Transfer history
        hist_frame = tk.LabelFrame(tab, text="Transfer History", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        hist_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        self.history_text = scrolledtext.ScrolledText(hist_frame, bg=self.colors["bg"],
                                                     fg=self.colors["text"], height=8, font=("Consolas", 9))
        self.history_text.pack(fill="both", expand=True, padx=5, pady=5)
        self._refresh_transfer_list()
        
    def setup_network_tab(self, notebook):
        """Setup network discovery tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="🌐 Network")
        
        # Network range selection
        discovery_frame = tk.LabelFrame(tab, text="Network Discovery", bg=self.colors["card"],
                                       fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        discovery_frame.pack(fill="x", pady=10, padx=20)
        
        input_frame = tk.Frame(discovery_frame, bg=self.colors["card"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(input_frame, text="Network Range:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.network_var = tk.StringVar(value="192.168.1.0/24")
        tk.Entry(input_frame, textvariable=self.network_var, bg=self.colors["bg"],
                fg=self.colors["text"], width=20).pack(side="left", padx=10)
        
        tk.Button(input_frame, text="🔍 Scan Network", command=self._scan_network,
                 bg=self.colors["accent"], fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        
        # Devices list
        devices_frame = tk.LabelFrame(tab, text="Available Devices", bg=self.colors["card"],
                                     fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        devices_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        columns = ("IP Address", "Hostname", "Status")
        self.devices_tree = ttk.Treeview(devices_frame, columns=columns, height=12)
        
        for col in columns:
            self.devices_tree.heading(col, text=col)
            self.devices_tree.column(col, width=150)
        
        scrollbar = tk.Scrollbar(devices_frame, orient="vertical", command=self.devices_tree.yview)
        self.devices_tree.configure(yscrollcommand=scrollbar.set)
        
        self.devices_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
    def setup_settings_tab(self, notebook):
        """Setup settings tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="⚙️ Settings")
        
        # Connection settings
        conn_frame = tk.LabelFrame(tab, text="Default Connection Settings", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        conn_frame.pack(fill="x", pady=10, padx=20)
        
        settings_frame = tk.Frame(conn_frame, bg=self.colors["card"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        # Host
        host_frame = tk.Frame(settings_frame, bg=self.colors["card"])
        host_frame.pack(fill="x", pady=5)
        tk.Label(host_frame, text="Host/IP:", bg=self.colors["card"], fg=self.colors["text"], width=15).pack(side="left")
        self.host_entry = tk.Entry(host_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.host_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Port
        port_frame = tk.Frame(settings_frame, bg=self.colors["card"])
        port_frame.pack(fill="x", pady=5)
        tk.Label(port_frame, text="Port:", bg=self.colors["card"], fg=self.colors["text"], width=15).pack(side="left")
        self.port_entry = tk.Entry(port_frame, bg=self.colors["bg"], fg=self.colors["text"], width=10)
        self.port_entry.insert(0, "9999")
        self.port_entry.pack(side="left", padx=5)
        
        # Username
        user_frame = tk.Frame(settings_frame, bg=self.colors["card"])
        user_frame.pack(fill="x", pady=5)
        tk.Label(user_frame, text="Username:", bg=self.colors["card"], fg=self.colors["text"], width=15).pack(side="left")
        self.user_entry = tk.Entry(user_frame, bg=self.colors["bg"], fg=self.colors["text"])
        self.user_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Password
        pwd_frame = tk.Frame(settings_frame, bg=self.colors["card"])
        pwd_frame.pack(fill="x", pady=5)
        tk.Label(pwd_frame, text="Password:", bg=self.colors["card"], fg=self.colors["text"], width=15).pack(side="left")
        self.pwd_entry = tk.Entry(pwd_frame, bg=self.colors["bg"], fg=self.colors["text"], show="*")
        self.pwd_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Test connection button
        tk.Button(settings_frame, text="🔗 Test Connection", command=self._test_connection,
                 bg=self.colors["success"], fg="#ffffff").pack(fill="x", pady=10)
        
        # Transfer settings
        transfer_frame = tk.LabelFrame(tab, text="Transfer Settings", bg=self.colors["card"],
                                      fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        transfer_frame.pack(fill="x", pady=10, padx=20)
        
        settings_frame = tk.Frame(transfer_frame, bg=self.colors["card"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        # Buffer size
        buffer_frame = tk.Frame(settings_frame, bg=self.colors["card"])
        buffer_frame.pack(fill="x", pady=5)
        tk.Label(buffer_frame, text="Buffer Size (MB):", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.buffer_var = tk.StringVar(value="1")
        tk.Spinbox(buffer_frame, from_=1, to=100, textvariable=self.buffer_var, width=10).pack(side="left", padx=10)
        
        # Verify transfers
        self.verify_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Verify transfers (checksum)", variable=self.verify_var,
                      bg=self.colors["card"], fg=self.colors["text"]).pack(anchor="w", pady=5)
        
    def setup_file_management_tab(self, notebook):
        """Setup file management and browser tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="📂 File Manager")
        
        # File browser section
        browser_frame = tk.LabelFrame(tab, text="File Browser", bg=self.colors["card"],
                                     fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        browser_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        # Current path
        path_frame = tk.Frame(browser_frame, bg=self.colors["card"])
        path_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(path_frame, text="Current Path:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left")
        self.browser_path_var = tk.StringVar(value=str(Path.home()))
        tk.Entry(path_frame, textvariable=self.browser_path_var, bg=self.colors["bg"], 
                fg=self.colors["text"], state="readonly").pack(side="left", fill="x", expand=True, padx=10)
        tk.Button(path_frame, text="📂 Browse", command=self._browse_file_path,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        
        # File tree browser
        tree_frame = tk.Frame(browser_frame, bg=self.colors["bg"])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Name", "Type", "Size", "Modified")
        self.file_tree = ttk.Treeview(tree_frame, columns=columns, height=12)
        self.file_tree.heading("#0", text="Files")
        
        for col in columns:
            self.file_tree.heading(col, text=col)
            self.file_tree.column(col, width=100)
        
        scrollbar = tk.Scrollbar(tree_frame, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        self.file_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Refresh and select buttons
        button_frame = tk.Frame(browser_frame, bg=self.colors["card"])
        button_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(button_frame, text="🔄 Refresh", command=self._refresh_file_browser,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        tk.Button(button_frame, text="✅ Select for Share", command=self._select_file_for_share,
                 bg=self.colors["success"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(button_frame, text="📋 View Properties", command=self._show_file_properties,
                 bg=self.colors["info"], fg="#ffffff").pack(side="left", padx=5)
        
    def setup_device_stats_tab(self, notebook):
        """Setup device statistics tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="📊 Device Stats")
        
        # Device info frame
        info_frame = tk.LabelFrame(tab, text="Device Information", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        info_frame.pack(fill="x", pady=10, padx=20)
        
        self.device_info_text = tk.Text(info_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                        height=8, font=("Consolas", 9), relief="flat")
        self.device_info_text.pack(fill="both", expand=True, padx=10, pady=10)
        self._update_device_info()
        
        # Stats section
        stats_frame = tk.LabelFrame(tab, text="Resource Usage", bg=self.colors["card"],
                                   fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        stats_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        self.stats_text = tk.Text(stats_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                 height=12, font=("Consolas", 9), relief="flat")
        self.stats_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        button_frame = tk.Frame(stats_frame, bg=self.colors["card"])
        button_frame.pack(fill="x", padx=10, pady=10)
        tk.Button(button_frame, text="🔄 Refresh Stats", command=self._update_device_info,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        
    def setup_permissions_tab(self, notebook):
        """Setup permissions and access control tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="🔐 Permissions")
        
        # Access control section
        access_frame = tk.LabelFrame(tab, text="Share Permissions", bg=self.colors["card"],
                                    fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        access_frame.pack(fill="x", pady=10, padx=20)
        
        # Access list
        list_frame = tk.Frame(access_frame, bg=self.colors["card"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("User/Host", "Permission", "Access Type")
        self.access_tree = ttk.Treeview(list_frame, columns=columns, height=8)
        
        for col in columns:
            self.access_tree.heading(col, text=col)
            self.access_tree.column(col, width=120)
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.access_tree.yview)
        self.access_tree.configure(yscrollcommand=scrollbar.set)
        
        self.access_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Add access control
        add_frame = tk.Frame(access_frame, bg=self.colors["card"])
        add_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(add_frame, text="User/Host:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=5)
        self.access_user_entry = tk.Entry(add_frame, bg=self.colors["bg"], fg=self.colors["text"], width=15)
        self.access_user_entry.pack(side="left", padx=5)
        
        tk.Label(add_frame, text="Permission:", bg=self.colors["card"], fg=self.colors["text"]).pack(side="left", padx=5)
        self.perm_var = tk.StringVar(value="Read-Only")
        perm_combo = ttk.Combobox(add_frame, textvariable=self.perm_var,
                                 values=["Read-Only", "Read-Write", "Admin"], state="readonly", width=15)
        perm_combo.pack(side="left", padx=5)
        
        tk.Button(add_frame, text="➕ Add", command=self._add_access_control,
                 bg=self.colors["success"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(add_frame, text="🗑️ Remove", command=self._remove_access_control,
                 bg=self.colors["danger"], fg="#ffffff").pack(side="left", padx=5)
        
    def setup_system_monitor_tab(self, notebook):
        """Setup system monitoring and process tracking tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="⚙️ Monitor")
        
        # System monitor section
        monitor_frame = tk.LabelFrame(tab, text="System Monitor", bg=self.colors["card"],
                                     fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        monitor_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        self.monitor_text = tk.Text(monitor_frame, bg=self.colors["bg"], fg=self.colors["text"],
                                   height=15, font=("Consolas", 9), relief="flat")
        self.monitor_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        button_frame = tk.Frame(monitor_frame, bg=self.colors["card"])
        button_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(button_frame, text="🔄 Refresh", command=self._update_monitor,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        tk.Button(button_frame, text="🧹 Clear", command=lambda: self.monitor_text.delete("1.0", tk.END),
                 bg=self.colors["warning"], fg="#000000").pack(side="left", padx=5)
        
    def setup_logs_tab(self, notebook):
        """Setup sharing logs and activity history tab"""
        tab = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab, text="📋 Logs & History")
        
        # Logs section
        logs_frame = tk.LabelFrame(tab, text="Activity Log", bg=self.colors["card"],
                                  fg=self.colors["text"], font=("Segoe UI", 11, "bold"))
        logs_frame.pack(fill="both", expand=True, pady=10, padx=20)
        
        self.logs_text = scrolledtext.ScrolledText(logs_frame, bg=self.colors["bg"],
                                                  fg=self.colors["text"], height=16, 
                                                  font=("Consolas", 9))
        self.logs_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        button_frame = tk.Frame(logs_frame, bg=self.colors["card"])
        button_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(button_frame, text="📥 Export Logs", command=self._export_logs,
                 bg=self.colors["success"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(button_frame, text="🧹 Clear Logs", command=self._clear_logs,
                 bg=self.colors["danger"], fg="#ffffff").pack(side="left", padx=5)
        tk.Button(button_frame, text="🔄 Refresh", command=self._refresh_logs,
                 bg=self.colors["accent"], fg="#000000").pack(side="left", padx=5)
        
        self._refresh_logs()
        
    def _browse_path(self):
        """Browse for path"""
        path = filedialog.askdirectory(title="Select folder to share")
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            
    def _create_share(self):
        """Create a new share"""
        path = self.path_entry.get()
        share_name = self.share_name_entry.get()
        
        if not path or not share_name:
            messagebox.showerror("Error", "Please enter path and share name")
            return
            
        if not os.path.exists(path):
            messagebox.showerror("Error", "Path does not exist")
            return
            
        protocol_str = self.protocol_var.get()
        protocol = next(p for p in ProtocolType if p.value == protocol_str)
        
        share_id, share = self.fsm.create_share(path, share_name, protocol)
        share.read_only = self.read_only_var.get()
        share.compressed = self.compress_var.get()
        share.encrypted = self.encrypt_var.get()
        
        self.log(f"Share created: {share_name} (ID: {share_id})")
        self._refresh_shares()
        self.path_entry.delete(0, tk.END)
        self.share_name_entry.delete(0, tk.END)
        messagebox.showinfo("Success", f"Share created: {share_name}")
        
    def _refresh_shares(self):
        """Refresh shares list"""
        for item in self.shares_tree.get_children():
            self.shares_tree.delete(item)
            
        for share_id, share in self.fsm.shares.items():
            size_mb = share.size / (1024 * 1024)
            status = "🔒 RO" if share.read_only else "✅ RW"
            self.shares_tree.insert("", "end", text="",
                                  values=(share_id, share.share_name, str(share.path),
                                         share.protocol.value, f"{size_mb:.2f}MB", status))
            
    def _refresh_transfer_list(self):
        """Refresh transfer queue display"""
        for item in self.transfers_tree.get_children():
            self.transfers_tree.delete(item)

        for transfer_id, transfer in self.fsm.transfers.items():
            status = transfer.status.value
            progress = f"{transfer.progress:.1f}%"
            speed = f"{transfer.speed / (1024*1024):.2f} MB/s" if transfer.speed else "0.00 MB/s"
            eta = f"{transfer.eta}s" if transfer.eta else "--"
            file_name = transfer.source.name if transfer.source else (transfer.remote_path or "remote")
            
            # Format file size
            if transfer.total_bytes > 0:
                if transfer.total_bytes >= 1024*1024*1024:
                    size_str = f"{transfer.total_bytes / (1024*1024*1024):.2f} GB"
                elif transfer.total_bytes >= 1024*1024:
                    size_str = f"{transfer.total_bytes / (1024*1024):.2f} MB"
                elif transfer.total_bytes >= 1024:
                    size_str = f"{transfer.total_bytes / 1024:.2f} KB"
                else:
                    size_str = f"{transfer.total_bytes} B"
            else:
                size_str = "--"
            
            self.transfers_tree.insert("", "end", text="",
                                      values=(transfer_id, file_name, size_str, progress, status, speed, eta))

        self.history_text.delete("1.0", tk.END)
        for transfer in list(self.fsm.transfer_history):
            timestamp = transfer.start_time.strftime('%Y-%m-%d %H:%M:%S') if transfer.start_time else "Pending"
            # Format file size for history
            size_info = ""
            if transfer.total_bytes > 0:
                if transfer.total_bytes >= 1024*1024:
                    size_info = f" | Size: {transfer.total_bytes / (1024*1024):.2f} MB"
                else:
                    size_info = f" | Size: {transfer.total_bytes / 1024:.2f} KB"
            
            history_line = f"[{timestamp}] {transfer.transfer_id} {transfer.status.value} - {transfer.remote_path or transfer.source or transfer.destination}{size_info}"
            if transfer.error_message:
                history_line += f" | Error: {transfer.error_message}"
            self.history_text.insert(tk.END, history_line + "\n")
            self.history_text.see(tk.END)
            
    def _remove_share(self):
        """Remove selected share"""
        selection = self.shares_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a share")
            return
            
        share_id = int(self.shares_tree.item(selection[0])['values'][0])
        if self.fsm.remove_share(share_id):
            self.log(f"Share removed: {share_id}")
            self._refresh_shares()
            self.save_state()
        
    def _show_share_details(self):
        """Show details of selected share"""
        selection = self.shares_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a share")
            return
            
        share_id = int(self.shares_tree.item(selection[0])['values'][0])
        share = self.fsm.shares[share_id]
        
        details = f"Share Details\n\n"
        details += f"Name: {share.share_name}\n"
        details += f"Path: {share.path}\n"
        details += f"Protocol: {share.protocol.value}\n"
        details += f"Size: {share.size / (1024*1024):.2f} MB\n"
        details += f"Read-Only: {'Yes' if share.read_only else 'No'}\n"
        details += f"Compressed: {'Yes' if share.compressed else 'No'}\n"
        details += f"Encrypted: {'Yes' if share.encrypted else 'No'}\n"
        details += f"Created: {share.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        messagebox.showinfo("Share Details", details)
        
    def _start_transfer(self):
        """Start a new file transfer"""
        if not self.fsm.shares:
            messagebox.showwarning("Warning", "No shares available. Create a share first.")
            return

        dialog = tk.Toplevel(self.main_frame)
        dialog.title("Start File Transfer")
        dialog.geometry("620x420")
        dialog.configure(bg=self.colors["bg"])

        tk.Label(dialog, text="Select a share to transfer", font=("Segoe UI", 14, "bold"),
                 bg=self.colors["bg"], fg=self.colors["text"]).pack(anchor="w", pady=15, padx=20)

        share_var = tk.IntVar()
        for share_id, share in self.fsm.shares.items():
            label = f"{share_id} - {share.share_name} ({share.protocol.value})"
            tk.Radiobutton(dialog, text=label, variable=share_var, value=share_id,
                           bg=self.colors["bg"], fg=self.colors["text"], selectcolor=self.colors["card"],
                           font=("Segoe UI", 10)).pack(anchor="w", padx=30, pady=4)

        target_frame = tk.Frame(dialog, bg=self.colors["bg"])
        target_frame.pack(fill="x", pady=20, padx=20)

        tk.Label(target_frame, text="Local destination folder:",
                 bg=self.colors["bg"], fg=self.colors["text"], font=("Segoe UI", 10)).pack(anchor="w")
        dest_var = tk.StringVar()
        tk.Entry(target_frame, textvariable=dest_var, bg=self.colors["card"], fg=self.colors["text"]).pack(fill="x", pady=8)
        tk.Button(target_frame, text="📁 Browse", command=lambda: dest_var.set(filedialog.askdirectory()),
                 bg=self.colors["accent"], fg="#000000").pack(anchor="e")

        def start_selected_transfer():
            share_id = share_var.get()
            if not share_id:
                messagebox.showwarning("Warning", "Please select a share")
                return
            share = self.fsm.shares.get(share_id)
            if not share:
                messagebox.showerror("Error", "Selected share not found")
                return
            if share.protocol == ProtocolType.SSH_SFTP and share.direction == "ubuntu2win":
                if not dest_var.get():
                    messagebox.showwarning("Warning", "Please choose a local destination folder")
                    return
                transfer_id = self.fsm.initiate_transfer(share_id, None, Path(dest_var.get()))
            else:
                transfer_id = self.fsm.initiate_transfer(share_id, share.path, None)

            self._refresh_transfer_list()
            self.history_text.insert(tk.END, f"Started transfer {transfer_id} for share {share.share_name}\n")
            self.history_text.see(tk.END)
            dialog.destroy()

        tk.Button(dialog, text="Start Transfer", command=start_selected_transfer,
                 bg=self.colors["success"], fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(pady=10)

    def _pause_transfer(self):
        """Pause selected transfer"""
        selection = self.transfers_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a transfer")
            return
        transfer_id = int(self.transfers_tree.item(selection[0])['values'][0])
        if self.fsm.pause_transfer(transfer_id):
            self._refresh_transfer_list()

    def _resume_transfer(self):
        """Resume selected transfer"""
        selection = self.transfers_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a transfer")
            return
        transfer_id = int(self.transfers_tree.item(selection[0])['values'][0])
        if self.fsm.resume_transfer(transfer_id):
            self._refresh_transfer_list()

    def _cancel_transfer(self):
        """Cancel selected transfer"""
        selection = self.transfers_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a transfer")
            return
        transfer_id = int(self.transfers_tree.item(selection[0])['values'][0])
        if self.fsm.cancel_transfer(transfer_id):
            self._refresh_transfer_list()
        
    def _scan_network(self):
        """Scan network for devices"""
        network_range = self.network_var.get()
        self.log(f"Scanning network: {network_range}")
        
        def callback(ip):
            self.devices_tree.insert("", "end", text="",
                                    values=(ip, "Scanning...", "✅ Active"))
            
        devices = self.fsm.discovery.scan_network(network_range, callback)
        self.log(f"Found {len(devices)} active devices")
        
    def _test_connection(self):
        """Test connection to remote host"""
        host = self.host_entry.get()
        port = int(self.port_entry.get() or "9999")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                messagebox.showinfo("Success", f"Connected to {host}:{port}")
                self.log(f"Connection test successful: {host}:{port}")
            else:
                messagebox.showerror("Failed", f"Cannot connect to {host}:{port}")
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {str(e)}")
            
    def _browse_file_path(self):
        """Browse for file path"""
        path = filedialog.askdirectory(title="Select folder to browse")
        if path:
            self.browser_path_var.set(path)
            self._refresh_file_browser()
    
    def _refresh_file_browser(self):
        """Refresh file browser tree"""
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        try:
            current_path = Path(self.browser_path_var.get())
            for item in sorted(current_path.iterdir()):
                try:
                    size = item.stat().st_size if item.is_file() else "-"
                    modified = datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    file_type = "📁 Folder" if item.is_dir() else "📄 File"
                    self.file_tree.insert("", "end", text=item.name,
                                        values=(file_type, size, modified))
                except:
                    pass
        except Exception as e:
            messagebox.showerror("Error", f"Cannot browse path: {str(e)}")
    
    def _select_file_for_share(self):
        """Select file/folder for sharing"""
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file or folder")
            return
        
        item = self.file_tree.item(selection[0])
        file_name = item['text']
        current_path = Path(self.browser_path_var.get()) / file_name
        
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, str(current_path))
        self.share_name_entry.delete(0, tk.END)
        self.share_name_entry.insert(0, file_name)
        self.log(f"Selected for sharing: {current_path}")
    
    def _show_file_properties(self):
        """Show properties of selected file"""
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file or folder")
            return
        
        item = self.file_tree.item(selection[0])
        file_name = item['text']
        current_path = Path(self.browser_path_var.get()) / file_name
        
        try:
            stats = current_path.stat()
            properties = f"File Properties\n\n"
            properties += f"Name: {current_path.name}\n"
            properties += f"Path: {current_path}\n"
            properties += f"Type: {'Directory' if current_path.is_dir() else 'File'}\n"
            properties += f"Size: {stats.st_size / 1024:.2f} KB\n"
            properties += f"Created: {datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            properties += f"Modified: {datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            messagebox.showinfo("File Properties", properties)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot get properties: {str(e)}")
    
    def _update_device_info(self):
        """Update device information display"""
        self.device_info_text.config(state="normal")
        self.device_info_text.delete("1.0", tk.END)
        
        try:
            if self.device:
                info = f"Device: {self.device.name}\n"
                info += f"Device ID: {self.device.device_id}\n"
                info += f"RAM: {self.device.memory_size} MB\n"
                info += f"Storage: {self.device.storage_size} MB\n"
                info += f"CPU Cores: {self.device.cpu_cores}\n"
                info += f"Created: {self.device.created_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                stats = self.device_manager.get_device_stats(self.device)
                info += f"\nMemory Usage: {stats['used_memory']}/{stats['total_memory']} MB\n"
                info += f"Storage Usage: {stats['used_storage'] / (1024*1024):.2f}/{stats['total_storage']:.2f} MB\n"
                info += f"Free Memory: {stats['free_memory']} MB\n"
                info += f"Free Storage: {stats['free_storage'] / (1024*1024):.2f} MB\n"
                info += f"Total Processes: {stats['total_processes']}\n"
                
                self.device_info_text.insert(tk.END, info)
            else:
                self.device_info_text.insert(tk.END, "No device selected")
        except Exception as e:
            self.device_info_text.insert(tk.END, f"Error: {str(e)}")
        
        self.device_info_text.config(state="disabled")
    
    def _update_monitor(self):
        """Update system monitor information"""
        try:
            monitor_info = "=== SYSTEM MONITOR ===\n"
            monitor_info += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            if self.device:
                stats = self.device_manager.get_device_stats(self.device)
                monitor_info += "MEMORY:\n"
                monitor_info += f"  Used: {stats['used_memory']} MB\n"
                monitor_info += f"  Total: {stats['total_memory']} MB\n"
                monitor_info += f"  Free: {stats['free_memory']} MB\n"
                monitor_info += f"  Usage: {(stats['used_memory']/stats['total_memory']*100):.1f}%\n\n"
                
                monitor_info += "STORAGE:\n"
                storage_used = stats['used_storage'] / (1024*1024)
                storage_total = stats['total_storage']
                monitor_info += f"  Used: {storage_used:.2f} MB\n"
                monitor_info += f"  Total: {storage_total:.2f} MB\n"
                monitor_info += f"  Free: {stats['free_storage'] / (1024*1024):.2f} MB\n"
                monitor_info += f"  Usage: {(storage_used/storage_total*100):.1f}%\n\n"
                
                monitor_info += "PROCESSES:\n"
                monitor_info += f"  Total: {stats['total_processes']}\n\n"
                
                monitor_info += "TRANSFERS:\n"
                monitor_info += f"  Active: {len([t for t in self.fsm.transfers.values() if t.status == TransferStatus.TRANSFERRING])}\n"
                monitor_info += f"  Completed: {len([t for t in self.fsm.transfers.values() if t.status == TransferStatus.COMPLETED])}\n"
                monitor_info += f"  Failed: {len([t for t in self.fsm.transfers.values() if t.status == TransferStatus.FAILED])}\n"
            
            self.monitor_text.config(state="normal")
            self.monitor_text.delete("1.0", tk.END)
            self.monitor_text.insert(tk.END, monitor_info)
            self.monitor_text.config(state="disabled")
        except Exception as e:
            self.monitor_text.insert(tk.END, f"Error: {str(e)}")
    
    def _add_access_control(self):
        """Add access control entry"""
        user = self.access_user_entry.get()
        perm = self.perm_var.get()
        
        if not user:
            messagebox.showwarning("Warning", "Please enter user/host")
            return
        
        self.access_tree.insert("", "end", text="",
                               values=(user, perm, "Active"))
        self.access_user_entry.delete(0, tk.END)
        self.log(f"Added access control: {user} - {perm}")
    
    def _remove_access_control(self):
        """Remove selected access control entry"""
        selection = self.access_tree.selection()
        if selection:
            self.access_tree.delete(selection)
            self.log("Removed access control entry")
    
    def _export_logs(self):
        """Export logs to file"""
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.logs_text.get("1.0", tk.END))
                messagebox.showinfo("Success", f"Logs exported to {file_path}")
                self.log(f"Logs exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {str(e)}")
    
    def _clear_logs(self):
        """Clear activity logs"""
        if messagebox.askyesno("Confirm", "Clear all logs?"):
            self.logs_text.delete("1.0", tk.END)
            self.log("Logs cleared")
    
    def _refresh_logs(self):
        """Refresh activity logs display"""
        self.logs_text.config(state="normal")
        self.logs_text.delete("1.0", tk.END)
        
        # Add recent activities
        activities = []
        
        # Transfer history
        for transfer in list(self.fsm.transfer_history):
            timestamp = transfer.start_time.strftime('%Y-%m-%d %H:%M:%S') if transfer.start_time else "Pending"
            file_name = transfer.source.name if transfer.source else (transfer.remote_path or "Remote")
            activity = f"[{timestamp}] [TRANSFER] {transfer.status.value} - {file_name} (ID: {transfer.transfer_id})"
            activities.append(activity)
        
        # Share creation events
        for share_id, share in self.fsm.shares.items():
            activity = f"[{share.created_at.strftime('%Y-%m-%d %H:%M:%S')}] [SHARE] Created - {share.share_name} ({share.protocol.value})"
            activities.append(activity)
        
        # Display activities
        for activity in sorted(activities, reverse=True):
            self.logs_text.insert(tk.END, activity + "\n")
        
        self.logs_text.config(state="disabled")
            
    def _launch_wizard(self):
        """Launch the Quick Setup Wizard"""
        def on_wizard_complete(result):
            if result:
                share = self._create_share_from_wizard(result)
                if share:
                    messagebox.showinfo("Setup Complete", 
                        f"Share '{share.share_name}' has been configured!\n\n"
                        f"Scenario: {share.direction}\n"
                        f"Local path: {share.path}")
                    self.log(f"Wizard setup complete: {share.share_name}")
                    self._refresh_shares()
        
        wizard = QuickSetupWizard(self.main_frame, on_wizard_complete)

    def _create_share_from_wizard(self, result):
        """Create share metadata from wizard results"""
        scenario = result.get('scenario')
        protocol = ProtocolType.SSH_SFTP if scenario in ('win2ubuntu', 'ubuntu2win') else ProtocolType.SMB
        local_path = result.get('path') or result.get('destination_folder') or ''
        share_name = result.get('share_name') or f"wizard_share_{datetime.now().strftime('%H%M%S')}"
        if not local_path:
            return None

        share_id, share = self.fsm.create_share(
            local_path,
            share_name,
            protocol=protocol,
            host=result.get('host'),
            username=result.get('username'),
            password=result.get('password'),
            port=22 if protocol == ProtocolType.SSH_SFTP else 445,
            auth_method=result.get('auth_method', 'password'),
            direction=scenario,
            remote_path=result.get('remote_path') or result.get('remote_source') or ''
        )
        share.read_only = result.get('readonly', False)
        share.compressed = result.get('compress', False)
        share.encrypted = result.get('encrypt', False)

        if scenario == 'ubuntu2win' and result.get('destination_folder'):
            self.fsm.initiate_transfer(share_id, None, Path(result.get('destination_folder')))
        elif scenario in ('win2ubuntu', 'win2win'):
            # for win2ubuntu and win2win we can queue the transfer once share is created
            self.fsm.initiate_transfer(share_id, Path(local_path), None)

        self.save_state()
        return share
            
    def go_back(self):
        """Go back to dashboard"""
        self.save_state()
        self.main_frame.destroy()
        self.back()
        
    def save_state(self):
        """Save state to JSON files"""
        try:
            state_dir = Path.home() / ".minios_shares"
            state_dir.mkdir(exist_ok=True)
            
            # Save shares data
            shares_data = {}
            for share_id, share in self.fsm.shares.items():
                shares_data[str(share_id)] = {
                    'path': str(share.path),
                    'share_name': share.share_name,
                    'protocol': share.protocol.value,
                    'host': share.host,
                    'username': share.username,
                    'password': share.password,
                    'port': share.port,
                    'auth_method': share.auth_method,
                    'direction': share.direction,
                    'remote_path': share.remote_path,
                    'read_only': share.read_only,
                    'compressed': share.compressed,
                    'encrypted': share.encrypted
                }
            
            with open(state_dir / 'shares.json', 'w') as f:
                json.dump(shares_data, f, indent=2)
            
            # Save transfer history
            history_data = []
            for transfer in list(self.fsm.transfer_history):
                history_data.append({
                    'transfer_id': transfer.transfer_id,
                    'source': str(transfer.source) if transfer.source else None,
                    'destination': str(transfer.destination) if transfer.destination else None,
                    'status': transfer.status.value,
                    'progress': transfer.progress,
                    'bytes_transferred': transfer.bytes_transferred,
                    'total_bytes': transfer.total_bytes,
                    'speed': transfer.speed,
                    'eta': transfer.eta,
                    'error_message': transfer.error_message,
                    'start_time': transfer.start_time.isoformat() if transfer.start_time else None,
                    'end_time': transfer.end_time.isoformat() if transfer.end_time else None,
                    'direction': transfer.direction,
                    'remote_path': transfer.remote_path
                })
            
            with open(state_dir / 'transfer_history.json', 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            print(f"🔥 Failed to save state: {repr(e)}")
        
    def load_saved_state(self):
        """Load saved state from JSON files"""
        try:
            state_dir = Path.home() / ".minios_shares"
            if not state_dir.exists():
                return
            
            # Load shares
            shares_file = state_dir / 'shares.json'
            if shares_file.exists():
                with open(shares_file, 'r') as f:
                    shares_data = json.load(f)
                
                for share_id_str, share_info in shares_data.items():
                    try:
                        share_id = int(share_id_str)
                        protocol = ProtocolType.SSH_SFTP if 'SSH' in share_info['protocol'] else ProtocolType.SMB if 'SMB' in share_info['protocol'] else ProtocolType.CUSTOM
                        
                        share_obj, _ = self.fsm.create_share(
                            share_info['path'],
                            share_info['share_name'],
                            protocol=protocol,
                            host=share_info.get('host'),
                            username=share_info.get('username'),
                            password=share_info.get('password'),
                            port=share_info.get('port', 22),
                            auth_method=share_info.get('auth_method', 'password'),
                            direction=share_info.get('direction', 'win2ubuntu'),
                            remote_path=share_info.get('remote_path', '')
                        )
                        share_obj.read_only = share_info.get('read_only', False)
                        share_obj.compressed = share_info.get('compressed', False)
                        share_obj.encrypted = share_info.get('encrypted', False)
                    except Exception:
                        pass
            
            # Load transfer history (for display only, not active transfers)
            history_file = state_dir / 'transfer_history.json'
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                # Note: We don't restore actual transfers, only show history in the log
            
            # Refresh UI with loaded shares
            if hasattr(self, '_refresh_shares'):
                self._refresh_shares()
            if hasattr(self, '_refresh_transfer_list'):
                self._refresh_transfer_list()
                
        except Exception as e:
            print(f"🔥 Failed to load state: {repr(e)}")
        
    def start_auto_updates(self):
        """Start automatic updates for transfers and monitor"""
        def auto_update():
            try:
                if hasattr(self, '_refresh_transfer_list'):
                    self._refresh_transfer_list()
                if hasattr(self, '_update_monitor'):
                    self._update_monitor()
                self.update_timer_id = self.parent.after(5000, auto_update)
            except:
                pass
        
        self.update_timer_id = self.parent.after(5000, auto_update)
    
    def cleanup_timers(self):
        """Cleanup timers before closing"""
        if self.update_timer_id:
            try:
                self.parent.after_cancel(self.update_timer_id)
            except:
                pass
