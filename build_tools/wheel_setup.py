#!/usr/bin/env python3
"""
Setup script specifically for wheel building.
This is called by build_wheel.py to create the wheel distribution.
"""

from setuptools import setup, find_packages
from pathlib import Path

def main():
    """Main setup function for wheel building"""
    
    # Read the contents of README file (one level up from build_tools)
    this_directory = Path(__file__).parent.parent  # Go up from build_tools to project root
    long_description = (this_directory / "README.md").read_text(encoding="utf-8") if (this_directory / "README.md").exists() else "DNG I/O Python Module"

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
            "dngio": ["*.pyd", "*.so", "*.dll"],
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
    )

if __name__ == "__main__":
    main()