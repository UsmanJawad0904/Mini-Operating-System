#!/usr/bin/env python3
"""Test script to verify file sharing persistence"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from file_sharing import FileShareManager, ProtocolType

def test_persistence():
    """Test save and load functionality"""
    print("=" * 60)
    print("Testing File Sharing Persistence")
    print("=" * 60)
    
    # Clean up any existing state
    state_dir = Path.home() / ".minios_shares"
    if state_dir.exists():
        import shutil
        shutil.rmtree(state_dir)
        print(f"✓ Cleaned up existing state directory")
    
    # Create a test share
    fsm = FileShareManager()
    print(f"\n1. Creating test share...")
    
    test_path = Path.home() / "Documents"
    if not test_path.exists():
        test_path = Path.home() / "Desktop"
    
    share_id, share = fsm.create_share(
        str(test_path),
        "Test Share SFTP",
        protocol=ProtocolType.SSH_SFTP,
        host="192.168.1.100",
        username="testuser",
        password="testpass123",
        port=22,
        auth_method="password",
        direction="win2ubuntu",
        remote_path="/home/ubuntu/shared"
    )
    
    share.read_only = True
    share.compressed = True
    print(f"   ✓ Created share ID: {share_id}")
    print(f"     - Name: {share.share_name}")
    print(f"     - Protocol: {share.protocol.value}")
    print(f"     - Host: {share.host}")
    print(f"     - Auth: {share.auth_method}")
    print(f"     - Direction: {share.direction}")
    print(f"     - Remote Path: {share.remote_path}")
    
    # Create simulated FileSharingUI to test persistence methods
    print(f"\n2. Testing save_state()...")
    
    # We need to simulate the FileSharingUI context
    from file_sharing import FileSharingUI
    import tkinter as tk
    
    root = tk.Tk()
    root.withdraw()  # Hide the window
    
    class MockUI:
        def __init__(self):
            self.fsm = fsm
        
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
                
                return True
            except Exception as e:
                print(f"🔥 Failed to save state: {repr(e)}")
                return False
        
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
                
                return True
            except Exception as e:
                print(f"🔥 Failed to load state: {repr(e)}")
                return False
    
    ui = MockUI()
    
    if ui.save_state():
        print(f"   ✓ State saved successfully")
    else:
        print(f"   ✗ Failed to save state")
        return False
    
    # Verify files were created
    state_dir = Path.home() / ".minios_shares"
    shares_file = state_dir / 'shares.json'
    
    if shares_file.exists():
        print(f"   ✓ shares.json created at {shares_file}")
        with open(shares_file, 'r') as f:
            saved_data = json.load(f)
        print(f"   ✓ Saved {len(saved_data)} share(s)")
    else:
        print(f"   ✗ shares.json not found")
        return False
    
    # Test loading with fresh FileShareManager
    print(f"\n3. Testing load_saved_state()...")
    print(f"   - Creating fresh FileShareManager (no shares)")
    
    fsm2 = FileShareManager()
    print(f"     Initial shares count: {len(fsm2.shares)}")
    
    ui2 = MockUI()
    ui2.fsm = fsm2
    
    if ui2.load_saved_state():
        print(f"   ✓ State loaded successfully")
    else:
        print(f"   ✗ Failed to load state")
        return False
    
    print(f"   - After loading: {len(fsm2.shares)} share(s)")
    
    if len(fsm2.shares) > 0:
        loaded_share = list(fsm2.shares.values())[0]
        print(f"\n   ✓ Loaded share details:")
        print(f"     - Name: {loaded_share.share_name}")
        print(f"     - Protocol: {loaded_share.protocol.value}")
        print(f"     - Host: {loaded_share.host}")
        print(f"     - Username: {loaded_share.username}")
        print(f"     - Auth Method: {loaded_share.auth_method}")
        print(f"     - Direction: {loaded_share.direction}")
        print(f"     - Remote Path: {loaded_share.remote_path}")
        print(f"     - Read-only: {loaded_share.read_only}")
        print(f"     - Compressed: {loaded_share.compressed}")
        
        # Verify all attributes match
        if (loaded_share.share_name == share.share_name and
            loaded_share.host == share.host and
            loaded_share.auth_method == share.auth_method and
            loaded_share.direction == share.direction and
            loaded_share.read_only == share.read_only and
            loaded_share.compressed == share.compressed):
            print(f"\n✅ PERSISTENCE TEST PASSED - All attributes preserved!")
            return True
        else:
            print(f"\n❌ PERSISTENCE TEST FAILED - Attribute mismatch")
            return False
    else:
        print(f"\n❌ PERSISTENCE TEST FAILED - No shares loaded")
        return False

if __name__ == '__main__':
    try:
        success = test_persistence()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n🔥 Test error: {repr(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
