###
# DNG SDK External Dependencies Build Script
# Fetches Adobe DNG SDK and builds required external dependencies using Visual Studio with example DNG Validator project.
#
### Prerequisites
# - Windows 10/11
# - Visual Studio 2022 Community (with C++ build tools)
#
### Core Dependencies built:
# - jxl.lib - JPEG XL compression support
# - brotli.lib - Brotli compression algorithm
# - highway.lib - SIMD optimization library
# - libjpeg.lib - JPEG compression (custom built from source)
#
### XMP Toolkit:
# - XMPCoreStaticRelease.lib - XMP metadata core functionality
# - XMPFilesStaticRelease.lib - XMP file handling


param(
    [string]$Configuration = "Validate Release",
    [string]$Platform = "x64",
    [switch]$Force = $false
)

$CACHE_DIR = ".cache"
$DNG_SDK_URL = "https://download.adobe.com/pub/adobe/dng/dng_sdk_1_7_1.zip"
$DNG_SDK_ZIP = "$CACHE_DIR\dng_sdk.zip"
$DNG_SDK_ROOT = "$CACHE_DIR\dng_sdk\dng_sdk_1_7_1"

Write-Host "DNG SDK External Dependencies Build Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Step 1: Detect Visual Studio
Write-Host "[1/8] Detecting Visual Studio..." -ForegroundColor Yellow
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vswhere) {
    $vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    $msbuildPath = "$vsPath\MSBuild\Current\Bin\MSBuild.exe"
} else {
    Write-Host "ERROR: Visual Studio not found" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $msbuildPath)) {
    Write-Host "ERROR: MSBuild not found" -ForegroundColor Red
    exit 1
}
Write-Host "  Found MSBuild: $msbuildPath" -ForegroundColor Green

# Step 2: Create cache directory
Write-Host "[2/8] Creating cache directory..." -ForegroundColor Yellow
if (-not (Test-Path $CACHE_DIR)) {
    New-Item -ItemType Directory -Path $CACHE_DIR | Out-Null
}
Write-Host "  Cache directory ready" -ForegroundColor Green

# Step 3: Download DNG SDK
Write-Host "[3/8] Downloading DNG SDK..." -ForegroundColor Yellow
if (-not (Test-Path $DNG_SDK_ZIP) -or $Force) {
    Write-Host "  Downloading from Adobe..." -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri $DNG_SDK_URL -OutFile $DNG_SDK_ZIP -UseBasicParsing
        Write-Host "  Downloaded successfully" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Download failed: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  Using existing download" -ForegroundColor Green
}

# Step 4: Extract DNG SDK
Write-Host "[4/8] Extracting DNG SDK..." -ForegroundColor Yellow
if (-not (Test-Path $DNG_SDK_ROOT) -or $Force) {
    try {
        if (Test-Path "$CACHE_DIR\dng_sdk") {
            Remove-Item "$CACHE_DIR\dng_sdk" -Recurse -Force
        }
        Expand-Archive -Path $DNG_SDK_ZIP -DestinationPath "$CACHE_DIR\dng_sdk" -Force
        Write-Host "  Extracted successfully" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Extraction failed: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  Using existing extraction" -ForegroundColor Green
}

# Step 5: Build external dependencies
Write-Host "[5/8] Building dependencies with MSBuild..." -ForegroundColor Yellow
$vsSolution = "$DNG_SDK_ROOT\dng_sdk\projects\win\dng_validate.sln"
if (-not (Test-Path $vsSolution)) {
    Write-Host "ERROR: Solution not found: $vsSolution" -ForegroundColor Red
    exit 1
}

try {
    & $msbuildPath $vsSolution "/p:Configuration=$Configuration" "/p:Platform=$Platform" "/m" "/verbosity:minimal"
    if ($LASTEXITCODE -ne 0) {
        throw "MSBuild failed"
    }
    Write-Host "  MSBuild completed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Build failed: $_" -ForegroundColor Red
    exit 1
}

# Step 6: Build libjpeg
Write-Host "[6/8] Building libjpeg..." -ForegroundColor Yellow

# Set up Visual Studio environment for command-line tools
$vsInstallPath = Split-Path -Parent $msbuildPath | Split-Path -Parent | Split-Path -Parent | Split-Path -Parent
$vcvarsPath = "$vsInstallPath\VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvarsPath)) {
    Write-Host "ERROR: vcvars64.bat not found at $vcvarsPath" -ForegroundColor Red
    exit 1
}
$libjpegDir = "$DNG_SDK_ROOT\libjpeg"
$libjpegLib = "$libjpegDir\libjpeg.lib"

if (-not (Test-Path $libjpegLib) -or $Force) {
    try {
        Push-Location $libjpegDir
        # Only compile core library files, exclude platform-specific and example files
        $sourceFiles = @(
            "jaricom.c", "jcapimin.c", "jcapistd.c", "jcarith.c", "jccoefct.c", 
            "jccolor.c", "jcdctmgr.c", "jchuff.c", "jcinit.c", "jcmainct.c", 
            "jcmarker.c", "jcmaster.c", "jcomapi.c", "jcparam.c", "jcprepct.c", 
            "jcsample.c", "jctrans.c", "jdapimin.c", "jdapistd.c", "jdarith.c", 
            "jdatadst.c", "jdatasrc.c", "jdcoefct.c", "jdcolor.c", "jddctmgr.c", 
            "jdhuff.c", "jdinput.c", "jdmainct.c", "jdmarker.c", "jdmaster.c", 
            "jdmerge.c", "jdpostct.c", "jdsample.c", "jdtrans.c", "jerror.c", 
            "jfdctflt.c", "jfdctfst.c", "jfdctint.c", "jidctflt.c", "jidctfst.c", 
            "jidctint.c", "jmemmgr.c", "jmemnobs.c", "jquant1.c", "jquant2.c", 
            "jutils.c"
        )
        
        # Run compiler with VS environment
        $compileCmd = "`"$vcvarsPath`" && cl /c /nologo /O2 /MT " + ($sourceFiles -join " ")
        cmd /c $compileCmd
        if ($LASTEXITCODE -ne 0) { throw "Compile failed" }
        
        $objFiles = Get-ChildItem -Filter "*.obj" | ForEach-Object { $_.Name }
        $libCmd = "`"$vcvarsPath`" && lib /nologo /out:libjpeg.lib " + ($objFiles -join " ")
        cmd /c $libCmd
        if ($LASTEXITCODE -ne 0) { throw "Library creation failed" }
        
        Remove-Item "*.obj" -Force -ErrorAction SilentlyContinue
        Write-Host "  libjpeg.lib created" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: libjpeg build failed: $_" -ForegroundColor Red
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  Using existing libjpeg.lib" -ForegroundColor Green
}

# Step 7: Verify results
Write-Host "[7/8] Verifying libraries..." -ForegroundColor Yellow
# Libraries are built to Release directory regardless of configuration name
$libDir = "$DNG_SDK_ROOT\dng_sdk\projects\win\$Platform\Release"
$xmpLibDir = "$DNG_SDK_ROOT\xmp\toolkit\public\libraries\windows_$Platform\Release"

$requiredLibs = @("jxl.lib", "brotli.lib", "highway.lib")
$requiredXmpLibs = @("XMPCoreStaticRelease.lib", "XMPFilesStaticRelease.lib")
$allGood = $true

foreach ($lib in $requiredLibs) {
    $libPath = "$libDir\$lib"
    if (Test-Path $libPath) {
        Write-Host "  Found: $lib" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $lib" -ForegroundColor Red
        $allGood = $false
    }
}

foreach ($lib in $requiredXmpLibs) {
    $libPath = "$xmpLibDir\$lib"
    if (Test-Path $libPath) {
        Write-Host "  Found: $lib" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $lib" -ForegroundColor Red
        $allGood = $false
    }
}

if (Test-Path $libjpegLib) {
    Write-Host "  Found: libjpeg.lib" -ForegroundColor Green
} else {
    Write-Host "  MISSING: libjpeg.lib" -ForegroundColor Red
    $allGood = $false
}

# Step 8: Final result
Write-Host "[8/8] Build complete!" -ForegroundColor Yellow
if ($allGood) {
    Write-Host ""
    Write-Host "SUCCESS: All dependencies built!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "FAILED: Some libraries missing" -ForegroundColor Red
    exit 1
}