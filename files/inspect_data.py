#!/usr/bin/env python3
"""
Debug script to inspect your spelling_bee_raw.json file
This helps figure out what format your data is in
"""

import json
from pathlib import Path

def inspect_data():
    """Inspect the structure of the raw data file."""
    
    raw_file = Path('spelling_bee_raw.json')
    
    if not raw_file.exists():
        print("❌ spelling_bee_raw.json not found!")
        return
    
    print("🔍 Inspecting spelling_bee_raw.json...\n")
    
    with open(raw_file, 'r') as f:
        content = f.read()
    
    print("=" * 70)
    print("FILE CONTENTS (first 500 characters):")
    print("=" * 70)
    print(content[:500])
    print("...\n")
    
    # Try to parse as JSON
    try:
        data = json.loads(content)
        
        print("=" * 70)
        print("DATA STRUCTURE:")
        print("=" * 70)
        print(f"Type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
            print("\nFirst few key-value pairs:")
            for i, (key, value) in enumerate(data.items()):
                if i >= 3:
                    break
                print(f"\n{key}:")
                print(f"  Type: {type(value)}")
                if isinstance(value, str):
                    print(f"  Value: {value[:100]}")
                elif isinstance(value, (list, dict)):
                    print(f"  Value: {str(value)[:100]}...")
                else:
                    print(f"  Value: {value}")
        
        elif isinstance(data, list):
            print(f"Length: {len(data)}")
            if len(data) > 0:
                print(f"\nFirst item type: {type(data[0])}")
                print(f"First item: {str(data[0])[:200]}...")
        
        else:
            print(f"Unexpected data type: {type(data)}")
        
        print("\n" + "=" * 70)
        print("RECOMMENDATIONS:")
        print("=" * 70)
        
        # Give specific advice based on what we found
        if isinstance(data, dict):
            # Check for common localStorage patterns
            sb_keys = [k for k in data.keys() if 'sb' in k.lower() or 'spelling' in k.lower() or 'bee' in k.lower()]
            
            if sb_keys:
                print(f"\n✅ Found Spelling Bee related keys: {sb_keys}")
                print("\nYour data looks like a localStorage export.")
                print("Let me show you what's in each key:\n")
                
                for key in sb_keys:
                    value = data[key]
                    print(f"{key}:")
                    print(f"  Type: {type(value)}")
                    
                    # Try to parse if it's a string
                    if isinstance(value, str):
                        try:
                            parsed = json.loads(value)
                            print(f"  Parsed type: {type(parsed)}")
                            if isinstance(parsed, dict):
                                print(f"  Keys: {list(parsed.keys())[:5]}")
                            elif isinstance(parsed, list):
                                print(f"  Length: {len(parsed)}")
                        except:
                            print(f"  Content: {value[:100]}")
                    print()
            else:
                print("\n⚠️  No obvious Spelling Bee keys found.")
                print("Available keys:", list(data.keys())[:10])
        
        elif isinstance(data, list):
            print("\n✅ Your data is a list of items.")
            if len(data) > 0 and isinstance(data[0], dict):
                print(f"First item keys: {list(data[0].keys())}")
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Could not parse as JSON: {e}")
        print("\nThe file might not be valid JSON.")
    
    print("\n" + "=" * 70)
    print("\nNext steps:")
    print("1. Share the output above so I can fix the extraction script")
    print("2. Or try the browser_extract.js script again")
    print("3. Or use manual entry: python3 extract_spelling_bee_data.py")
    print()


if __name__ == '__main__':
    inspect_data()
