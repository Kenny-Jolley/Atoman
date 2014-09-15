
/*******************************************************************************
 ** Copyright Chris Scott 2011
 ** IO routines written in C to improve performance
 *******************************************************************************/

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <errno.h>
#include "input.h"


static int specieIndex(char*, int, char*);


/*******************************************************************************
 * Update specie list and counter
 *******************************************************************************/
static int specieIndex(char* sym, int NSpecies, char* specieList)
{
    int index, j, comp;
    
    
    index = NSpecies;
    for (j=0; j<NSpecies; j++)
    {
        comp = strcmp( &specieList[3*j], &sym[0] );
        if (comp == 0)
        {
            index = j;
            
            break;
        }
    }
    
    return index;
}


/*******************************************************************************
** read animation-reference file
*******************************************************************************/
int readRef(char* file, int* atomID, int* specie, double* pos, double* charge, double* KE, double* PE, double* force, 
            char* specieList_c, int* specieCount_c, double* maxPos, double* minPos)
{
    int i, NAtoms, specInd, stat;
    FILE *INFILE;
    double xdim, ydim, zdim;
    char symtemp[3];
    char* specieList;
    double xpos, ypos, zpos;
    double xforce, yforce, zforce;
    int id, index;
    double ketemp, petemp, chargetemp;
    int NSpecies;
    
    
    INFILE = fopen( file, "r" );
    if (INFILE == NULL)
    {
        printf("ERROR: could not open file: %s\n", file);
        printf("       reason: %s\n", strerror(errno));
        exit(35);
    }
    
    stat = fscanf(INFILE, "%d", &NAtoms);
    if (stat != 1)
        return -3;
    
    stat = fscanf(INFILE, "%lf%lf%lf", &xdim, &ydim, &zdim);
    if (stat != 3)
        return -3;
    
    specieList = malloc(3 * sizeof(char));
    
    minPos[0] = 1000000;
    minPos[1] = 1000000;
    minPos[2] = 1000000;
    maxPos[0] = -1000000;
    maxPos[1] = -1000000;
    maxPos[2] = -1000000;
    NSpecies = 0;
    for (i=0; i<NAtoms; i++)
    {
        stat = fscanf(INFILE, "%d%s%lf%lf%lf%lf%lf%lf%lf%lf%lf", &id, symtemp, &xpos, &ypos, &zpos, &ketemp, &petemp, &xforce, &yforce, &zforce, &chargetemp);
        if (stat != 11)
            return -3;
        
        /* index for storage is (id-1) */
        index = id - 1;
        
        atomID[index] = id;
        
        pos[3*index] = xpos;
        pos[3*index+1] = ypos;
        pos[3*index+2] = zpos;
        
        KE[index] = ketemp;
        PE[index] = petemp;
        
//        force[3*index] = xforce;
//        force[3*index+1] = yforce;
//        force[3*index+2] = zforce;
        
        charge[index] = chargetemp;
        
        /* find specie index */
        specInd = specieIndex(symtemp, NSpecies, specieList);
        
        specie[i] = specInd;
        
        if (specInd == NSpecies)
        {
            /* new specie */
            specieList = realloc( specieList, 3 * (NSpecies+1) * sizeof(char) );
            
            specieList[3*specInd] = symtemp[0];
            specieList[3*specInd+1] = symtemp[1];
            specieList[3*specInd+2] = symtemp[2];
            
            specieList_c[2*specInd] = symtemp[0];
            specieList_c[2*specInd+1] = symtemp[1];
            
            NSpecies++;
        }
        
        /* update specie counter */
        specieCount_c[specInd]++;
                
        /* max and min positions */
        if ( xpos > maxPos[0] )
        {
            maxPos[0] = xpos;
        }
        if ( ypos > maxPos[1] )
        {
            maxPos[1] = ypos;
        }
        if ( zpos > maxPos[2] )
        {
            maxPos[2] = zpos;
        }
        if ( xpos < minPos[0] )
        {
            minPos[0] = xpos;
        }
        if ( ypos < minPos[1] )
        {
            minPos[1] = ypos;
        }
        if ( zpos < minPos[2] )
        {
            minPos[2] = zpos;
        }
    }
    
    fclose(INFILE);
    
    /* terminate specie list */
    specieList_c[2*NSpecies] = 'X';
    specieList_c[2*NSpecies+1] = 'X';
    
    free(specieList);
    
    return 0;
}


/*******************************************************************************
** read xyz input file
*******************************************************************************/
int readLBOMDXYZ(char* file, int* atomID, double* pos, double* charge, double* KE, double* PE, 
                 double* force, double* maxPos, double* minPos, int xyzformat)
{
    FILE *INFILE;
    int i, index, id, NAtoms, stat;
    double simTime, xpos, ypos, zpos;
    double chargetmp, KEtmp, PEtmp;
//    double xfor, yfor, zfor;
    
    
    /* open file */
    INFILE = fopen(file, "r");
    if (INFILE == NULL)
    {
        printf("ERROR: could not open file: %s\n", file);
        printf("       reason: %s\n", strerror(errno));
        exit(35);
    }
    
    /* read header */
    stat = fscanf(INFILE, "%d", &NAtoms);
    if (stat != 1)
        return -3;
    
    stat = fscanf(INFILE, "%lf", &simTime);
    if (stat != 1)
        return -3;
        
    /* read atoms */
    minPos[0] = 1000000;
    minPos[1] = 1000000;
    minPos[2] = 1000000;
    maxPos[0] = -1000000;
    maxPos[1] = -1000000;
    maxPos[2] = -1000000;
    for (i=0; i<NAtoms; i++)
    {
        if (xyzformat == 0)
        {
            stat = fscanf(INFILE, "%d %lf %lf %lf %lf %lf", &id, &xpos, &ypos, &zpos, &KEtmp, &PEtmp);
            if (stat != 6)
                return -3;
        }
        else if (xyzformat == 1)
        {
            stat = fscanf(INFILE, "%d%lf%lf%lf%lf%lf%lf", &id, &xpos, &ypos, &zpos, &KEtmp, &PEtmp, &chargetmp);
            if (stat != 7)
                return -3;
        }
        
        index = id - 1;
        
        /* store data */
        atomID[index] = id;
        
        pos[3*index] = xpos;
        pos[3*index+1] = ypos;
        pos[3*index+2] = zpos;
        
        KE[index] = KEtmp;
        PE[index] = PEtmp;
        
        if (xyzformat == 1)
        {
            charge[index] = chargetmp;
        }
        
        /* max and min positions */
        if ( xpos > maxPos[0] )
        {
            maxPos[0] = xpos;
        }
        if ( ypos > maxPos[1] )
        {
            maxPos[1] = ypos;
        }
        if ( zpos > maxPos[2] )
        {
            maxPos[2] = zpos;
        }
        if ( xpos < minPos[0] )
        {
            minPos[0] = xpos;
        }
        if ( ypos < minPos[1] )
        {
            minPos[1] = ypos;
        }
        if ( zpos < minPos[2] )
        {
            minPos[2] = zpos;
        }
    }
    
    fclose(INFILE);
    
    return 0;
}


/*******************************************************************************
 * Read LBOMD lattice file
 *******************************************************************************/
int readLatticeLBOMD(char* file, int* atomID, int* specie, double* pos, double* charge, char* specieList_c, 
                     int* specieCount_c, double* maxPos, double* minPos)
{
    FILE *INFILE;
    int i, NAtoms, specInd;
    double xdim, ydim, zdim;
    char symtemp[3];
    char* specieList;
    double xpos, ypos, zpos, chargetemp;
    int NSpecies, stat;
    
    
    /* open file */
    INFILE = fopen( file, "r" );
    if (INFILE == NULL)
    {
        printf("ERROR: could not open file: %s\n", file);
        printf("       reason: %s\n", strerror(errno));
        exit(35);
    }
    
    /* read header */
    stat = fscanf( INFILE, "%d", &NAtoms );
    if (stat != 1)
        return -3;
    
    stat = fscanf(INFILE, "%lf %lf %lf", &xdim, &ydim, &zdim);
    if (stat != 3)
        return -3;
    
    /* allocate specieList */
    specieList = malloc( 3 * sizeof(char) );
    
    /* read in atoms */
    minPos[0] = 1000000;
    minPos[1] = 1000000;
    minPos[2] = 1000000;
    maxPos[0] = -1000000;
    maxPos[1] = -1000000;
    maxPos[2] = -1000000;
    NSpecies = 0;
    for (i=0; i<NAtoms; i++)
    {
        stat = fscanf(INFILE, "%s %lf %lf %lf %lf", symtemp, &xpos, &ypos, &zpos, &chargetemp);
        if (stat != 5)
            return -3;
        
        /* atom ID */
        atomID[i] = i + 1;
        
        /* store position and charge */
        pos[3*i] = xpos;
        pos[3*i+1] = ypos;
        pos[3*i+2] = zpos;
        
        charge[i] = chargetemp;
        
        /* find specie index */
        specInd = specieIndex(symtemp, NSpecies, specieList);
        
        specie[i] = specInd;
        
        if (specInd == NSpecies)
        {
            /* new specie */
            specieList = realloc( specieList, 3 * (NSpecies+1) * sizeof(char) );
            
            specieList[3*specInd] = symtemp[0];
            specieList[3*specInd+1] = symtemp[1];
            specieList[3*specInd+2] = symtemp[2];
            
            specieList_c[2*specInd] = symtemp[0];
            specieList_c[2*specInd+1] = symtemp[1];
            
            NSpecies++;
        }
        
        /* update specie counter */
        specieCount_c[specInd]++;
                
        /* max and min positions */
        if ( xpos > maxPos[0] )
        {
            maxPos[0] = xpos;
        }
        if ( ypos > maxPos[1] )
        {
            maxPos[1] = ypos;
        }
        if ( zpos > maxPos[2] )
        {
            maxPos[2] = zpos;
        }
        if ( xpos < minPos[0] )
        {
            minPos[0] = xpos;
        }
        if ( ypos < minPos[1] )
        {
            minPos[1] = ypos;
        }
        if ( zpos < minPos[2] )
        {
            minPos[2] = zpos;
        }
    }
    
    fclose(INFILE);
    
    /* terminate specie list */
    specieList_c[2*NSpecies] = 'X';
    specieList_c[2*NSpecies+1] = 'X';
        
    free(specieList);
    
    return 0;
}

