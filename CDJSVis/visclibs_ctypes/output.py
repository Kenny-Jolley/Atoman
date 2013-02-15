
"""
Wrapper to output.c

@author: Chris Scott

"""
import os
import sys
import platform

from ctypes import CDLL, c_double, POINTER, c_int, c_char_p, c_char

from .numpy_utils import CPtrToDouble, CPtrToInt, CPtrToChar


################################################################################

# load lib (this is messy!!)
osname = platform.system()
if osname == "Darwin":
    try:
        if hasattr(sys, "_MEIPASS"):
            _lib = CDLL(os.path.join(sys._MEIPASS, "_output.dylib"))
        else:
            _lib = CDLL("_output.dylib")
    except OSError:
        _lib = CDLL(os.path.join(os.path.dirname(__file__), "_output.dylib"))

elif osname == "Linux":
    _lib = CDLL("_output.so")

################################################################################

# read ref prototype
_lib.writeLattice.restype = c_int
_lib.writeLattice.argtypes = [c_char_p, c_int, POINTER(c_int), POINTER(c_double), POINTER(c_char), 
                              POINTER(c_int), POINTER(c_double), POINTER(c_double)]

# read ref
def writeLattice(filename, visibleAtoms, cellDims, specieList, specie, pos, charge):
    """
    Read LBOMD ref file.
    
    """
    return _lib.writeLattice(filename, len(visibleAtoms), CPtrToInt(visibleAtoms), CPtrToDouble(cellDims), CPtrToChar(specieList), 
                             CPtrToInt(specie), CPtrToDouble(pos), CPtrToDouble(charge))

################################################################################

# write pov defects prototype
_lib.writePOVRAYDefects.restype = c_int
_lib.writePOVRAYDefects.argtypes = [c_char_p, c_int, POINTER(c_int), c_int, POINTER(c_int), c_int, POINTER(c_int), c_int, POINTER(c_int), 
                                    POINTER(c_int), POINTER(c_double), POINTER(c_int), POINTER(c_double), POINTER(c_double), POINTER(c_double), 
                                    POINTER(c_double), POINTER(c_double)]

# write pov defects
def writePOVRAYDefects(filename, vacs, ints, ants, onAnts, specie, pos, refSpecie, refPos, specieRGB, specieCovalentRadius,
                       refSpecieRGB, refSpecieCovalentRadius):
    """
    Read LBOMD ref file.
    
    """
    return _lib.writePOVRAYDefects(filename, len(vacs), CPtrToInt(vacs), len(ints), CPtrToInt(ints), len(ants), CPtrToInt(ants), 
                                   len(onAnts), CPtrToInt(onAnts), CPtrToInt(specie), CPtrToDouble(pos), CPtrToInt(refSpecie), 
                                   CPtrToDouble(refPos), CPtrToDouble(specieRGB), CPtrToDouble(specieCovalentRadius), 
                                   CPtrToDouble(refSpecieRGB), CPtrToDouble(refSpecieCovalentRadius))

