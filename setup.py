#!/usr/bin/env python3
"""
Setup script for dngio package.
This is used by cibuildwheel to create platform-specific wheels.
The C++ extension is pre-built by CIBW_BEFORE_BUILD_WINDOWS.
"""

from setuptools import setup, find_packages
from setuptools.dist import Distribution
from pathlib import Path
import glob

class BinaryDistribution(Distribution):
    """Force platform-specific wheel tag since C++ extension binaries are included."""
    def has_ext_modules(self):
        return True

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8") if (this_directory / "README.md").exists() else "DNG I/O Python Module"

# Find any built extension files in src/dngio
extension_files = []
src_dngio_path = this_directory / "src" / "dngio"
if src_dngio_path.exists():
    extension_files.extend(glob.glob(str(src_dngio_path / "*.pyd")))
    extension_files.extend(glob.glob(str(src_dngio_path / "*.so")))
    extension_files.extend(glob.glob(str(src_dngio_path / "*.dylib")))

print(f"Found extension files: {extension_files}")

setup(
    name="dngio",
    version="1.0.0",
    author="Kyle Scholz",
    author_email="kyle.scholz@gmail.com",
    description="Python module for reading and writing Adobe DNG files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gkyle/dngio",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "dngio": ["*.pyd", "*.so", "*.dylib", "py.typed"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.19.0",
    ],
    distclass=BinaryDistribution,
)