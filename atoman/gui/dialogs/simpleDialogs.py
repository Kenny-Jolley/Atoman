# -*- coding: utf-8 -*-

"""
Additional dialogs.

@author: Chris Scott

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import copy
import logging

from PySide import QtGui, QtCore
import numpy as np
import math as math

from ...system.atoms import elements
from ...visutils.utilities import resourcePath, iconPath
from ...visutils import utilities


################################################################################

class CameraSettingsDialog(QtGui.QDialog):
    """
    Camera settings dialog
    
    """
    def __init__(self, parent, renderer):
        super(CameraSettingsDialog, self).__init__(parent)
        
#         self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        self.renderer = renderer
        
        self.setModal(True)
        
        self.setWindowTitle("Camera settings")
        self.setWindowIcon(QtGui.QIcon(iconPath("cam.png")))
        
        self.contentLayout = QtGui.QFormLayout(self)
#         self.contentLayout.setAlignment(QtCore.Qt.AlignHCenter)
        
        # ini vals
        self.campos = list(renderer.camera.GetPosition())
        self.camfoc = list(renderer.camera.GetFocalPoint())
        self.camvup = list(renderer.camera.GetViewUp())
        
        self.camposbkup = copy.deepcopy(self.campos)
        self.camfocbkup = copy.deepcopy(self.camfoc)
        self.camvupbkup = copy.deepcopy(self.camvup)
        
        # cam pos
        self.camPosXSpin = QtGui.QDoubleSpinBox()
        self.camPosXSpin.setMinimum(-99999.0)
        self.camPosXSpin.setMaximum(99999.0)
        self.camPosXSpin.setValue(self.campos[0])
        self.camPosXSpin.valueChanged[float].connect(self.camxposChanged)
        
        self.camPosYSpin = QtGui.QDoubleSpinBox()
        self.camPosYSpin.setMinimum(-99999.0)
        self.camPosYSpin.setMaximum(99999.0)
        self.camPosYSpin.setValue(self.campos[1])
        self.camPosYSpin.valueChanged[float].connect(self.camyposChanged)
        
        self.camPosZSpin = QtGui.QDoubleSpinBox()
        self.camPosZSpin.setMinimum(-99999.0)
        self.camPosZSpin.setMaximum(99999.0)
        self.camPosZSpin.setValue(self.campos[2])
        self.camPosZSpin.valueChanged[float].connect(self.camzposChanged)
        
        row = QtGui.QHBoxLayout()
        row.addWidget(self.camPosXSpin)
        row.addWidget(self.camPosYSpin)
        row.addWidget(self.camPosZSpin)
        self.contentLayout.addRow("Position", row)
        
        # cam focal point
        self.camFocXSpin = QtGui.QDoubleSpinBox()
        self.camFocXSpin.setMinimum(-99999.0)
        self.camFocXSpin.setMaximum(99999.0)
        self.camFocXSpin.setValue(self.camfoc[0])
        self.camFocXSpin.valueChanged[float].connect(self.camxfocChanged)
        
        self.camFocYSpin = QtGui.QDoubleSpinBox()
        self.camFocYSpin.setMinimum(-99999.0)
        self.camFocYSpin.setMaximum(99999.0)
        self.camFocYSpin.setValue(self.camfoc[1])
        self.camFocYSpin.valueChanged[float].connect(self.camyfocChanged)
        
        self.camFocZSpin = QtGui.QDoubleSpinBox()
        self.camFocZSpin.setMinimum(-99999.0)
        self.camFocZSpin.setMaximum(99999.0)
        self.camFocZSpin.setValue(self.camfoc[2])
        self.camFocZSpin.valueChanged[float].connect(self.camzfocChanged)
        
        row = QtGui.QHBoxLayout()
        row.addWidget(self.camFocXSpin)
        row.addWidget(self.camFocYSpin)
        row.addWidget(self.camFocZSpin)
        self.contentLayout.addRow("Focal point", row)
        
        # cam view up
        self.camVupXSpin = QtGui.QDoubleSpinBox()
        self.camVupXSpin.setMinimum(-99999.0)
        self.camVupXSpin.setMaximum(99999.0)
        self.camVupXSpin.setValue(self.camvup[0])
        self.camVupXSpin.valueChanged[float].connect(self.camxvupChanged)
        
        self.camVupYSpin = QtGui.QDoubleSpinBox()
        self.camVupYSpin.setMinimum(-99999.0)
        self.camVupYSpin.setMaximum(99999.0)
        self.camVupYSpin.setValue(self.camvup[1])
        self.camVupYSpin.valueChanged[float].connect(self.camyvupChanged)
        
        self.camVupZSpin = QtGui.QDoubleSpinBox()
        self.camVupZSpin.setMinimum(-99999.0)
        self.camVupZSpin.setMaximum(99999.0)
        self.camVupZSpin.setValue(self.camvup[2])
        self.camVupZSpin.valueChanged[float].connect(self.camzvupChanged)
        
        row = QtGui.QHBoxLayout()
        row.addWidget(self.camVupXSpin)
        row.addWidget(self.camVupYSpin)
        row.addWidget(self.camVupZSpin)
        self.contentLayout.addRow("View up", row)
        
        # button box
        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close | QtGui.QDialogButtonBox.Reset)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.clicked.connect(self.buttonBoxClicked)
        self.contentLayout.addWidget(self.buttonBox)
    
    def buttonBoxClicked(self, button):
        """A button was clicked."""
        if self.buttonBox.button(QtGui.QDialogButtonBox.Reset) == button:
            self.resetChanges()
    
    def resetChanges(self):
        """
        Reset changes
        
        """
        self.campos = self.camposbkup
        self.camfoc = self.camfocbkup
        self.camvup = self.camvupbkup
        
        self.renderer.camera.SetPosition(self.campos)
        self.renderer.camera.SetFocalPoint(self.camfoc)
        self.renderer.camera.SetViewUp(self.camvup)
        
        self.renderer.reinit()
    
    def camxposChanged(self, val):
        """
        Cam x pos changed
        
        """
        self.campos[0] = val
        self.renderer.camera.SetPosition(self.campos)
        self.renderer.reinit()
    
    def camyposChanged(self, val):
        """
        Cam y pos changed
        
        """
        self.campos[1] = val
        self.renderer.camera.SetPosition(self.campos)
        self.renderer.reinit()
    
    def camzposChanged(self, val):
        """
        Cam z pos changed
        
        """
        self.campos[2] = val
        self.renderer.camera.SetPosition(self.campos)
        self.renderer.reinit()
    
    def camxfocChanged(self, val):
        """
        Cam x foc changed
        
        """
        self.camfoc[0] = val
        self.renderer.camera.SetFocalPoint(self.camfoc)
        self.renderer.reinit()
    
    def camyfocChanged(self, val):
        """
        Cam y foc changed
        
        """
        self.camfoc[1] = val
        self.renderer.camera.SetFocalPoint(self.camfoc)
        self.renderer.reinit()
    
    def camzfocChanged(self, val):
        """
        Cam z foc changed
        
        """
        self.camfoc[2] = val
        self.renderer.camera.SetFocalPoint(self.camfoc)
        self.renderer.reinit()
    
    def camxvupChanged(self, val):
        """
        Cam x foc changed
        
        """
        self.camvup[0] = val
        self.renderer.camera.SetViewUp(self.camvup)
        self.renderer.reinit()
    
    def camyvupChanged(self, val):
        """
        Cam y foc changed
        
        """
        self.camvup[1] = val
        self.renderer.camera.SetViewUp(self.camvup)
        self.renderer.reinit()
    
    def camzvupChanged(self, val):
        """
        Cam z foc changed
        
        """
        self.camvup[2] = val
        self.renderer.camera.SetViewUp(self.camvup)
        self.renderer.reinit()

################################################################################

class ImageViewer(QtGui.QDialog):
    """
    Image viewer.
    
    @author: Marc Robinson
    Rewritten by Chris Scott
    
    """
    def __init__(self, mainWindow, parent=None):
        super(ImageViewer, self).__init__(parent)
        
#         self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        self.parent = parent
        self.mainWindow = mainWindow
        
        self.setWindowTitle("Image Viewer:")
        self.setWindowIcon(QtGui.QIcon(iconPath("oxygen/applications-graphics.png")))
        
        # main layout
        dialogLayout = QtGui.QHBoxLayout()
        
        # initial dir
        startDir = os.getcwd()
        
        # dir model
        self.model = QtGui.QFileSystemModel()
        self.model.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllDirs | QtCore.QDir.Files)
        self.model.setNameFilters(["*.jpg", "*.tif","*.png","*.bmp"])
        self.model.setNameFilterDisables(0)
        self.model.setRootPath(startDir)
        
        # dir view
        self.view = QtGui.QTreeView(parent=self)
        self.view.setModel(self.model)
        self.view.clicked[QtCore.QModelIndex].connect(self.clicked)
        self.view.hideColumn(1)
        self.view.setRootIndex(self.model.index(startDir))
        self.view.setMinimumWidth(300)
        self.view.setColumnWidth(0, 150)
        self.view.setColumnWidth(2, 50)
        
        # add to main layout
        dialogLayout.addWidget(self.view)
        
        # image label
        self.imageLabel = QtGui.QLabel()
        
        column = QtGui.QWidget()
        columnLayout = QtGui.QVBoxLayout(column)
        columnLayout.setSpacing(0)
        columnLayout.setContentsMargins(0, 0, 0, 0)
        
        columnLayout.addWidget(self.imageLabel)
        
        # delete button
        deleteImageButton = QtGui.QPushButton(QtGui.QIcon(iconPath("oxygen/edit-delete.png")), "Delete image")
        deleteImageButton.clicked.connect(self.deleteImage)
        deleteImageButton.setStatusTip("Delete image")
        deleteImageButton.setAutoDefault(False)
        columnLayout.addWidget(deleteImageButton)
        
        # add to layout
        dialogLayout.addWidget(column)
        
        # set layout
        self.setLayout(dialogLayout)
    
    def clicked(self, index):
        """
        File clicked.
        
        """
        self.showImage(self.model.filePath(index))
    
    def showImage(self, filename):
        """
        Show image.
        
        """
        try:
            image = QtGui.QImage(filename)
            self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(image))
            self.setWindowTitle("Image Viewer: %s" % filename)
        
        except:
            print("ERROR: could not display image in Image Viewer")
    
    def deleteImage(self):
        """
        Delete image.
        
        """
        reply = QtGui.QMessageBox.question(self, "Message", 
                                           "Delete file: %s?" % self.model.filePath(self.view.currentIndex()),
                                           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        
        if reply == QtGui.QMessageBox.Yes:
            success = self.model.remove(self.view.currentIndex())
        
            if success:
                self.clearImage()
    
    def clearImage(self):
        """
        Clear the image label.
        
        """
        self.imageLabel.clear()
        self.setWindowTitle("Image Viewer:")
    
    def changeDir(self, dirname):
        """
        Change directory
        
        """
        self.view.setRootIndex(self.model.index(dirname))
        self.clearImage()
    
    def keyReleaseEvent(self, event):
        """
        Handle up/down key press
        
        """
        if event.key() == QtCore.Qt.Key_Up or event.key() == QtCore.Qt.Key_Down:
            self.model.filePath(self.view.currentIndex())
            self.showImage(self.model.filePath(self.view.currentIndex()))

################################################################################

class AboutMeDialog(QtGui.QMessageBox):
    """
    About me dialog.
    
    """
    def __init__(self, parent=None):
        super(AboutMeDialog, self).__init__(parent)
        
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        from ..visutils.version import getVersion
        import datetime
        import paramiko
        import matplotlib
        import platform
        import PySide
        import vtk
        import scipy
        version = getVersion()
        
        self.setWindowTitle("Atoman %s" % version)
        
        # message box layout (grid layout)
        l = self.layout()
        
        self.setText("""<p><b>Atoman</b> %s</p>
                          <p>Copyright &copy; %d Loughborough University</p>
                          <p>Written by Chris Scott</p>
                          <p>This application can be used to visualise atomistic simulations.</p>
                          <p>GUI based on <a href="http://sourceforge.net/projects/avas/">AVAS</a> 
                             by Marc Robinson.</p>""" % (
                          version, datetime.date.today().year))
        
        packageList = QtGui.QListWidget()
        
        packageList.addItem("Python %s" % platform.python_version())
        packageList.addItem("Qt %s" % QtCore.__version__)
        packageList.addItem("PySide %s" % PySide.__version__)
        packageList.addItem("VTK %s" % vtk.vtkVersion.GetVTKVersion())
        packageList.addItem("NumPy %s" % np.__version__)
        packageList.addItem("SciPy %s" % scipy.__version__)
        packageList.addItem("Matplotlib %s" % matplotlib.__version__)
        packageList.addItem("Paramiko %s" % paramiko.__version__)
        
        
        # Hide the default button
        button = l.itemAtPosition( l.rowCount() - 1, 1 ).widget()
        l.removeWidget(button)
        
        # add list widget to layout
        l.addWidget(packageList, l.rowCount(), 1, 1, l.columnCount(), QtCore.Qt.AlignHCenter)
        
        # add widget back in
        l.addWidget(button, l.rowCount(), 1, 1, 1, QtCore.Qt.AlignRight)
        
        self.setStandardButtons(QtGui.QMessageBox.Ok)
        self.setIcon(QtGui.QMessageBox.Information)

################################################################################

class ConfirmCloseDialog(QtGui.QDialog):
    """
    Confirm close dialog.
    
    """
    def __init__(self, parent=None):
        super(ConfirmCloseDialog, self).__init__(parent)
        
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        self.setModal(1)
        self.setWindowTitle("Exit application?")
        
        layout = QtGui.QVBoxLayout(self)
        
        # label
        label = QtGui.QLabel("<b>Are you sure you want to exit?</b>")
        row = QtGui.QHBoxLayout()
        row.addWidget(label)
        layout.addLayout(row)
        
        # clear settings
        self.clearSettingsCheck = QtGui.QCheckBox("Clear settings")
        row = QtGui.QHBoxLayout()
        row.setAlignment(QtCore.Qt.AlignRight)
        row.addWidget(self.clearSettingsCheck)
        layout.addLayout(row)
        
        # buttons
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Yes | QtGui.QDialogButtonBox.No)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        
        layout.addWidget(buttonBox)

################################################################################

class RotateViewPointDialog(QtGui.QDialog):
    """
    Rotate view point dialog
    
    """
    def __init__(self, rw, parent=None):
        super(RotateViewPointDialog, self).__init__(parent)
        
#         self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        self.setWindowTitle("Rotate view point")
        self.setWindowIcon(QtGui.QIcon(iconPath("oxygen/transform-rotate.png")))
        self.setModal(0)
        
        self.rw = rw
        self.parent = parent
        
        # Dialog layout
        layout = QtGui.QGridLayout(self)
        
        
        # Rotation group
        RotGroup = QtGui.QGroupBox("Custom Rotation")
        RotGroup.setAlignment(QtCore.Qt.AlignHCenter)
        RotGroupLayout = QtGui.QGridLayout(RotGroup)
           
        # rotate up button
        UpButton = QtGui.QPushButton(QtGui.QIcon(iconPath('other/rotup.png')),"Up")
        UpButton.setStatusTip("Rotate Up by selected angle")
        UpButton.setToolTip("Rotate Up by selected angle")
        UpButton.clicked.connect(self.RotateUp)
        RotGroupLayout.addWidget(UpButton, 0, 1 )
        
        # angle selection
        row = QtGui.QWidget(self)
        rowLayout = QtGui.QHBoxLayout(row)
        
        label = QtGui.QLabel("Angle:")
        
        self.angleSpin = QtGui.QDoubleSpinBox()
        self.angleSpin.setSingleStep(0.1)
        self.angleSpin.setMinimum(0.0)
        self.angleSpin.setMaximum(180.0)
        self.angleSpin.setValue(90)
        
        rowLayout.addWidget(label)
        rowLayout.addWidget(self.angleSpin)
        RotGroupLayout.addWidget(row, 1, 1)
        
        # rotate left button
        LeftButton = QtGui.QPushButton(QtGui.QIcon(iconPath('other/rotleft.png')), "Left")
        LeftButton.setStatusTip("Rotate Left by selected angle")
        LeftButton.setToolTip("Rotate Left by selected angle")
        LeftButton.clicked.connect(self.RotateLeft)
        RotGroupLayout.addWidget(LeftButton, 1, 0)
            
        # rotate right button
        RightButton = QtGui.QPushButton(QtGui.QIcon(iconPath('other/rotright.png')), 'Right')
        RightButton.setStatusTip("Rotate right by selected angle")
        RightButton.setToolTip("Rotate right by selected angle")
        RightButton.clicked.connect(self.RotateRight)
        RotGroupLayout.addWidget(RightButton, 1, 2)
        
        # rotate down button
        DownButton = QtGui.QPushButton(QtGui.QIcon(iconPath('other/rotdown.png')),"Down")
        DownButton.setStatusTip("Rotate Down by selected angle")
        DownButton.setToolTip("Rotate Down by selected angle")
        DownButton.clicked.connect(self.RotateDown)
        RotGroupLayout.addWidget(DownButton, 2, 1)
        
        # Reset button
        ResetButton = QtGui.QPushButton("Reset View")
        ResetButton.setStatusTip("Reset view to the visualiser default")
        ResetButton.setToolTip("Reset view to the visualiser default")
        ResetButton.clicked.connect(self.setCameraToCell)
        RotGroupLayout.addWidget(ResetButton, 4, 1)
        
        # Clockwise Rotation
        CWButton = QtGui.QPushButton(QtGui.QIcon(iconPath('oxygen/view-refresh.png')),"ClockWise")
        CWButton.setStatusTip("Rotate lattice clockwise by selected angle")
        CWButton.setToolTip("Rotate lattice clockwise by selected angle")
        CWButton.clicked.connect(self.RotateClockWise)
        RotGroupLayout.addWidget(CWButton, 3, 0)
        
        # AntiClockwise Rotation
        ACWButton = QtGui.QPushButton(QtGui.QIcon(iconPath('other/anticlockwise.png')),"Anti-ClockWise")
        ACWButton.setStatusTip("Rotate lattice anti-clockwise by selected angle")
        ACWButton.setToolTip("Rotate lattice anti-clockwise by selected angle")
        ACWButton.clicked.connect(self.RotateAntiClockWise)
        RotGroupLayout.addWidget(ACWButton, 3, 2)   
        
        
        # Add RotGroup to window
        layout.addWidget(RotGroup,1,0)
        
        
        # Custom rotate to crystal plane
        CrystalGroup = QtGui.QGroupBox("Rotate to top-down view of given crystal plane (EXPERIMENTAL)")
        CrystalGroup.setAlignment(QtCore.Qt.AlignHCenter)
        CrystalGroupLayout = QtGui.QGridLayout(CrystalGroup)
        
        label2 = QtGui.QLabel("Select crystal plane")
        CrystalGroupLayout.addWidget(label2, 0, 1)
        
        
        self.CrystalXSpin = QtGui.QSpinBox()
        self.CrystalXSpin.setSingleStep(1)
        self.CrystalXSpin.setMinimum(-10)
        self.CrystalXSpin.setMaximum(10)
        self.CrystalXSpin.setValue(1)
        CrystalGroupLayout.addWidget(self.CrystalXSpin, 1, 0)
        
        self.CrystalYSpin = QtGui.QSpinBox()
        self.CrystalYSpin.setSingleStep(1)
        self.CrystalYSpin.setMinimum(-10)
        self.CrystalYSpin.setMaximum(10)
        self.CrystalYSpin.setValue(1)
        CrystalGroupLayout.addWidget(self.CrystalYSpin, 1, 1)
        
        self.CrystalZSpin = QtGui.QSpinBox()
        self.CrystalZSpin.setSingleStep(1)
        self.CrystalZSpin.setMinimum(-10)
        self.CrystalZSpin.setMaximum(10)
        self.CrystalZSpin.setValue(1)
        CrystalGroupLayout.addWidget(self.CrystalZSpin, 1, 2)
        
        # Button to do the rotation
        CrystalRotButton = QtGui.QPushButton("Rotate")
        CrystalRotButton.setStatusTip("Rotate to a top-down view of the given plane above.")
        CrystalRotButton.setToolTip("Rotate to a top-down view of the given plane above.")
        CrystalRotButton.clicked.connect(self.RotateViewGeneral)
        CrystalGroupLayout.addWidget(CrystalRotButton, 2, 1)
        
        # Add shortcuts group to window
        layout.addWidget(CrystalGroup,2,0)
        
        
        
        # Top-down view shortcuts group
        ShortcutGroup = QtGui.QGroupBox("Rotate to a top-down view of some crystal planes")
        ShortcutGroup.setAlignment(QtCore.Qt.AlignHCenter)
        ShortcutGroupLayout = QtGui.QGridLayout(ShortcutGroup)
        
        # 001
        View001Button = QtGui.QPushButton("(001) Plane")
        View001Button.setStatusTip("Rotate to a top-down view of the (001) Plane")
        View001Button.setToolTip("Rotate to a top-down view of the (001) Plane")
        View001Button.clicked.connect(self.RotateView001)
        ShortcutGroupLayout.addWidget(View001Button, 1, 2)
        
        # 010
        View010Button = QtGui.QPushButton("(010) Plane")
        View010Button.setStatusTip("Rotate to a top-down view of the (010) Plane")
        View010Button.setToolTip("Rotate to a top-down view of the (010) Plane")
        View010Button.clicked.connect(self.RotateView010)
        ShortcutGroupLayout.addWidget(View010Button, 1, 1)
        
        # 100
        View100Button = QtGui.QPushButton("(100) Plane")
        View100Button.setStatusTip("Rotate to a top-down view of the (100) Plane")
        View100Button.setToolTip("Rotate to a top-down view of the (100) Plane")
        View100Button.clicked.connect(self.RotateView100)
        ShortcutGroupLayout.addWidget(View100Button, 1, 0)
        
        # commented out to de-clutter the window
        """
        # 110
        View110Button = QtGui.QPushButton("(110) Plane")
        View110Button.setStatusTip("Rotate to a top-down view of the (110) Plane")
        View110Button.setToolTip("Rotate to a top-down view of the (110) Plane")
        View110Button.clicked.connect(self.RotateView110)
        ShortcutGroupLayout.addWidget(View110Button, 2, 0)
        
        # 101
        View101Button = QtGui.QPushButton("(101) Plane")
        View101Button.setStatusTip("Rotate to a top-down view of the (101) Plane")
        View101Button.setToolTip("Rotate to a top-down view of the (101) Plane")
        View101Button.clicked.connect(self.RotateView101)
        ShortcutGroupLayout.addWidget(View101Button, 2, 1)
        
        # 011
        View011Button = QtGui.QPushButton("(011) Plane")
        View011Button.setStatusTip("Rotate to a top-down view of the (011) Plane")
        View011Button.setToolTip("Rotate to a top-down view of the (011) Plane")
        View011Button.clicked.connect(self.RotateView011)
        ShortcutGroupLayout.addWidget(View011Button, 2, 2)
        
        # 111
        View111Button = QtGui.QPushButton("(111) Plane")
        View111Button.setStatusTip("Rotate to a top-down view of the (111) Plane")
        View111Button.setToolTip("Rotate to a top-down view of the (111) Plane")
        View111Button.clicked.connect(self.RotateView111)
        ShortcutGroupLayout.addWidget(View111Button, 3, 1)
        
        # 102
        View102Button = QtGui.QPushButton("(102) Plane")
        View102Button.setStatusTip("Rotate to a top-down view of the (102) Plane")
        View102Button.setToolTip("Rotate to a top-down view of the (102) Plane")
        View102Button.clicked.connect(self.RotateView102)
        ShortcutGroupLayout.addWidget(View102Button, 4, 0)
        
        # 103
        View103Button = QtGui.QPushButton("(103) Plane")
        View103Button.setStatusTip("Rotate to a top-down view of the (103) Plane")
        View103Button.setToolTip("Rotate to a top-down view of the (103) Plane")
        View103Button.clicked.connect(self.RotateView103)
        ShortcutGroupLayout.addWidget(View103Button, 4, 1)
        
        # 104
        View104Button = QtGui.QPushButton("(104) Plane")
        View104Button.setStatusTip("Rotate to a top-down view of the (104) Plane")
        View104Button.setToolTip("Rotate to a top-down view of the (104) Plane")
        View104Button.clicked.connect(self.RotateView104)
        ShortcutGroupLayout.addWidget(View104Button, 4, 2)
        """
        
        # Add shortcuts group to window
        layout.addWidget(ShortcutGroup,3,0)
        
        
        # Close Button
        row = QtGui.QWidget(self)
        rowLayout = QtGui.QHBoxLayout(row)
        rowLayout.setAlignment(QtCore.Qt.AlignHCenter)
        
        CloseButton = QtGui.QPushButton("Close")
        CloseButton.clicked.connect(self.reject) 
        CloseButton.setDefault(True)
        rowLayout.addWidget(CloseButton)
        layout.addWidget(row,4,0)


    def RotateClockWise(self):
        """
        Rotate viewpoint clockwise about the vector coming out of the center of the screen.
        
        """
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        angle = -self.angleSpin.value()
        
        # apply rotation
        logger.debug("Appling clockwise rotation by %f degrees", angle)
        logger.debug("Calling: Roll %f", angle)
        renderer.camera.Roll(float(angle))
        renderer.reinit()
        
    def RotateAntiClockWise(self):
        """
        Rotate viewpoint anticlockwise about the vector coming out of the center of the screen.
        
        """
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        angle = self.angleSpin.value()
        
        # apply rotation
        logger.debug("Appling anticlockwise rotation by %f degrees", angle)
        logger.debug("Calling: Roll %f", angle)
        renderer.camera.Roll(float(angle))
        renderer.reinit()

    def RotateRight(self):
        """
        Rotate viewpoint Right by the given angle.
        
        """
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        angle = -self.angleSpin.value()
        
        # apply rotation
        logger.debug("Appling right rotation by %f degrees", angle)
        logger.debug("Calling: azimuth %f", angle)
        renderer.camera.Azimuth(float(angle)) 
        renderer.reinit()
        
    def RotateLeft(self):
        """
        Rotate viewpoint Left by the given angle.
        
        """
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        angle = self.angleSpin.value()
        
        # apply rotation
        logger.debug("Appling right rotation by %f degrees", angle)
        logger.debug("Calling: azimuth %f", angle)
        renderer.camera.Azimuth(float(angle))
        renderer.reinit()   
        
    def RotateUp(self):
        """
        Rotate viewpoint Up by the given angle.
        
        """
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        angle = -self.angleSpin.value()
        
        # apply rotation
        logger.debug("Appling right rotation by %f degrees", angle)
        logger.debug("Calling: elevation %f", angle)
        if( ((angle > 89) and (angle < 91)) or ((angle > -91) and (angle < -89))  ):
            # This is done in two steps so new viewup can be calculated correctly
            # otherwise ViewUp and DirectionOfProjection vectors become parallel
            renderer.camera.Elevation(float(angle/2.0))
            renderer.camera.OrthogonalizeViewUp()
            renderer.camera.Elevation(float(angle/2.0))
            renderer.camera.OrthogonalizeViewUp()
        else:
            renderer.camera.Elevation(float(angle))
            renderer.camera.OrthogonalizeViewUp() 
        
        renderer.reinit()
        
    def RotateDown(self):
        """
        Rotate viewpoint Down by the given angle.
        
        """
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        angle = self.angleSpin.value()
        
        # apply rotation
        logger.debug("Appling right rotation by %f degrees", angle)
        logger.debug("Calling: elevation %f", angle)
        if( ((angle > 89) and (angle < 91)) or ((angle > -91) and (angle < -89))  ):
            # This is done in two steps so new viewup can be calculated correctly
            # otherwise ViewUp and DirectionOfProjection vectors become parallel
            renderer.camera.Elevation(float(angle/2.0))
            renderer.camera.OrthogonalizeViewUp()
            renderer.camera.Elevation(float(angle/2.0))
            renderer.camera.OrthogonalizeViewUp()
        else:
            renderer.camera.Elevation(float(angle))
            renderer.camera.OrthogonalizeViewUp() 
        
        renderer.reinit()
        
    def setCameraToCell(self):
        """
        Reset the camera to point at the cell
        
        """
        renderer = self.rw.renderer
        renderer.setCameraToCell()  
        
    def RotateViewGeneral(self):  
        # crystal plane (also normal vector)
        x = self.CrystalXSpin.value()
        y = self.CrystalYSpin.value()
        z = self.CrystalZSpin.value()
        # return without doing anything if zero plane is given
        if( (x == 0) and (y == 0) and (z == 0) ):
            return
        
        mag_norm = math.sqrt(x*x + y*y +z*z)
        
        mag_proj = math.sqrt(x*x + y*y)
        
        # Angle between normal and projection to xy plane
        # xy projection plane (1/sqrt(2),1/sqrt(2),0)
        if(z == 0):
            ang_norm_xy = 0
        elif( (x == 0) and (y == 0) ):
            ang_norm_xy = 90.0
        if( (z < 0) ):
            ang_dp = x*x + y*y
            ang_norm_xy = 360 - math.degrees( math.acos(ang_dp/(mag_proj*mag_norm)) )
        else:
            ang_dp = x*x + y*y
            ang_norm_xy = math.degrees( math.acos(ang_dp/(mag_proj*mag_norm)) )
        
        # Angle between xy projection and x axis
        if( (x == 0) and (y == 0) ):
            ang_norm_xz = 0.0
        if( (y < 0) ):
            mag_proj = math.sqrt(x*x + y*y)
            ang_norm_xz = 360 - math.degrees( math.acos(x/mag_proj) )
        else:
            mag_proj = math.sqrt(x*x + y*y)
            ang_norm_xz = math.degrees( math.acos(x/mag_proj) )
        
        
        # reset view
        self.setCameraToCell()
        # get renderer
        renderer = self.rw.renderer
        # Rotate to view yz plane down the x axis
        renderer.camera.Azimuth(float(90.0))
        renderer.camera.Elevation(float(-45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.camera.Elevation(float(-45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.camera.Azimuth(float(90.0))
        
        # rotate to the crystal plane
        renderer.camera.Azimuth(float(ang_norm_xz))
        
        renderer.camera.Elevation(float(ang_norm_xy))
        renderer.camera.OrthogonalizeViewUp()
        
        renderer.reinit()  
        
    def RotateView001(self):  
        self.setCameraToCell()
        
        #RotateLeft90
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # apply rotation
        logger.debug("Appling right rotation by %f degrees", 90.0)
        logger.debug("Calling: azimuth %f", 90.0)
        renderer.camera.Azimuth(float(90.0))
        renderer.reinit()  
        
    def RotateView010(self):  
        self.setCameraToCell()
        
        #RotateDown90
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # This is done in two steps so new viewup can be calculated correctly
        # otherwise ViewUp and DirectionOfProjection vectors become parallel
        logger.debug("Calling: elevation %f", 90.0)
        renderer.camera.Elevation(float(45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.camera.Elevation(float(45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.reinit()
        
    def RotateView100(self):  
        self.setCameraToCell()
        
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # RotateDown90
        # This is done in two steps so new viewup can be calculated correctly
        # otherwise ViewUp and DirectionOfProjection vectors become parallel
        logger.debug("Calling: elevation %f", 90.0)
        renderer.camera.Elevation(float(45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.camera.Elevation(float(45.0))
        renderer.camera.OrthogonalizeViewUp()
        
        # RotateRight90
        logger.debug("Calling: azimuth %f", -90.0)
        renderer.camera.Azimuth(float(-90.0))
        
        # RotateDown90
        # This is done in two steps so new viewup can be calculated correctly
        # otherwise ViewUp and DirectionOfProjection vectors become parallel
        logger.debug("Calling: elevation %f", 90.0)
        renderer.camera.Elevation(float(45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.camera.Elevation(float(45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.reinit()
        
    def RotateView111(self):  
        self.setCameraToCell()
        
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # RotateLeft135
        logger.debug("Appling right rotation by %f degrees", 135.0)
        logger.debug("Calling: azimuth %f", 135.0)
        renderer.camera.Azimuth(float(135.0))
        
        # RotateDown
        # Rotation angle is angle between [1,1,1] and [1,1,0] = 35.26438968
        logger.debug("Calling: elevation %f", 35.26438968)
        renderer.camera.Elevation(float(35.26438968))
        renderer.camera.OrthogonalizeViewUp()
        renderer.reinit()  
        
    def RotateView110(self):  
        self.setCameraToCell()
        
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # RotateLeft90
        logger.debug("Appling right rotation by %f degrees", 90.0)
        logger.debug("Calling: azimuth %f", 90.0)
        renderer.camera.Azimuth(float(90.0))
        
        # RotateUp90
        # This is done in two steps so new viewup can be calculated correctly
        # otherwise ViewUp and DirectionOfProjection vectors become parallel
        logger.debug("Calling: elevation %f", -90.0)
        renderer.camera.Elevation(float(-45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.camera.Elevation(float(-45.0))
        renderer.camera.OrthogonalizeViewUp()
        
        # RotateLeft135
        logger.debug("Appling right rotation by %f degrees", 135.0)
        logger.debug("Calling: azimuth %f", 135.0)
        renderer.camera.Azimuth(float(135.0))
        renderer.reinit()  
        
    def RotateView101(self):  
        self.setCameraToCell()
        
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # RotateLeft135
        logger.debug("Appling right rotation by %f degrees", 135.0)
        logger.debug("Calling: azimuth %f", 135.0)
        renderer.camera.Azimuth(float(135.0))
        renderer.reinit()  
    
    def RotateView011(self):  
        self.setCameraToCell()
        
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # RotateDown90
        # This is done in two steps so new viewup can be calculated correctly
        # otherwise ViewUp and DirectionOfProjection vectors become parallel
        logger.debug("Calling: elevation %f", 90.0)
        renderer.camera.Elevation(float(45.0))
        renderer.camera.OrthogonalizeViewUp()
        renderer.camera.Elevation(float(45.0))
        renderer.camera.OrthogonalizeViewUp()
        
        # RotateLeft45
        logger.debug("Appling right rotation by %f degrees", 45.0)
        logger.debug("Calling: azimuth %f", 45.0)
        renderer.camera.Azimuth(float(45.0))
        renderer.reinit()  
    
    def RotateView102(self):  
        self.setCameraToCell()
        
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # tan^-1 1/2  + 90.0
        # 26.56505118 + 90.0
        # RotateLeft116.5650512
        logger.debug("Appling right rotation by %f degrees", 116.5650512)
        logger.debug("Calling: azimuth %f", 116.5650512)
        renderer.camera.Azimuth(float(116.5650512))
        renderer.reinit()  
        
    def RotateView103(self):  
        self.setCameraToCell()
        
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # tan^-1 1/3  + 90.0
        # 18.43494882 + 90.0
        # RotateLeft108.4349488
        logger.debug("Appling right rotation by %f degrees", 108.4349488)
        logger.debug("Calling: azimuth %f", 108.4349488)
        renderer.camera.Azimuth(float(108.4349488))
        renderer.reinit() 
        
    def RotateView104(self):  
        self.setCameraToCell()
        
        logger = logging.getLogger(__name__+".RotateViewPoint")
        renderer = self.rw.renderer
        
        # tan^-1 1/4  + 90.0
        # 14.03624347 + 90.0
        # RotateLeft104.0362435
        logger.debug("Appling right rotation by %f degrees", 104.0362435)
        logger.debug("Calling: azimuth %f", 104.0362435)
        renderer.camera.Azimuth(float(104.0362435))
        renderer.reinit()        
              
################################################################################

class ReplicateCellDialog(QtGui.QDialog):
    """
    Ask user which directions they want to replicate the cell in
    
    """
    def __init__(self, pbc, parent=None):
        super(ReplicateCellDialog, self).__init__(parent)
        
        self.setWindowTitle("Replicate cell options")
        
        # layout
        layout = QtGui.QFormLayout()
        self.setLayout(layout)
        
        self.setMinimumWidth(230)
        #self.setMinimumHeight(200)
        
        # x
        self.replicateInXSpin = QtGui.QSpinBox()
        self.replicateInXSpin.setMinimum(0)
        self.replicateInXSpin.setMaximum(10)
        self.replicateInXSpin.setValue(0)
        self.replicateInXSpin.setToolTip("Number of times to replicate the cell in the x direction")
        if not pbc[0]:
            self.replicateInXSpin.setEnabled(False)
        layout.addRow("Replicate in x", self.replicateInXSpin)
        
        # y
        self.replicateInYSpin = QtGui.QSpinBox()
        self.replicateInYSpin.setMinimum(0)
        self.replicateInYSpin.setMaximum(10)
        self.replicateInYSpin.setValue(0)
        self.replicateInYSpin.setToolTip("Number of times to replicate the cell in the y direction")
        if not pbc[1]:
            self.replicateInYSpin.setEnabled(False)
        layout.addRow("Replicate in y", self.replicateInYSpin)
        
        # z
        self.replicateInZSpin = QtGui.QSpinBox()
        self.replicateInZSpin.setMinimum(0)
        self.replicateInZSpin.setMaximum(10)
        self.replicateInZSpin.setValue(0)
        self.replicateInZSpin.setToolTip("Number of times to replicate the cell in the z direction")
        if not pbc[2]:
            self.replicateInYSpin.setEnabled(False)
        layout.addRow("Replicate in z", self.replicateInZSpin)
        
        # button box
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addRow(buttonBox)

################################################################################

class ShiftCellDialog(QtGui.QDialog):
    """
    Ask user which directions they want to replicate the cell in
    
    """
    def __init__(self, pbc, cellDims, parent=None):
        super(ShiftCellDialog, self).__init__(parent)
        
        self.setWindowTitle("Shift cell options")
        
        # layout
        layout = QtGui.QFormLayout()
        self.setLayout(layout)
        
        # x
        self.shiftXSpin = QtGui.QDoubleSpinBox()
        self.shiftXSpin.setMinimum(-cellDims[0])
        self.shiftXSpin.setMaximum(cellDims[0])
        self.shiftXSpin.setSingleStep(1)
        self.shiftXSpin.setValue(0)
        self.shiftXSpin.setToolTip("Distance to shift the cell in the x direction")
        if not pbc[0]:
            self.shiftXSpin.setEnabled(False)
        layout.addRow("Shift in x", self.shiftXSpin)
        
        # y
        self.shiftYSpin = QtGui.QDoubleSpinBox()
        self.shiftYSpin.setMinimum(-cellDims[1])
        self.shiftYSpin.setMaximum(cellDims[1])
        self.shiftYSpin.setSingleStep(1)
        self.shiftYSpin.setValue(0)
        self.shiftYSpin.setToolTip("Distance to shift the cell in the y direction")
        if not pbc[1]:
            self.shiftYSpin.setEnabled(False)
        layout.addRow("Shift in y", self.shiftYSpin)
        
        # z
        self.shiftZSpin = QtGui.QDoubleSpinBox()
        self.shiftZSpin.setMinimum(-cellDims[2])
        self.shiftZSpin.setMaximum(cellDims[2])
        self.shiftZSpin.setSingleStep(1)
        self.shiftZSpin.setValue(0)
        self.shiftZSpin.setToolTip("Distance to shift the cell in the z direction")
        if not pbc[2]:
            self.shiftZSpin.setEnabled(False)
        layout.addRow("Shift in z", self.shiftZSpin)
        
        # button box
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addRow(buttonBox)


################################################################################

class ShiftAtomDialog(QtGui.QDialog):
    """
    Ask user which atom should be shifted and the distance of the shift in each direction.
    
    """
    def __init__(self, inputID, pbc, cellDims, NumAtoms, parent=None):
        super(ShiftAtomDialog, self).__init__(parent)
        
        self.setWindowTitle("Shift atom options")
        
        # layout
        layout = QtGui.QFormLayout()
        self.setLayout(layout)
        
        self.setMinimumWidth(220)
        self.setMinimumHeight(200)
        
        # Atom ID
        # only allow numbers, commas and hyphens
        rx = QtCore.QRegExp("[0-9]+(?:[-,]?[0-9]+)*")
        validator = QtGui.QRegExpValidator(rx, self)
        
        self.lineEdit = QtGui.QLineEdit()
        self.lineEdit.setValidator(validator)
        if (inputID>=0):
            self.lineEdit.setText(str(inputID))
        self.lineEdit.setToolTip("Comma separated list of atom IDs or ranges of atom IDs (hyphenated) that are visible (eg. '22,30-33' will show atom IDs 22, 30, 31, 32 and 33)")
        #self.lineEdit.editingFinished.connect(self._settings.updateSetting("filterString", str(self.lineEdit.text())))
        layout.addRow("Atom IDs", self.lineEdit)
        
        
        
        
        # x
        self.shiftXSpin = QtGui.QDoubleSpinBox()
        self.shiftXSpin.setMinimum(-cellDims[0])
        self.shiftXSpin.setMaximum(cellDims[0])
        self.shiftXSpin.setSingleStep(1)
        self.shiftXSpin.setValue(0)
        self.shiftXSpin.setToolTip("Distance to shift the atom in the x direction")
        if not pbc[0]:
            self.shiftXSpin.setEnabled(False)
        layout.addRow("Shift in x", self.shiftXSpin)
        
        # y
        self.shiftYSpin = QtGui.QDoubleSpinBox()
        self.shiftYSpin.setMinimum(-cellDims[1])
        self.shiftYSpin.setMaximum(cellDims[1])
        self.shiftYSpin.setSingleStep(1)
        self.shiftYSpin.setValue(0)
        self.shiftYSpin.setToolTip("Distance to shift the atom in the y direction")
        if not pbc[1]:
            self.shiftYSpin.setEnabled(False)
        layout.addRow("Shift in y", self.shiftYSpin)
        
        # z
        self.shiftZSpin = QtGui.QDoubleSpinBox()
        self.shiftZSpin.setMinimum(-cellDims[2])
        self.shiftZSpin.setMaximum(cellDims[2])
        self.shiftZSpin.setSingleStep(1)
        self.shiftZSpin.setValue(0)
        self.shiftZSpin.setToolTip("Distance to shift the atom in the z direction")
        if not pbc[2]:
            self.shiftZSpin.setEnabled(False)
        layout.addRow("Shift in z", self.shiftZSpin)
        
        # button box
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addRow(buttonBox)




