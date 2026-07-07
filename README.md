# MiniOS v6.0 - Ultimate Edition 🐧

A comprehensive operating system simulator built with Python and Tkinter, featuring realistic OS concepts including process management, virtual memory, user permissions, inter-process communication, and system logging.

## 📋 Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [File Sharing](#file-sharing)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Advanced Features](#advanced-features)
- [Contribution & Branch Protection Policy](#contribution--branch-protection-policy)
- [License](#license)

## ✨ Features

### Core Operating System Components

#### 1. **Process Management** ⚙️
- Realistic process lifecycle with states: NEW, READY, RUNNING, WAITING, TERMINATED
- Process creation, termination, and monitoring
- Priority-based scheduling
- CPU time tracking and statistics
- Process resource allocation (memory, file descriptors)
- Parent-child process relationships

#### 2. **Virtual Memory & Paging** 💾
- Page table management with configurable page sizes (default: 4KB)
- Multiple page replacement algorithms:
  - **LRU** (Least Recently Used) - Default
  - **FIFO** (First In First Out)
  - **Random** replacement
- Physical frame allocation and management
- Swap disk simulation for page swapping
- Page fault detection and handling
- Memory utilization tracking and statistics

#### 3. **User & Permission System** 👥
- Unix-style user and group management
- File permissions with rwx model (read, write, execute)
- User authentication framework
- Group membership management
- Multi-level access control:
  - Owner permissions (rwx)
  - Group permissions (rwx)
  - Other permissions (rwx)
- Default system users (root, user) and groups

#### 4. **Inter-Process Communication (IPC)** 🔗
- **Pipes**: Named pipes for unidirectional communication
- **Message Queues**: Priority-based message queuing
- **Shared Memory**: Process-shared memory segments
- IPC resource tracking and management
- Message buffering with statistics

#### 5. **Device Management** 🖥️
- Create and manage virtual devices
- Persistent device storage with JSON
- Multi-device support with switching
- Device configuration and settings
- Hardware resource allocation per device

#### 6. **CPU Scheduling** ⚡
- Multiple scheduling algorithms:
  - FCFS (First Come First Served)
  - SJF (Shortest Job First)
  - Priority-based scheduling
- Process arrival time and burst time simulation
- Gantt chart visualization
- Scheduling statistics and analysis

#### 7. **File System** 📁
- Hierarchical file system structure
- File and directory management
- File metadata (creation time, size, permissions)
- Directory traversal and navigation
- File content management

#### 8. **Memory Management** 🧠
- Memory block allocation
- First Fit, Best Fit, Worst Fit algorithms
- Fragmentation analysis
- Memory statistics and visualization
- Dynamic memory allocation simulation

#### 9. **System Logging** 📋
- Syslog-style logging system
- Log levels: DEBUG, INFO, NOTICE, WARNING, ERROR, CRITICAL, ALERT, EMERGENCY
- Facility-based categorization
- Log filtering and search
- Log statistics and analysis
- Export logs to JSON

#### 10. **Terminal/Shell** 🖥️
- Ubuntu-style shell interface
- Built-in commands:
  - Navigation: `cd`, `pwd`
  - File operations: `ls`, `mkdir`, `touch`, `rm`
  - System info: `whoami`, `hostname`, `date`
  - Help: `help`, `clear`
- Command history with navigation
- Cross-platform compatibility (Windows/Linux/macOS)
- Command aliasing support

#### 11. **Advanced Features** 🚀
- Real-time process simulation
- Banker's Algorithm deadlock avoidance visualization
- Live performance monitoring
- Memory pressure simulation
- System metrics dashboard

#### 12. **File Sharing & Data Transfer** 📤
- **Cross-Platform Sharing**: Windows ↔ Linux/Ubuntu file transfer
- **Multiple Protocols**:
  - SMB (Samba) for Windows networks
  - SSH/SFTP for secure remote access
  - HTTP for web-based transfer
  - Custom Socket protocol for direct transfer
  - NFS for network file system access
- **Comprehensive Features**:
  - File browser with quick selection
  - Real-time transfer monitoring and progress tracking
  - Network device discovery and scanning
  - Permission-based access control (Read-Only, Read-Write, Admin)
  - Encryption and compression options
  - Checksum verification for data integrity
- **Management & Monitoring**:
  - Active share management
  - Transfer queue and history
  - System resource monitoring
  - Complete activity logging with export
  - Device statistics and performance tracking
- **Quick Setup Wizard**: 5-step guided configuration for different scenarios
- **Security**: Multiple authentication methods, encryption support, read-only mode

## 🔧 System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 512 MB
- **Disk Space**: 100 MB
- **OS**: Windows, macOS, or Linux

### Recommended
- **Python**: 3.9 or higher
- **RAM**: 2 GB
- **Display**: 1920x1080 or higher for optimal UI experience

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/MiniOS.git
cd MiniOS
```

### 2. Create Virtual Environment (Optional but Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python main.py
```

## 🚀 Quick Start

1. **Launch MiniOS**
   ```bash
   python main.py
   ```

2. **Create a Virtual Device**
   - Click "Device Manager"
   - Enter device name, memory (MB), and storage (MB)
   - Click "Create Device"

3. **Explore Components**
   - **Process Manager**: Create and manage processes
   - **Virtual Memory**: Simulate page replacement algorithms
   - **User Manager**: Create users and manage permissions
   - **IPC Manager**: Test inter-process communication
   - **System Logger**: View system events
   - **Shell**: Execute commands

## File Sharing

MiniOS includes a full cross-platform file transfer module that supports transfers between Windows and Ubuntu/Linux. When running MiniOS on Ubuntu, you can send files to Windows using either:

- **SMB (Samba)**: Recommended for local network transfers to Windows file shares.
- **SSH/SFTP**: Useful if Windows is running OpenSSH Server or another SFTP server.

### Send Files from Ubuntu to Windows

When MiniOS runs on Ubuntu, the recommended transfer path is SMB to a Windows shared folder. If Windows has OpenSSH Server enabled, you can also transfer files securely with SSH/SFTP.

#### Ubuntu → Windows using SMB

1. Install the required Ubuntu package:
   ```bash
   sudo apt update
   sudo apt install cifs-utils
   ```

2. On the Windows machine:
   - Enable File Sharing and Network Discovery.
   - Share a folder such as `Documents` or `SharedFiles`.
   - Note the Windows host IP and share name.
   - Ensure the Windows account has permission to access the share.

3. In MiniOS on Ubuntu:
   - Open **MiniOS** → **📤 File Sharing**
   - Choose **SMB (Samba)** as the protocol
   - Set **Host/IP** to the Windows machine address
   - Set **Share Name** to the Windows shared folder name
   - Enter the Windows username and password
   - Select the Ubuntu source file or folder to send
   - Optionally set a **Remote Path** inside the Windows share
   - Start the transfer and monitor progress

4. Verify the file in the Windows shared folder after transfer completes.

#### Ubuntu → Windows using SSH/SFTP

1. Enable OpenSSH Server on Windows using PowerShell as Administrator:
   ```powershell
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   Start-Service sshd
   Set-Service -Name sshd -StartupType Automatic
   ```

2. Confirm the Windows SSH connection from Ubuntu:
   ```bash
   ssh username@192.168.1.50
   ```

3. In MiniOS on Ubuntu:
   - Open **MiniOS** → **📤 File Sharing**
   - Choose **SSH/SFTP** as the protocol
   - Set **Host/IP** to the Windows machine address
   - Enter the Windows username and password (or SSH key path)
   - Set the Windows destination path, for example `C:\Users\YourName\Downloads`
   - Select the Ubuntu source file or folder
   - Start the transfer and monitor progress

### Ubuntu to Windows Transfer Example

- Ubuntu source path: `/home/ubuntu/example.txt`
- Windows host IP: `192.168.1.50`
- Windows shared folder: `SharedDocs`
- Windows destination path: `C:\Users\YourName\Downloads`

Use the MiniOS File Sharing UI to configure the share and begin transfer. Once completed, the file will appear in the Windows destination folder.

### Important Notes

- `paramiko` is already included in `requirements.txt` for SSH/SFTP support.
- `tkinter` is built into Python and is used by the MiniOS UI.
- If you prefer not to use MiniOS for SMB copies, you can also mount the Windows share on Ubuntu with `mount.cifs` and copy files manually.

## 📁 Project Structure

```
MiniOS/
├── main.py                      # Main application entry point
├── device_manager.py            # Virtual device management
├── process_manager.py           # Process lifecycle and management
├── scheduler.py                 # CPU scheduling algorithms
├── memory.py                    # Memory management
├── filesystem.py                # File system simulation
├── virtual_memory.py            # Virtual memory & paging
├── user_permissions.py          # User & permission management
├── ipc_manager.py               # Inter-process communication
├── system_logger.py             # System logging
├── file_sharing.py              # Advanced file sharing & transfer
├── shell.py                     # Terminal/shell interface
├── adv_features.py              # Advanced features & simulations
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── CHANGES.md                   # Change log
└── MiniOS_Devices/              # Device storage directory
    ├── config.json              # Global configuration
    └── devices/                 # Individual device data
        └── *.json               # Device state files
```



## 🏛️ Architecture

### System Layers

```
┌─────────────────────────────────────────────┐
│             GUI Layer (Tkinter)             │
├─────────────────────────────────────────────┤
│              Application Layer              │
│       (All manager & service modules)       │
├─────────────────────────────────────────────┤
│                Core Services                │
│   (Process, Memory, IPC, Logging, Sharing)  │
├─────────────────────────────────────────────┤
│            Device & Network Layer           │
│       (Virtual Device & File Transfer)      │
├─────────────────────────────────────────────┤
│            Storage & Persistence            │
│     (Device Storage, JSON, File System)     │
└─────────────────────────────────────────────┘
```

### Data Flow
1. **User Input** → GUI Layer
2. **Command Processing** → Application Layer
3. **Resource Management** → Core Services
4. **Persistence** → Device Storage (JSON)



## 🚀 Advanced Features

### 1. CPU Scheduling Simulation
- Compare different scheduling algorithms
- Visualize Gantt charts
- Calculate average waiting/turnaround time
- Analyze scheduling efficiency

### 2. Banker's Algorithm
- Deadlock avoidance
- Resource allocation safety analysis
- Multiple resource types
- Process safety state verification

### 3. Memory Visualization
- Real-time memory usage tracking
- Fragmentation visualization
- Memory block allocation display
- Performance metrics

### 4. Performance Monitoring
- CPU utilization tracking
- Memory pressure simulation
- I/O operation monitoring
- Real-time statistics dashboard



## 📊 Performance Considerations

- **Memory**: Efficient use of Python data structures
- **CPU**: Optimized scheduling algorithms
- **Storage**: Persistent JSON-based device storage
- **UI**: Responsive Tkinter interface with threading support

## 🐛 Known Limitations

- Virtual memory simulation doesn't use actual disk I/O
- Shell commands are simulated, not executed on actual OS
- File system is simulated, not real filesystem
- Network simulation is not included in current version
- Single-threaded main event loop (uses threading for background tasks)

## 🤝 Contribution & Branch Protection Policy

To maintain code quality and repository stability, direct pushes to the `main` branch are disabled. All contributors must follow the branch-based workflow outlined below:

### 🛡️ Repository Constraints
*   **No Direct Pushes**: Direct uploads or pushes to `main` are restricted for all users, including repository owners.
*   **Pull Requests (PR)**: All modifications must be submitted via a PR targeting `main`.
*   **Mandatory Review**: Each Pull Request requires at least **1 approval** from a designated collaborator before merging. Code authors cannot approve their own submissions.
*   **Review Ownership**: Required approvals are defined and enforced by the repository's `CODEOWNERS` configuration.

---

### 🚀 Developer Workflow

#### 1. Clone the Repository
Initialize your local environment by cloning the repository and navigating into the project directory:
```bash
git clone https://github.com/itsusman0904-spec/Mini-Operating-System.git
cd Mini-Operating-System
```

#### 2. Create a Working Branch
Do not commit directly to the `main` branch. Create and switch to a separate branch for your feature or bug fix:
```bash
git checkout -b feature/your-feature-name
```

#### 3. Commit Changes
Implement your changes, stage the files, and commit them with a descriptive commit message:
```bash
git add .
git commit -m "Brief description of changes"
```

#### 4. Push to GitHub
Publish your local branch to the remote repository:
```bash
git push origin feature/your-feature-name
```

#### 5. Submit a Pull Request
1. Open the [GitHub Repository](https://github.com/itsusman0904-spec/Mini-Operating-System) in your browser.
2. Click the **"Compare & pull request"** button displayed for your recently pushed branch.
3. Review your changes and submit the Pull Request.
4. Request a review from the designated collaborator on the right-hand panel. Once approved, the branch will be eligible for merging.

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Inspired by real operating systems concepts
- Built with Python and Tkinter
- Thanks to all contributors and users

---

## 📚 Additional Resources

### Learning Materials
- [Operating Systems Concepts](https://www.cs.uic.edu/~jbell/CourseNotes/OperatingSystems/)
- [Python Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
- [Linux Kernel Documentation](https://www.kernel.org/doc/)

### Related Projects
- [xv6 Operating System](https://github.com/mit-pdos/xv6-public)
- [OSDev.org](https://wiki.osdev.org/)

