from setuptools import setup, Extension
import pybind11
import os
import sys
import platform
from glob import glob
from pathlib import Path

cache_dir = ".cache"

# Get all DNG SDK source files
dng_sdk_source_dir = cache_dir + "/dng_sdk/dng_sdk_1_7_1/dng_sdk/source/"
dng_sdk_sources = glob(os.path.join(dng_sdk_source_dir, "*.cpp"))
all_sources = ['../src/dngio/dng.cpp'] + dng_sdk_sources

print(f"Compiling {len(all_sources)} source files...")
print(f"Platform: {platform.system()}")

# Platform-specific configuration
is_windows = platform.system() == "Windows"
is_linux = platform.system() == "Linux" 
is_macos = platform.system() == "Darwin"

# Base configuration
include_dirs = [
    pybind11.get_include(),
    dng_sdk_source_dir,
    cache_dir + "/dng_sdk/dng_sdk_1_7_1/libjpeg",
    cache_dir + "/dng_sdk/dng_sdk_1_7_1/libjxl/libjxl/lib/include",
    cache_dir + "/dng_sdk/dng_sdk_1_7_1/libjxl/client_projects/include",
    cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/include",
    cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/third-party/zlib",
]

library_dirs = []
libraries = []
extra_compile_args = []
extra_link_args = []

if is_windows:
    # Windows configuration
    library_dirs.extend([
        cache_dir + "/dng_sdk/dng_sdk_1_7_1/dng_sdk/projects/win/x64/Release",
        cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/windows_x64/Release",
        cache_dir + "/dng_sdk/dng_sdk_1_7_1/libjpeg",
    ])
    libraries.extend([
        'jxl',
        'brotli',
        'highway',
        'XMPCoreStaticRelease',
        'XMPFilesStaticRelease',
        'libjpeg',
        'ole32'
    ])
    extra_compile_args.extend([
        '/std:c++17', '/EHsc', '/MT', '/DqDNGValidateTarget=1',
        '/DqDNGUseLibJPEG=1', '/DqDNGUseXMP=1', '/DqDNGThreadSafe=1', '/DqWinOS=1'
    ])
    extra_link_args.extend(['/NODEFAULTLIB:msvcrt'])

else:
    # Platform not supported yet
    raise RuntimeError(f"Platform {platform.system()} is not supported yet. Only Windows is currently supported.")

dng_module = Extension(
    '_dngio_impl',  # Internal extension name to avoid circular import
    sources=all_sources,
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    language='c++',
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
)

setup(
    name='dngio',
    version='1.0.0',
    description='Python wrapper around Adobe DNG SDK with full external dependencies for reading and writing DNG files',
    ext_modules=[dng_module],
)
