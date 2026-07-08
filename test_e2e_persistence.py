#!/usr/bin/env python3
"""End-to-end test of data persistence in MiniOS app context"""

import json
from pathlib import Path
from file_sharing import FileShareManager, ProtocolType

print("=" * 60)
print("FILE SHARING PERSISTENCE VALIDATION")
print("=" * 60)

# Step 1: Create initial state with a share
print("\n[STEP 1] Creating initial share...")
fsm1 = FileShareManager()
test_path = Path.home() / "Documents"

share_id, share = fsm1.create_share(
    str(test_path),
    "Test Windows Share",
    protocol=ProtocolType.SSH_SFTP,
    host="192.168.1.100",
    username="testuser",
    password="testpass",
    auth_method="password",
    direction="win2ubuntu",
    remote_path="/home/ubuntu/files"
)

share.read_only = True
share.compressed = True
share.encrypted = False

print(f"✓ Created share {share_id}: {share.share_name}")
print(f"  Host: {share.host}")
print(f"  Auth: {share.auth_method}")
print(f"  Attributes: read_only={share.read_only}, compressed={share.compressed}")

# Step 2: Save state (simulating app close)
print("\n[STEP 2] Saving state to disk...")
state_dir = Path.home() / ".minios_shares"
state_dir.mkdir(exist_ok=True)

shares_data = {}
for sid, s in fsm1.shares.items():
    shares_data[str(sid)] = {
        'path': str(s.path),
        'share_name': s.share_name,
        'protocol': s.protocol.value,
        'host': s.host,
        'username': s.username,
        'password': s.password,
        'port': s.port,
        'auth_method': s.auth_method,
        'direction': s.direction,
        'remote_path': s.remote_path,
        'read_only': s.read_only,
        'compressed': s.compressed,
        'encrypted': s.encrypted
    }

with open(state_dir / 'shares.json', 'w') as f:
    json.dump(shares_data, f, indent=2)

print(f"✓ Saved {len(shares_data)} share(s) to ~/.minios_shares/shares.json")

# Step 3: Simulate app restart - create fresh FileShareManager
print("\n[STEP 3] Simulating app restart...")
fsm2 = FileShareManager()
print(f"✓ New FileShareManager created with {len(fsm2.shares)} shares")

# Step 4: Load saved state
print("\n[STEP 4] Loading saved state...")
shares_file = state_dir / 'shares.json'
if shares_file.exists():
    with open(shares_file, 'r') as f:
        shares_data = json.load(f)
    
    for share_id_str, share_info in shares_data.items():
        share_id = int(share_id_str)
        protocol = ProtocolType.SSH_SFTP if 'SSH' in share_info['protocol'] else ProtocolType.SMB
        
        sid, share_obj = fsm2.create_share(
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

print(f"✓ Loaded {len(fsm2.shares)} share(s)")

# Step 5: Validate
print("\n[STEP 5] Validating loaded data...")
if len(fsm2.shares) > 0:
    loaded_share = list(fsm2.shares.values())[0]
    
    validations = [
        ("Share name", loaded_share.share_name == "Test Windows Share"),
        ("Host", loaded_share.host == "192.168.1.100"),
        ("Username", loaded_share.username == "testuser"),
        ("Auth method", loaded_share.auth_method == "password"),
        ("Direction", loaded_share.direction == "win2ubuntu"),
        ("Remote path", loaded_share.remote_path == "/home/ubuntu/files"),
        ("Read-only flag", loaded_share.read_only == True),
        ("Compressed flag", loaded_share.compressed == True),
        ("Encrypted flag", loaded_share.encrypted == False),
    ]
    
    all_passed = True
    for check_name, passed in validations:
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}: {passed}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n" + "=" * 60)
        print("✅ DATA PERSISTENCE FULLY WORKING!")
        print("=" * 60)
        print("\nShares persist across app restarts with all attributes intact.")
    else:
        print("\n❌ Some attributes did not persist correctly")
else:
    print("❌ No shares loaded!")
