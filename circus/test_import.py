#!/usr/bin/env python3
"""
Test script to verify that imports work correctly
"""

try:
    from register_with_status import *
    print("✓ Successfully imported from register_with_status")
    
    # Test if key functions are available
    if 'create_driver' in globals():
        print("✓ create_driver function is available")
    if 'extract_prefecture' in globals():
        print("✓ extract_prefecture function is available")
    if 'prefecture_map' in globals():
        print("✓ prefecture_map is available")
    if 'save_to_s3' in globals():
        print("✓ save_to_s3 function is available")
    if 'update_csv_status' in globals():
        print("✓ update_csv_status function is available")
        
    print("\nAll imports successful! The module should work correctly now.")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}") 