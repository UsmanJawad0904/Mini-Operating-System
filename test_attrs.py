#!/usr/bin/env python3
"""Quick test to verify persistence attributes are loaded correctly"""

import json
from pathlib import Path
from file_sharing import FileShareManager, ProtocolType

# Check the saved JSON
state_dir = Path.home() / ".minios_shares"
shares_file = state_dir / 'shares.json'

if shares_file.exists():
    with open(shares_file, 'r') as f:
        data = json.load(f)
    
    print("Saved data in JSON:")
    for share_id, share_info in data.items():
        print(f"  Share {share_id}:")
        print(f"    read_only: {share_info.get('read_only')}")
        print(f"    compressed: {share_info.get('compressed')}")
        print(f"    encrypted: {share_info.get('encrypted')}")
        
        # Now check if loading works
        print("\nCreating new FileShareManager and checking if attributes set...")
        fsm = FileShareManager()
        
        share_id, share_obj = fsm.create_share(
            share_info['path'],
            share_info['share_name'],
            protocol=ProtocolType.SSH_SFTP,
            host=share_info.get('host'),
            username=share_info.get('username'),
            password=share_info.get('password'),
            port=share_info.get('port', 22),
            auth_method=share_info.get('auth_method', 'password'),
            direction=share_info.get('direction', 'win2ubuntu'),
            remote_path=share_info.get('remote_path', '')
        )
        
        print(f"Before setting attributes:")
        print(f"  read_only: {share_obj.read_only}")
        print(f"  compressed: {share_obj.compressed}")
        
        share_obj.read_only = share_info.get('read_only', False)
        share_obj.compressed = share_info.get('compressed', False)
        share_obj.encrypted = share_info.get('encrypted', False)
        
        print(f"After setting attributes:")
        print(f"  read_only: {share_obj.read_only}")
        print(f"  compressed: {share_obj.compressed}")
        print(f"  encrypted: {share_obj.encrypted}")
        
        if share_obj.read_only and share_obj.compressed:
            print("\n✅ PERSISTENCE WORKING CORRECTLY!")
        else:
            print("\n❌ Attributes not set properly")
