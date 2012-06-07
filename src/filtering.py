
"""
The filter tab for the main toolbar

@author: Chris Scott

"""
import os
import sys
import subprocess
import copy
import re

import numpy as np
import vtk

from visclibs import filtering_c
from visclibs import defects_c
from visclibs import clusters_c
import rendering


################################################################################
class Filterer:
    """
    Filter class.
    
    Contains list of subfilters to be performed in order.
    
    """
    def __init__(self, parent):
        
        self.parent = parent
        self.mainWindow = self.parent.mainWindow
        
        self.log = self.mainWindow.console.write
        
        self.visibleAtoms = np.empty(0, np.int32)
        
        self.actorsCollection = vtk.vtkActorCollection()
    
    def removeActors(self):
        """
        Remove actors.
        
        """
        self.hideActors()
        
        self.actorsCollection = vtk.vtkActorCollection()
    
    def hideActors(self):
        """
        Hide all actors
        
        """
        self.actorsCollection.InitTraversal()
        actor = self.actorsCollection.GetNextItem()
        while actor is not None:
            try:
                self.mainWindow.VTKRen.RemoveActor(actor)
            except:
                pass
            
            actor = self.actorsCollection.GetNextItem()
        
        self.mainWindow.VTKWidget.ReInitialize()
    
    def addActors(self):
        """
        Add all actors
        
        """
        self.actorsCollection.InitTraversal()
        actor = self.actorsCollection.GetNextItem()
        while actor is not None:
            try:
                self.mainWindow.VTKRen.AddActor(actor)
            except:
                pass
            
            actor = self.actorsCollection.GetNextItem()
        
        self.mainWindow.VTKWidget.ReInitialize()
    
    def runFilters(self):
        """
        Run the filters.
        
        """
        self.removeActors()
        
        # first set up visible atoms arrays
        NAtoms = self.parent.mainWindow.inputState.NAtoms
        
        if not self.parent.defectFilterSelected:
            self.visibleAtoms = np.arange(NAtoms, dtype=np.int32)
            self.log("%d visible atoms" % (len(self.visibleAtoms),), 0, 2)
        
        # run filters
        currentFilters = self.parent.currentFilters
        currentSettings = self.parent.currentSettings
        for i in xrange(len(currentFilters)):
            filterName = currentFilters[i]
            filterSettings = currentSettings[i]
            
            self.log("Running filter: %s" % (filterName,), 0, 2)
            
            if filterName == "Specie":
                self.filterSpecie(filterSettings)
            
            elif filterName == "Crop":
                self.cropFilter(filterSettings)
            
            elif filterName == "Displacement":
                self.displacementFilter(filterSettings)
            
            elif filterName == "Point defects":
                interstitials, vacancies, antisites, onAntisites, clusterList, defectType = self.pointDefectFilter(filterSettings)
            
            elif filterName == "Kinetic energy":
                self.KEFilter(filterSettings)
            
            elif filterName == "Potential energy":
                self.PEFilter(filterSettings)
            
            elif filterName == "Charge":
                self.chargeFilter(filterSettings)
            
            elif filterName == "Cluster":
                clusterList = self.clusterFilter(filterSettings)
                
                if filterSettings.drawConvexHulls:
                    # povray file
                    hullFile = os.path.join(self.mainWindow.tmpDirectory, "hulls%d.pov" % self.parent.tab)
                    if os.path.exists(hullFile):
                        os.unlink(hullFile)
                    
                    self.clusterFilterDrawHulls(clusterList, filterSettings, hullFile)
                
                if filterSettings.calculateVolumes:
                    self.clusterFilterCalculateVolumes(clusterList, filterSettings)
            
            # write to log
            if self.parent.defectFilterSelected:
                NVis = len(interstitials) + len(vacancies) + len(antisites)
                self.log("%d visible atoms" % (NVis,), 0, 3)
            
            else:
                self.log("%d visible atoms" % (len(self.visibleAtoms),), 0, 3)
        
        # render
        povfile = "atoms%d.pov" % (self.parent.tab,)
        if self.parent.defectFilterSelected:
            # vtk render
            if filterSettings.findClusters:
                self.pointDefectFilterDrawHulls(clusterList, defectType, filterSettings)
            
            rendering.getActorsForFilteredDefects(interstitials, vacancies, antisites, onAntisites, self.mainWindow, self.actorsCollection)
        
        else:
            rendering.getActorsForFilteredSystem(self.visibleAtoms, self.mainWindow, self.actorsCollection)
            
            # write pov-ray file too (only if pov-ray located??)
            rendering.writePovrayAtoms(povfile, self.visibleAtoms, self.mainWindow)
                
        if self.parent.visible:
            self.addActors()
    
    def getActorsForFilteredSystem(self):
        """
        Render systems after applying filters.
        
        """
        pass
            
    def filterSpecie(self, settings):
        """
        Filter by specie
        
        """
        if settings.allSpeciesSelected:
            visSpecArray = np.arange(len(self.mainWindow.inputState.specieList), dtype=np.int32)
        
        else:
            visSpecArray = np.empty(len(settings.visibleSpecieList), np.int32)
            count = 0
            for i in xrange(len(self.mainWindow.inputState.specieList)):
                if self.mainWindow.inputState.specieList[i] in settings.visibleSpecieList:
                    visSpecArray[count] = i
                    count += 1
        
            if count != len(visSpecArray):
                visSpecArray.resize(count)
        
        NVisible = filtering_c.specieFilter(self.visibleAtoms, visSpecArray, self.mainWindow.inputState.specie)
        
        self.visibleAtoms.resize(NVisible, refcheck=False)
    
    def displacementFilter(self, settings):
        """
        Displacement filter
        
        """
        # only run displacement filter if input and reference NAtoms are the same
        inputState = self.mainWindow.inputState
        refState = self.mainWindow.refState
        
        if inputState.NAtoms != refState.NAtoms:
            self.log("WARNING: cannot run displacement filter with different numbers of input and reference atoms: skipping this filter list")
            self.visibleAtoms.resize(0, refcheck=False)
        
        else:
            # run displacement filter
            NVisible = filtering_c.displacementFilter(self.visibleAtoms, inputState.pos, refState.pos, refState.cellDims, 
                                                      self.mainWindow.PBC, settings.minDisplacement, settings.maxDisplacement)
            
            self.visibleAtoms.resize(NVisible, refcheck=False)
    
    def cropFilter(self, settings):
        """
        Crop lattice
        
        """
        lattice = self.mainWindow.inputState
        
        NVisible = filtering_c.cropFilter(self.visibleAtoms, lattice.pos, settings.xmin, settings.xmax, settings.ymin, 
                                          settings.ymax, settings.zmin, settings.zmax, settings.xEnabled, 
                                          settings.yEnabled, settings.zEnabled)
        
        self.visibleAtoms.resize(NVisible, refcheck=False)
    
    def chargeFilter(self, settings):
        """
        Charge filter.
        
        """
        lattice = self.mainWindow.inputState
        
        NVisible = filtering_c.chargeFilter(self.visibleAtoms, lattice.charge, settings.minCharge, settings.maxCharge)
        
        self.visibleAtoms.resize(NVisible, refcheck=False)
    
    def KEFilter(self, settings):
        """
        Filter kinetic energy.
        
        """
        lattice = self.mainWindow.inputState
        
        NVisible = filtering_c.KEFilter(self.visibleAtoms, lattice.KE, settings.minKE, settings.maxKE)
        
        self.visibleAtoms.resize(NVisible, refcheck=False)
    
    def PEFilter(self, settings):
        """
        Filter potential energy.
        
        """
        lattice = self.mainWindow.inputState
        
        NVisible = filtering_c.PEFilter(self.visibleAtoms, lattice.PE, settings.minPE, settings.maxPE)
        
        self.visibleAtoms.resize(NVisible, refcheck=False)
    
    def pointDefectFilter(self, settings):
        """
        Point defects filter
        
        """
        inputLattice = self.mainWindow.inputState
        refLattice = self.mainWindow.refState
        
        # set up arrays
        if settings.showInterstitials:
            interstitials = np.empty(inputLattice.NAtoms, np.int32)
        
        else:
            interstitials = np.empty(0, np.int32)
        
        if settings.showVacancies:
            vacancies = np.empty(refLattice.NAtoms, np.int32)
        
        else:
            vacancies = np.empty(0, np.int32)
        
        if settings.showAntisites:
            antisites = np.empty(refLattice.NAtoms, np.int32)
            onAntisites = np.empty(refLattice.NAtoms, np.int32)
        
        else:
            antisites = np.empty(0, np.int32)
            onAntisites = np.empty(0, np.int32)
        
        # set up excluded specie arrays
        if settings.allSpeciesSelected:
            exclSpecsInput = np.zeros(0, np.int32)
            exclSpecsRef = np.zeros(0, np.int32)
        
        else:
            exclSpecs = []
            for i in xrange(len(inputLattice.specieList)):
                spec = inputLattice.specieList[i]
                if spec not in settings.visibleSpecieList:
                    exclSpecs.append(i)
            exclSpecsInput = np.empty(len(exclSpecs), np.int32)
            for i in xrange(len(exclSpecs)):
                exclSpecsInput[i] = exclSpecs[i]
            
            exclSpecs = []
            for i in xrange(len(refLattice.specieList)):
                spec = refLattice.specieList[i]
                if spec not in settings.visibleSpecieList:
                    exclSpecs.append(i)
            exclSpecsRef = np.empty(len(exclSpecs), np.int32)
            for i in xrange(len(exclSpecs)):
                exclSpecsRef[i] = exclSpecs[i]
        
        # specie counter arrays
        vacSpecCount = np.zeros( len(refLattice.specieList), np.int32 )
        intSpecCount = np.zeros( len(inputLattice.specieList), np.int32 )
        antSpecCount = np.zeros( len(refLattice.specieList), np.int32 )
        onAntSpecCount = np.zeros( (len(refLattice.specieList), len(inputLattice.specieList)), np.int32 )
        
        NDefectsByType = np.zeros(5, np.int32)
        
        # set min/max pos to lattice (for boxing)
        minPos = refLattice.minPos
        maxPos = refLattice.maxPos
        
        if settings.findClusters:
            defectCluster = np.empty(inputLattice.NAtoms + refLattice.NAtoms, np.int32)
        
        else:
            defectCluster = np.empty(0, np.int32)
        
        # call C library
        status = defects_c.findDefects(settings.showVacancies, settings.showInterstitials, settings.showAntisites, NDefectsByType, vacancies, 
                                       interstitials, antisites, onAntisites, exclSpecsInput, exclSpecsRef, inputLattice.NAtoms, inputLattice.specieList,
                                       inputLattice.specie, inputLattice.pos, refLattice.NAtoms, refLattice.specieList, refLattice.specie, 
                                       refLattice.pos, refLattice.cellDims, self.mainWindow.PBC, settings.vacancyRadius, minPos, maxPos, 
                                       settings.findClusters, settings.neighbourRadius, defectCluster, vacSpecCount, intSpecCount, antSpecCount,
                                       onAntSpecCount)
        
        # summarise
        NDef = NDefectsByType[0]
        NVac = NDefectsByType[1]
        NInt = NDefectsByType[2]
        NAnt = NDefectsByType[3]
        vacancies.resize(NVac)
        interstitials.resize(NInt)
        antisites.resize(NAnt)
        onAntisites.resize(NAnt)
        
        # report counters
        self.log("Found %d defects" % (NDef,), 0, 3)
        
        if settings.showVacancies:
            self.log("%d vacancies" % (NVac,), 0, 4)
            for i in xrange(len(refLattice.specieList)):
                self.log("%d %s vacancies" % (vacSpecCount[i], refLattice.specieList[i]), 0, 5)
        
        if settings.showInterstitials:
            self.log("%d interstitials" % (NInt,), 0, 4)
            for i in xrange(len(inputLattice.specieList)):
                self.log("%d %s interstitials" % (intSpecCount[i], inputLattice.specieList[i]), 0, 5)
        
        if settings.showAntisites:
            self.log("%d antisites" % (NAnt,), 0, 4)
            for i in xrange(len(refLattice.specieList)):
#                self.log("%d %s antisites" % (antSpecCount[i], refLattice.specieList[i]), 0, 5)
                for j in xrange(len(inputLattice.specieList)):
                    if inputLattice.specieList[j] == refLattice.specieList[i]:
                        continue
                    
                    self.log("%d %s on %s antisites" % (onAntSpecCount[i][j], inputLattice.specieList[j], refLattice.specieList[i]), 0, 6)
        
        # sort clusters here
        clusterList = []
        defectType = []
        if settings.findClusters:
            NClusters = NDefectsByType[4]
            
            defectCluster.resize(NDef)
            
            # build cluster lists
            for i in xrange(NClusters):
                clusterList.append([])
                defectType.append([])
            
            # add atoms to cluster lists
            clusterIndexMapper = {}
            count = 0
            for i in xrange(NVac):
                atomIndex = vacancies[i]
                clusterIndex = defectCluster[i]
                
                if clusterIndex not in clusterIndexMapper:
                    clusterIndexMapper[clusterIndex] = count
                    count += 1
                
                clusterListIndex = clusterIndexMapper[clusterIndex]
                
                clusterList[clusterListIndex].append(atomIndex)
                defectType[clusterIndex].append("R")
            
            for i in xrange(NInt):
                atomIndex = interstitials[i]
                clusterIndex = defectCluster[NVac + i]
                
                if clusterIndex not in clusterIndexMapper:
                    clusterIndexMapper[clusterIndex] = count
                    count += 1
                
                clusterListIndex = clusterIndexMapper[clusterIndex]
                
                clusterList[clusterListIndex].append(atomIndex)
                defectType[clusterIndex].append("I")
            
            for i in xrange(NAnt):
                atomIndex = antisites[i]
                clusterIndex = defectCluster[NVac + NInt + i]
                
                if clusterIndex not in clusterIndexMapper:
                    clusterIndexMapper[clusterIndex] = count
                    count += 1
                
                clusterListIndex = clusterIndexMapper[clusterIndex]
                
                clusterList[clusterListIndex].append(atomIndex)
                defectType[clusterIndex].append("R")
            
        
        return (interstitials, vacancies, antisites, onAntisites, clusterList, defectType)
    
    def pointDefectFilterDrawHulls(self, clusterList, defectType, settings):
        """
        Draw convex hulls around defect volumes
        
        """
        PBC = self.mainWindow.PBC
        if PBC[0] or PBC[1] or PBC[2]:
            self.pointDefectFilterDrawHullsWithPBCs(clusterList, settings)
        
        else:
            self.pointDefectFilterDrawHullsWithPBCs(clusterList, settings)
    
    def pointDefectFilterDrawHullsWithPBCs(self, clusterList, defectType):
        """
        Draw hulls around defect volumes (PBCs)
        
        """
        pass
        
    def clusterFilter(self, settings, PBC=None, minSize=None, maxSize=None, nebRad=None):
        """
        Run the cluster filter
        
        """
        lattice = self.mainWindow.inputState
        
        atomCluster = np.empty(len(self.visibleAtoms), np.int32)
        result = np.empty(2, np.int32)
        
        if PBC is not None and len(PBC) == 3:
            pass
        else:
            PBC = self.mainWindow.PBC
        
        if minSize is None:
            minSize = settings.minClusterSize
        
        if maxSize is None:
            maxSize = settings.maxClusterSize
        
        if nebRad is None:
            nebRad = settings.neighbourRadius
        
        # set min/max pos to lattice (for boxing)
        minPos = np.zeros(3, np.float64)
        maxPos = copy.deepcopy(lattice.cellDims)
        
        clusters_c.findClusters(self.visibleAtoms, lattice.pos, atomCluster, nebRad, lattice.cellDims, PBC, 
                                minPos, maxPos, minSize, maxSize, result)
        
        NVisible = result[0]
        NClusters = result[1]
        
        self.visibleAtoms.resize(NVisible, refcheck=False)
        atomCluster.resize(NVisible, refcheck=False)
        
        # build cluster lists
        clusterList = []
        for i in xrange(NClusters):
            clusterList.append([])
        
        # add atoms to cluster lists
        clusterIndexMapper = {}
        count = 0
        for i in xrange(NVisible):
            atomIndex = self.visibleAtoms[i]
            clusterIndex = atomCluster[i]
            
            if clusterIndex not in clusterIndexMapper:
                clusterIndexMapper[clusterIndex] = count
                count += 1
            
            clusterListIndex = clusterIndexMapper[clusterIndex]
            
            clusterList[clusterListIndex].append(atomIndex)
        
        #TODO: rebuild scalars array of atom cluster (so can colour by cluster maybe?)
        
        
        return clusterList
    
    def clusterFilterDrawHulls(self, clusterList, settings, hullPovFile):
        """
        Draw hulls around filters.
        
        If the clusterList was created using PBCs we need to recalculate each 
        cluster without PBCs.
        
        """
        PBC = self.mainWindow.PBC
        if PBC[0] or PBC[1] or PBC[2]:
            self.clusterFilterDrawHullsWithPBCs(clusterList, settings, hullPovFile)
        
        else:
            self.clusterFilterDrawHullsNoPBCs(clusterList, settings, hullPovFile)
    
    def clusterFilterDrawHullsNoPBCs(self, clusterList, settings, hullPovFile):
        """
        
        
        """
        lattice = self.mainWindow.inputState
        
        # draw them as they are
        for cluster in clusterList:
            # first make pos array for this cluster
            clusterPos = np.empty(3 * len(cluster), np.float64)
            for i in xrange(len(cluster)):
                index = cluster[i]
                
                clusterPos[3*i] = lattice.pos[3*index]
                clusterPos[3*i+1] = lattice.pos[3*index+1]
                clusterPos[3*i+2] = lattice.pos[3*index+2]
            
            # now get convex hull
            if len(cluster) == 3:
                facets = []
                facets.append([0, 1, 2])
            
            elif len(cluster) == 2:
                # draw bond
                continue
            
            elif len(cluster) < 2:
                continue
            
            else:
                facets = findConvexHullFacets(len(cluster), clusterPos, qconvex=settings.qconvex)
            
            # now render
            if facets is not None:
                rendering.getActorsForHullFacets(facets, clusterPos, self.mainWindow, self.actorsCollection, settings)
                
                # write povray file too
                rendering.writePovrayHull(facets, clusterPos, self.mainWindow, hullPovFile, settings)
    
    def clusterFilterDrawHullsWithPBCs(self, clusterList, settings, hullPovFile):
        """
        
        
        """
        lattice = self.mainWindow.inputState
        
        for cluster in clusterList:
            
            appliedPBCs = np.zeros(7, np.int32)
            clusterPos = np.empty(3 * len(cluster), np.float64)
            for i in xrange(len(cluster)):
                index = cluster[i]
                
                clusterPos[3*i] = lattice.pos[3*index]
                clusterPos[3*i+1] = lattice.pos[3*index+1]
                clusterPos[3*i+2] = lattice.pos[3*index+2]
            
            clusters_c.prepareClusterToDrawHulls(len(cluster), clusterPos, lattice.cellDims, 
                                                 self.mainWindow.PBC, appliedPBCs, settings.neighbourRadius)
            
            facets = None
            if len(cluster) > 3:
                facets = findConvexHullFacets(len(cluster), clusterPos, qconvex=settings.qconvex)
            
            elif len(cluster) == 3:
                facets = []
                facets.append([0, 1, 2])
            
            # now render
            if facets is not None:
                #TODO: make sure not facets more than neighbour rad from cell
                facets = checkFacetsPBCs(facets, clusterPos, 2.0 * settings.neighbourRadius, self.mainWindow.PBC, lattice.cellDims)
                
                rendering.getActorsForHullFacets(facets, clusterPos, self.mainWindow, self.actorsCollection, settings)
                
                # write povray file too
                rendering.writePovrayHull(facets, clusterPos, self.mainWindow, hullPovFile, settings)
            
            # handle PBCs
            if len(cluster) > 1:
                while max(appliedPBCs) > 0:
                    tmpClusterPos = copy.deepcopy(clusterPos)
                    applyPBCsToCluster(tmpClusterPos, lattice.cellDims, appliedPBCs)
                    
                    # get facets
                    facets = None
                    if len(cluster) > 3:
                        facets = findConvexHullFacets(len(cluster), tmpClusterPos, qconvex=settings.qconvex)
                    
                    elif len(cluster) == 3:
                        facets = []
                        facets.append([0, 1, 2])
                    
                    # render
                    if facets is not None:
                        #TODO: make sure not facets more than neighbour rad from cell
                        facets = checkFacetsPBCs(facets, tmpClusterPos, 2.0 * settings.neighbourRadius, self.mainWindow.PBC, lattice.cellDims)
                        
                        rendering.getActorsForHullFacets(facets, tmpClusterPos, self.mainWindow, self.actorsCollection, settings)
                        
                        # write povray file too
                        rendering.writePovrayHull(facets, tmpClusterPos, self.mainWindow, hullPovFile, settings)
                
    
    def clusterFilterCalculateVolumes(self, clusterList, filterSettings):
        """
        Calculate volumes of clusters.
        
        """    
        # this will not work properly over PBCs at the moment
        lattice = self.mainWindow.inputState
        
        # draw them as they are
        count = 0
        for cluster in clusterList:
            # first make pos array for this cluster
            clusterPos = np.empty(3 * len(cluster), np.float64)
            for i in xrange(len(cluster)):
                index = cluster[i]
                
                clusterPos[3*i] = lattice.pos[3*index]
                clusterPos[3*i+1] = lattice.pos[3*index+1]
                clusterPos[3*i+2] = lattice.pos[3*index+2]
            
            # now get convex hull
            if len(cluster) < 4:
                pass
            
            else:
                PBC = self.mainWindow.PBC
                if PBC[0] or PBC[1] or PBC[2]:
                    appliedPBCs = np.zeros(7, np.int32)
                    clusters_c.prepareClusterToDrawHulls(len(cluster), clusterPos, lattice.cellDims, 
                                                         PBC, appliedPBCs, filterSettings.neighbourRadius)
                
                volume, area = findConvexHullVolume(len(cluster), clusterPos, qconvex=filterSettings.qconvex)
            
            self.log("Cluster %d (%d atoms)" % (count, len(cluster)), 0, 4)
            self.log("volume is %f; facet area is %f" % (volume, area), 0, 5)
            
            count += 1


################################################################################
def findConvexHullFacets(N, pos, qconvex="qconvex"):
    """
    Find convex hull of given points
    
    """
    # create string to pass to qconvex
    stringList = []
    appList = stringList.append
    appList("3")
    appList("%d" % (N,))
    for i in xrange(N):
        appList("%f %f %f" % (pos[3*i], pos[3*i+1], pos[3*i+2]))
    string = "\n".join(stringList)
    
    # run qconvex
    command = "%s Qt i" % (qconvex,)
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                            stdin=subprocess.PIPE)
    output, stderr = proc.communicate(string)
    status = proc.poll()
    if status:
        print "qconvex failed"
        print stderr
        sys.exit(35)
    
    # parse output
    output = output.strip()
    lines = output.split("\n")
    
    lines.pop(0)
    
    facets = []
    for line in lines:
        array = line.split()
        facets.append([np.int32(array[0]), np.int32(array[1]), np.int32(array[2])])
    
    return facets


################################################################################
def findConvexHullVolume(N, pos, qconvex="qconvex"):
    """
    Find convex hull of given points
    
    """
    # create string to pass to qconvex
    stringList = []
    appList = stringList.append
    appList("3")
    appList("%d" % (N,))
    for i in xrange(N):
        appList("%f %f %f" % (pos[3*i], pos[3*i+1], pos[3*i+2]))
    string = "\n".join(stringList)
    
    # run qconvex
    command = "%s Qt FA" % (qconvex,)
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                            stdin=subprocess.PIPE)
    output, stderr = proc.communicate(string)
    status = proc.poll()
    if status:
        print "qconvex failed"
        print stderr
        sys.exit(35)
    
    # parse output
    volume = None
    facetArea = None
    
    output = output.strip()
    lines = output.split("\n")
    
    volstr = re.compile("volume")
    areastr = re.compile("facet area")
    
    for line in lines:
        line = line.strip()
        
        if volstr.search(line):
            array = line.split(":")
            volume = float(array[1])
        
        elif areastr.search(line):
            array = line.split(":")
            facetArea = float(array[1])
    
    return volume, facetArea


################################################################################
def applyPBCsToCluster(clusterPos, cellDims, appliedPBCs):
    """
    Apply PBCs to cluster.
    
    """
    for i in xrange(7):
        if appliedPBCs[i]:
            # apply in x direction
            if i == 0:
                if min(clusterPos[0::3]) < 0.0:
                    clusterPos[0::3] += cellDims[0]
                
                else:
                    clusterPos[0::3] -= cellDims[0]
            
            elif i == 1:
                if min(clusterPos[1::3]) < 0.0:
                    clusterPos[1::3] += cellDims[1]
                
                else:
                    clusterPos[1::3] -= cellDims[1]
            
            elif i == 2:
                if min(clusterPos[2::3]) < 0.0:
                    clusterPos[2::3] += cellDims[2]
                
                else:
                    clusterPos[2::3] -= cellDims[2]
            
            elif i == 3:
                if min(clusterPos[0::3]) < 0.0:
                    clusterPos[0::3] += cellDims[0]
                
                else:
                    clusterPos[0::3] -= cellDims[0]
                
                if min(clusterPos[1::3]) < 0.0:
                    clusterPos[1::3] += cellDims[1]
                
                else:
                    clusterPos[1::3] -= cellDims[1]
            
            elif i == 4:
                if min(clusterPos[0::3]) < 0.0:
                    clusterPos[0::3] += cellDims[0]
                
                else:
                    clusterPos[0::3] -= cellDims[0]
                
                if min(clusterPos[2::3]) < 0.0:
                    clusterPos[2::3] += cellDims[2]
                
                else:
                    clusterPos[2::3] -= cellDims[2]
            
            elif i == 5:
                if min(clusterPos[1::3]) < 0.0:
                    clusterPos[1::3] += cellDims[1]
                
                else:
                    clusterPos[1::3] -= cellDims[1]
                
                if min(clusterPos[2::3]) < 0.0:
                    clusterPos[2::3] += cellDims[2]
                
                else:
                    clusterPos[2::3] -= cellDims[2]
            
            elif i == 6:
                if min(clusterPos[0::3]) < 0.0:
                    clusterPos[0::3] += cellDims[0]
                
                else:
                    clusterPos[0::3] -= cellDims[0]
                
                if min(clusterPos[1::3]) < 0.0:
                    clusterPos[1::3] += cellDims[1]
                
                else:
                    clusterPos[1::3] -= cellDims[1]
                
                if min(clusterPos[2::3]) < 0.0:
                    clusterPos[2::3] += cellDims[2]
                
                else:
                    clusterPos[2::3] -= cellDims[2]
            
            appliedPBCs[i] = 0
            
            break


################################################################################
def checkFacetsPBCs(facetsIn, clusterPos, excludeRadius, PBC, cellDims):
    """
    Remove facets that are far from cell
    
    """
    facets = []
    for facet in facetsIn:
        includeFlag = 1
        for i in xrange(3):
            index = facet[i]
            
            for j in xrange(3):
                if PBC[j]:
                    if clusterPos[3*index+j] > cellDims[j] + excludeRadius or clusterPos[3*index+j] < 0.0 - excludeRadius:
                        includeFlag = 0
                        break
            
            if not includeFlag:
                break
        
        if includeFlag:
            facets.append(facet)
    
    return facets
