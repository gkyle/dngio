#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <stdexcept>
#include <vector>

#include "dng_exceptions.h"
#include "dng_file_stream.h"
#include "dng_host.h"
#include "dng_info.h"
#include "dng_mosaic_info.h"
#include "dng_negative.h"
#include "dng_image.h"
#include "dng_pixel_buffer.h"
#include "dng_image_writer.h"

namespace py = pybind11;

class DNG {
private:
    bool debug;
    std::string filename;
    dng_host host;
    AutoPtr<dng_negative> negative;
    bool processRGB;

    // Helper method to read and validate DNG file. Fails if DNG does not appear to contain raw CFA data.
    void parseDngFile() {
        dng_file_stream stream(filename.c_str());
        
        {
            dng_info info;
            info.Parse(host, stream);
            info.PostParse(host);
            
            if (!info.IsValidDNG()) {
                throw std::runtime_error("Invalid DNG file: " + filename);
            }
            
            negative.Reset(host.Make_dng_negative());
            negative->Parse(host, stream, info);
            negative->PostParse(host, stream, info);
            
            // Read raw image data
            negative->ReadStage1Image(host, stream, info);
            if (processRGB) {
              negative->BuildStage2Image(host);
              negative->BuildStage3Image(host);

              if (debug) {
                printf("Processed to Stage 3 RGB image\n");
              }
            }
        }
        
        // Validate raw image digest/checksum for data integrity
        try {
            negative->ValidateRawImageDigest(host);
            if (debug) {
                printf("Raw image digest validation: PASSED\n");
            }
        } catch (const dng_exception &e) {
            if (debug) {
                printf("Raw image digest validation: FAILED (error code: %d)\n", e.ErrorCode());
                printf("Warning: Raw image data may be corrupted or modified\n");
            }
            throw std::runtime_error("Raw image digest validation failed - data may be corrupted");
        }

        if (!processRGB) {
          // Validate CFA pattern exists
          const dng_mosaic_info* mosaic_info = negative->GetMosaicInfo();
          if (mosaic_info == NULL) {
            throw std::runtime_error(
                "No CFA pattern found - this is not raw sensor data");
          }

          if (debug) {
            printf("CFA pattern detected: %u x %u\n",
                   mosaic_info->fCFAPatternSize.h,
                   mosaic_info->fCFAPatternSize.v);
          }
        }

        const dng_image &raw_image = negative->RawImage();
        uint32 channels = raw_image.Planes();
        
        if (debug) {
            printf("Image - Width: %u, Height: %u, Channels: %u\n", 
                   raw_image.Width(), raw_image.Height(), channels);
        }

        if (processRGB) {
          if (channels != 3) {
            throw std::runtime_error(
                "Expected 3-channel RGB data after processing, but found "
                "different number of channels");
          }
        } else {
          if (channels != 1) {
            throw std::runtime_error(
                "Expected single-channel CFA data, but found multiple "
                "channels");
          }
        }
    }

    // Helper method to create and configure a pixel buffer for raw data
    void createPixelBuffer(dng_pixel_buffer& buffer, const dng_rect& bounds,
                           uint32 width, uint32 height, uint32 channels,
                           void* data) {
      buffer.fArea = bounds;
      buffer.fPlane = 0;
      buffer.fPlanes = channels;
      buffer.fRowStep = width * channels;
      buffer.fColStep = channels;
      buffer.fPlaneStep = 1;
      buffer.fPixelType = ttShort;
      buffer.fPixelSize = 2;
      buffer.fData = data;
    }

public:
 DNG(const std::string& dngFilename)
     : debug(false), filename(dngFilename), processRGB(false) {
   parseDngFile();
 }

    DNG(const std::string& dngFilename, bool processRGB)
        : debug(false), filename(dngFilename), processRGB(processRGB) {
      parseDngFile();
    }

    DNG(const std::string& dngFilename, bool processRGB, bool enableDebug)
        : debug(enableDebug), filename(dngFilename), processRGB(processRGB) {
      parseDngFile();
    }

    void setDebug(bool enable) {
        debug = enable;
    }

    // Return data from DNG file as numpy array
    py::array_t<uint16_t> readRawData() {
        const dng_image &raw_image = negative->RawImage();
        uint32 width = raw_image.Width();
        uint32 height = raw_image.Height();

        // Configure pixel buffer for data using helper
        dng_rect bounds = raw_image.Bounds();
        dng_pixel_buffer buffer;
        uint32 channels = 1;
        if (processRGB) {
          channels = 3;
        }

        // Extract image data
        std::vector<uint16_t> raw_data(width * height * channels);
        createPixelBuffer(buffer, bounds, width, height, channels,
                          raw_data.data());
        raw_image.Get(buffer, dng_image::edge_none);

        if (processRGB) {
          // Return as 3D numpy array (height, width, channels)
          return py::array_t<uint16_t>(
              {height, width, channels},
              {width * channels * sizeof(uint16_t), channels * sizeof(uint16_t),
               sizeof(uint16_t)},
              raw_data.data());
        } else {
          // Return as 2D numpy array (height, width)
          return py::array_t<uint16_t>(
              {height, width}, {width * sizeof(uint16_t), sizeof(uint16_t)},
              raw_data.data());
        }
    }

    // Replace raw image data in a DNG file with numpy array data
    bool replaceRawData(py::array_t<uint16_t> newRawData, const char* outputDngPath) {
      if (processRGB) {
        throw std::runtime_error(
            "Replacing raw data is only supported for single-channel CFA data");
      }

        if (debug) {
            printf("Replacing raw data: %s -> %s\n", filename.c_str(), outputDngPath);
        }

        // Validate input array
        py::buffer_info buf = newRawData.request();
        if (buf.ndim != 2) {
            throw std::runtime_error("Input array must be 2-dimensional (height, width)");
        }

        uint32 newHeight = static_cast<uint32>(buf.shape[0]);
        uint32 newWidth = static_cast<uint32>(buf.shape[1]);
        uint16_t* newData = static_cast<uint16_t*>(buf.ptr);

        const dng_image &originalRaw = negative->RawImage();
        uint32 originalWidth = originalRaw.Width();
        uint32 originalHeight = originalRaw.Height();
        
        if (newWidth != originalWidth || newHeight != originalHeight) {
            throw std::runtime_error("New raw data dimensions (" + std::to_string(newWidth) + "x" + std::to_string(newHeight) + 
                                   ") don't match original (" + std::to_string(originalWidth) + "x" + std::to_string(originalHeight) + ")");
        }

        try {
            // Get a mutable reference to the raw image
            dng_image &mutableRawImage = const_cast<dng_image&>(negative->RawImage());
            
            // Create a pixel buffer to write the new data using helper
            dng_rect bounds = mutableRawImage.Bounds();
            dng_pixel_buffer writeBuffer;
            createPixelBuffer(writeBuffer, bounds, newWidth, newHeight, 1,
                              newData);

            // Write the new data to the raw image
            mutableRawImage.Put(writeBuffer);
            
            // Clear the old raw image digests so they will be recomputed
            // This prevents "NewRawImageDigest does not match raw image" errors
            negative->ClearRawImageDigest();
            
            if (debug) {
                printf("Cleared old image digests - will recompute on write\n");
            }
            
            dng_file_stream outputStream(outputDngPath, true);
            dng_image_writer writer;
            writer.WriteDNG(host, outputStream, *negative.Get());
            
            if (debug) {
                printf("DNG file successfully written to disk!\n");
            }
            
            return true;
        } catch (const dng_exception& e) {
          throw std::runtime_error(
              "DNG SDK error during raw data replacement: " +
              std::to_string(e.ErrorCode()));
        } catch (const std::exception& e) {
          throw std::runtime_error("Error during raw data replacement: " +
                                   std::string(e.what()));
        }

        return false;
    }
    
    // Return mosaic pattern information as numpy array
    py::array_t<uint8_t> getMosaic() {
      if (processRGB) {
        throw std::runtime_error(
            "Mosaic pattern is only available for single-channel CFA data");
      }

        const dng_mosaic_info *mosaic_info = negative->GetMosaicInfo();
        if (mosaic_info == NULL) {
            throw std::runtime_error("No CFA pattern found - this is not raw sensor data");
        }

        uint32 pattern_height = mosaic_info->fCFAPatternSize.v;
        uint32 pattern_width = mosaic_info->fCFAPatternSize.h;
        
        if (debug) {
            printf("CFA pattern size: %u x %u\n", pattern_width, pattern_height);
        }

        // Copy mosaic pattern data
        std::vector<uint8_t> mosaic_data(pattern_width * pattern_height);
        for (uint32 row = 0; row < pattern_height; row++) {
            for (uint32 col = 0; col < pattern_width; col++) {
                mosaic_data[row * pattern_width + col] = mosaic_info->fCFAPattern[row][col];
            }
        }

        // Return as numpy array (height, width)
        return py::array_t<uint8_t>(
            {pattern_height, pattern_width},
            {pattern_width * sizeof(uint8_t), sizeof(uint8_t)},
            mosaic_data.data()
        );
    }
};

PYBIND11_MODULE(_dngio_impl, m) {
  py::class_<DNG>(m, "DNG")
      .def(py::init<const std::string&>())
      .def(py::init<const std::string&, bool>())
      .def(py::init<const std::string&, bool, bool>())
      .def("setDebug", &DNG::setDebug)
      .def("readRawData", &DNG::readRawData,
           "Read data from DNG file as numpy array")
      .def("replaceRawData", &DNG::replaceRawData,
           "Replace raw image data in a DNG file with numpy array data")
      .def("getMosaic", &DNG::getMosaic,
           "Get CFA mosaic pattern as numpy array");

#ifdef VERSION_INFO
	m.attr("__version__") = VERSION_INFO;
#else
	m.attr("__version__") = "dev";
#endif
}

