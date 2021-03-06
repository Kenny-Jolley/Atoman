/*******************************************************************************
 ** Find defects functions
 *******************************************************************************/

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
//#define DEBUG
//#define DEBUGACNA

#include <Python.h> // includes stdio.h, string.h, errno.h, stdlib.h
#include <numpy/arrayobject.h>
#include <math.h>
#include "visclibs/boxeslib.h"
#include "visclibs/neb_list.h"
#include "visclibs/utilities.h"
#include "visclibs/array_utils.h"
#include "filtering/atom_structure.h"

#if PY_MAJOR_VERSION >= 3
    #define MOD_ERROR_VAL NULL
    #define MOD_SUCCESS_VAL(val) val
    #define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
    #define MOD_DEF(ob, name, doc, methods) \
        static struct PyModuleDef moduledef = { \
            PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
        ob = PyModule_Create(&moduledef);
#else
    #define MOD_ERROR_VAL
    #define MOD_SUCCESS_VAL(val)
    #define MOD_INIT(name) void init##name(void)
    #define MOD_DEF(ob, name, doc, methods) \
        ob = Py_InitModule3(name, methods, doc);
#endif

static PyObject* findDefects(PyObject*, PyObject*);
static int findDefectClusters(int, double *, int *, int *, struct Boxes *, double, double *, int *);
static int findDefectNeighbours(int, int, int, int *, double *, struct Boxes *, double, double *, int *);
static int basicDefectClassification(double, int, char *,int *, double *, int, char *, int *, double *, int *,
        double *, int *, int *, int *, int *, int *);
static int identifySplitInterstitials(int, int *, int, int *, int *, double *, double *, int *, double *, int *, double);
static int identifySplitInterstitialsOld(int, int *, int, int *, int *, double *, double *, int *, double *, int *, double);
static int refineDefectsUsingAcna(int, int *, int, int *, double, int *, double *, double *, double *, double *, int, int *);
static int refineDefectsUsingAcnaOld(int, int *, int, int *, double, int *, double *, double *, double *, double *, int, int *);
static int compare_two_nebs(const void *, const void *);
static int checkVacancyACNARecursive(int, int, int *, int *, int *, struct NeighbourList2 *, struct NeighbourList2 *, int *, int *);

/*******************************************************************************
 ** List of python methods available in this module
 *******************************************************************************/
static struct PyMethodDef module_methods[] = {
    {"findDefects", findDefects, METH_VARARGS, "Find point defects"},
    {NULL, NULL, 0, NULL}
};

/*******************************************************************************
 ** Module initialisation function
 *******************************************************************************/
MOD_INIT(_defects)
{
    PyObject *mod;
    
    MOD_DEF(mod, "_defects", "Defects C extension", module_methods)
    if (mod == NULL)
        return MOD_ERROR_VAL;
    
    import_array();
    
    return MOD_SUCCESS_VAL(mod);
}

/*******************************************************************************
 * do the basic defect classification: vacancy/interstitial/antisite
 *******************************************************************************/
static int
basicDefectClassification(double vacancyRadius, int NAtoms, char *specieList, int* specie, double *pos,
        int refNAtoms, char *specieListRef, int *specieRef, double *refPos, int *PBC, double *cellDims,
        int *counters, int *vacancies, int *interstitials, int *antisites, int *onAntisites)
{
    int boxstat, i;
    int *possibleVacancy, *possibleInterstitial;
    int *possibleAntisite, *possibleOnAntisite;
    int NVacancies, NInterstitials, NAntisites;
    double approxBoxWidth, vacRad2;
    struct Boxes *boxes;
    
    
    /* approx width, must be at least vacRad
     * should vary depending on size of cell
     * ie. don't want too many boxes
     */
    approxBoxWidth = (vacancyRadius > 3.0) ? vacancyRadius : 3.0;
    
    /* box atoms */
    boxes = setupBoxes(approxBoxWidth, PBC, cellDims);
    if (boxes == NULL) return 1;
    boxstat = putAtomsInBoxes(NAtoms, pos, boxes);
    if (boxstat) return 2;
    
    /* allocate local arrays for checking atoms */
    possibleVacancy = malloc(refNAtoms * sizeof(int));
    if (possibleVacancy == NULL)
    {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate possibleVacancy");
        freeBoxes(boxes);
        return 3;
    }
    
    possibleInterstitial = malloc(NAtoms * sizeof(int));
    if (possibleInterstitial == NULL)
    {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate possibleInterstitial");
        freeBoxes(boxes);
        free(possibleVacancy);
        return 4;
    }
    
    possibleAntisite = malloc(refNAtoms * sizeof(int));
    if (possibleAntisite == NULL)
    {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate possibleAntisite");
        freeBoxes(boxes);
        free(possibleInterstitial);
        free(possibleVacancy);
        return 5;
    }
    
    possibleOnAntisite = malloc(refNAtoms * sizeof(int));
    if (possibleOnAntisite == NULL)
    {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate possibleOnAntisite");
        freeBoxes(boxes);
        free(possibleAntisite);
        free(possibleInterstitial);
        free(possibleVacancy);
        return 6;
    }
    
    /* initialise arrays */
    for (i = 0; i < NAtoms; i++) possibleInterstitial[i] = 1;
    for (i = 0; i < refNAtoms; i++)
    {
        possibleVacancy[i] = 1;
        possibleAntisite[i] = 1;
    }
    
    vacRad2 = vacancyRadius * vacancyRadius;
    
    /* loop over reference sites */
    for (i = 0; i < refNAtoms; i++)
    {
        int boxNebList[27], boxIndex, j, boxNebListSize;
        int nearestIndex = -1;
        int occupancyCount = 0;
        int i3 = 3 * i;
        double refxpos, refypos, refzpos;
        double nearestSep2 = 9999.0;

        refxpos = refPos[i3    ];
        refypos = refPos[i3 + 1];
        refzpos = refPos[i3 + 2];

        /* get box index of this atom */
        boxIndex = boxIndexOfAtom(refxpos, refypos, refzpos, boxes);
        if (boxIndex < 0)
        {
            freeBoxes(boxes);
            free(possibleAntisite);
            free(possibleInterstitial);
            free(possibleVacancy);
            free(possibleOnAntisite);
            return 7;
        }

        /* find neighbouring boxes */
        boxNebListSize = getBoxNeighbourhood(boxIndex, boxNebList, boxes);

//        printf("Checking site %d for occupancy (%lf, %lf, %lf)\n", i, refxpos, refypos, refzpos);
        
        /* loop over neighbouring boxes */
        for (j = 0; j < boxNebListSize; j++)
        {
            int checkBox, k;

            checkBox = boxNebList[j];

            /* loop over all input atoms in the box */
            for (k = 0; k < boxes->boxNAtoms[checkBox]; k++)
            {
                int index, index3;
                double xpos, ypos, zpos, sep2;

                /* index of this input atom */
                index = boxes->boxAtoms[checkBox][k];

                /* atom position */
                index3 = 3 * index;
                xpos = pos[index3    ];
                ypos = pos[index3 + 1];
                zpos = pos[index3 + 2];

                /* atomic separation of possible vacancy and possible interstitial */
                sep2 = atomicSeparation2(xpos, ypos, zpos, refxpos, refypos, refzpos,
                                         cellDims[0], cellDims[1], cellDims[2],
                                         PBC[0], PBC[1], PBC[2]);

                /* if within vacancy radius, is it an antisite or normal lattice point */
                if (sep2 < vacRad2)
                {
//                    printf("  Input atom %d within vac rad: sep = %lf (%lf, %lf, %lf)\n", index, sqrt(sep2), xpos, ypos, zpos);
                    
                    /* check whether this is the closest atom to this vacancy */
                    if (sep2 < nearestSep2)
                    {
                        /* assume that the vacancy radius is chosen so that atoms cannot belong to multiple sites */
                        //if (!possibleInterstitial[index])
                        //{
                        //    char errstring[256];
                        //    sprintf(errstring, "Input atom associated with multiple reference sites (index = %d, site = %d).", index, i);
                        //    PyErr_SetString(PyExc_RuntimeError, errstring);
                        //    freeBoxes(boxes);
                        //    free(possibleOnAntisite);
                        //    free(possibleAntisite);
                        //    free(possibleInterstitial);
                        //    free(possibleVacancy);
                        //    return 8;
                        //}

                        if (possibleInterstitial[index])
                        {
                            nearestSep2 = sep2;
                            nearestIndex = index;
                        }
                    }
                    
                    occupancyCount++;
                }
            }
        }

        /* classify - check the atom that was closest to this site (within the vacancy radius) */
        if (nearestIndex != -1)
        {
            char symtemp[3], symtemp2[3];
            int comp;
            
//            printf("Classifying site %d: nearest index = %d (sep = %lf)\n", i, nearestIndex, sqrt(nearestSep2));

            /* this site is filled; now we check if antisite or normal site */
            symtemp[0] = specieList[3*specie[nearestIndex]];
            symtemp[1] = specieList[3*specie[nearestIndex]+1];
            symtemp[2] = '\0';

            symtemp2[0] = specieListRef[3*specieRef[i]];
            symtemp2[1] = specieListRef[3*specieRef[i]+1];
            symtemp2[2] = '\0';

            comp = strcmp(symtemp, symtemp2);
            /* symbols match, so not antisite */
            if (comp == 0) possibleAntisite[i] = 0;
            /* symbols do not match => antisite */
            else possibleOnAntisite[i] = nearestIndex;

            /* not an interstitial or vacancy */
            possibleInterstitial[nearestIndex] = 0;
            possibleVacancy[i] = 0;

//            if (occupancyCount > 1)
//                printf("INFO: Occupancy for site %d = %d\n", i, occupancyCount);
        }
    }
    
    /* free box arrays */
    freeBoxes(boxes);

    /* now classify defects */
    NVacancies = 0;
    NInterstitials = 0;
    NAntisites = 0;
    for (i = 0; i < refNAtoms; i++ )
    {
        /* vacancies */
        if (possibleVacancy[i] == 1) vacancies[NVacancies++] = i;
        
        /* antisites */
        else if (possibleAntisite[i] == 1)
        {
            antisites[NAntisites] = i;
            onAntisites[NAntisites++] = possibleOnAntisite[i];
        }
    }
    
    /* interstitials */
    for (i = 0; i < NAtoms; i++ )
        if (possibleInterstitial[i] == 1) interstitials[NInterstitials++] = i;
    
    /* store counters */
    counters[0] = NVacancies;
    counters[1] = NInterstitials;
    counters[2] = NAntisites;
    
    /* free arrays */
    free(possibleVacancy);
    free(possibleInterstitial);
    free(possibleAntisite);
    free(possibleOnAntisite);
    
    return 0;
}

/*******************************************************************************
 ** Function that compares two elements in a neighbour list
 *******************************************************************************/
static int compare_two_nebs(const void * a, const void * b)
{
    const struct Neighbour *n1 = a;
    const struct Neighbour *n2 = b;
    
    if (n1->separation < n2->separation) return -1;
    else if (n1->separation > n2->separation) return 1;
    else return 0;
}

/*******************************************************************************
 * identify split interstitials (new)
 *******************************************************************************/
static int
identifySplitInterstitials(int NVacancies, int *vacancies, int NInterstitials, int *interstitials, int *splitInterstitials,
        double *pos, double *refPos, int *PBC, double *cellDims, int *counters, double vacancyRadius)
{
    int i, NSplit;
    double *intPos, *vacPos, maxSep;
    struct NeighbourList2 *nebListInts;
    struct NeighbourList2 *nebListVacs;
    

#ifdef DEBUG
    printf("DEFECTSC: Identifying split interstitials (new)\n");
#endif
    
    /* build positions array of all vacancies and interstitials */
    vacPos = malloc(3 * NVacancies * sizeof(double));
    if (vacPos == NULL)
    {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate vacPos");
        return 1;
    }
    intPos = malloc(3 * NInterstitials * sizeof(double));
    if (intPos == NULL)
    {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate intPos");
        free(vacPos);
        return 2;
    }
    
    /* add vacancy positions */
    for (i = 0; i < NVacancies; i++)
    {
        int index = vacancies[i];
        int index3 = 3 * index;
        int i3 = 3 * i;
        vacPos[i3    ] = refPos[index3    ];
        vacPos[i3 + 1] = refPos[index3 + 1];
        vacPos[i3 + 2] = refPos[index3 + 2];
    }
    
    /* interstitial positions */
    for (i = 0; i < NInterstitials; i++)
    {
        int index = interstitials[i];
        int index3 = 3 * index;
        int i3 = i * 3;
        intPos[i3    ] = pos[index3    ];
        intPos[i3 + 1] = pos[index3 + 1];
        intPos[i3 + 2] = pos[index3 + 2];
    }
    
    /* max separation */
    maxSep = 2.0 * vacancyRadius;
    
    /* construct list of neighbouring interstitials for each vacancy */
    nebListVacs = constructNeighbourList2DiffPos(NVacancies, vacPos, NInterstitials, intPos, cellDims, PBC, maxSep);
    
    if (nebListVacs == NULL)
    {
        free(vacPos);
        free(intPos);
        return 3;
    }
    
    /* construct list of neighbouring vacancies for each interstitial */
    nebListInts = constructNeighbourList2DiffPos(NInterstitials, intPos, NVacancies, vacPos, cellDims, PBC, maxSep);
    
    /* free position arrays (only required for constructing neighbour lists) */
    free(intPos);
    free(vacPos);
    
    if (nebListInts == NULL)
    {
        freeNeighbourList2(nebListVacs, NVacancies);
        return 4;
    }
    
    /* sort the neighbour lists by separation */
    for (i = 0; i < NVacancies; i++)
        qsort(nebListVacs[i].neighbour, nebListVacs[i].neighbourCount, sizeof(struct Neighbour), compare_two_nebs);
    
    for (i = 0; i < NInterstitials; i++)
        qsort(nebListInts[i].neighbour, nebListInts[i].neighbourCount, sizeof(struct Neighbour), compare_two_nebs);
    
#ifdef DEBUGSPLIT
    printf("DEFECTSC: Vacancy neb lists\n");
    for (i = 0; i < NVacancies; i++)
    {
        int j;

        printf("DEFECTSC:   Vacancy %d\n", i);
        for (j = 0; j < nebListVacs[i].neighbourCount; j++)
        {
            struct Neighbour neb = nebListVacs[i].neighbour[j];
            printf("DEFECTSC:     Neb %d: int index %d; sep %lf\n", j, neb.index, neb.separation);
        }
    }

    printf("DEFECTSC: Interstitial neb lists\n");
    for (i = 0; i < NInterstitials; i++)
    {
        int j;

        printf("DEFECTSC:   Interstitial %d\n", i);
        for (j = 0; j < nebListInts[i].neighbourCount; j++)
        {
            struct Neighbour neb = nebListInts[i].neighbour[j];
            printf("DEFECTSC:     Neb %d: vac index %d; sep %lf\n", j, neb.index, neb.separation);
        }
    }
#endif
    
    /* loop over vacancies, checking if they belong to a split interstitial */
    NSplit = 0;
    for (i = 0; i < NVacancies; i++)
    {
        int numVacNebs;
        struct NeighbourList2 vacNebs;
        
        /* list of neighbouring interstitials for this vacancy */
        vacNebs = nebListVacs[i];
        numVacNebs = vacNebs.neighbourCount;
        
#ifdef DEBUGSPLIT
        printf("DEFECTSC: Checking if vacancy %d (%d) belongs to a split interstitial\n", i, vacancies[i]);
        printf("DEFECTSC:   Number of neighbouring interstitials: %d\n", numVacNebs);
#endif
        
        /* proceed only if have at least 2 neighbouring interstitials */
        if (numVacNebs > 1)
        {
            int j, splitCount, splitIndexes[2];
            
            /* loop over neighbouring interstitials until we find 2 interstitials that are closest
             * to this vacancy or we run out of neighbours
             */
            j = 0;
            splitCount = 0;
            while (j < numVacNebs && splitCount != 2)
            {
                struct Neighbour vacNeb = vacNebs.neighbour[j];
                struct NeighbourList2 intNebs = nebListInts[vacNeb.index];
                int numIntNebs = intNebs.neighbourCount;
                
                /* check if closest vacancy is this one */
                if (numIntNebs > 0 && intNebs.neighbour[0].index == i)
                {
                    splitIndexes[splitCount++] = vacNeb.index;
                    
#ifdef DEBUGSPLIT
                    printf("DEFECTSC:     Interstitial neighbour %d (%d) is closest to this vacancy (separation = %lf)\n", j, vacNeb.index, vacNeb.separation);
#endif
                }
                
                j++;
            }
            
            /* check if we have found a split interstitial */
            if (splitCount == 2)
            {
                int n3 = 3 * NSplit;
                
#ifdef DEBUGSPLIT
                printf("DEFECTSC:   Vacancy %d is split: %d, %d\n", i, splitIndexes[0], splitIndexes[1]);
#endif

                /* store vacancy in split interstitials array */
                splitInterstitials[n3] = vacancies[i];

                /* remove from vacancies array */
                vacancies[i] = -1;

                /* store interstitials */
                for (j = 0; j < 2; j++)
                {
                    int intIndex = splitIndexes[j];

                    /* store in split interstitials array */
                    splitInterstitials[n3 + j + 1] = interstitials[intIndex];

                    /* remove from interstitials array */
                    interstitials[intIndex] = -1;
                }
                
                NSplit++;
            }
            
        }
    }
    
#ifdef DEBUG
    printf("DEFECTSC: Found %d split interstitials\n", NSplit);
#endif
    
    /* free memory */
    freeNeighbourList2(nebListVacs, NVacancies);
    freeNeighbourList2(nebListInts, NInterstitials);
    
    if (NSplit)
    {
        int count, numIntIn = NInterstitials;
        
        /* recreate interstitials arrays */
        count = 0;
        for (i = 0; i < NInterstitials; i++)
            if (interstitials[i] != -1) interstitials[count++] = interstitials[i];
        NInterstitials = count;
        
        /* recreate vacancies array */
        count = 0;
        for (i = 0; i < NVacancies; i++)
            if (vacancies[i] != -1) vacancies[count++] = vacancies[i];
        NVacancies = count;

        /* sanity check */
        if (numIntIn != NInterstitials + NSplit * 2)
        {
            char errstring[256];
            sprintf(errstring, "Interstitial atoms lost/gained during split detection: %d + %d * 2 != %d (%d vacancies)", NInterstitials,
                    NSplit, numIntIn, NVacancies);
            PyErr_SetString(PyExc_RuntimeError, errstring);
            return 7;
        }
    }

    /* store counters */
    counters[0] = NVacancies;
    counters[1] = NInterstitials;
    counters[2] = NSplit;
    
    return 0;
}

/*******************************************************************************
 * identify split interstitials
 *******************************************************************************/
static int
identifySplitInterstitialsOld(int NVacancies, int *vacancies, int NInterstitials, int *interstitials, int *splitInterstitials,
       double *pos, double *refPos, int *PBC, double *cellDims, int *counters, double vacancyRadius)
{
   int i, count, NDefects, boxstat;
   int *NDefectsCluster, *defectClusterSplit, NClusters;
   int NVacNew, NIntNew, NSplitInterstitials;
   double *defectPos, splitIntRad;
   double approxBoxWidth;
   struct Boxes *boxes;
   

#ifdef DEBUG
   printf("DEFECTSC: Identifying split interstitials (old)\n");
#endif
   
   /* build positions array of all defects */
   NDefects = NVacancies + NInterstitials;
   defectPos = malloc(3 * NDefects * sizeof(double));
   if (defectPos == NULL)
   {
       PyErr_SetString(PyExc_MemoryError, "Could not allocate defectPos");
       return 1;
   }
   
   /* add defects positions: vac then int */
   count = 0;
   for (i = 0; i < NVacancies; i++)
   {
       int index = vacancies[i];
       int index3 = 3 * index;
       int c3 = count * 3;
       defectPos[c3    ] = refPos[index3    ];
       defectPos[c3 + 1] = refPos[index3 + 1];
       defectPos[c3 + 2] = refPos[index3 + 2];
       
       count++;
   }
   
   for (i = 0; i < NInterstitials; i++)
   {
       int index = interstitials[i];
       int index3 = 3 * index;
       int c3 = count * 3;
       defectPos[c3    ] = pos[index3    ];
       defectPos[c3 + 1] = pos[index3 + 1];
       defectPos[c3 + 2] = pos[index3 + 2];
       
       count++;
   }
   
   splitIntRad = 2.0 * vacancyRadius;
   
   /* box defects */
   approxBoxWidth = (splitIntRad < 3.0) ? 3.0 : splitIntRad;
   boxes = setupBoxes(approxBoxWidth, PBC, cellDims);
   if (boxes == NULL)
   {
       free(defectPos);
       return 2;
   }
   boxstat = putAtomsInBoxes(NDefects, defectPos, boxes);
   if (boxstat)
   {
       free(defectPos);
       return 3;
   }
   
   /* number of defects per cluster */
   NDefectsCluster = malloc(NDefects * sizeof(int));
   if (NDefectsCluster == NULL)
   {
       PyErr_SetString(PyExc_MemoryError, "Could not allocate NDefectsCluster");
       free(defectPos);
       freeBoxes(boxes);
       return 4;
   }
   
   /* cluster number */
   defectClusterSplit = malloc(NDefects * sizeof(int));
   if (defectClusterSplit == NULL)
   {
       PyErr_SetString(PyExc_MemoryError, "Could not allocate defectClusterSplit");
       free(defectPos);
       free(NDefectsCluster);
       freeBoxes(boxes);
       return 5;
   }
   
   /* find clusters */
   NClusters = findDefectClusters(NDefects, defectPos, defectClusterSplit, NDefectsCluster, boxes, splitIntRad, cellDims, PBC);
   
   /* free */
   freeBoxes(boxes);
   free(defectPos);
   
   if (NClusters < 0)
   {
       free(NDefectsCluster);
       free(defectClusterSplit);
       return 6;
   }
   
   NDefectsCluster = realloc(NDefectsCluster, NClusters * sizeof(int));
   if (NDefectsCluster == NULL)
   {
       PyErr_SetString(PyExc_MemoryError, "Could not reallocate NDefectsCluster");
       free(NDefectsCluster);
       free(defectClusterSplit);
       return 7;
   }
   
   NVacNew = NVacancies;
   NIntNew = NInterstitials;
   NSplitInterstitials = 0;
   
   /* find split ints */
   for (i = 0; i < NClusters; i++)
   {
       if (NDefectsCluster[i] == 3)
       {
           int j, vacCount, splitIndexes[3];

           /* check if 2 interstitials and 1 vacancy */
//                printf("  POSSIBLE SPLIT INTERSTITIAL\n");
           
           count = 0;
           vacCount = 0;
           for (j = 0; j < NDefects; j++)
           {
               if (defectClusterSplit[j] == i)
               {
                   if (j < NVacancies) vacCount++;
                   
                   splitIndexes[count] = j;
                   count++;
               }
           }
           
           if (vacCount == 1)
           {
//                    printf("    FOUND SPLIT INTERSTITIAL\n");
               
               /* indexes */
               count = 1;
               for (j = 0; j < 3; j++)
               {
                   int index;

                   index = splitIndexes[j];
                   
                   if (index < NVacancies)
                   {
                       int index2;

                       index2 = vacancies[index];
                       vacancies[index] = -1;
                       splitInterstitials[3*NSplitInterstitials] = index2;
                       NVacNew--;
                   }
                   else
                   {
                       int index2;

                       index2 = interstitials[index - NVacancies];
                       interstitials[index - NVacancies] = -1;
                       splitInterstitials[3*NSplitInterstitials+count] = index2;
                       NIntNew--;
                       count++;
                   }
               }
               NSplitInterstitials++;
           }
       }
   }
   
   /* free memory */
   free(defectClusterSplit);
   free(NDefectsCluster);
   
   /* recreate interstitials array */
   count = 0;
   for (i = 0; i < NInterstitials; i++)
   {
       if (interstitials[i] != -1)
       {
           interstitials[count] = interstitials[i];
           count++;
       }
   }
   NInterstitials = count;
   
   /* recreate vacancies array */
   count = 0;
   for (i = 0; i < NVacancies; i++)
   {
       if (vacancies[i] != -1)
       {
           vacancies[count] = vacancies[i];
           count++;
       }
   }
   NVacancies = count;

   /* store counters */
   counters[0] = NVacancies;
   counters[1] = NInterstitials;
   counters[2] = NSplitInterstitials;
   
   return 0;
}

/*******************************************************************************
 * check if vacancy is linked to an ACNA interstitial
 *******************************************************************************/
static int checkVacancyACNARecursive(int vacIndex, int numChanges, int *vacs, int *ints, int *acnaInts, struct NeighbourList2 *nebListVacs,
        struct NeighbourList2 *nebListInts, int *vacMask, int *intMask)
{
    int i, foundNeb;
    struct NeighbourList2 vacNebs;
    int numVacNebs, nebIndex = -1;
    
    
    /* return if this vacancy has already been checked */
    if (vacMask[vacIndex]) return numChanges;

    /* we are checking this vacancy now */
    vacMask[vacIndex] = 1;
    
    /* list of neighbouring interstitials for this vacancy */
    vacNebs = nebListVacs[vacIndex];
    numVacNebs = vacNebs.neighbourCount;
    
    /* skip if doesn't have any neighbouring interstitials */
    if (numVacNebs < 1) return numChanges;

#ifdef DEBUGACNA
    printf("DEFECTSC: Start checking vacancy %d (num int nebs %d)\n", vacIndex, numVacNebs);
#endif

    /* we loop over the neighbouring interstitials of this vacancy until we
     * we find a suitable neighbour or we run out of neighbours
     */
    i = 0;
    foundNeb = 0;
    while (foundNeb == 0 && i < numVacNebs)
    {
        int j;
        struct Neighbour vacNeb = vacNebs.neighbour[i];
        struct NeighbourList2 intNebs = nebListInts[vacNeb.index];
        int numIntNebs = intNebs.neighbourCount;
        
        /* check if this interstitial is closest to this vacancy */
        j = 0;
        while (intMask[vacNeb.index] == 0 && foundNeb == 0 && j < numIntNebs)
        {
            struct Neighbour intNeb = intNebs.neighbour[j];
            int vacIndex2 = intNeb.index;
            
            /* not the closest, so we check the vacancy that is closer */
            if (vacIndex2 != vacIndex)
            {
#ifdef DEBUGACNA
                printf("DEFECTSC: Need to check vacancy %d first (interstitial %d)\n", vacIndex2, vacNeb.index);
#endif

                /* call self */
                numChanges = checkVacancyACNARecursive(vacIndex2, numChanges, vacs, ints, acnaInts, nebListVacs, nebListInts, vacMask, intMask);
            }
            /* it is the closest, so we store it as possible split int atom with this vacancy */
            else 
            {
                foundNeb = 1;
                nebIndex = vacNeb.index;
            }
            
            j++;
        }
        
        i++;
    }
    
    /* check if this is a split interstitial */
    if (foundNeb)
    {
        int intIndex = acnaInts[nebIndex];
        
#ifdef DEBUGACNA
        printf("DEFECTSC: Vacancy %d combines with interstitial %d\n", vacIndex, intIndex);
#endif

        /* remove from vacancies array */
        vacs[vacIndex] = -1;

        /* remove from interstitials array */
        ints[intIndex] = -1;

        /* set mask */
        intMask[nebIndex] = 1;
        
        numChanges++;
    }
    
    return numChanges;
}

/*******************************************************************************
 * Use ACNA to refine the defects.
 * 
 * First we make a list of all interstitials that have the ideal ACNA value.
 * Next we build lists of neighbours for ints and vacs and sort these lists.
 * Looping over vacancies we find the closest int that is not closer to another
 * vac and mark as normal atoms
 *******************************************************************************/
static int
refineDefectsUsingAcna(int NVacancies, int *vacancies, int NInterstitials, int *interstitials, double vacancyRadius,
        int *PBC, double *cellDims, double *pos, double *refPos, double *acnaArray, int acnaStructureType, int *counters)
{
    int i;
    int numAcnaInts, *acnaInts;
    
    
#ifdef DEBUG
    printf("DEFECTSC: Refining defects using ACNA...\n");
#endif
    
    /* first we make a list of interstitials that have the ideal ACNA value */
    acnaInts = malloc(NInterstitials * sizeof(int));
    if (acnaInts == NULL)
    {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate acnaInts");
        return 101;
    }
    numAcnaInts = 0;
    for (i = 0; i < NInterstitials; i++)
    {
        int index = interstitials[i];
        int acnaVal = (int) acnaArray[index];
        /* we store the index in the interstitials array */
        if (acnaVal == acnaStructureType) acnaInts[numAcnaInts++] = i;
    }
    //TODO: realloc if different size
    
#ifdef DEBUG
    printf("DEFECTSC: Number of interstitials with ideal ACNA type: %d\n", numAcnaInts);
#endif
    
    if (numAcnaInts > 0 && NVacancies > 0)
    {
        int *intMask, *vacMask, numChanges;
        double *intPos, *vacPos, maxSep;
        struct NeighbourList2 *nebListInts;
        struct NeighbourList2 *nebListVacs;
        
        /* build positions array of all vacancies and interstitials */
        vacPos = malloc(3 * NVacancies * sizeof(double));
        if (vacPos == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate vacPos");
            free(acnaInts);
            return 1;
        }
        intPos = malloc(3 * numAcnaInts * sizeof(double));
        if (intPos == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate intPos");
            free(vacPos);
            free(acnaInts);
            return 2;
        }
        
        /* add vacancy positions */
        for (i = 0; i < NVacancies; i++)
        {
            int index = vacancies[i];
            int index3 = 3 * index;
            int i3 = 3 * i;
            vacPos[i3    ] = refPos[index3    ];
            vacPos[i3 + 1] = refPos[index3 + 1];
            vacPos[i3 + 2] = refPos[index3 + 2];
        }
        
        /* interstitial positions */
        for (i = 0; i < numAcnaInts; i++)
        {
            int intIndex = acnaInts[i];
            int index = interstitials[intIndex];
            int index3 = 3 * index;
            int i3 = i * 3;
            intPos[i3    ] = pos[index3    ];
            intPos[i3 + 1] = pos[index3 + 1];
            intPos[i3 + 2] = pos[index3 + 2];
        }
        
        /* max separation */
        maxSep = 2.0 * vacancyRadius;
        
        /* construct list of neighbouring interstitials for each vacancy */
        nebListVacs = constructNeighbourList2DiffPos(NVacancies, vacPos, numAcnaInts, intPos, cellDims, PBC, maxSep);
        
        if (nebListVacs == NULL)
        {
            free(vacPos);
            free(intPos);
            free(acnaInts);
            return 3;
        }
        
        /* construct list of neighbouring vacancies for each interstitial */
        nebListInts = constructNeighbourList2DiffPos(numAcnaInts, intPos, NVacancies, vacPos, cellDims, PBC, maxSep);
        
        /* free position arrays (only required for constructing neighbour lists) */
        free(intPos);
        free(vacPos);
        
        if (nebListInts == NULL)
        {
            freeNeighbourList2(nebListVacs, NVacancies);
            free(acnaInts);
            return 4;
        }
        
        /* sort the neighbour lists by separation */
        for (i = 0; i < NVacancies; i++)
            qsort(nebListVacs[i].neighbour, nebListVacs[i].neighbourCount, sizeof(struct Neighbour), compare_two_nebs);
        
        for (i = 0; i < numAcnaInts; i++)
            qsort(nebListInts[i].neighbour, nebListInts[i].neighbourCount, sizeof(struct Neighbour), compare_two_nebs);
        
#ifdef DEBUGACNA
        printf("DEFECTSC: Vacancy neb lists\n");
        for (i = 0; i < NVacancies; i++)
        {
            int j;
    
            printf("DEFECTSC:   Vacancy %d\n", i);
            for (j = 0; j < nebListVacs[i].neighbourCount; j++)
            {
                struct Neighbour neb = nebListVacs[i].neighbour[j];
                printf("DEFECTSC:     Neb %d: int index %d; sep %lf\n", j, neb.index, neb.separation);
            }
        }
    
        printf("DEFECTSC: Interstitial neb lists\n");
        for (i = 0; i < numAcnaInts; i++)
        {
            int j;
    
            printf("DEFECTSC:   Interstitial %d\n", i);
            for (j = 0; j < nebListInts[i].neighbourCount; j++)
            {
                struct Neighbour neb = nebListInts[i].neighbour[j];
                printf("DEFECTSC:     Neb %d: vac index %d; sep %lf\n", j, neb.index, neb.separation);
            }
        }
#endif        
        
        /* set up mask arrays */
        intMask = calloc(numAcnaInts, sizeof(int));
        if (intMask == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate intMask");
            free(acnaInts);
            freeNeighbourList2(nebListVacs, NVacancies);
            freeNeighbourList2(nebListInts, numAcnaInts);
            return 5;
        }
        vacMask = calloc(NVacancies, sizeof(int));
        if (vacMask == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate vacMask");
            free(acnaInts);
            free(intMask);
            freeNeighbourList2(nebListVacs, NVacancies);
            freeNeighbourList2(nebListInts, numAcnaInts);
            return 6;
        }
        
        /* loop over vacancies, checking if they combine with an ACNA interstitial */
        numChanges = 0;
        for (i = 0; i < NVacancies; i++)
            numChanges = checkVacancyACNARecursive(i, numChanges, vacancies, interstitials, acnaInts, nebListVacs, nebListInts, vacMask, intMask);
        
        /* recreate vacancies/interstitials arrays */
#ifdef DEBUG
        printf("DEFECTSC: number of changes during ACNA refinement = %d\n", numChanges);
#endif
        
        /* free memory */
        free(vacMask);
        free(intMask);
        free(acnaInts);
        freeNeighbourList2(nebListVacs, NVacancies);
        freeNeighbourList2(nebListInts, numAcnaInts);
        
        if (numChanges)
        {
            int count;
    
            /* recreate interstitials array */
            count = 0;
            for (i = 0; i < NInterstitials; i++)
                if (interstitials[i] != -1) interstitials[count++] = interstitials[i];
            NInterstitials = count;
            
            /* recreate vacancies array */
            count = 0;
            for (i = 0; i < NVacancies; i++)
                if (vacancies[i] != -1) vacancies[count++] = vacancies[i];
            NVacancies = count;
        }
    }
    
    /* store counters */
    counters[0] = NVacancies;
    counters[1] = NInterstitials;
    
    return 0;
}

/*******************************************************************************
 * Use ACNA to refine the defects
 *******************************************************************************/
static int
refineDefectsUsingAcnaOld(int NVacancies, int *vacancies, int NInterstitials, int *interstitials, double vacancyRadius,
        int *PBC, double *cellDims, double *pos, double *refPos, double *acnaArray, int acnaStructureType, int *counters)
{
    int i, boxstat;
    int numChanges = 0;
    double maxSep, maxSep2, *defectPos;
    double approxBoxWidth;
    struct Boxes *boxes;
    
    
#ifdef DEBUG
    printf("DEFECTSC: Refining defects using ACNA...\n");
#endif
    
    /* first make defect pos and box */
    /* build positions array of all defects */
    defectPos = malloc(3 * NInterstitials * sizeof(double));
    if (defectPos == NULL)
    {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate defectPos");
        return 1;
    }
    
    /* add defects positions: int then split */
    for (i = 0; i < NInterstitials; i++)
    {
        int index  = interstitials[i];
        int i3 = i * 3;
        int ind3 = index * 3;
        defectPos[i3    ] = pos[ind3    ];
        defectPos[i3 + 1] = pos[ind3 + 1];
        defectPos[i3 + 2] = pos[ind3 + 2];
    }
    
    /* max separation */
    maxSep = 2.0 * vacancyRadius;
    maxSep2 = maxSep * maxSep;
    
    /* box defects */
    approxBoxWidth = (maxSep < 3.0) ? 3.0 : maxSep;
    boxes = setupBoxes(approxBoxWidth, PBC, cellDims);
    if (boxes == NULL)
    {
        free(defectPos);
        return 2;
    }
    boxstat = putAtomsInBoxes(NInterstitials, defectPos, boxes);
    free(defectPos);
    if (boxstat) return 3;
    
    /* loop over vacancies and see if there is a single neighbouring intersitial */
    for (i = 0; i < NVacancies; i++)
    {
        int vacIndex, j, exitLoop, boxNebListSize;
        int boxNebList[27] , boxIndex;
        int nebIntCount = 0;
        int foundIndex = -1;
        int foundIntIndex = -1;
        double refxpos, refypos, refzpos;
//            double foundSep2;
        
        vacIndex = vacancies[i];
        
        refxpos = refPos[3*vacIndex];
        refypos = refPos[3*vacIndex+1];
        refzpos = refPos[3*vacIndex+2];
        
        /* get box index of this atom */
        boxIndex = boxIndexOfAtom(refxpos, refypos, refzpos, boxes);
        if (boxIndex < 0)
        {
            freeBoxes(boxes);
            return 4;
        }
        
        /* find neighbouring boxes */
        boxNebListSize = getBoxNeighbourhood(boxIndex, boxNebList, boxes);
        
        /* loop over neighbouring boxes */
        exitLoop = 0;
        for (j = 0; j < boxNebListSize; j++)
        {
            int k, checkBox;

            if (exitLoop) break;
            
            checkBox = boxNebList[j];
            
            /* now loop over all reference atoms in the box */
            for (k = 0; k < boxes->boxNAtoms[checkBox]; k++)
            {
                int index, intIndex;
                double xpos, ypos, zpos, sep2;

                intIndex = boxes->boxAtoms[checkBox][k];
                index = interstitials[intIndex];
                
                /* skip if this interstitial has already been detected as lattice atom */
                if (index < 0) continue;
                
                /* pos of interstitial */
                xpos = pos[3*index];
                ypos = pos[3*index+1];
                zpos = pos[3*index+2];
                
                /* separation */
                sep2 = atomicSeparation2(refxpos, refypos, refzpos, xpos, ypos, zpos, 
                                         cellDims[0], cellDims[1], cellDims[2], PBC[0], PBC[1], PBC[2]);
                
                if (sep2 < maxSep2)
                {
                    if (++nebIntCount > 1)
                    {
                        exitLoop = 1;
                        break;
                    }
                    
                    foundIndex = index;
                    foundIntIndex = intIndex;
//                        foundSep2 = sep2;
                }
            }
        }
        
        if (nebIntCount == 1)
        {
            int acnaVal;
            
//                printf("DEBUG: found 1 neb for vac; checking acna val\n");
            
            /* check ACNA for FCC (hardcoded for now, not good...) */
            acnaVal = (int) acnaArray[foundIndex];
//                printf("DEBUG:   acna val is %d (%d)\n", acnaVal, ATOM_STRUCTURE_FCC);
            if (acnaVal == acnaStructureType)
            {
//                    printf("DEBUG:   this should not be a Frenkel pair... (sep = %lf)\n", sqrt(foundSep2));
                
                vacancies[i] = -1;
                interstitials[foundIntIndex] = -1;
                
                numChanges++;
            }
            
            /* could also check extending local vac rad and see if that helps... */
            
            
        }
        
        
    }
    
    /* free */
    freeBoxes(boxes);
    
    /* recreate vacancies/interstitials arrays */
#ifdef DEBUG
    printf("DEFECTSC: number of changes during ACNA refinement = %d\n", numChanges);
#endif
    if (numChanges)
    {
        int count;

        /* recreate interstitials array */
        count = 0;
        for (i = 0; i < NInterstitials; i++)
            if (interstitials[i] != -1) interstitials[count++] = interstitials[i];
        NInterstitials = count;
        
        /* recreate vacancies array */
        count = 0;
        for (i = 0; i < NVacancies; i++)
            if (vacancies[i] != -1) vacancies[count++] = vacancies[i];
        NVacancies = count;
    }
    
    /* store counters */
    counters[0] = NVacancies;
    counters[1] = NInterstitials;
    
    return 0;
}

/*******************************************************************************
 * Search for defects and return the sub-system surrounding them
 *******************************************************************************/
static PyObject*
findDefects(PyObject *self, PyObject *args)
{
    char *specieList, *specieListRef;
    int includeVacs, includeInts, includeAnts, *NDefectsType, *vacancies, *interstitials, *antisites, *onAntisites;
    int exclSpecInputDim, *exclSpecInput, exclSpecRefDim, *exclSpecRef, NAtoms, *specie, refNAtoms, *PBC, *specieRef;
    int findClustersFlag, *defectCluster, NSpecies, *vacSpecCount, *intSpecCount, *antSpecCount, *onAntSpecCount;
    int *splitIntSpecCount, minClusterSize, maxClusterSize, *splitInterstitials, identifySplits, driftCompensation;
    int acnaArrayDim, acnaStructureType, filterSpecies, identifySplitsOld, refineAcnaOld;
    double *pos, *refPosIn, *cellDims, vacancyRadius, clusterRadius, *driftVector, *acnaArray;
    PyObject *specieListIn=NULL;
    PyObject *specieListRefIn=NULL;
    PyArrayObject *NDefectsTypeIn=NULL;
    PyArrayObject *vacanciesIn=NULL;
    PyArrayObject *interstitialsIn=NULL;
    PyArrayObject *antisitesIn=NULL;
    PyArrayObject *onAntisitesIn=NULL;
    PyArrayObject *exclSpecInputIn=NULL;
    PyArrayObject *exclSpecRefIn=NULL;
    PyArrayObject *specieIn=NULL;
    PyArrayObject *specieRefIn=NULL;
    PyArrayObject *PBCIn=NULL;
    PyArrayObject *defectClusterIn=NULL;
    PyArrayObject *vacSpecCountIn=NULL;
    PyArrayObject *intSpecCountIn=NULL;
    PyArrayObject *antSpecCountIn=NULL;
    PyArrayObject *onAntSpecCountIn=NULL;
    PyArrayObject *splitIntSpecCountIn=NULL;
    PyArrayObject *splitInterstitialsIn=NULL;
    PyArrayObject *posIn=NULL;
    PyArrayObject *refPosIn_np=NULL;
    PyArrayObject *cellDimsIn=NULL;
    PyArrayObject *driftVectorIn=NULL;
    PyArrayObject *acnaArrayIn=NULL;
    
    int i, boxstat, status, defectCounters[4] = {0};
    int NDefects, NAntisites, NInterstitials, NVacancies;
    int *NDefectsCluster, *NDefectsClusterNew;
    int NClusters, NSplitInterstitials;
    int NVacNew, NIntNew, NAntNew, NSplitNew, numInCluster;
    double approxBoxWidth, *refPos;
    struct Boxes *boxes;
#ifdef DEBUG
    double basicTime = 0, splitTime = 0, acnaTime = 0, totalTime = 0;
    
    
    printf("DEFECTSC: Find defects\n");
    totalTime = walltime();
#endif
    
    /* parse and check arguments from Python */
    if (!PyArg_ParseTuple(args, "iiiO!O!O!O!O!O!O!iO!O!O!iO!O!O!O!O!didO!O!O!O!O!O!iiO!iiO!O!iiii", &includeVacs, &includeInts, &includeAnts,
            &PyArray_Type, &NDefectsTypeIn, &PyArray_Type, &vacanciesIn, &PyArray_Type, &interstitialsIn, &PyArray_Type, &antisitesIn,
            &PyArray_Type, &onAntisitesIn, &PyArray_Type, &exclSpecInputIn, &PyArray_Type, &exclSpecRefIn, &NAtoms, &PyList_Type, 
            &specieListIn, &PyArray_Type, &specieIn, &PyArray_Type, &posIn, &refNAtoms, &PyList_Type, &specieListRefIn, &PyArray_Type, 
            &specieRefIn, &PyArray_Type, &refPosIn_np, &PyArray_Type, &cellDimsIn, &PyArray_Type, &PBCIn, &vacancyRadius, &findClustersFlag,
            &clusterRadius, &PyArray_Type, &defectClusterIn, &PyArray_Type, &vacSpecCountIn, &PyArray_Type, &intSpecCountIn, &PyArray_Type,
            &antSpecCountIn, &PyArray_Type, &onAntSpecCountIn, &PyArray_Type, &splitIntSpecCountIn, &minClusterSize, &maxClusterSize,
            &PyArray_Type, &splitInterstitialsIn, &identifySplits, &driftCompensation, &PyArray_Type, &driftVectorIn, &PyArray_Type,
            &acnaArrayIn, &acnaStructureType, &filterSpecies, &identifySplitsOld, &refineAcnaOld))
        return NULL;
    
    if (not_intVector(NDefectsTypeIn)) return NULL;
    NDefectsType = pyvector_to_Cptr_int(NDefectsTypeIn);
    
    if (not_intVector(vacanciesIn)) return NULL;
    vacancies = pyvector_to_Cptr_int(vacanciesIn);
    
    if (not_intVector(interstitialsIn)) return NULL;
    interstitials = pyvector_to_Cptr_int(interstitialsIn);
    
    if (not_intVector(antisitesIn)) return NULL;
    antisites = pyvector_to_Cptr_int(antisitesIn);
    
    if (not_intVector(onAntisitesIn)) return NULL;
    onAntisites = pyvector_to_Cptr_int(onAntisitesIn);
    
    if (not_intVector(exclSpecInputIn)) return NULL;
    exclSpecInput = pyvector_to_Cptr_int(exclSpecInputIn);
    exclSpecInputDim = (int) PyArray_DIM(exclSpecInputIn, 0);
    
    if (not_intVector(exclSpecRefIn)) return NULL;
    exclSpecRef = pyvector_to_Cptr_int(exclSpecRefIn);
    exclSpecRefDim = (int) PyArray_DIM(exclSpecRefIn, 0);
    
    if (not_intVector(specieIn)) return NULL;
    specie = pyvector_to_Cptr_int(specieIn);
    
    if (not_doubleVector(posIn)) return NULL;
    pos = pyvector_to_Cptr_double(posIn);
    
    if (not_intVector(specieRefIn)) return NULL;
    specieRef = pyvector_to_Cptr_int(specieRefIn);
    
    if (not_doubleVector(refPosIn_np)) return NULL;
    refPosIn = pyvector_to_Cptr_double(refPosIn_np);
    
    if (not_doubleVector(cellDimsIn)) return NULL;
    cellDims = pyvector_to_Cptr_double(cellDimsIn);
        
    if (not_intVector(PBCIn)) return NULL;
    PBC = pyvector_to_Cptr_int(PBCIn);
    
    if (not_intVector(defectClusterIn)) return NULL;
    defectCluster = pyvector_to_Cptr_int(defectClusterIn);
    
    if (not_intVector(vacSpecCountIn)) return NULL;
    vacSpecCount = pyvector_to_Cptr_int(vacSpecCountIn);
    NSpecies = (int) PyArray_DIM(vacSpecCountIn, 0);
    
    if (not_intVector(intSpecCountIn)) return NULL;
    intSpecCount = pyvector_to_Cptr_int(intSpecCountIn);
    
    if (not_intVector(antSpecCountIn)) return NULL;
    antSpecCount = pyvector_to_Cptr_int(antSpecCountIn);
    
    if (not_intVector(onAntSpecCountIn)) return NULL;
    onAntSpecCount = pyvector_to_Cptr_int(onAntSpecCountIn);
    
    if (not_intVector(splitIntSpecCountIn)) return NULL;
    splitIntSpecCount = pyvector_to_Cptr_int(splitIntSpecCountIn);
    
    if (not_intVector(splitInterstitialsIn)) return NULL;
    splitInterstitials = pyvector_to_Cptr_int(splitInterstitialsIn);
    
    if (not_doubleVector(driftVectorIn)) return NULL;
    driftVector = pyvector_to_Cptr_double(driftVectorIn);
    
    if (not_doubleVector(acnaArrayIn)) return NULL;
    acnaArray = pyvector_to_Cptr_double(acnaArrayIn);
    acnaArrayDim = (int) PyArray_DIM(acnaArrayIn, 0);
    
    /* make C specie lists */
    specieList = specieListFromPyObject(specieListIn);
    specieListRef = specieListFromPyObject(specieListRefIn);
    
    /* drift compensation - modify reference positions */
    if (driftCompensation)
    {
#ifdef DEBUG
        printf("DEFECTSC: Drift compensation: %lf %lf %lf\n", driftVector[0], driftVector[1], driftVector[2]);
#endif
        
        refPos = malloc(3 * refNAtoms * sizeof(double));
        if (refPos == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate refPos");
            free(specieList);
            free(specieListRef);
            return NULL;
        }
        
        for (i = 0; i < refNAtoms; i++)
        {
            int j, i3 = 3 * i;
            for (j = 0; j < 3; j++)
                refPos[i3 + j] = refPosIn[i3 + j] + driftVector[j];
        }
    }
    else refPos = refPosIn;
    
#ifdef DEBUG
    basicTime = walltime();
#endif
    
    /* basic defect classification: interstitials, vacancies and antisites */
    status = basicDefectClassification(vacancyRadius, NAtoms, specieList, specie, pos, refNAtoms, specieListRef, specieRef, refPos, 
            PBC, cellDims, defectCounters, vacancies, interstitials, antisites, onAntisites);
    free(specieList);
    free(specieListRef);
    if (status)
    {
        if (driftCompensation) free(refPos);
        return NULL;
    }
    
    /* unpack counters */
    NVacancies = defectCounters[0];
    NInterstitials = defectCounters[1];
    NAntisites = defectCounters[2];
    
#ifdef DEBUG
    basicTime = walltime() - basicTime;
    printf("DEFECTSC: Basic defect classification: %d vacancies; %d interstitials; %d antisites\n", NVacancies, NInterstitials, NAntisites);
#endif
    
    /* use ACNA array, if provided, to refine defect classification */
    if (acnaArrayDim)
    {
#ifdef DEBUG
        acnaTime = walltime();
#endif
        if (refineAcnaOld)
        {
            status = refineDefectsUsingAcnaOld(NVacancies, vacancies, NInterstitials, interstitials, vacancyRadius, PBC, cellDims, pos, refPos,
                    acnaArray, acnaStructureType, defectCounters);
        }
        else
        {
            status = refineDefectsUsingAcna(NVacancies, vacancies, NInterstitials, interstitials, vacancyRadius, PBC, cellDims, pos, refPos,
                    acnaArray, acnaStructureType, defectCounters);
        }
        if (status)
        {
            if (driftCompensation) free(refPos);
            return NULL;
        }
        
        /* unpack counters */
        NVacancies = defectCounters[0];
        NInterstitials = defectCounters[1];
        
#ifdef DEBUG
        acnaTime = walltime() - acnaTime;
        printf("DEFECTSC: Defect count after ACNA refinement: %d vacancies; %d interstitials\n", NVacancies, NInterstitials);
#endif
    }
    
    /* identify split interstitials */
    if (identifySplits && NVacancies > 0 && NInterstitials > 1)
    {
#ifdef DEBUG
        splitTime = walltime();
#endif
        
        if (identifySplitsOld)
        {
            status = identifySplitInterstitialsOld(NVacancies, vacancies, NInterstitials, interstitials, splitInterstitials, pos, refPos, PBC,
                    cellDims, defectCounters, vacancyRadius);
        }
        else
        {
            status = identifySplitInterstitials(NVacancies, vacancies, NInterstitials, interstitials, splitInterstitials, pos, refPos, PBC,
                    cellDims, defectCounters, vacancyRadius);
        }
        if (status)
        {
            if (driftCompensation) free(refPos);
            return NULL;
        }
        
        /* unpack counters */
        NVacancies = defectCounters[0];
        NInterstitials = defectCounters[1];
        NSplitInterstitials = defectCounters[2];
        
#ifdef DEBUG
        splitTime = walltime() - splitTime;
        printf("DEFECTSC: Defect count after split interstitial identification: %d vacancies; %d interstitials; %d split interstitials\n", 
                NVacancies, NInterstitials, NSplitInterstitials);
#endif
    }
    else NSplitInterstitials = 0;
    
    /* exclude defect types and species here... */
    if (!includeInts)
    {
        NInterstitials = 0;
        NSplitInterstitials = 0;
    }
    else if (filterSpecies)
    {
        NIntNew = 0;
        for (i = 0; i < NInterstitials; i++)
        {
            int index, j, skip;

            index = interstitials[i];
            
            skip = 0;
            for (j = 0; j < exclSpecInputDim; j++)
            {
                if (specie[index] == exclSpecInput[j])
                {
                    skip = 1;
                    break;
                }
            }
            if (!skip) interstitials[NIntNew++] = index;
        }
        NInterstitials = NIntNew;
        
        NSplitNew = 0;
        for (i = 0; i < NSplitInterstitials; i++)
        {
            int i3 = 3 * i;
            int indexa = splitInterstitials[i3 + 1];
            int indexb = splitInterstitials[i3 + 2];
            int speca = specie[indexa];
            int specb = specie[indexb];
            int j;
            int skip = 0;
            
            for (j = 0; j < exclSpecInputDim; j++)
            {
                if (speca == exclSpecInput[j] || specb == exclSpecInput[j])
                {
                    skip = 1;
                    break;
                }
            }
            
            if (!skip)
            {
                int n3 = NSplitNew * 3;
                
                splitInterstitials[n3    ] = splitInterstitials[i3];
                splitInterstitials[n3 + 1] = indexa;
                splitInterstitials[n3 + 2] = indexb;
                NSplitNew++;
            }
        }
        NSplitInterstitials = NSplitNew;
    }
    
    if (!includeVacs) NVacancies = 0;
    else if (filterSpecies)
    {
        NVacNew = 0;
        for (i = 0; i < NVacancies; i++)
        {
            int index, j, skip;

            index = vacancies[i];
            
            skip = 0;
            for (j = 0; j < exclSpecRefDim; j++)
            {
                if (specieRef[index] == exclSpecRef[j])
                {
                    skip = 1;
                    break;
                }
            }
            if (!skip) vacancies[NVacNew++] = index;
        }
        NVacancies = NVacNew;
    }
    
    if (!includeAnts) NAntisites = 0;
    else if (filterSpecies)
    {
        NAntNew = 0;
        for (i = 0; i < NAntisites; i++)
        {
            int index, j, skip;
            
            index = onAntisites[i];
            
            skip = 0;
            for (j = 0; j < exclSpecInputDim; j++)
            {
                if (specie[index] == exclSpecInput[j])
                {
                    skip = 1;
                    break;
                }
            }
            if (!skip)
            {
                antisites[NAntNew] = antisites[i];
                onAntisites[NAntNew++] = index;
            }
        }
        NAntisites = NAntNew;
    }
    
#ifdef DEBUG
    printf("DEFECTSC: Defect count after filter by type: %d vacancies; %d interstitials; %d split interstitials; %d antisites\n", 
            NVacancies, NInterstitials, NSplitInterstitials, NAntisites);
#endif
    
    /* find clusters of defects */
    if (findClustersFlag)
    {
        int count;
        double *defectPos;

#ifdef DEBUG
        printf("DEFECTSC: Finding clusters of defects...\n");
#endif
        
        /* build positions array of all defects */
        NDefects = NVacancies + NInterstitials + NAntisites + 3 * NSplitInterstitials;
        defectPos = malloc(3 * NDefects * sizeof(double));
        if (defectPos == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate defectPos");
            if (driftCompensation) free(refPos);
            return NULL;
        }
        
        /* add defects positions: vac then int then ant */
        count = 0;
        for (i = 0; i < NVacancies; i++)
        {
            int index  = vacancies[i];
            int c3 = count * 3;
            int index3 = index * 3;
            defectPos[c3    ] = refPos[index3    ];
            defectPos[c3 + 1] = refPos[index3 + 1];
            defectPos[c3 + 2] = refPos[index3 + 2];
            count++;
        }
        
        for (i = 0; i < NInterstitials; i++)
        {
            int index = interstitials[i];
            int c3 = count * 3;
            int index3 = index * 3;
            defectPos[c3    ] = pos[index3    ];
            defectPos[c3 + 1] = pos[index3 + 1];
            defectPos[c3 + 2] = pos[index3 + 2];
            count++;
        }
        
        for (i = 0; i < NAntisites; i++)
        {
            int index  = antisites[i];
            int c3 = count * 3;
            int index3 = index * 3;
            defectPos[c3    ] = refPos[index3    ];
            defectPos[c3 + 1] = refPos[index3 + 1];
            defectPos[c3 + 2] = refPos[index3 + 2];
            count++;
        }
        
        for (i = 0; i < NSplitInterstitials; i++)
        {
            int index, c3, index3;

            index = splitInterstitials[3*i];
            c3 = count * 3;
            index3 = index * 3;
            defectPos[c3    ] = refPos[index3    ];
            defectPos[c3 + 1] = refPos[index3 + 1];
            defectPos[c3 + 2] = refPos[index3 + 2];
            count++;
            
            index = splitInterstitials[3*i+1];
            c3 = count * 3;
            index3 = index * 3;
            defectPos[c3    ] = pos[index3    ];
            defectPos[c3 + 1] = pos[index3 + 1];
            defectPos[c3 + 2] = pos[index3 + 2];
            count++;
            
            index = splitInterstitials[3*i+2];
            c3 = count * 3;
            index3 = index * 3;
            defectPos[c3    ] = pos[index3    ];
            defectPos[c3 + 1] = pos[index3 + 1];
            defectPos[c3 + 2] = pos[index3 + 2];
            count++;
        }
        
        /* box defects */
        approxBoxWidth = clusterRadius;
        boxes = setupBoxes(approxBoxWidth, PBC, cellDims);
        if (boxes == NULL)
        {
            if (driftCompensation) free(refPos);
            free(defectPos);
            return NULL;
        }
        boxstat = putAtomsInBoxes(NDefects, defectPos, boxes);
        if (boxstat)
        {
            if (driftCompensation) free(refPos);
            free(defectPos);
            return NULL;
        }
        
        /* number of defects per cluster */
        NDefectsCluster = malloc(NDefects * sizeof(int));
        if (NDefectsCluster == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate NDefectsCluster");
            if (driftCompensation) free(refPos);
            free(defectPos);
            freeBoxes(boxes);
            return NULL;
        }
        
        /* find clusters */
        NClusters = findDefectClusters(NDefects, defectPos, defectCluster, NDefectsCluster, boxes, clusterRadius, cellDims, PBC);
        
        freeBoxes(boxes);
        free(defectPos);
        
        if (NClusters < 0)
        {
            if (driftCompensation) free(refPos);
            free(NDefectsCluster);
            return NULL;
        }
        
        NDefectsCluster = realloc(NDefectsCluster, NClusters * sizeof(int));
        if (NDefectsCluster == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not reallocate NDefectsCluster");
            if (driftCompensation) free(refPos);
            return NULL;
        }
        
        /* first we have to adjust the number of atoms in clusters containing split interstitials */
        for (i = 0; i < NSplitInterstitials; i++)
        {
            int j, index;
//            int clusterIndex;

            /* assume all lone defects forming split interstitial are in same cluster; maybe should check!? */
            j = NVacancies + NInterstitials + NAntisites;
//            clusterIndex = defectCluster[j + 3 * i];
            
            /* subtract one from other atoms' clusters */
            /* we could also check they are same as main one? */
            index = defectCluster[j + 3 * i + 1];
            NDefectsCluster[index]--;
            index = defectCluster[j + 3 * i + 2];
            NDefectsCluster[index]--;
        }
        
        /* now limit by size */
        NDefectsClusterNew = calloc(NClusters, sizeof(int));
        if (NDefectsClusterNew == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "Could not reallocate NDefectsClusterNew");
            if (driftCompensation) free(refPos);
            free(NDefectsCluster);
            return NULL;
        }
        
        /* first vacancies */
        NVacNew = 0;
        for (i = 0; i < NVacancies; i++)
        {
            int index, clusterIndex;

            clusterIndex = defectCluster[i];
            index = vacancies[i];
            
            numInCluster = NDefectsCluster[clusterIndex];
            if (numInCluster < minClusterSize) continue;
            if (maxClusterSize >= minClusterSize && numInCluster > maxClusterSize) continue;
            
            vacancies[NVacNew] = index;
            defectCluster[NVacNew] = clusterIndex;
            NDefectsClusterNew[clusterIndex]++;
            
            NVacNew++;
        }
        
        /* now interstitials */
        NIntNew = 0;
        for (i = 0; i < NInterstitials; i++)
        {
            int index, clusterIndex;

            clusterIndex = defectCluster[NVacancies+i];
            index = interstitials[i];
            
            numInCluster = NDefectsCluster[clusterIndex];
            if (numInCluster < minClusterSize) continue;
            if (maxClusterSize >= minClusterSize && numInCluster > maxClusterSize) continue;
            
            interstitials[NIntNew] = index;
            defectCluster[NVacNew+NIntNew] = clusterIndex;
            NDefectsClusterNew[clusterIndex]++;
            
            NIntNew++;
        }
        
        /* antisites */
        NAntNew = 0;
        for (i = 0; i < NAntisites; i++)
        {
            int index, index2, clusterIndex;

            clusterIndex = defectCluster[NVacancies+NInterstitials+i];
            index = antisites[i];
            index2 = onAntisites[i];
            
            numInCluster = NDefectsCluster[clusterIndex];
            if (numInCluster < minClusterSize) continue;
            if (maxClusterSize >= minClusterSize && numInCluster > maxClusterSize) continue;
            
            antisites[NAntNew] = index;
            onAntisites[NAntNew] = index2;
            defectCluster[NVacNew+NIntNew+NAntNew] = clusterIndex;
            NDefectsClusterNew[clusterIndex]++;
            
            NAntNew++;
        }
        
        /* split interstitials */
        NSplitNew = 0;
        for (i = 0; i < NSplitInterstitials; i++)
        {
            int j, clusterIndex;

            /* assume all lone defects forming split interstitial are in same cluster */
            j = NVacancies + NInterstitials + NAntisites;
            clusterIndex = defectCluster[j + 3 * i];
            
            /* note, this number is wrong because we add 3 per split int, not 1 */
            numInCluster = NDefectsCluster[clusterIndex];
            if (numInCluster < minClusterSize) continue;
            if (maxClusterSize >= minClusterSize && numInCluster > maxClusterSize) continue;
            
            splitInterstitials[3*NSplitNew] = splitInterstitials[3*i];
            splitInterstitials[3*NSplitNew+1] = splitInterstitials[3*i+1];
            splitInterstitials[3*NSplitNew+2] = splitInterstitials[3*i+2];
            defectCluster[NVacNew+NIntNew+NAntNew+NSplitNew] = clusterIndex;
            NDefectsClusterNew[clusterIndex]++;
            
            NSplitNew++;
        }
        
        /* number of visible defects */
        NVacancies = NVacNew;
        NInterstitials = NIntNew;
        NAntisites = NAntNew;
        NSplitInterstitials = NSplitNew;
        
        /* recalc number of clusters */
        count = 0;
        for (i = 0; i < NClusters; i++) if (NDefectsClusterNew[i] > 0) count++;
        NClusters = count;
        
        /* number of clusters */
        NDefectsType[4] = NClusters;
        
        /* free stuff */
        free(NDefectsCluster);
        free(NDefectsClusterNew);
        
#ifdef DEBUG
        printf("DEFECTSC: Found %d defect clusters\n", NClusters);
#endif
    }
    
    /* counters */
    NDefects = NVacancies + NInterstitials + NAntisites + NSplitInterstitials;
    
    NDefectsType[0] = NDefects;
    NDefectsType[1] = NVacancies;
    NDefectsType[2] = NInterstitials;
    NDefectsType[3] = NAntisites;
    NDefectsType[5] = NSplitInterstitials;
    
    /* species counters */
    for (i = 0; i < NVacancies; i++)
    {
        int index = vacancies[i];
        vacSpecCount[specieRef[index]]++;
    }
    
    for (i = 0; i < NInterstitials; i++)
    {
        int index  = interstitials[i];
        intSpecCount[specie[index]]++;
    }
    
    for (i = 0; i < NAntisites; i++)
    {
        int index, index2;

        index = antisites[i];
        antSpecCount[specieRef[index]]++;
        
        index2 = onAntisites[i];
        onAntSpecCount[specieRef[index]*NSpecies+specie[index2]]++;
    }
    
    for (i = 0; i < NSplitInterstitials; i++)
    {
        int index, index2;

        index = splitInterstitials[3*i+1];
        index2 = splitInterstitials[3*i+2];
        
        splitIntSpecCount[specie[index]*NSpecies+specie[index2]]++;
    }
    
    if (driftCompensation) free(refPos);
    else refPos = NULL;
    
#ifdef DEBUG
    totalTime = walltime() - totalTime;
    printf("DEFECTSC: Timings\n");
    printf("DEFECTSC:   Total: %lf s\n", totalTime);
    printf("DEFECTSC:     Basic classification: %lf s\n", basicTime);
    if (acnaArrayDim) printf("DEFECTSC:     ACNA refinement: %lf s\n", acnaTime);
    if (identifySplits) printf("DEFECTSC:     Identify splits: %lf s\n", splitTime);
    printf("DEFECTSC: end\n");
#endif
    
    return Py_BuildValue("i", 0);
}


/*******************************************************************************
 * put defects into clusters
 *******************************************************************************/
static int findDefectClusters(int NDefects, double *defectPos, int *defectCluster, int *NDefectsCluster, struct Boxes *boxes, double maxSep, 
                              double *cellDims, int *PBC)
{
    int i, maxNumInCluster;
    int NClusters, numInCluster;
    double maxSep2;
    
    
    maxSep2 = maxSep * maxSep;
    
    /* initialise cluster array
     * = -1 : not yet allocated
     * > -1 : cluster ID of defect
     */
    for (i = 0; i < NDefects; i++) defectCluster[i] = -1;
    
    /* loop over defects */
    NClusters = 0;
    maxNumInCluster = -9999;
    for (i = 0; i < NDefects; i++)
    {
        /* skip if atom already allocated */
        if (defectCluster[i] == -1)
        {
            /* allocate cluster ID */
            defectCluster[i] = NClusters;
            NClusters++;
            
            numInCluster = 1;
            
            /* recursive search for cluster atoms */
            numInCluster = findDefectNeighbours(i, defectCluster[i], numInCluster, defectCluster, defectPos, boxes, maxSep2, cellDims, PBC);
            if (numInCluster < 0) return -1;
            
            NDefectsCluster[defectCluster[i]] = numInCluster;
            maxNumInCluster = (numInCluster > maxNumInCluster) ? numInCluster : maxNumInCluster;
        }
    }
    
    return NClusters;
}


/*******************************************************************************
 * recursive search for neighbouring defects
 *******************************************************************************/
static int findDefectNeighbours(int index, int clusterID, int numInCluster, int* atomCluster, double *pos, struct Boxes *boxes, 
                                double maxSep2, double *cellDims, int *PBC)
{
    int i, j, index2, boxNebListSize;
    int boxIndex, boxNebList[27];
    double sep2;
    
    
    /* box of primary atom */
    boxIndex = boxIndexOfAtom(pos[3*index], pos[3*index+1], pos[3*index+2], boxes);
    if (boxIndex < 0) return -1;
        
    /* find neighbouring boxes */
    boxNebListSize = getBoxNeighbourhood(boxIndex, boxNebList, boxes);
    
    /* loop over neighbouring boxes */
    for (i = 0; i < boxNebListSize; i++)
    {
        boxIndex = boxNebList[i];
        
        for (j=0; j<boxes->boxNAtoms[boxIndex]; j++)
        {
            index2 = boxes->boxAtoms[boxIndex][j];
            
            /* skip itself or if already searched */
            if ((index == index2) || (atomCluster[index2] != -1)) continue;
            
            /* calculate separation */
            sep2 = atomicSeparation2( pos[3*index], pos[3*index+1], pos[3*index+2], pos[3*index2], pos[3*index2+1], pos[3*index2+2], 
                                      cellDims[0], cellDims[1], cellDims[2], PBC[0], PBC[1], PBC[2] );
            
            /* check if neighbours */
            if (sep2 < maxSep2)
            {
                atomCluster[index2] = clusterID;
                numInCluster++;
                
                /* search for neighbours to this new cluster atom */
                numInCluster = findDefectNeighbours(index2, clusterID, numInCluster, atomCluster, pos, boxes, maxSep2, cellDims, PBC);
                if (numInCluster < 0) return -1;
            }
        }
    }
    
    return numInCluster;
}
