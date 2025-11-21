# DNGIO Python Module

A minimal Python wrapper around Adobe DNG SDK for reading and writing DNG files.

This is specifically designed for performing mutations on raw sensor data, then writing back into the original file structure. The functionality includes:
- Reading raw data from a DNG file.
- Writing raw data into a DNG file.
- Reading processed RGB data.

## Platform Support

| Platform | Architecture | Status |
|----------|--------------|--------|
| Windows  | AMD64/ARM64        | ✅ Supported |
| macOS    | x86_64/ARM64 | ✅ Supported |
| Linux    | x86_64       | ⏳ Not yet |

## Installation

### Option 1: Install from Wheels

Download the appropriate wheel for your platform from the [releases page](https://github.com/gkyle/dngio/releases):

```bash
pip install dngio-1.0.0-cp39-cp39-win_amd64.whl
```

### Option 2: Build from Source

```powershell
git clone https://github.com/gkyle/dngio.git
cd dngio
python build_tools/build.py
pip install .
```

The build script will:
1. Build external dependencies (Adobe DNG SDK, JPEG XL, etc.)
2. Compile the C++ extension
3. Copy the extension to the source directory
4. Create a wheel in the `wheels/` directory

## Quick Start

### Read Raw CFA Data

```python
import dngio
import numpy as np

dng_reader = dngio.DNG("path/to/image.dng")
raw_data = dng_reader.readRawData()
print(f"Raw data shape: {raw_data.shape}")
```

The returned value is a 2D numpy-compatible matrix of single-channel values.

### Replace Raw Data
```python
import dngio
import numpy as np

dng = dngio.DNG("path/to/image.dng")
raw_data = dng.readRawData()
modified_data = np.clip(raw_data * 1.2, 0, 65535).astype(np.uint16) # increase brightness
dng.replaceRawData(modified_data, "path/to/newimage.dng")
```

### Read RGB Data

In the Adobe DNG SDK, file processing is stateful. If the file is fully "Stage 3" processed into demosaic RGB, we can't access the single channel raw data without resetting and "Stage 1" processing the file again. To keep things simple, in the dngio API, an instance of DNG is instantiated *either* to access raw *or* RGB data.

The replaceRawData() and getMosaic() methods are not available in RGB mode.

```python
import dngio
import numpy as np

rgb_reader = dngio.DNG("path/to/image.dng", process_rgb=True)
rgb_data = rgb_reader.readRawData()

print(f"RGB data shape: {rgb_data.shape}")
```

The returned value is a 3D numpy-compatible matrix of RGB values.
