#!/usr/bin/env python3
"""
Test suite for dngio module.
"""

import pytest
import numpy as np
import os
import tempfile
from pathlib import Path

import dngio

# Test data file path
TEST_DNG_FILE = "tests/data/03_jxl_bayer_raw_integer.dng"


@pytest.fixture
def dng_file():
    """Fixture providing path to test DNG file."""
    if not os.path.exists(TEST_DNG_FILE):
        pytest.skip(f"Test DNG file not found: {TEST_DNG_FILE}")
    return TEST_DNG_FILE


@pytest.fixture
def dng_object(dng_file):
    """Fixture providing initialized DNG object."""
    return dngio.DNG(dng_file, False, True)


@pytest.fixture
def reference_data(dng_object):
    """Fixture providing reference raw data for tests."""
    return dng_object.readRawData()


@pytest.fixture
def temp_output_file():
    """Fixture providing temporary output file path."""
    with tempfile.NamedTemporaryFile(suffix='.dng', delete=False) as tmp:
        tmp_path = tmp.name
    yield tmp_path
    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


class TestDNGIO:
    """Test suite for dngio module core functionality."""

    def test_module_import_and_version(self):
        """Test 1: Module imports correctly and has version info."""
        assert hasattr(dngio, 'DNG'), "DNG class not found in dngio module"
        assert hasattr(dngio, '__version__'), "Version info not found"
        assert isinstance(dngio.__version__, str), "Version should be a string"

    def test_dng_object_creation(self, dng_file):
        """Test 2: DNG object can be created with valid file."""
        dng = dngio.DNG(dng_file, False, True)
        assert dng is not None, "DNG object creation failed"

    def test_invalid_file_handling(self):
        """Test 3: Proper error handling for invalid files."""
        with pytest.raises(Exception):
            dngio.DNG("nonexistent_file.dng", False, True)

    def test_raw_data_reading(self, dng_object):
        """Test 4: Raw CFA data can be read successfully."""
        raw_data = dng_object.readRawData()
        
        assert raw_data is not None, "Raw data reading returned None"
        assert isinstance(raw_data, np.ndarray), "Raw data should be numpy array"
        assert raw_data.dtype == np.uint16, "Raw data should be uint16"
        assert raw_data.ndim == 2, "Raw data should be 2D array"
        assert raw_data.size > 0, "Raw data should not be empty"

    def test_mosaic_info_reading(self, dng_object):
        """Test 5: CFA pattern/mosaic info can be extracted."""
        mosaic_info = dng_object.getMosaic()
        
        assert mosaic_info is not None, "Mosaic info reading returned None"
        assert isinstance(mosaic_info, np.ndarray), "Mosaic info should be numpy array"
        assert mosaic_info.dtype == np.uint8, "Mosaic info should be uint8"
        assert mosaic_info.ndim == 2, "Mosaic info should be 2D array"
        assert mosaic_info.size > 0, "Mosaic info should not be empty"

    def test_raw_data_replacement(self, dng_object, reference_data, temp_output_file):
        """Test 6: Raw data can be modified and written to new file."""
        # Create modified data (simple brightness adjustment)
        modified_data = np.clip(reference_data * 1.2, 0, 65535).astype(np.uint16)
        
        # Test data replacement
        result = dng_object.replaceRawData(modified_data, temp_output_file)
        assert result is True, "Raw data replacement failed"
        assert os.path.exists(temp_output_file), "Output file was not created"
        assert os.path.getsize(temp_output_file) > 0, "Output file is empty"

    def test_data_integrity_round_trip(self, dng_object, reference_data, temp_output_file):
        """Test 7: Data integrity through read-modify-write-read cycle."""
        # Write modified data
        modified_data = np.clip(reference_data * 1.1, 0, 65535).astype(np.uint16)
        write_result = dng_object.replaceRawData(modified_data, temp_output_file)
        assert write_result is True, "Writing modified data failed"
        
        # Read it back
        verify_dng = dngio.DNG(temp_output_file, False, True)
        readback_data = verify_dng.readRawData()
        
        # Verify data integrity
        assert readback_data is not None, "Failed to read back written data"
        assert readback_data.shape == modified_data.shape, "Shape mismatch in round-trip"
        assert np.allclose(readback_data, modified_data, atol=1), "Data integrity lost in round-trip"

    def test_invalid_data_handling(self, dng_object, reference_data, temp_output_file):
        """Test 8: Proper handling of invalid input data."""
        # Test wrong shape - should raise RuntimeError
        wrong_shape_data = np.ones((100, 100), dtype=np.uint16)
        with pytest.raises(RuntimeError, match="dimensions.*don't match"):
            dng_object.replaceRawData(wrong_shape_data, temp_output_file)
        
        # Test wrong data type (should be handled gracefully)
        float_data = reference_data.astype(np.float64)
        result = dng_object.replaceRawData(float_data, temp_output_file)
        # Library should handle type conversion or reject gracefully
        assert isinstance(result, bool), "Should return boolean result for type conversion"

    def test_rgb_mode_functionality(self, dng_file):
        """Test 9: RGB mode object creation and data reading."""
        # Create RGB mode DNG object
        rgb_dng = dngio.DNG(dng_file, True, True)  # RGB mode enabled
        
        rgb_data = rgb_dng.readRawData()
        assert rgb_data is not None, "RGB data reading failed"
        assert isinstance(rgb_data, np.ndarray), "RGB data should be numpy array"
        assert rgb_data.dtype == np.uint16, "RGB data should be uint16"
        assert rgb_data.ndim == 3, "RGB data should be 3D array"
        assert rgb_data.shape[2] == 3, "RGB data should have 3 channels"

    def test_output_file_cleanup(self, dng_object, reference_data):
        """Test 10: Verify output files can be created and cleaned up properly."""
        test_files = []
        
        try:
            # Create multiple test files
            for i in range(3):
                temp_file = f"tests/data/expected_outputs/cleanup_test_{i}.dng"
                test_files.append(temp_file)
                
                # Ensure output directory exists
                os.makedirs(os.path.dirname(temp_file), exist_ok=True)
                
                # Create test file
                test_data = np.clip(reference_data * (1.0 + i * 0.1), 0, 65535).astype(np.uint16)
                result = dng_object.replaceRawData(test_data, temp_file)
                assert result is True, f"Failed to create test file {i}"
                assert os.path.exists(temp_file), f"Test file {i} was not created"
        
        finally:
            # Cleanup
            for test_file in test_files:
                if os.path.exists(test_file):
                    os.unlink(test_file)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])