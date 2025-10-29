#!/usr/bin/env python3
"""
Build script for creating distributable wheels
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_extension():
    """Build the C++ extension"""
    print("Building C++ extension...")

    os.chdir('build_tools')

    # Run the build
    result = subprocess.run([sys.executable, 'setup.py', 'build_ext', '--inplace'], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Build failed: {result.stderr}")
        return False
        
    print("✓ Extension built successfully")
    return True

def copy_extension():
    """Copy the built extension to the package directory"""
    print("Copying extension to package...")
    
    current_dir = Path('.')
    ext_files = list(current_dir.glob('_dngio_impl*.pyd')) + list(current_dir.glob('_dngio_impl*.so'))
    
    if not ext_files:
        print("✗ No extension files found in build_tools directory")
        print("   Make sure 'python setup.py build_ext --inplace' ran successfully")
        return False
    
    ext_file = ext_files[0]
    print(f"Found extension: {ext_file.name}")
    
    target_dir = Path('../src/dngio')
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / ext_file.name
    
    # Copy the extension
    shutil.copy2(ext_file, target_file)
    print(f"✓ Copied {ext_file.name} to {target_dir}")
    return True

def build_wheel():
    """Build the wheel using setuptools"""
    print("Building wheel...")

    os.chdir('..')
    try:
        result = subprocess.run([sys.executable, 'build_tools/wheel_setup.py', 'bdist_wheel'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Wheel build failed: {result.stderr}")
            return False
            
        print("✓ Wheel built successfully")
        return True
        
    except Exception as e:
        print(f"✗ Wheel build failed: {e}")
        return False

def main():
    """Main build process"""
    print("Building dngio package...")
    print("=" * 50)
    
    # Save current directory and ensure we start from the project root
    original_dir = os.getcwd()
    script_dir = Path(__file__).parent  # build_tools directory
    project_root = script_dir.parent    # parent of build_tools
    os.chdir(project_root)              # start from project root
    
    try:
        # Step 1: Build extension
        if not build_extension():
            return 1
            
        # Step 2: Copy extension
        if not copy_extension():
            return 1
            
        # Step 3: Build wheel
        if not build_wheel():
            return 1
            
        print("=" * 50)
        print("✓ Package built successfully!")
        
        # Show the built files
        dist_dir = Path('dist')
        if dist_dir.exists():
            wheels = list(dist_dir.glob('*.whl'))
            if wheels:
                print(f"Built wheel: {wheels[0]}")
        
        return 0
        
    except Exception as e:
        print(f"✗ Build failed: {e}")
        return 1
        
    finally:
        # Restore original directory
        os.chdir(original_dir)

if __name__ == "__main__":
    sys.exit(main())