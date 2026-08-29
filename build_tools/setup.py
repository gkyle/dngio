from setuptools import setup, Extension
import pybind11
import os
import sys
import platform
from glob import glob
from pathlib import Path

# Both macOS and Windows scripts use .cache in build_tools directory
cache_dir = os.path.abspath(".cache")
print(f"Using cache directory: {cache_dir}")

# Get all DNG SDK source files
dng_sdk_source_dir = cache_dir + "/dng_sdk/dng_sdk_1_7_1/dng_sdk/source/"
print(f"Looking for DNG SDK sources in: {dng_sdk_source_dir}")

if not os.path.exists(dng_sdk_source_dir):
    print(f"ERROR: DNG SDK source directory not found: {dng_sdk_source_dir}")
    print("Dependencies must be built first using the appropriate build script:")
    print("  macOS: bash build_dependencies_macos.sh")
    print("  Windows: powershell -ExecutionPolicy Bypass -File build_dependencies.ps1")
    raise RuntimeError("DNG SDK sources not available - run dependency build first")

dng_sdk_sources = glob(os.path.join(dng_sdk_source_dir, "*.cpp"))
if not dng_sdk_sources:
    print(f"ERROR: No DNG SDK source files found in: {dng_sdk_source_dir}")
    raise RuntimeError("DNG SDK source files not found")

# Auto-patch dng_memory.h for GCC/Clang C++ allocator compatibility
dng_memory_h = os.path.join(dng_sdk_source_dir, "dng_memory.h")
if os.path.exists(dng_memory_h):
    with open(dng_memory_h, "r") as f:
        dng_mem_content = f.read()

    old_allocator_def = """template <typename T>
class dng_std_allocator
	{
	
	public:

		typedef T value_type;
		
		#if defined(_MSC_VER) && _MSC_VER >= 1900

		// Default implementations of default constructor and copy
		// constructor.

		dng_std_allocator () = default;

		// dng_std_allocator (const dng_std_allocator &) = default;

		template<class U> dng_std_allocator (const dng_std_allocator<U> &) {}
		
		#endif"""

    new_allocator_def = """template <typename T>
class dng_std_allocator
	{
	
	public:

		typedef T value_type;
		typedef T* pointer;
		typedef const T* const_pointer;
		typedef T& reference;
		typedef const T& const_reference;
		typedef std::size_t size_type;
		typedef std::ptrdiff_t difference_type;

		template<class U> struct rebind { typedef dng_std_allocator<U> other; };

		// Default implementations of default constructor and copy
		// constructor.

		dng_std_allocator () = default;

		template<class U> dng_std_allocator (const dng_std_allocator<U> &) {}"""

    if old_allocator_def in dng_mem_content:
        print("Patching dng_memory.h for GCC/Clang C++ allocator compatibility...")
        dng_mem_content = dng_mem_content.replace(old_allocator_def, new_allocator_def)
        with open(dng_memory_h, "w") as f:
            f.write(dng_mem_content)
        print("✓ dng_memory.h successfully patched")
    elif "#if defined(_MSC_VER) && _MSC_VER >= 1900" in dng_mem_content:
        print("Patching dng_memory.h (fallback) for GCC/Clang compatibility...")
        dng_mem_content = dng_mem_content.replace(
            "#if defined(_MSC_VER) && _MSC_VER >= 1900",
            "// #if defined(_MSC_VER) && _MSC_VER >= 1900"
        )
        with open(dng_memory_h, "w") as f:
            f.write(dng_mem_content)
        print("✓ dng_memory.h fallback patch applied")

# Get libjpeg source files from DNG SDK
libjpeg_source_dir = cache_dir + "/dng_sdk/dng_sdk_1_7_1/libjpeg/"
libjpeg_sources = glob(os.path.join(libjpeg_source_dir, "*.c"))

# Exclude example/test/utility files
libjpeg_exclude = ['example.c', 'cjpeg.c', 'djpeg.c', 'jpegtran.c', 'rdjpgcom.c', 'wrjpgcom.c', 
                   'ckconfig.c', 'ansi2knr.c', 'cdjpeg.c', 'rdbmp.c', 'rdcolmap.c', 'rdgif.c',
                   'rdppm.c', 'rdrle.c', 'rdswitch.c', 'rdtarga.c', 'wrbmp.c', 'wrgif.c',
                   'wrppm.c', 'wrrle.c', 'wrtarga.c', 'transupp.c']

# Exclude platform-specific memory managers - keep only the appropriate one
# macOS/Unix: jmemnobs.c (no backing store)
# Windows: jmemansi.c (ANSI C - portable and recommended)
if platform.system() == 'Windows':
    # Windows: exclude all except jmemansi.c
    libjpeg_exclude.extend(['jmemdos.c', 'jmemmac.c', 'jmemname.c', 'jmemnobs.c'])
else:
    # macOS/Unix: exclude all except jmemnobs.c
    libjpeg_exclude.extend(['jmemansi.c', 'jmemdos.c', 'jmemmac.c', 'jmemname.c'])

libjpeg_sources = [f for f in libjpeg_sources if os.path.basename(f) not in libjpeg_exclude]
if not libjpeg_sources:
    print(f"WARNING: No libjpeg source files found in: {libjpeg_source_dir}")
else:
    print(f"Found {len(libjpeg_sources)} libjpeg source files")

all_sources = ['../src/dngio/dng.cpp'] + dng_sdk_sources + libjpeg_sources

print(f"Found {len(dng_sdk_sources)} DNG SDK source files")
print(f"Compiling {len(all_sources)} total source files...")
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

elif is_macos:
    # macOS configuration - use paths from Xcode build output
    print("macOS build configuration - checking for dependencies...")

    # Check if DNG SDK dependencies exist
    dependency_paths = [
        cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/mac/Release",
        cache_dir + "/dng_sdk/dng_sdk_1_7_1/libjpeg"
    ]

    dependencies_available = all(os.path.exists(path) for path in dependency_paths)

    if not dependencies_available:
        print("ERROR: DNG SDK dependencies not found for macOS.")
        print("Missing dependency paths:")
        for path in dependency_paths:
            exists = os.path.exists(path)
            print(f"  {path} - {'EXISTS' if exists else 'MISSING'}")
        print("\nDependencies must be built first using 'bash build_dependencies_macos.sh'")
        raise RuntimeError("macOS dependencies not available - cannot build C++ extension")
    else:
        print("Found DNG SDK dependencies for macOS")

        # Base library directories including XMP build output locations
        base_lib_dirs = [
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/dng_sdk/projects/mac/targets/mac/libraries",
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/mac/Release",
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/macintosh/intel_64/Debug",  # Article location
            # Article location (Release variant)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/macintosh/intel_64/Release",
            # cmake generated location (modern)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode/dynamic/universal",
            # cmake generated location (modern)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode/static/universal",
            # cmake generated location (older)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode/dynamic/intel_64",
            # cmake generated location (older)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode/static/intel_64",
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode12-universal/build/Release",  # Old XMP build output
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode12-universal/build",  # Old XMP build root
            cache_dir + "/libjxl/build/lib",  # JPEG XL libraries
            cache_dir + "/libjxl/build/third_party/brotli",  # Brotli libraries (JPEG XL dependency)
            cache_dir + "/libjxl/build/third_party/highway",  # Highway libraries (JPEG XL dependency)
        ]
        library_dirs.extend(base_lib_dirs)

        # Find actual XMP library names (they might vary)
        xmp_libs_dir = cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/mac/Release"
        xmp_core_lib = None
        xmp_files_lib = None

        # Search for XMP libraries based on actual XMP build target names
        # The XMP project creates targets like XMPCMake64_Static_libcpp, so look for corresponding libraries
        xmp_search_locations = [
            xmp_libs_dir,  # Standard location
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/macintosh/intel_64/Debug",  # Article location
            # Article location (Release)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/macintosh/intel_64/Release",
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode/dynamic/universal",  # cmake dynamic (modern)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode/static/universal",  # cmake static (modern)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode/dynamic/intel_64",  # cmake dynamic (older)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode/static/intel_64",  # cmake static (older)
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode12-universal/build/Release",  # Old build output
            cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/build/xcode12-universal/build",  # Old build root
        ]

        # Common XMP library name patterns based on actual XMP toolkit structure
        xmp_core_patterns = ['XMPCoreStatic', 'XMPCore', 'libXMPCoreStatic',
                             'libXMPCore', 'XMPCMake64_Static_libcpp', 'XMPCMake_Static_libcpp',
                             'XMPCoreStaticRelease', 'libXMPCoreStaticRelease']
        xmp_files_patterns = ['XMPFilesStatic', 'XMPFiles', 'libXMPFilesStatic',
                              'libXMPFiles', 'XMPFiles64_Static_libcpp', 'XMPFiles_Static_libcpp',
                              'XMPFilesStaticRelease', 'libXMPFilesStaticRelease']

        for search_dir in xmp_search_locations:
            if not os.path.exists(search_dir):
                continue

            # Look for XMP Core library
            if not xmp_core_lib:
                for lib_name in xmp_core_patterns:
                    for lib_path in [f"{search_dir}/lib{lib_name}.a", f"{search_dir}/{lib_name}.a", f"{search_dir}/lib{lib_name}.dylib"]:
                        if os.path.exists(lib_path):
                            xmp_core_lib = lib_name.replace('lib', '') if lib_name.startswith('lib') else lib_name
                            print(f"  Found XMP Core library: {lib_path}")
                            break
                    if xmp_core_lib:
                        break

            # Look for XMP Files library
            if not xmp_files_lib:
                for lib_name in xmp_files_patterns:
                    for lib_path in [f"{search_dir}/lib{lib_name}.a", f"{search_dir}/{lib_name}.a", f"{search_dir}/lib{lib_name}.dylib"]:
                        if os.path.exists(lib_path):
                            xmp_files_lib = lib_name.replace('lib', '') if lib_name.startswith('lib') else lib_name
                            print(f"  Found XMP Files library: {lib_path}")
                            break
                    if xmp_files_lib:
                        break

        # Base libraries - libjpeg compiled directly, not linked
        # JPEG XL and dependencies linked via full paths in extra_link_args
        libs_to_link = []

        # XMP libraries are CRITICAL - build must fail if not available
        if not xmp_core_lib:
            print("  ERROR: XMP Core library not found - this is required for DNG functionality")
            print("  Available files in XMP directory:")
            if os.path.exists(xmp_libs_dir):
                for f in os.listdir(xmp_libs_dir):
                    print(f"    {f}")
            else:
                print(f"    Directory does not exist: {xmp_libs_dir}")
            raise RuntimeError("XMP Core library is required but not found - cannot build C++ extension")

        if not xmp_files_lib:
            print("  ERROR: XMP Files library not found - this is required for DNG functionality")
            print("  Available files in XMP directory:")
            if os.path.exists(xmp_libs_dir):
                for f in os.listdir(xmp_libs_dir):
                    print(f"    {f}")
            else:
                print(f"    Directory does not exist: {xmp_libs_dir}")
            raise RuntimeError("XMP Files library is required but not found - cannot build C++ extension")

        # Add required XMP libraries
        libs_to_link.extend([xmp_core_lib, xmp_files_lib])
        print(f"  ✓ Using required XMP libraries: {xmp_core_lib}, {xmp_files_lib}")

        libraries.extend(libs_to_link)

        extra_compile_args.extend([
            '-DqDNGValidateTarget=1',
            '-DqDNGUseLibJPEG=1', '-DqDNGUseXMP=1', '-DqDNGThreadSafe=1', '-DqMacOS=1',
            '-arch', 'x86_64', '-arch', 'arm64'  # Universal binary support
        ])
        # Force static linking of all libraries by specifying full paths
        extra_link_args.extend([
            '-arch', 'x86_64', '-arch', 'arm64',  # Universal binary support
            # JPEG XL and its dependencies (full paths to force static linking)
            cache_dir + "/libjxl/build/lib/libjxl.a",
            cache_dir + "/libjxl/build/third_party/brotli/libbrotlidec.a",
            cache_dir + "/libjxl/build/third_party/brotli/libbrotlienc.a",
            cache_dir + "/libjxl/build/third_party/brotli/libbrotlicommon.a",
            cache_dir + "/libjxl/build/third_party/highway/libhwy.a",
        ])

elif is_linux:
    # Linux configuration
    print("Linux build configuration - checking for dependencies...")

    # Base library directories including XMP build output locations
    base_lib_dirs = [
        cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/linux/Release",
        cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/linux",
        cache_dir + "/libjxl/build/lib",
        cache_dir + "/libjxl/build/third_party/brotli",
        cache_dir + "/libjxl/build/third_party/highway",
    ]
    library_dirs.extend(base_lib_dirs)

    # Search for XMP Core and XMP Files libraries
    xmp_libs_dir = cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/linux/Release"
    xmp_core_lib = None
    xmp_files_lib = None

    xmp_search_locations = [
        xmp_libs_dir,
        cache_dir + "/dng_sdk/dng_sdk_1_7_1/xmp/toolkit/public/libraries/linux",
    ]

    xmp_core_patterns = ['XMPCoreStatic', 'XMPCore', 'libXMPCoreStatic']
    xmp_files_patterns = ['XMPFilesStatic', 'XMPFiles', 'libXMPFilesStatic']

    for search_dir in xmp_search_locations:
        if not os.path.exists(search_dir):
            continue

        if not xmp_core_lib:
            for lib_name in xmp_core_patterns:
                for lib_path in [f"{search_dir}/lib{lib_name}.a", f"{search_dir}/{lib_name}.a"]:
                    if os.path.exists(lib_path):
                        xmp_core_lib = lib_name.replace('lib', '') if lib_name.startswith('lib') else lib_name
                        print(f"  Found XMP Core library: {lib_path}")
                        break
                if xmp_core_lib:
                    break

        if not xmp_files_lib:
            for lib_name in xmp_files_patterns:
                for lib_path in [f"{search_dir}/lib{lib_name}.a", f"{search_dir}/{lib_name}.a"]:
                    if os.path.exists(lib_path):
                        xmp_files_lib = lib_name.replace('lib', '') if lib_name.startswith('lib') else lib_name
                        print(f"  Found XMP Files library: {lib_path}")
                        break
                if xmp_files_lib:
                    break

    if not xmp_core_lib:
        print("  ERROR: XMP Core library not found for Linux")
        raise RuntimeError("XMP Core library is required but not found - cannot build C++ extension")

    if not xmp_files_lib:
        print("  ERROR: XMP Files library not found for Linux")
        raise RuntimeError("XMP Files library is required but not found - cannot build C++ extension")

    libraries.extend([xmp_core_lib, xmp_files_lib])
    print(f"  ✓ Using required XMP libraries: {xmp_core_lib}, {xmp_files_lib}")

    extra_compile_args.extend([
        '-std=c++17', '-DqDNGValidateTarget=1',
        '-DqDNGUseLibJPEG=1', '-DqDNGUseXMP=1', '-DqDNGThreadSafe=1', '-DqLinux=1', '-DqLinuxOS=1', '-DUNIX_ENV=1', '-DXMP_StaticBuild=1'
    ])

    extra_link_args.extend([
        cache_dir + "/libjxl/build/lib/libjxl.a",
        cache_dir + "/libjxl/build/lib/libjxl_threads.a",
        cache_dir + "/libjxl/build/lib/libjxl_cms.a",
        cache_dir + "/libjxl/build/third_party/brotli/libbrotlidec.a",
        cache_dir + "/libjxl/build/third_party/brotli/libbrotlienc.a",
        cache_dir + "/libjxl/build/third_party/brotli/libbrotlicommon.a",
        cache_dir + "/libjxl/build/third_party/highway/libhwy.a",
    ])

else:
    # Platform not supported yet
    raise RuntimeError(f"Platform {platform.system()} is not supported yet.")

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

# Debug output
print(f"\nBuilding extension with configuration:")
print(f"  Extension name: _dngio_impl")
print(f"  Source files: {len(all_sources)}")
print(f"  Include directories: {len(include_dirs)}")
print(f"  Library directories: {len(library_dirs)}")
print(f"  Libraries: {len(libraries)}")
print(f"  First few libraries: {libraries[:5] if libraries else 'None'}")

setup(
    name='dngio',
    version='1.0.0',
    description='Python wrapper around Adobe DNG SDK with full external dependencies for reading and writing DNG files',
    ext_modules=[dng_module],
)

print(f"\nSetup completed. Extension should be named '_dngio_impl.*'")

# List files that exist after build
import glob
built_files = glob.glob("_dngio_impl*")
print(f"Found extension files after build: {built_files}")
