
/*******************************************************************************
 ** Copyright Chris Scott 2014
 ** Rendering routines written in C to improve performance
 *******************************************************************************/

#include <stdlib.h>
#include "numpy_utils.h"
#include "rendering.h"

/*******************************************************************************
 ** Split visible atoms by specie (position and scalar)
 *******************************************************************************/
int splitVisAtomsBySpecie(int NVisible, int* visibleAtoms, int NSpecies, int* specieArray, int* specieCount, double* pos, double* PE, double* KE, double* charge, double* scalars, int scalarType, int heightAxis, allocator_t allocator)
{
    int i, j, index, specie, count;
    int numpyDims[1], numpyDims2[2];
    double *speciePos, *specieScalars;
    double scalar;
    
    
    /* first pass to get counters, assume counter zeroed before */
    for (i = 0; i < NVisible; i++)
    {
        index = visibleAtoms[i];
        specie = specieArray[index];
        specieCount[specie]++;
    }
    
    /* loop over species */
    for (i = 0; i < NSpecies; i++)
    {
        /* allocate position array */
        numpyDims2[0] = specieCount[i];
        numpyDims2[1] = 3;
        speciePos = (double*) allocator("", 2, numpyDims2, 'd');
        
        /* allocate position array */
        numpyDims[0] = specieCount[i];
        specieScalars = (double*) allocator("", 1, numpyDims, 'd');
        
        /* loop over atoms */
        count = 0;
        for (j = 0; j < NVisible; j++)
        {
            index = visibleAtoms[j];
            specie = specieArray[index];
            
            if (specie == i)
            {
                /* position */
                speciePos[3*count+0] = pos[3*index+0];
                speciePos[3*count+1] = pos[3*index+1];
                speciePos[3*count+2] = pos[3*index+2];
                
                /* scalar */
                if (scalarType == 0)
                {
                    scalar = specie;
                }
                else if (scalarType == 1)
                {
                    scalar = pos[3*index+heightAxis];
                }
                else if (scalarType == 2)
                {
                    scalar = KE[index];
                }
                else if (scalarType == 3)
                {
                    scalar = PE[index];
                }
                else if (scalarType == 4)
                {
                    scalar = charge[index];
                }
                else
                {
                    scalar = scalars[j];
                }
                
                specieScalars[count] = scalar;
                
                count++;
            }
        }
        
        /* deref */
        speciePos = NULL;
        specieScalars = NULL;
    }
    
    return 0;
}
