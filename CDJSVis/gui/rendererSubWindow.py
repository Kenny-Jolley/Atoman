# -*- coding: utf-8 -*-

"""
Mdi sub window for displaying VTK render window.

@author: Chris Scott

"""
import logging

from PySide import QtGui, QtCore
#from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from .QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk
import numpy as np

from ..visutils.utilities import iconPath
from ..visutils import utilities
from . import dialogs
from . import onScreenInfoDialog
from ..rendering import renderer
from .outputDialog import OutputDialog
from ..rendering.text import vtkRenderWindowText
from ..state.lattice import Lattice


################################################################################

class RendererWindow(QtGui.QWidget):
    """
    Renderer sub window.
    
    Holds VTK render window.
    
    """
    def __init__(self, mainWindow, index, parent=None):
        super(RendererWindow, self).__init__(parent)
        
        self.parent = parent
        self.mainWindow = mainWindow
        self.rendererIndex = index
        
        self.setWindowTitle("Render window %d" % index)
        
        self.logger = logging.getLogger(__name__)
        
        self.closed = False
        
        self.slicePlaneActor = None
        
        self.blackBackground = False
        
        self.currentAAFrames = 2
        
        self.highlighters = {}
        
        self.leftClick = False
        self.rightClick = False
        
        self.parallelProjection = False
        
        # layout
        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        self.currentPipelineIndex = 0
        self.currentPipelineString = "Pipeline 0"
        self.onScreenInfoActors = vtk.vtkActor2DCollection()
        
        # toolbar
        toolbar = QtGui.QToolBar()
        layout.addWidget(toolbar)
        
        # button to displace lattice frame
        showCellAction = self.createAction("Toggle cell", slot=self.toggleCellFrame, icon="cell_icon.svg", 
                                           tip="Toggle cell frame visibility")
        
        # button to display axes
        showAxesAction = self.createAction("Toggle axes", slot=self.toggleAxes, icon="axis_icon.svg", 
                                           tip="Toggle axes visiblity")
        
        # reset camera to cell
        setCamToCellAction = self.createAction("Reset to cell", slot=self.setCameraToCell, icon="oxygen/zoom-fit-best.png", 
                                               tip="Reset camera to cell")
        
        # rotate image
        rotateViewPoint = self.createAction("Rotate view point", slot=self.rotateViewPoint, icon="oxygen/transform-rotate.png",
                                            tip="Rotate view point")
        
        # text selector
        openTextSelectorAction = self.createAction("On-screen info", self.showTextSelector, 
                                                   icon="oxygen/preferences-desktop-font.png", 
                                                   tip="Show on-screen text selector")
        
        # output dialog
        showOutputDialogAction = self.createAction("Output dialog", slot=self.showOutputDialog, icon="oxygen/document-save.png",
                                                   tip="Show output dialog")
        
        # background colour
        backgroundColourAction = self.createAction("Toggle background colour", slot=self.toggleBackgroundColour, 
                                                   icon="oxygen/preferences-desktop-display-color.png",
                                                   tip="Toggle background colour")
        
        # aa up
        aaUpAction = self.createAction("Increase anti-aliasing", slot=self.increaseAA, icon="oxygen/go-up.png",
                                       tip="Increase anti-aliasing")
        
        # aa up
        aaDownAction = self.createAction("Decrease anti-aliasing", slot=self.decreaseAA, icon="oxygen/go-down.png",
                                       tip="Decrease anti-aliasing")
        
        # camera settings
        cameraSettingsAction = self.createAction("Camera settings", slot=self.showCameraSettings, icon="oxygen/camera-photo.png", tip="Show camera settings")
        
        # parallel projection action
        projectionAction = self.createAction("Parallel projection", slot=self.toggleProjection, icon="perspective-ava.svg", tip="Parallel projection", checkable=True)
        
        # add actions
        self.addActions(toolbar, (showCellAction, showAxesAction, backgroundColourAction, None, 
                                  setCamToCellAction, rotateViewPoint, cameraSettingsAction, projectionAction, None, 
                                  openTextSelectorAction, showOutputDialogAction, None,
                                  aaUpAction, aaDownAction))
        
        # VTK render window
        self.vtkRenWin = vtk.vtkRenderWindow()
        
        # VTK interactor
        self.vtkRenWinInteract = QVTKRenderWindowInteractor(self, rw=self.vtkRenWin)
        
        # interactor style
        self.vtkRenWinInteract._Iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        
        # disable wheel event?
        self.vtkRenWinInteract.changeDisableMouseWheel(self.mainWindow.preferences.generalForm.disableMouseWheel)
        
        # add observers
#         self.vtkRenWinInteract._Iren.AddObserver("LeftButtonPressEvent", self.leftButtonPressed)
        
        # connect signals from QVTK
        self.vtkRenWinInteract.leftButtonPressOverride.connect(self.leftButtonPressed)
        self.vtkRenWinInteract.leftButtonReleaseOverride.connect(self.leftButtonReleased)
        self.vtkRenWinInteract.rightButtonPressOverride.connect(self.rightButtonPressed)
        self.vtkRenWinInteract.rightButtonReleaseOverride.connect(self.rightButtonReleased)
        self.vtkRenWinInteract.mouseMoveOverride.connect(self.mouseMoved)
        
        # add picker
        self.vtkPicker = vtk.vtkCellPicker()
        self.vtkPicker.SetTolerance(0.001)
        self.vtkPicker.AddObserver("EndPickEvent", self.endPickEvent)
        self.vtkRenWinInteract.SetPicker(self.vtkPicker)
        
        # vtk renderer
        self.vtkRen = vtk.vtkRenderer()
        self.vtkRen.SetBackground(1, 1, 1)
        
        self.vtkRenWin.AddRenderer(self.vtkRen)
        
        self.vtkRenWin.SetAAFrames(self.currentAAFrames)
        
        self.vtkRenWinInteract.Initialize()
        self.vtkRenWinInteract.Start()
        
        layout.addWidget(self.vtkRenWinInteract)
        
        # renderer
        self.renderer = renderer.Renderer(self)
        
        # do a post ref render if the ref is already loaded
        if self.mainWindow.refLoaded:
            self.renderer.postRefRender()
        
        # output dialog
        self.outputDialog = OutputDialog(self, self.mainWindow, None, index)
        
        # refresh rdf tab if ref already loaded
        if self.mainWindow.refLoaded:
            self.outputDialog.rdfTab.refresh()
        
        # text selector
        self.textSelector = onScreenInfoDialog.OnScreenInfoDialog(self.mainWindow, index, parent=self)
        
        # view point rotate dialog
        self.rotateViewPointDialog = dialogs.RotateViewPointDialog(self, parent=self)
        
        # which filter list is it associated with
        label = QtGui.QLabel("Analysis pipeline:")
        self.analysisPipelineCombo = QtGui.QComboBox()
        self.analysisPipelineCombo.currentIndexChanged.connect(self.pipelineChanged)
        self.initPipelines()
        
        row = QtGui.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setAlignment(QtCore.Qt.AlignHCenter)
        row.addWidget(label)
        row.addWidget(self.analysisPipelineCombo)
        
        layout.addLayout(row)
    
    def toggleProjection(self):
        """
        Toggle projection
        
        """
        if self.parallelProjection:
            self.renderer.camera.ParallelProjectionOff()
            self.parallelProjection = False
        
        else:
            self.renderer.camera.ParallelProjectionOn()
            
            inp = self.getCurrentInputState()
            s = (inp.cellDims[0] + inp.cellDims[1]) / 2.0
            self.renderer.camera.SetParallelScale(s)
            
            self.parallelProjection = True
        
        self.renderer.reinit()
    
    def rotateViewPoint(self):
        """
        Show rotate view point dialog
        
        """
        if self.getCurrentRefState() is None:
            return
        
        self.rotateViewPointDialog.hide()
        self.rotateViewPointDialog.show()
    
    def showCameraSettings(self):
        """
        Show camera settings
        
        """
        dlg = dialogs.CameraSettingsDialog(self, self.renderer)
        dlg.show()
    
    def increaseAA(self):
        """
        Increase AA setting
        
        """
        self.currentAAFrames += 1
        
        print "SET AA FRAMES", self.currentAAFrames
        
        self.vtkRenWin.SetAAFrames(self.currentAAFrames)
        
        self.vtkRenWinInteract.ReInitialize()
    
    def decreaseAA(self):
        """
        Decrease AA settings
        
        """
        if self.currentAAFrames == 0:
            return
        
        self.currentAAFrames -= 1
        
        print "SET AA FRAMES", self.currentAAFrames
        
        self.vtkRenWin.SetAAFrames(self.currentAAFrames)
        
        self.vtkRenWinInteract.ReInitialize()
    
    def toggleBackgroundColour(self):
        """
        Toggle background colour between black and white.
        
        """
        if self.blackBackground:
            self.blackBackground = False
            
            # background
            self.vtkRen.SetBackground(1, 1, 1)
            
            # cell frame
            self.renderer.latticeFrame.setColour((0, 0, 0))
        
        else:
            self.blackBackground = True
            
            # background
            self.vtkRen.SetBackground(0, 0, 0)
            
            # cell frame
            self.renderer.latticeFrame.setColour((1, 1, 1))
        
        # text
        self.refreshOnScreenInfo()
        
        # toggle scalar bar
        self.toggleScalarBar()
        
        # reinit
        self.renderer.reinit()
    
    def toggleScalarBar(self):
        """
        Toggle colour of scalar bar
        
        """
        # assume self.blackBackground has already been changed
        
        black_bg_now = self.blackBackground
        if black_bg_now:
            black_bg = False
        else:
            black_bg = True
        
        filterLists = self.getFilterLists()
        
        for filterList in filterLists:
            filterer = filterList.filterer
            
            if filterer.scalarBarAdded:
                # which scalar bar
                if black_bg:
                    scalarBar = filterer.scalarBar_black_bg
                    scalarBarAdd = filterer.scalarBar_white_bg
                else:
                    scalarBar = filterer.scalarBar_white_bg
                    scalarBarAdd = filterer.scalarBar_black_bg
                
                # remove it
                self.vtkRen.RemoveActor2D(scalarBar)
                
                # add other one
                self.vtkRen.AddActor2D(scalarBarAdd)
                
                self.vtkRenWinInteract.ReInitialize()
    
    def initPipelines(self):
        """
        Initialise pipeline combo.
        
        """
        if not hasattr(self.mainWindow, "mainToolbar"):
            return
        
        combo = self.mainWindow.mainToolbar.pipelineCombo
        
        for i in xrange(combo.count()):
            self.newPipeline(str(combo.itemText(i)))
    
    def getCurrentPipelinePage(self):
        """
        Return current pipeline page.
        
        """
        try:
            toolbar = self.mainWindow.mainToolbar
        
        except AttributeError:
            pp = None
        
        else:
            pp = toolbar.pipelineList[self.currentPipelineIndex]
        
        return pp
    
    def getFilterLists(self):
        """
        Returns the filter lists for given pipeline.
        
        """
        if hasattr(self.mainWindow, "mainToolbar"):
            filterLists = self.getCurrentPipelinePage().filterLists
        else:
            filterLists = []
        
        return filterLists
    
    def gatherVisibleAtoms(self):
        """
        Gather visible atoms array.
        
        """
        return self.getCurrentPipelinePage().gatherVisibleAtoms()
    
    def removeActors(self):
        """
        Remove current actors.
        
        """
        filterLists = self.getFilterLists()
        
        # remove actors from filter lists
        for filterList in filterLists:
            filterer = filterList.filterer
            actorsCollection = filterer.actorsCollection
            
            actorsCollection.InitTraversal()
            actor = actorsCollection.GetNextItem()
            while actor is not None:
                try:
                    self.vtkRen.RemoveActor(actor)
                except:
                    pass
                
                actor = actorsCollection.GetNextItem()
            
            if filterer.scalarBarAdded:
                # which scalar bar
                if self.blackBackground:
                    scalarBar = filterer.scalarBar_black_bg
                else:
                    scalarBar = filterer.scalarBar_white_bg
                
                self.vtkRen.RemoveActor2D(scalarBar)
        
        # remove slice plane?
        self.removeSlicePlane()
        
        # remove 
        for key in self.highlighters.keys():
            self.removeHighlighters(key)
        
        self.vtkRenWinInteract.ReInitialize()
    
    def addActors(self):
        """
        Add current actors.
        
        """
        filterLists = self.getFilterLists()
        
        for filterList in filterLists:
            filterer = filterList.filterer
            actorsCollection = filterer.actorsCollection
            
            actorsCollection.InitTraversal()
            actor = actorsCollection.GetNextItem()
            while actor is not None:
                try:
                    self.vtkRen.AddActor(actor)
                except:
                    pass
                
                actor = actorsCollection.GetNextItem()
            
            if filterer.scalarBarAdded:
                # which scalar bar
                if self.blackBackground:
                    scalarBar = filterer.scalarBar_black_bg
                else:
                    scalarBar = filterer.scalarBar_white_bg
                
                self.vtkRen.AddActor2D(scalarBar)
            
            self.vtkRenWinInteract.ReInitialize()
    
    def getCurrentRefState(self):
        """
        Returns current ref state
        
        """
        pp = self.getCurrentPipelinePage()
        
        if pp is None:
            refState = None
        
        else:
            refState = pp.refState
        
        return refState
    
    def getCurrentInputState(self):
        """
        Returns current input state
        
        """
        pp = self.getCurrentPipelinePage()
        
        if pp is None:
            inputState = None
        
        else:
            inputState = pp.inputState
        
        return inputState
    
    def postInputChanged(self):
        """
        Refresh stuff when the input system has changed
        
        """
        self.textSelector.refresh()
        self.outputDialog.plotTab.rdfForm.refresh()
        self.outputDialog.plotTab.scalarsForm.refreshScalarPlotOptions()
        self.outputDialog.imageTab.imageSequenceTab.resetPrefix()
    
    def pipelineChanged(self, index):
        """
        Current pipeline changed.
        
        """
        # remove actors
        self.removeActors()
        
        # update vars
        self.currentPipelineString = str(self.analysisPipelineCombo.currentText())
        self.currentPipelineIndex = index
        
        # post ref render
        if self.getCurrentRefState() is not None:
            self.renderer.postRefRender()
        
        # get new actors
        self.addActors()
        
        # refresh text
        self.refreshOnScreenInfo()
        
        # refresh optiona etc
        if self.getCurrentInputState() is not None:
            self.postInputChanged()
    
    def showOutputDialog(self):
        """
        Show output dialog.
        
        """
        if self.getCurrentRefState() is None:
            return
        
        self.outputDialog.hide()
        self.outputDialog.show()
    
    def removePipeline(self, index):
        """
        Remove given pipeline.
        
        """
        self.analysisPipelineCombo.removeItem(index)
        
        # update index and string
        self.currentPipelineString = str(self.analysisPipelineCombo.currentText())
        self.currentPipelineIndex = self.analysisPipelineCombo.currentIndex()
        
    
    def newPipeline(self, name):
        """
        Add new pipeline to the combo.
        
        """
        self.analysisPipelineCombo.addItem(name)
    
    def endPickEvent(self, obj, event):
        """
        End of vtk pick event.
        
        """
        logger = self.logger
        
        if self.leftClick and not self.rightClick:
            logger.debug("Left click event")
            clickType = "LeftClick"
        
        elif self.rightClick and not self.leftClick:
            logger.debug("Right click event")
            clickType = "RightClick"
        
        else:
            logger.error("Left/right click not set")
            return
        
        if self.vtkPicker.GetCellId() < 0:
            pass
        
        else:
            logger.debug("End pick event: sending pick to pipeline")
            
            pickPos = self.vtkPicker.GetPickPosition()
            pickPos_np = np.asarray(pickPos, dtype=np.float64)
            
            # pipeline form
            pipelinePage = self.getCurrentPipelinePage()
            pipelinePage.pickObject(pickPos_np, clickType)
    
    def mouseMoved(self, event):
        """
        Mouse moved
        
        """
        self.mouseMotion = True
    
    def leftButtonPressed(self, event):
        """
        Left mouse button pressed
        
        """
        self.mouseMotion = False
        self.rightClick = False
        self.leftClick = True
    
    def leftButtonReleased(self, event):
        """
        Left button released.
        
        """
        if not self.mouseMotion:
            self.leftClick = True
            pos = self.vtkRenWinInteract.GetEventPosition()
            self.vtkPicker.Pick(pos[0], pos[1], 0, self.vtkRen)
        
        self.leftClick = False
    
    def rightButtonPressed(self, event):
        """
        Left mouse button pressed
        
        """
        self.mouseMotion = False
    
    def rightButtonReleased(self, event):
        """
        Left button released.
        
        """
        if not self.mouseMotion:
            self.rightClick = True
            pos = self.vtkRenWinInteract.GetEventPosition()
            self.vtkPicker.Pick(pos[0], pos[1], 0, self.vtkRen)
        
        self.rightClick = False
    
    def setCameraToCell(self):
        """
        Reset the camera to point at the cell
        
        """
        self.renderer.setCameraToCell()
    
    def toggleCellFrame(self):
        """
        Toggle lattice frame visibility
        
        """
        self.renderer.toggleLatticeFrame()
    
    def toggleAxes(self):
        """
        Toggle axes visibility
        
        """
        self.renderer.toggleAxes()
    
    def createAction(self, text, slot=None, shortcut=None, icon=None,
                     tip=None, checkable=False, signal="triggered()"):
        """
        Create an action
        
        """
        action = QtGui.QAction(text, self)
        
        if icon is not None:
            action.setIcon(QtGui.QIcon(iconPath(icon)))
        
        if shortcut is not None:
            action.setShortcut(shortcut)
        
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        
        if slot is not None:
            self.connect(action, QtCore.SIGNAL(signal), slot)
        
        if checkable:
            action.setCheckable(True)
        
        return action
    
    def addActions(self, target, actions):
        """
        Add a tuple of actions to the target.
        
        """
        for action in actions:
            if action is None:
                target.addSeparator()
            
            else:
                target.addAction(action)
    
    def showTextSelector(self):
        """
        Show the text selector.
        
        """
        self.textSelector.hide()
        self.textSelector.show()
    
    def removeOnScreenInfo(self):
        """
        Remove on screen info.
        
        """
        self.onScreenInfoActors.InitTraversal()
        actor = self.onScreenInfoActors.GetNextItem()
        while actor is not None:
            try:
                self.vtkRen.RemoveActor(actor)
            except:
                pass
            
            actor = self.onScreenInfoActors.GetNextItem()
        
        self.vtkRenWinInteract.ReInitialize()
        
        self.onScreenInfoActors = vtk.vtkActor2DCollection()
    
    def refreshOnScreenInfo(self):
        """
        Refresh the on-screen information.
        
        """
        if self.getCurrentRefState() is None:
            return
        
        self.logger.debug("Refreshing on screen info")
        
        textSel = self.textSelector
        selectedText = textSel.selectedText()
        
        self.onScreenInfo = {}
        self.removeOnScreenInfo()
        
        if not len(selectedText):
            return
        
        inputState = self.getCurrentInputState()
        
        # if input state not set yet just use empty lattice
        if inputState is None:
            inputState = Lattice()
        
        # atom count
        self.onScreenInfo["Atom count"] = (inputState.NAtoms,)
        
        # Lattice attributes
        for key, value in inputState.attributes.iteritems():
            if key == "Time":
                self.onScreenInfo[key] = tuple(utilities.simulationTimeLine(value).split())
            
            else:
                self.onScreenInfo[key] = (value,)        

        # lattice temperature
        if not "Temperature" in inputState.attributes:
            temperature = inputState.calcTemperature()
            if temperature is not None:
                self.onScreenInfo["Temperature"] = ("%.3f" % temperature,)
        
        # filter lists
        filterLists = self.getFilterLists()
        
        # visible counts always recalculated
        visCountActive = False
        visCount = 0
        numClusters = 0
        for filterList in filterLists:
            if filterList.visible:
                if not filterList.defectFilterSelected:
                    visCountActive = True
                    visCount += filterList.filterer.NVis
                
                numClusters += len(filterList.filterer.clusterList)
        
        if numClusters:
            self.onScreenInfo["Cluster count"] = (numClusters,)
        
        if visCountActive:
            self.onScreenInfo["Visible count"] = (visCount,)
        
            visSpecCount = np.zeros(len(inputState.specieList), np.int32)
            for filterList in filterLists:
                if filterList.visible and not filterList.defectFilterSelected and filterList.filterer.NVis:
                    if len(visSpecCount) == len(filterList.filterer.visibleSpecieCount):
                        visSpecCount = np.add(visSpecCount, filterList.filterer.visibleSpecieCount)
        
            specieList = inputState.specieList
            self.onScreenInfo["Visible specie count"] = []
            for i, cnt in enumerate(visSpecCount):
                self.onScreenInfo["Visible specie count"].append((cnt, specieList[i]))
        
        # structure counters
        for filterList in filterLists:
            for key, structureCounterDict in filterList.filterer.structureCounterDicts.iteritems():
                self.logger.debug("Adding on-screen info for structure counter: '%s'", key)
                self.onScreenInfo[key] = []
                
                for structure in sorted(structureCounterDict.keys()):
                    self.logger.debug("  %d %s" % (structureCounterDict[structure], structure))
                    self.onScreenInfo[key].append((structureCounterDict[structure], structure))
        
        # defects counts
        defectFilterActive = False
        NVac = 0
        NInt = 0
        NAnt = 0
        showVacs = False
        showInts = False
        showAnts = False
        for filterList in filterLists:
            if filterList.visible and filterList.defectFilterSelected:
                defectFilterActive = True
                
                NVac += filterList.filterer.NVac
                NInt += filterList.filterer.NInt
                NAnt += filterList.filterer.NAnt
                
                # defects settings
                defectsSettings = filterList.getCurrentFilterSettings()[0]
                
                if defectsSettings.showVacancies:
                    showVacs = True
                
                if defectsSettings.showInterstitials:
                    showInts = True
                
                if defectsSettings.showAntisites:
                    showAnts = True
        
        if defectFilterActive:
            refState = self.getCurrentRefState()
            
            # defect specie counters
            vacSpecCount = np.zeros(len(refState.specieList), np.int32)
            intSpecCount = np.zeros(len(inputState.specieList), np.int32)
            antSpecCount = np.zeros((len(refState.specieList), len(inputState.specieList)), np.int32)
            splitSpecCount = np.zeros((len(inputState.specieList), len(inputState.specieList)), np.int32)
            for filterList in filterLists:
                if filterList.visible and filterList.defectFilterSelected and filterList.filterer.NVis:
                    if len(vacSpecCount) == len(filterList.filterer.vacancySpecieCount):
                        vacSpecCount = np.add(vacSpecCount, filterList.filterer.vacancySpecieCount)
                        intSpecCount = np.add(intSpecCount, filterList.filterer.interstitialSpecieCount)
                        antSpecCount = np.add(antSpecCount, filterList.filterer.antisiteSpecieCount)
                        splitSpecCount = np.add(splitSpecCount, filterList.filterer.splitIntSpecieCount)
            
            # now add to dict
            self.onScreenInfo["Defect count"] = []
            
            if showVacs:
                self.onScreenInfo["Defect count"].append((NVac, "vacancies"))
            
            if showInts:
                self.onScreenInfo["Defect count"].append((NInt, "interstitials"))
            
            if showAnts:
                self.onScreenInfo["Defect count"].append((NAnt, "antisites"))
            
            specListInput = inputState.specieList
            specListRef = refState.specieList
            specRGBInput = inputState.specieRGB
            specRGBRef = refState.specieRGB
            
            self.onScreenInfo["Defect specie count"] = []
            
            if showVacs:
                for i, cnt in enumerate(vacSpecCount):
                    self.onScreenInfo["Defect specie count"].append([(cnt, specListRef[i], "vacancies"), specRGBRef[i]])
            
            if showInts:
                for i, cnt in enumerate(intSpecCount):
                    self.onScreenInfo["Defect specie count"].append([(cnt, specListInput[i], "interstitials"), specRGBInput[i]])
                
                if defectsSettings.identifySplitInts:
                    for i in xrange(len(specListInput)):
                        for j in xrange(i, len(specListInput)):
                            if j == i:
                                N = splitSpecCount[i][j]
                                rgb = specRGBInput[i]
                            else:
                                N = splitSpecCount[i][j] + splitSpecCount[j][i]
                                rgb = (specRGBInput[i] + specRGBInput[j]) / 2.0
                            
                            self.onScreenInfo["Defect specie count"].append([(N, "%s-%s" % (specListInput[i], specListInput[j]), "split ints"), rgb])
            
            if showAnts:
                for i in xrange(len(specListRef)):
                    for j in xrange(len(specListInput)):
                        if i == j:
                            continue
                        self.onScreenInfo["Defect specie count"].append([(antSpecCount[i][j], "%s on %s" % (specListInput[j], specListRef[i]), "antisites"), specRGBRef[i]])
        
        # alignment/position stuff
        topyLeft = self.vtkRenWinInteract.height() - 5
        topxLeft = 5
        topyRight = self.vtkRenWinInteract.height() - 5
        topxRight = self.vtkRenWinInteract.width() - 220
        
        # loop over selected text
        for i in xrange(len(selectedText)):
            settings = selectedText[i]
            item = settings.title
            
            try:
                line = self.onScreenInfo[item]
            
            except KeyError:
                self.logger.debug("Item '%s' not in onScreenInfo dict", item)
            
            else:
                if item == "Visible specie count":
                    for j, specline in enumerate(line):
                        r, g, b = inputState.specieRGB[j]
                        r, g, b = self.checkTextRGB(r, g, b)
                        
                        if settings.position == "Top left":
                            xpos = topxLeft
                            ypos = topyLeft
                        else:
                            xpos = topxRight
                            ypos = topyRight
                        
                        # make text string
                        text = settings.makeText(specline)
                        
                        # add actor
                        actor = vtkRenderWindowText(text, 20, xpos, ypos, r, g, b)
                        
                        if settings.position == "Top left":
                            topyLeft -= 20
                        else:
                            topyRight -= 20
                        
                        self.onScreenInfoActors.AddItem(actor)
                
                elif item == "Defect count":
                    for specline in line:
                        r = g = b = 0
                        r, g, b = self.checkTextRGB(r, g, b)
                        
                        if settings.position == "Top left":
                            xpos = topxLeft
                            ypos = topyLeft
                        else:
                            xpos = topxRight
                            ypos = topyRight
                        
                        # make text string
                        text = settings.makeText(specline)
                        
                        # add actor
                        actor = vtkRenderWindowText(text, 20, xpos, ypos, r, g, b)
                        
                        if settings.position == "Top left":
                            topyLeft -= 20
                        else:
                            topyRight -= 20
                        
                        self.onScreenInfoActors.AddItem(actor)
                
                elif item == "Defect specie count":
                    for array in line:
                        lineArgs = array[0]
                        r, g, b = array[1]
                        r, g, b = self.checkTextRGB(r, g, b)
                        
                        if settings.position == "Top left":
                            xpos = topxLeft
                            ypos = topyLeft
                        else:
                            xpos = topxRight
                            ypos = topyRight
                        
                        # make text string
                        text = settings.makeText(lineArgs)
                        
                        # add actor
                        actor = vtkRenderWindowText(text, 20, xpos, ypos, r, g, b)
                        
                        if settings.position == "Top left":
                            topyLeft -= 20
                        else:
                            topyRight -= 20
                        
                        self.onScreenInfoActors.AddItem(actor)
                
                elif type(line) is list:
                    for subl in line:
                        r = g = b = 0
                        r, g, b = self.checkTextRGB(r, g, b)
                        
                        if settings.position == "Top left":
                            xpos = topxLeft
                            ypos = topyLeft
                        else:
                            xpos = topxRight
                            ypos = topyRight
                        
                        # make text string
                        text = settings.makeText(subl)
                        
                        # add actor
                        actor = vtkRenderWindowText(text, 20, xpos, ypos, r, g, b)
                        
                        if settings.position == "Top left":
                            topyLeft -= 20
                        else:
                            topyRight -= 20
                        
                        self.onScreenInfoActors.AddItem(actor)
                
                else:
                    r = g = b = 0
                    r, g, b = self.checkTextRGB(r, g, b)
                    
                    if settings.position == "Top left":
                        xpos = topxLeft
                        ypos = topyLeft
                    else:
                        xpos = topxRight
                        ypos = topyRight
                    
                    # make text string
                    text = settings.makeText(line)
                    
                    # add actor
                    actor = vtkRenderWindowText(text, 20, xpos, ypos, r, g, b)
                    
                    if settings.position == "Top left":
                        topyLeft -= 20
                    else:
                        topyRight -= 20
                    
                    self.onScreenInfoActors.AddItem(actor)
        
        # add to render window
        self.onScreenInfoActors.InitTraversal()
        actor = self.onScreenInfoActors.GetNextItem()
        while actor is not None:
            try:
                self.vtkRen.AddActor(actor)
            except:
                pass
            
            actor = self.onScreenInfoActors.GetNextItem()
        
        self.vtkRenWinInteract.ReInitialize()
    
    def checkTextRGB(self, r, g, b):
        """
        Check rgb values.
        
        """
        if self.blackBackground:
            if r == g == b == 0:
                r = b = g = 1
        
        else:
            if r == g == b == 1:
                r = b = g = 0
        
        return r, g, b
    
    def closeEvent(self, event):
        """
        Override close event.
        
        """
        reply = QtGui.QMessageBox.question(self, 'Message', "Are you sure you want to close this window", 
                                           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        
        if reply == QtGui.QMessageBox.Yes:
            self.closed = True
            self.mainWindow.renderWindowClosed()
            event.accept()
        else:
            event.ignore()
    
    def showSlicePlane(self, actor):
        """
        Show the slice plane helper actor.
        
        """
        if self.slicePlaneActor is not None:
            try:
                self.vtkRen.RemoveActor(self.slicePlaneActor)
                self.vtkRenWinInteract.ReInitialize()
            except:
                print "REM SLICE ACTOR FAILED"
            
        self.slicePlaneActor = actor
        
        self.vtkRen.AddActor(self.slicePlaneActor)
        self.vtkRenWinInteract.ReInitialize()
    
    def removeSlicePlane(self):
        """
        Remove the slice plane actor.
        
        """
        if self.slicePlaneActor is not None:
            try:
                self.vtkRen.RemoveActor(self.slicePlaneActor)
                self.vtkRenWinInteract.ReInitialize()
                self.slicePlaneActor = None
            except:
                print "REM SLICE ACTOR FAILED"
    
    def addHighlighters(self, highlightersID, highlighters):
        """
        Add highlighters to renderer
        
        """
        logger = self.logger
        logger.debug("Adding highlighters to renderer %d", self.rendererIndex)
        
        # first check if highlighter is already in our dict
        if highlightersID in self.highlighters:
            logger.debug("Highlighters already in dict: ignoring")
            return
        
        # add to renderer
        for actor in highlighters:
            self.vtkRen.AddActor(actor)
        
        # reinit
        self.vtkRenWinInteract.ReInitialize()
        
        # add to dict
        self.highlighters[highlightersID] = highlighters
    
    def removeHighlighters(self, highlightersID):
        """
        Remove specified highlighters from render
        
        """
        logger = self.logger
        logger.debug("Removing highlighters from renderer %d", self.rendererIndex)
        
        if highlightersID not in self.highlighters:
            return
        
        # get highlighters
        hls = self.highlighters[highlightersID]
        
        # remove actors
        for actor in hls:
            self.vtkRen.RemoveActor(actor)
        
        # reinit
        self.vtkRenWinInteract.ReInitialize()
        
        # remove from dict
        self.highlighters.pop(highlightersID)
