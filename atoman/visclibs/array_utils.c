
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION

#include <Python.h> // includes stdio.h, string.h, errno.h, stdlib.h
#include <numpy/arrayobject.h>
#include "visclibs/array_utils.h"


static double **ptrvector_double(long);


double *pyvector_to_Cptr_double(PyArrayObject *vectin)
{
    return (double *) PyArray_DATA(vectin);
}

int *pyvector_to_Cptr_int(PyArrayObject *vectin)
{
    return (int *) PyArray_DATA(vectin);
}

char *pyvector_to_Cptr_char(PyArrayObject *vectin)
{
    return (char *) PyArray_DATA(vectin);
}

int not_doubleVector(PyArrayObject *vectin)
{
    if (PyArray_TYPE(vectin) != NPY_FLOAT64)
    {
        PyErr_SetString(PyExc_ValueError, "In not_doubleVector: vector must be of type float");
        return 1;
    }
    
    return 0;
}

int not_intVector(PyArrayObject *vectin)
{
    if (PyArray_TYPE(vectin) != NPY_INT32)
    {
        PyErr_SetString(PyExc_ValueError, "In not_intVector: vector must be of type int");
        return 1;
    }
    
    return 0;
}

static double **ptrvector_double(long n)
{
    double **v;
    
    v = (double **) malloc((size_t) (n * sizeof(double)));
    if (!v)
    {
        printf("In **ptrvector_double. Allocation of memory for double array failed.\n");
        exit(34);
    }
    
    return v;
}

double **pymatrix_to_Cptrs_double(PyArrayObject *arrayin)
{
    double **c, *a;
    int i, n, m;
    
    n = PyArray_DIM(arrayin, 0);
    m = PyArray_DIM(arrayin, 1);
    c = ptrvector_double(n);
    a = (double *) PyArray_DATA(arrayin);
    for (i = 0; i < n; i++)
        c[i] = a + i * m;
    
    return c;
}

void free_Cptrs_double(double **v)
{
    free((char *) v);
}
