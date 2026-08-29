#!/bin/bash
set -e

echo "Building macOS dependencies for dngio..."

# Resolve absolute path to cache directory (matching Windows build location)
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
        
        cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DJPEGXL_ENABLE_TOOLS=OFF -DBUILD_TESTING=OFF -DJPEGXL_ENABLE_SAMPLES=OFF -DJPEGXL_ENABLE_MANPAGES=OFF -DJPEGXL_ENABLE_BENCHMARK=OFF ..
        make -j$(sysctl -n hw.ncpu)
        echo "  ✓ JPEG XL built successfully"
    else
        echo "  ✓ JPEG XL already built"
    fi
}

# Build XMP libraries
build_xmp() {
    echo "Building XMP libraries..."
    
    # Look for XMP toolkit in the DNG SDK
    XMP_TOOLKIT_DIR="$DNG_SDK_ROOT/xmp/toolkit"
    
    # Check if toolkit directory exists
    if [ ! -d "$XMP_TOOLKIT_DIR" ]; then
        echo "  ✗ XMP toolkit directory not found: $XMP_TOOLKIT_DIR"
        exit 1
    fi
    
    echo "  ✓ Found XMP toolkit directory"
    
    # Output directory for built libraries
    XMP_OUTPUT_PATH="$DNG_SDK_ROOT/xmp/toolkit/public/libraries/mac/Release"
    mkdir -p "$XMP_OUTPUT_PATH"
    
    # Check if libraries already exist
    if [ -f "$XMP_OUTPUT_PATH/libXMPCoreStaticRelease.a" ] && [ -f "$XMP_OUTPUT_PATH/libXMPFilesStaticRelease.a" ]; then
        echo "  ✓ XMP libraries already built"
        return 0
    fi
    
    echo "  Building XMP libraries with xcodebuild..."
    
    # Build XMPCore
    XMPCORE_PROJECT="$XMP_TOOLKIT_DIR/XMPCore/build/CMake64_libcpp_Static/XMPCore64.xcodeproj"
    if [ -d "$XMPCORE_PROJECT" ]; then
        echo "  Building XMPCore..."
        xcodebuild -project "$XMPCORE_PROJECT" -scheme XMPCoreStatic -configuration Release -arch arm64 -arch x86_64 build
        
        # Copy built library to expected location
        # The library is built to toolkit/public/libraries/macintosh/intel_64_libcpp/Release/
        XMPCORE_BUILD_OUTPUT="$XMP_TOOLKIT_DIR/public/libraries/macintosh/intel_64_libcpp/Release"
        if [ -f "$XMPCORE_BUILD_OUTPUT/libXMPCoreStaticRelease.a" ]; then
            cp "$XMPCORE_BUILD_OUTPUT/libXMPCoreStaticRelease.a" "$XMP_OUTPUT_PATH/libXMPCoreStaticRelease.a"
            echo "  ✓ XMPCore built successfully"
        else
            echo "  ✗ XMPCore library not found after build"
            echo "  Expected at: $XMPCORE_BUILD_OUTPUT/libXMPCoreStaticRelease.a"
            ls -la "$XMPCORE_BUILD_OUTPUT" || echo "  Directory doesn't exist"
            exit 1
        fi
    else
        echo "  ✗ XMPCore project not found: $XMPCORE_PROJECT"
        exit 1
    fi
    
    # Build XMPFiles  
    XMPFILES_PROJECT="$XMP_TOOLKIT_DIR/XMPFiles/build/CMake64_libcpp_Static/XMPFiles64.xcodeproj"
    if [ -d "$XMPFILES_PROJECT" ]; then
        echo "  Building XMPFiles..."
        
        # Fix zutil.h header conflict before building
        ZUTIL_H="$XMP_TOOLKIT_DIR/third-party/zlib/zutil.h"
        if [ -f "$ZUTIL_H" ]; then
            # Check if any fdopen macros exist (with flexible whitespace)
            if grep -q "define.*fdopen" "$ZUTIL_H"; then
                echo "  Fixing zutil.h header conflict..."
                # Replace the three fdopen macro lines with comments
                cp "$ZUTIL_H" "$ZUTIL_H.bak"
                sed -i.tmp -e '140s/.*/#        \/* fdopen not available *\//' \
                           -e '167s/.*/#  \/* fdopen not available *\//' \
                           -e '172s/.*/#    \/* fdopen not available *\//' "$ZUTIL_H"
                rm -f "$ZUTIL_H.tmp"
            fi
        fi
        
        xcodebuild -project "$XMPFILES_PROJECT" -scheme XMPFilesStatic -configuration Release -arch arm64 -arch x86_64 build
        
        # Copy built library to expected location
        XMPFILES_BUILD_OUTPUT="$XMP_TOOLKIT_DIR/public/libraries/macintosh/intel_64_libcpp/Release"
        if [ -f "$XMPFILES_BUILD_OUTPUT/libXMPFilesStaticRelease.a" ]; then
            cp "$XMPFILES_BUILD_OUTPUT/libXMPFilesStaticRelease.a" "$XMP_OUTPUT_PATH/libXMPFilesStaticRelease.a"
            echo "  ✓ XMPFiles built successfully"
        else
            echo "  ✗ XMPFiles library not found after build"
            echo "  Expected at: $XMPFILES_BUILD_OUTPUT/libXMPFilesStaticRelease.a"
            ls -la "$XMPFILES_BUILD_OUTPUT" || echo "  Directory doesn't exist"
            exit 1
        fi
    else
        echo "  ✗ XMPFiles project not found: $XMPFILES_PROJECT"
        exit 1
    fi
    
    echo "  ✓ All XMP libraries built successfully"
}

# Main build process
echo "Starting dependency builds..."

build_jpeg_xl
build_xmp

echo "✓ All macOS dependencies built successfully"

# List built libraries for verification
echo "Built library files:"
find "$CACHE_ABS_PATH" -name "*.a" | head -10
echo "DNG SDK location: $DNG_SDK_ROOT"
