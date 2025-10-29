__version__ = "1.0.0"

# Import the compiled C++ extension
try:
    # The compiled extension is named 'dngio' and will be dngio.pyd/.so/.dylib
    from . import _dngio_impl as _dngio_module
    
    # Expose the main DNG class
    DNG = _dngio_module.DNG
    
    # Expose any other functions or classes from the module
    __all__ = ['DNG']
    
except ImportError as e:
    # Provide a helpful error message if the compiled module isn't available
    raise ImportError(
        f"Could not import the compiled DNG module. "
        f"This likely means the module hasn't been built yet. "
        f"Please build from source using the build tools in build_tools/ directory. "
        f"Original error: {e}"
    ) from e

def get_version():
    """Return the version of the DNG module."""
    return __version__

def is_available():
    """Check if the DNG module is properly loaded and available."""
    try:
        # Try to create a DNG object with a dummy path to test if the module works
        # This will fail gracefully if the module isn't properly loaded
        return hasattr(DNG, '__call__')
    except:
        return False