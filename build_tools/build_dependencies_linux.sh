#!/bin/bash
set -e

echo "Building Linux dependencies for dngio..."

# Resolve absolute path to cache directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="${SCRIPT_DIR}/.cache"

# Create cache directory if it doesn't exist
mkdir -p "$CACHE_DIR"
CACHE_ABS_PATH="$(cd "$CACHE_DIR" && pwd)"

echo "Using cache directory: $CACHE_ABS_PATH"

# Download and extract DNG SDK if needed
DNG_SDK_ROOT="$CACHE_ABS_PATH/dng_sdk/dng_sdk_1_7_1"
if [ ! -d "$DNG_SDK_ROOT" ]; then
    echo "Downloading Adobe DNG SDK..."
    mkdir -p "$CACHE_ABS_PATH/dng_sdk"
    cd "$CACHE_ABS_PATH/dng_sdk"
    curl -L -o dng_sdk_1_7_1.zip "https://download.adobe.com/pub/adobe/dng/dng_sdk_1_7_1.zip"
    unzip -q dng_sdk_1_7_1.zip
    echo "✓ Adobe DNG SDK extracted"
fi

# Build JPEG XL dependencies
build_jpeg_xl() {
    echo "Building JPEG XL dependencies..."
    
    JPEG_XL_ROOT="$CACHE_ABS_PATH/libjxl"
    JPEG_XL_BUILD="$JPEG_XL_ROOT/build"
    
    if [ ! -d "$JPEG_XL_ROOT" ]; then
        echo "  Cloning JPEG XL..."
        cd "$CACHE_ABS_PATH"
        git clone --recursive --shallow-submodules https://github.com/libjxl/libjxl.git
    fi
    
    if [ ! -f "$JPEG_XL_BUILD/lib/libjxl.a" ]; then
        echo "  Building JPEG XL..."
        cd "$JPEG_XL_ROOT"
        mkdir -p build
        cd build
        
        NPROC=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 2)
        cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DJPEGXL_ENABLE_TOOLS=OFF -DBUILD_TESTING=OFF -DJPEGXL_ENABLE_SAMPLES=OFF -DJPEGXL_ENABLE_MANPAGES=OFF -DJPEGXL_ENABLE_BENCHMARK=OFF ..
        make -j"$NPROC"
        echo "  ✓ JPEG XL built successfully"
    else
        echo "  ✓ JPEG XL already built"
    fi
}

# Build XMP libraries
build_xmp() {
    echo "Building XMP libraries..."
    
    XMP_TOOLKIT_DIR="$DNG_SDK_ROOT/xmp/toolkit"
    
    if [ ! -d "$XMP_TOOLKIT_DIR" ]; then
        echo "  ✗ XMP toolkit directory not found: $XMP_TOOLKIT_DIR"
        exit 1
    fi
    
    echo "  ✓ Found XMP toolkit directory"
    
    XMP_OUTPUT_PATH="$XMP_TOOLKIT_DIR/public/libraries/linux/Release"
    mkdir -p "$XMP_OUTPUT_PATH"
    
    if [ -f "$XMP_OUTPUT_PATH/libXMPCoreStatic.a" ] && [ -f "$XMP_OUTPUT_PATH/libXMPFilesStatic.a" ]; then
        echo "  ✓ XMP libraries already built"
        return 0
    fi
    
    TEMP_BUILD_DIR="$CACHE_ABS_PATH/xmp_build_temp"
    mkdir -p "$TEMP_BUILD_DIR"
    cd "$TEMP_BUILD_DIR"
    
    # 1. Build XMPCore
    if [ ! -f "$XMP_OUTPUT_PATH/libXMPCoreStatic.a" ]; then
        echo "  Building XMPCore..."
        
        INCLUDES_CORE="-I$XMP_TOOLKIT_DIR \
          -I$XMP_TOOLKIT_DIR/public/include \
          -I$XMP_TOOLKIT_DIR/source \
          -I$XMP_TOOLKIT_DIR/XMPCore/source \
          -I$XMP_TOOLKIT_DIR/XMPCore/resource/linux \
          -I$XMP_TOOLKIT_DIR/XMPCore/third-party/expat/public/lib \
          -I$XMP_TOOLKIT_DIR/XMPCore/third-party/boost \
          -I$XMP_TOOLKIT_DIR/third-party/zuid/interfaces \
          -I$XMP_TOOLKIT_DIR/third-party/zlib"

        DEFINES_CORE="-DUNIX_ENV=1 -DAdobePrivate=1 -DHAVE_EXPAT_CONFIG_H=1 -DXML_STATIC=1 -DXML_POOR_ENTROPY=1 -DXMP_64=1 -D__x86_64__=1 -DqLinux=1 -DqLinuxOS=1 -DXMP_COMPONENT_INT_NAMESPACE=AdobeXMPCore_Int -DBUILDING_XMPCORE_LIB=1 -DBUILDING_XMPCORE_AS_STATIC=1 -DXMP_StaticBuild=1 -DXMP_BUILD_STATIC=1"

        rm -f *.o
        g++ $DEFINES_CORE $INCLUDES_CORE -c -O2 -fPIC -std=c++17 \
          $XMP_TOOLKIT_DIR/XMPCore/source/*.cpp \
          $XMP_TOOLKIT_DIR/source/UnicodeConversions.cpp \
          $XMP_TOOLKIT_DIR/source/XML_Node.cpp \
          $XMP_TOOLKIT_DIR/source/XMP_LibUtils.cpp \
          $XMP_TOOLKIT_DIR/third-party/zuid/sources/*.cpp \
          $XMP_TOOLKIT_DIR/XMPCommon/source/*.cpp

        gcc -DHAVE_EXPAT_CONFIG_H=1 -DXML_STATIC=1 -DXML_POOR_ENTROPY=1 -I$XMP_TOOLKIT_DIR/XMPCore/resource/linux -c -O2 -fPIC \
          $XMP_TOOLKIT_DIR/XMPCore/third-party/expat/public/lib/xmlparse.c \
          $XMP_TOOLKIT_DIR/XMPCore/third-party/expat/public/lib/xmlrole.c \
          $XMP_TOOLKIT_DIR/XMPCore/third-party/expat/public/lib/xmltok.c

        ar rcs "$XMP_OUTPUT_PATH/libXMPCoreStatic.a" *.o
        rm -f *.o
        echo "  ✓ XMPCore built successfully"
    fi
    
    # 2. Build XMPFiles
    if [ ! -f "$XMP_OUTPUT_PATH/libXMPFilesStatic.a" ]; then
        echo "  Building XMPFiles..."
        
        INCLUDES_FILES="-I$XMP_TOOLKIT_DIR \
          -I$XMP_TOOLKIT_DIR/public/include \
          -I$XMP_TOOLKIT_DIR/public/include/client-glue \
          -I$XMP_TOOLKIT_DIR/source \
          -I$XMP_TOOLKIT_DIR/XMPFiles/source \
          -I$XMP_TOOLKIT_DIR/XMPFiles/source/FileHandlers \
          -I$XMP_TOOLKIT_DIR/XMPFiles/source/FormatSupport \
          -I$XMP_TOOLKIT_DIR/XMPFiles/source/NativeMetadataSupport \
          -I$XMP_TOOLKIT_DIR/XMPFiles/source/PluginHandler \
          -I$XMP_TOOLKIT_DIR/XMPFilesPlugins/api/source \
          -I$XMP_TOOLKIT_DIR/XMPFiles/resource/linux \
          -I$XMP_TOOLKIT_DIR/XMPCore/source \
          -I$XMP_TOOLKIT_DIR/XMPCore/resource/linux \
          -I$XMP_TOOLKIT_DIR/XMPCore/third-party/expat/public/lib \
          -I$XMP_TOOLKIT_DIR/XMPCore/third-party/boost \
          -I$XMP_TOOLKIT_DIR/third-party/zuid/interfaces \
          -I$XMP_TOOLKIT_DIR/third-party/zlib"

        DEFINES_FILES="-DUNIX_ENV=1 -DAdobePrivate=1 -DHAVE_EXPAT_CONFIG_H=1 -DXML_STATIC=1 -DXMP_64=1 -D__x86_64__=1 -DqLinux=1 -DqLinuxOS=1 -DXMP_COMPONENT_INT_NAMESPACE=AdobeXMPFiles_Int -DBUILDING_XMPFILES_LIB=1 -DBUILDING_XMPFILES_AS_STATIC=1 -DXMP_StaticBuild=1 -DXMP_BUILD_STATIC=1"

        rm -f *.o
        g++ $DEFINES_FILES $INCLUDES_FILES -c -O2 -fPIC -std=c++17 \
          $XMP_TOOLKIT_DIR/XMPFiles/source/*.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/FileHandlers/*.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/FormatSupport/*.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/FormatSupport/AIFF/*.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/FormatSupport/IFF/*.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/FormatSupport/WAVE/*.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/FormatSupport/WebP/*.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/NativeMetadataSupport/*.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/PluginHandler/FileHandlerInstance.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/PluginHandler/HostAPIImpl.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/PluginHandler/Module.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/PluginHandler/PluginManager.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/PluginHandler/XMPAtoms.cpp \
          $XMP_TOOLKIT_DIR/XMPFiles/source/PluginHandler/OS_Utils_Linux.cpp \
          $XMP_TOOLKIT_DIR/source/Host_IO-POSIX.cpp \
          $XMP_TOOLKIT_DIR/source/IOUtils.cpp \
          $XMP_TOOLKIT_DIR/source/PerfUtils.cpp \
          $XMP_TOOLKIT_DIR/source/SafeStringAPIs.cpp \
          $XMP_TOOLKIT_DIR/source/XIO.cpp \
          $XMP_TOOLKIT_DIR/source/XMPFiles_IO.cpp \
          $XMP_TOOLKIT_DIR/source/XMP_ProgressTracker.cpp

        gcc -c -O2 -fPIC -I$XMP_TOOLKIT_DIR/third-party/zlib $XMP_TOOLKIT_DIR/third-party/zlib/*.c

        ar rcs "$XMP_OUTPUT_PATH/libXMPFilesStatic.a" *.o
        rm -f *.o
        echo "  ✓ XMPFiles built successfully"
    fi
    
    cd "$CACHE_ABS_PATH"
    rm -rf "$TEMP_BUILD_DIR"
    echo "  ✓ All XMP libraries built successfully"
}

# Main build process
echo "Starting dependency builds..."

build_jpeg_xl
build_xmp

echo "✓ All Linux dependencies built successfully"

# List built libraries for verification
echo "Built library files:"
find "$CACHE_ABS_PATH" -name "*.a" | head -10
echo "DNG SDK location: $DNG_SDK_ROOT"
