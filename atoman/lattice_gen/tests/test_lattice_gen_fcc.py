
"""
Unit tests for the FCC lattice generator

"""
from __future__ import absolute_import
from __future__ import unicode_literals
import unittest

import numpy as np

from ...system.lattice import Lattice
from .. import lattice_gen_fcc


################################################################################

class TestLatticeGenFCC(unittest.TestCase):
    """
    Test FCC lattice generator
    
    """
    def setUp(self):
        self.generator = lattice_gen_fcc.FCCLatticeGenerator()
    
    def tearDown(self):
        self.generator = None
    
    def test_latticeGenFCCPBC(self):
        """
        FCC lattice generator (PBCs)
        
        """
        args = lattice_gen_fcc.Args(sym="Au", NCells=[2, 2, 2], a0=3.0, pbcx=True, pbcy=True, pbcz=True)
        status, lattice = self.generator.generateLattice(args)
        
        pos = np.asarray([ 0. ,  0. ,  0. ,  0. ,  1.5,  1.5,  1.5,  0. ,  1.5,  1.5,  1.5,
                          0. ,  0. ,  0. ,  3. ,  0. ,  1.5,  4.5,  1.5,  0. ,  4.5,  1.5,
                          1.5,  3. ,  0. ,  3. ,  0. ,  0. ,  4.5,  1.5,  1.5,  3. ,  1.5,
                          1.5,  4.5,  0. ,  0. ,  3. ,  3. ,  0. ,  4.5,  4.5,  1.5,  3. ,
                          4.5,  1.5,  4.5,  3. ,  3. ,  0. ,  0. ,  3. ,  1.5,  1.5,  4.5,
                          0. ,  1.5,  4.5,  1.5,  0. ,  3. ,  0. ,  3. ,  3. ,  1.5,  4.5,
                          4.5,  0. ,  4.5,  4.5,  1.5,  3. ,  3. ,  3. ,  0. ,  3. ,  4.5,
                          1.5,  4.5,  3. ,  1.5,  4.5,  4.5,  0. ,  3. ,  3. ,  3. ,  3. ,
                          4.5,  4.5,  4.5,  3. ,  4.5,  4.5,  4.5,  3. ])
        
        self.assertEqual(status, 0)
        self.assertIsInstance(lattice, Lattice)
        self.assertEqual(lattice.NAtoms, 32)
        self.assertTrue(np.allclose(lattice.pos, pos))
        self.assertEqual(len(lattice.specieList), 1)
        self.assertEqual(lattice.specieList[0], "Au")
        self.assertEqual(len(lattice.specieCount), 1)
        self.assertEqual(lattice.specieCount[0], 32)
        self.assertTrue(np.allclose(lattice.specie, np.zeros(32, np.int32)))
        self.assertTrue(np.allclose(lattice.cellDims, [6,6,6]))
    
    def test_latticeGenFCCNoPBC(self):
        """
        FCC lattice generator (no PBCs)
        
        """
        args = lattice_gen_fcc.Args(sym="Sn", NCells=[1, 3, 2], a0=3.0, pbcx=False, pbcy=False, pbcz=False)
        status, lattice = self.generator.generateLattice(args)
        
        pos = np.asarray([ 0. ,  0. ,  0. ,  0. ,  1.5,  1.5,  1.5,  0. ,  1.5,  1.5,  1.5,
                          0. ,  0. ,  0. ,  3. ,  0. ,  1.5,  4.5,  1.5,  0. ,  4.5,  1.5,
                          1.5,  3. ,  0. ,  0. ,  6. ,  1.5,  1.5,  6. ,  0. ,  3. ,  0. ,
                          0. ,  4.5,  1.5,  1.5,  3. ,  1.5,  1.5,  4.5,  0. ,  0. ,  3. ,
                          3. ,  0. ,  4.5,  4.5,  1.5,  3. ,  4.5,  1.5,  4.5,  3. ,  0. ,
                          3. ,  6. ,  1.5,  4.5,  6. ,  0. ,  6. ,  0. ,  0. ,  7.5,  1.5,
                          1.5,  6. ,  1.5,  1.5,  7.5,  0. ,  0. ,  6. ,  3. ,  0. ,  7.5,
                          4.5,  1.5,  6. ,  4.5,  1.5,  7.5,  3. ,  0. ,  6. ,  6. ,  1.5,
                          7.5,  6. ,  0. ,  9. ,  0. ,  1.5,  9. ,  1.5,  0. ,  9. ,  3. ,
                          1.5,  9. ,  4.5,  0. ,  9. ,  6. ,  3. ,  0. ,  0. ,  3. ,  1.5,
                          1.5,  3. ,  0. ,  3. ,  3. ,  1.5,  4.5,  3. ,  0. ,  6. ,  3. ,
                          3. ,  0. ,  3. ,  4.5,  1.5,  3. ,  3. ,  3. ,  3. ,  4.5,  4.5,
                          3. ,  3. ,  6. ,  3. ,  6. ,  0. ,  3. ,  7.5,  1.5,  3. ,  6. ,
                          3. ,  3. ,  7.5,  4.5,  3. ,  6. ,  6. ,  3. ,  9. ,  0. ,  3. ,
                          9. ,  3. ,  3. ,  9. ,  6. ])

        
        self.assertEqual(status, 0)
        self.assertIsInstance(lattice, Lattice)
        self.assertEqual(lattice.NAtoms, 53)
        self.assertTrue(np.allclose(lattice.pos, pos))
        self.assertEqual(len(lattice.specieList), 1)
        self.assertEqual(lattice.specieList[0], "Sn")
        self.assertEqual(len(lattice.specieCount), 1)
        self.assertEqual(lattice.specieCount[0], 53)
        self.assertTrue(np.allclose(lattice.specie, np.zeros(53, np.int32)))
        self.assertTrue(np.allclose(lattice.cellDims, [3,9,6]))
