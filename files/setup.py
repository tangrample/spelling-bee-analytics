#!/usr/bin/env python3
"""
Main setup script for NYT Spelling Bee Analytics Pipeline
Runs the complete pipeline from setup to analysis
"""

import sys
import subprocess
from pathlib import Path

STEPS = [
    {
        'name': 'Database Setup',
        'script': 'create_database.py',
        'description': 'Creates the SQLite database schema'
    },
    {
        'name': 'Data Processing',
        'script': 'process_data.py',
        'description': 'Processes and loads your game data'
    },
    {
        'name': 'Analytics',
        'script': 'analyze.py',
        'description': 'Runs analytics on your games'
    }
]


def check_requirements():
    """Check if required dependencies are installed."""
    try:
        import pandas
        return True
    except ImportError:
        return False


def print_header():
    """Print welcome header."""
    print("\n" + "=" * 70)
    print(" " * 15 + "NYT SPELLING BEE ANALYTICS PIPELINE")
    print("=" * 70)
    print("\n🐝 Welcome! This script will help you set up your personal")
    print("   Spelling Bee analytics database.\n")


def print_instructions():
    """Print data extraction instructions."""
    print("\n" + "=" * 70)
    print("STEP 0: EXTRACT YOUR DATA")
    print("=" * 70)
    print("\nBefore running this pipeline, you need to extract your game history.")
    print("\n📱 OPTION A: Browser Extract (Recommended)")
    print("-" * 70)
    print("1. Go to: https://www.nytimes.com/puzzles/spelling-bee")
    print("2. Open browser DevTools (press F12)")
    print("3. Go to Console tab")
    print("4. Copy & paste contents of 'browser_extract.js'")
    print("5. Press Enter")
    print("6. Save the downloaded JSON file as 'spelling_bee_raw.json'")
    print("   in this directory")
    
    print("\n💻 OPTION B: Manual Entry")
    print("-" * 70)
    print("Run: python3 extract_spelling_bee_data.py")
    print("     Then choose option 2 for manual entry")
    
    print("\n🧪 OPTION C: Try Sample Data (for testing)")
    print("-" * 70)
    print("To test the pipeline with sample data:")
    print("     cp sample_data.json spelling_bee_raw.json")
    
    print("\n" + "=" * 70)


def run_step(step_num, step_info):
    """Run a pipeline step."""
    print(f"\n{'=' * 70}")
    print(f"STEP {step_num}: {step_info['name'].upper()}")
    print(f"{'=' * 70}")
    print(f"\n{step_info['description']}")
    print(f"\nRunning {step_info['script']}...\n")
    
    try:
        result = subprocess.run(
            [sys.executable, step_info['script']],
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print(f"\n⚠️  Step failed with return code {result.returncode}")
            return False
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error running step: {e}")
        return False


def main():
    """Main entry point."""
    print_header()
    
    # Check requirements
    if not check_requirements():
        print("⚠️  Missing required dependency: pandas")
        print("\nInstall it with: pip install pandas")
        print("\nThen run this script again.")
        return
    
    print("✓ All requirements satisfied\n")
    
    # Show data extraction instructions
    print_instructions()
    
    # Check if data file exists
    data_file = Path('spelling_bee_raw.json')
    
    if not data_file.exists():
        print("\n⚠️  No data file found!")
        print("\nPlease extract your data first using one of the options above.")
        print("Then run this script again.\n")
        
        use_sample = input("Would you like to use sample data for testing? (y/n): ").strip().lower()
        if use_sample == 'y':
            import shutil
            shutil.copy('sample_data.json', 'spelling_bee_raw.json')
            print("✓ Sample data copied to spelling_bee_raw.json")
        else:
            return
    else:
        print("\n✓ Found data file: spelling_bee_raw.json")
    
    # Confirm before proceeding
    print("\n" + "=" * 70)
    proceed = input("\nReady to run the pipeline? (y/n): ").strip().lower()
    
    if proceed != 'y':
        print("\nSetup cancelled. Run this script again when ready.")
        return
    
    # Run each step
    for i, step in enumerate(STEPS, 1):
        success = run_step(i, step)
        
        if not success:
            print(f"\n❌ Pipeline stopped at step {i}")
            print("Fix the error and run this script again.")
            return
    
    # Success!
    print("\n" + "=" * 70)
    print("✨ PIPELINE COMPLETE!")
    print("=" * 70)
    print("\n🎉 Your Spelling Bee analytics database is ready!")
    print("\n📊 What you can do now:")
    print("   • Run analyze.py anytime for updated statistics")
    print("   • Query spelling_bee.db directly with SQL")
    print("   • Export to CSV for Excel/Sheets analysis")
    print("   • Build custom visualizations with Python")
    print("\n📝 See README.md for more information and examples")
    print("\n🔄 To update with new games:")
    print("   1. Extract new data from browser")
    print("   2. Run: python3 process_data.py")
    print("   3. Run: python3 analyze.py")
    print("\n" + "=" * 70 + "\n")


if __name__ == '__main__':
    main()
