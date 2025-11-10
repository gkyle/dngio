#!/usr/bin/env python3
"""
Main build script for the DNG Python module.
This script coordinates the entire build process.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description, cwd=None):
    """Run a command and handle errors."""
    print(f"\n[BUILD] {description}")
    print(f"Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, check=True, cwd=cwd)
        else:
            result = subprocess.run(cmd, check=True, cwd=cwd)
        print(f"[SUCCESS] {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} failed with return code {e.returncode}")
        return False

def main():
    """Main build process."""
    print("DNG Python Module Build Script")
    print("=" * 50)
    
    # Get paths
    root_dir = Path(__file__).parent.parent
    build_tools_dir = Path(__file__).parent
    src_dir = root_dir / "src"
    
    print(f"Root directory: {root_dir}")
    print(f"Build tools directory: {build_tools_dir}")
    print(f"Source directory: {src_dir}")
    
    # Step 1: Build dependencies (Windows only for now)
    if sys.platform == "win32":
        deps_script = build_tools_dir / "build_dependencies.ps1"
        if deps_script.exists():
            print("\n[STEP 1] Building dependencies...")
            success = run_command(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(deps_script)],
                "Building external dependencies",
                cwd=build_tools_dir
            )
            if not success:
                print("[ERROR] Dependency build failed. Cannot continue.")
                return False
        else:
            print("[WARNING] build_dependencies.ps1 not found. Assuming dependencies are already built.")
    else:
        if sys.platform == "darwin":  # macOS
            deps_script = build_tools_dir / "build_dependencies_macos.sh"
            if deps_script.exists():
                print("[STEP 1] Building dependencies (macOS)...")
                success = run_command(
                    ["bash", str(deps_script)],
                    "Building external dependencies (macOS)",
                    cwd=build_tools_dir
                )
                if not success:
                    print("[WARNING] macOS dependency build failed - this is expected as macOS support is not yet complete")
            else:
                print("[WARNING] build_dependencies_macos.sh not found")
        else:
            print("[WARNING] Dependency building for Linux not implemented yet.")
        print("   Please ensure all dependencies are available.")
    
    # Step 2: Build the Python extension
    print("\n[STEP 2] Building Python extension...")
    success = run_command(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        "Building Python extension",
        cwd=build_tools_dir
    )
    if not success:
        return False
    
    # Step 3: Copy built extension to src directory
    print("\n[STEP 3] Copying built extension to source directory...")
    
    # Find the built extension file
    built_files = []
    for ext in ['.pyd', '.so', '.dylib']:
        built_files.extend(list(build_tools_dir.glob(f"*{ext}")))
    
    if built_files:
        for built_file in built_files:
            dest_file = src_dir / "dngio" / built_file.name
            shutil.copy2(built_file, dest_file)
            print(f"[SUCCESS] Copied {built_file.name} to {dest_file}")
    else:
        print("[ERROR] No built extension files found!")
        return False
    
    # Step 4: Build wheel
    print("\n[STEP 4] Building wheel...")
    success = run_command(
        [sys.executable, "setup.py", "bdist_wheel"],
        "Building wheel",
        cwd=build_tools_dir
    )
    if not success:
        return False
    
    # Step 5: Copy wheel to wheels directory
    wheels_dir = root_dir / "wheels"
    wheels_dir.mkdir(exist_ok=True)
    
    build_dist_dir = build_tools_dir / "dist"
    if build_dist_dir.exists():
        for wheel_file in build_dist_dir.glob("*.whl"):
            dest_wheel = wheels_dir / wheel_file.name
            shutil.copy2(wheel_file, dest_wheel)
            print(f"[SUCCESS] Copied wheel to {dest_wheel}")
    
    print("\n[COMPLETE] Build completed successfully!")
    print(f"Extension files are in: {src_dir / 'dngio'}")
    print(f"Wheel files are in: {wheels_dir}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)