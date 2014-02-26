
"""
Data input is handled by the systems dialog. 
From here you can load or generate a lattice; view loaded lattices; set input/ref system, etc.
Once loaded systems will be added to the "Loaded systems" list.  
Systems can be removed from the list by selecting them (multiple selection is possible) and clicking the minus sign. 
Note that systems that are currently selected on an analysis pipeline, as either a ref or input, cannot be removed.

"""
import os
import sys
import logging

from PySide import QtGui, QtCore

from ..visutils.utilities import iconPath
from .genericForm import GenericForm
from . import latticeReaderForms
from . import latticeGeneratorForms

try:
    from .. import resources
except ImportError:
    print "ERROR: could not import resources: ensure setup.py ran correctly"
    sys.exit(36)


################################################################################

class GenerateInputForm(GenericForm):
    """
    Form for generating a new system
    
    """
    def __init__(self, parent, mainWindow, mainToolbar):
        super(GenerateInputForm, self).__init__(parent, None, "Generate new system")
        
        self.parent = parent
        self.mainWindow = mainWindow
        self.mainToolbar = mainToolbar
        
        # system type combo
        self.inputTypeCombo = QtGui.QComboBox()
        self.inputTypeCombo.addItem("FCC")
        self.inputTypeCombo.addItem("Pu-Ga (L12 method)")
#         self.inputTypeCombo.addItem("Rock salt (eg. MgO)")
#         self.inputTypeCombo.addItem("Fluorite")
#         self.inputTypeCombo.addItem("Pyrochlore")
#         self.inputTypeCombo.addItem("6H")
        self.inputTypeCombo.currentIndexChanged.connect(self.setWidgetStack)
        
        row = self.newRow()
        row.addWidget(self.inputTypeCombo)
        
        self.show()
        
        # stacked widget
        self.stackedWidget = QtGui.QStackedWidget()
        
        row = self.newRow()
        row.addWidget(self.stackedWidget)
        
        # FCC generator
        self.fcc_generator = latticeGeneratorForms.FCCLatticeGeneratorForm(self, self.mainWindow)
        self.stackedWidget.addWidget(self.fcc_generator)
        
        # Pu3Ga generator
        self.pu3ga_generator = latticeGeneratorForms.Pu3GaLatticeGeneratorForm(self, self.mainWindow)
        self.stackedWidget.addWidget(self.pu3ga_generator)
        
        # help icon
        row = self.newRow()
        row.RowLayout.addStretch(1)
        
        helpButton = QtGui.QPushButton(QtGui.QIcon(iconPath("Help-icon.png")), "")
        helpButton.setFixedWidth(20)
        helpButton.setFixedHeight(20)
        helpButton.setToolTip("Show help page")
        helpButton.clicked.connect(self.loadHelpPage)
        row.addWidget(helpButton)
        
        self.show()
    
    def loadHelpPage(self):
        """
        Load the help page for this form
        
        """
        self.mainWindow.helpWindow.loadPage("usage/input/lattice_generation.html")
        self.mainWindow.showHelp()
    
    def file_generated(self, lattice, filename):
        """
        File generated
        
        """
        self.parent.file_generated(lattice, filename)
    
    def setWidgetStack(self, index):
        """
        Set stack
        
        """
        self.stackedWidget.setCurrentIndex(index)

################################################################################

class LoadSystemForm(GenericForm):
    """
    Form for reading new lattice.
    
    """
    def __init__(self, parent, mainWindow, mainToolbar):
        super(LoadSystemForm, self).__init__(parent, None, "Load new system")
        
        self.parent = parent
        self.mainWindow = mainWindow
        self.mainToolbar = mainToolbar
        
        # ordered list of keys
        self.readerFormsKeys = [
            "LBOMD DAT",
            "LBOMD REF",
            "LBOMD XYZ",
            "AUTO DETECT"
        ]
        
        # reader forms
        self.readerForms = {
            "LBOMD DAT": latticeReaderForms.LbomdDatReaderForm(self, self.mainToolbar, self.mainWindow, "LBOMD DAT"),
            "LBOMD REF": latticeReaderForms.LbomdRefReaderForm(self, self.mainToolbar, self.mainWindow, "LBOMD REF"),
            "LBOMD XYZ": latticeReaderForms.LbomdXYZReaderForm(self, self.mainToolbar, self.mainWindow, "LBOMD XYZ"),
            "AUTO DETECT": latticeReaderForms.AutoDetectReaderForm(self, self.mainToolbar, self.mainWindow, "AUTO DETECT"),
        }
        
        # file type combo
        self.inputTypeCombo = QtGui.QComboBox()
        self.inputTypeCombo.addItems(self.readerFormsKeys)
        self.inputTypeCombo.currentIndexChanged.connect(self.setWidgetStack)
        
        row = self.newRow()
        row.addWidget(self.inputTypeCombo)
        
        # stacked widget
        self.stackedWidget = QtGui.QStackedWidget()
        
        # add reader forms
        for key in self.readerFormsKeys:
            self.stackedWidget.addWidget(self.readerForms[key])
        
        row = self.newRow()
        row.addWidget(self.stackedWidget)
        
        # select auto by default
        self.inputTypeCombo.setCurrentIndex(self.readerFormsKeys.index("AUTO DETECT"))
        
        # help icon
        row = self.newRow()
        row.RowLayout.addStretch(1)
        
        helpButton = QtGui.QPushButton(QtGui.QIcon(iconPath("Help-icon.png")), "")
        helpButton.setFixedWidth(20)
        helpButton.setFixedHeight(20)
        helpButton.setToolTip("Show help page")
        helpButton.clicked.connect(self.loadHelpPage)
        row.addWidget(helpButton)
        
        self.show()
    
    def loadHelpPage(self):
        """
        Load the help page for this form
        
        """
        self.mainWindow.helpWindow.loadPage("usage/input/file_input.html")
        self.mainWindow.showHelp()
    
    def setWidgetStack(self, index):
        """
        Change load ref stack.
        
        """
        self.stackedWidget.setCurrentIndex(index)
    
    def fileLoaded(self, fileType, state, filename, extension, readerStackIndex):
        """
        Called when a file is loaded
        
        """
        self.parent.file_loaded(state, filename, extension, readerStackIndex)

################################################################################

class SystemsListWidgetItem(QtGui.QListWidgetItem):
    """
    Item that goes in the systems list
    
    """
    def __init__(self, lattice, filename, displayName, stackIndex, abspath):
        super(SystemsListWidgetItem, self).__init__()
        
        self.lattice = lattice
        self.filename = filename
        self.displayName = displayName
        self.stackIndex = stackIndex
        self.abspath = stackIndex
        
        self.setText("%s (%d atoms)" % (displayName, lattice.NAtoms))
        self.setToolTip(abspath)
    
    def changeDisplayName(self, displayName):
        """
        Change the display name
        
        """
        self.displayName = displayName
        
        self.setText("%s (%d atoms)" % (displayName, self.lattice.NAtoms))
    

################################################################################

class SystemsDialog(QtGui.QDialog):
    """
    Systems dialog
    
    """
    def __init__(self, parent, mainWindow):
        super(SystemsDialog, self).__init__(parent)
        
        self.setWindowTitle("Systems dialog")
        self.setModal(False)
        
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        self.mainToolbar = mainWindow
        self.mainWindow = mainWindow
        
        self.logger = logging.getLogger(__name__)
        
        self.resize(80, 120)
        
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        
        # dict for storing loaded systems
#         self.lattice_list = []
#         self.filenames_list = []
#         self.extensions_list = []
#         self.stackIndex_list = []
#         self.abspath_list = []
#         self.displayNames_list = []
        
        # dialog layout
        dialog_layout = QtGui.QVBoxLayout(self)
        
        # box for list of loaded systems
        list_holder = GenericForm(self, None, "Loaded systems")
        list_holder.show()
        dialog_layout.addWidget(list_holder)
        
        # add list widget
        self.systems_list_widget = QtGui.QListWidget(self)
#         self.systems_list_widget.setFixedHeight(60)
        self.systems_list_widget.setSelectionMode(self.systems_list_widget.ExtendedSelection)
        self.systems_list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.systems_list_widget.customContextMenuRequested.connect(self.showListWidgetContextMenu)
        
        row = list_holder.newRow()
        row.addWidget(self.systems_list_widget)
        
        # remove system button
        remove_system = QtGui.QPushButton(QtGui.QIcon(iconPath("list-remove.svg")), "")
        remove_system.setAutoDefault(False)
        remove_system.setToolTip("Remove system")
        remove_system.clicked.connect(self.remove_system)
        
        row = list_holder.newRow()
        row.addWidget(remove_system)
        
        # box for new system stuff
        new_holder = GenericForm(self, None, "New system")
        new_holder.show()
        dialog_layout.addWidget(new_holder)
        
        # load or generate combo
        self.new_type_combo = QtGui.QComboBox()
        self.new_type_combo.addItem("Load system")
        self.new_type_combo.addItem("Generate system")
        self.new_type_combo.currentIndexChanged.connect(self.set_new_system_stack)
        
        row = new_holder.newRow()
        row.addWidget(self.new_type_combo)
        
        # stacked widget
        self.new_system_stack = QtGui.QStackedWidget()
        
        row = new_holder.newRow()
        row.addWidget(self.new_system_stack)
        
        # load input form
        self.load_system_form = LoadSystemForm(self, self.mainWindow, self.mainToolbar)
        self.new_system_stack.addWidget(self.load_system_form)
        
        # generate input form
        self.generate_system_form = GenerateInputForm(self, self.mainWindow, self.mainToolbar)
        self.new_system_stack.addWidget(self.generate_system_form)
        
        # help icon
        helpButton = QtGui.QPushButton(QtGui.QIcon(iconPath("Help-icon.png")), "")
        helpButton.setFixedWidth(20)
        helpButton.setFixedHeight(20)
        helpButton.setToolTip("Show help page")
        helpButton.clicked.connect(self.load_help_page)
        
        # hide button
        hideButton = QtGui.QPushButton("&Hide")
        hideButton.clicked.connect(self.close)
        row = QtGui.QHBoxLayout()
        row.addStretch(1)
        row.addWidget(hideButton)
        row.addStretch(1)
        row.addWidget(helpButton)
        dialog_layout.addLayout(row)
    
    def showListWidgetContextMenu(self, point):
        """
        Show context menu for listWidgetItem
        
        """
        logger = logging.getLogger(__name__)
        logger.debug("Show list widget context menu")
        
        globalPoint = self.systems_list_widget.mapToGlobal(point)
        print "POINT", point, globalPoint
        
        t = self.systems_list_widget.indexAt(point)
        print "INDEX", t
        print "ROW", t.row()
        print "ITEM", self.systems_list_widget.item(t.row())
    
    def load_help_page(self):
        """
        Load the help page for this form
        
        """
        self.mainWindow.helpWindow.loadPage("usage/input/index.html")
        self.mainWindow.showHelp()
    
    def file_generated(self, lattice, filename):
        """
        File generated
        
        """
        self.add_lattice(lattice, filename, "dat")
    
    def file_loaded(self, lattice, filename, extension, readerStackIndex):
        """
        Called after a file had been loaded (or generated too?)
        
        """
        self.add_lattice(lattice, filename, extension, idb=readerStackIndex, ida=0)
    
    def add_lattice(self, lattice, filename, extension, ida=None, idb=None):
        """
        Add lattice
        
        """
        index = len(self.lattice_list)
        
        abspath = os.path.abspath(filename)
        if abspath in self.abspath_list:
            self.logger.info("This file has already been loaded (%s): not adding it again", filename)
            
            index = self.abspath_list.index(abspath)
            
            # select this one
            for row in self.systems_list_widget.count():
                self.systems_list_widget.item(row).setSelected(False)
            self.systems_list_widget.item(index).setSelected(True)
            
            return
        
#         self.lattice_list.append(lattice)
#         self.filenames_list.append(filename)
#         self.displayNames_list.append(filename)
#         self.extensions_list.append(extension)
#         self.abspath_list.append(abspath)
        
        # stack index
        if ida is None:
            ida = self.new_system_stack.currentIndex()
            page = self.new_system_stack.currentWidget()
        
        if idb is None:
            idb = page.stackedWidget.currentIndex()
        
        stackIndex = (ida, idb)
#         self.stackIndex_list.append((ida, idb))
        
        self.logger.debug("Adding new lattice to systemsList: %s; %s; %d,%d", filename, extension, ida, idb)
        
        list_item = SystemsListWidgetItem(lattice, filename, filename, stackIndex, abspath)
        
#         list_item = QtGui.QListWidgetItem()
#         list_item.setText("%s (%d atoms)" % (filename, lattice.NAtoms))
#         list_item.setToolTip(abspath)
        
        self.systems_list_widget.addItem(list_item)
        
        # select last one added only
        for row in xrange(index):
            self.systems_list_widget.item(row).setSelected(False)
        self.systems_list_widget.item(index).setSelected(True)
        
        # also add lattice to pipeline forms
        self.mainWindow.mainToolbar.addStateOptionToPipelines(filename)
        
        return index
    
    def set_new_system_stack(self, index):
        """
        Set new system stack
        
        """
        self.new_system_stack.setCurrentIndex(index)
    
    def remove_system(self):
        """
        Remove system(s) from list
        
        """
        if not self.systems_list_widget.count():
            return
        
        items = self.systems_list_widget.selectedItems()
        
        # loops over selected items
        for item in items:
            # get the index
            modelIndex = self.systems_list_widget.indexFromItem(item)
            index = modelIndex.row()
            
            if index < 0:
                continue
            
            # do not allow removal of system that is tagged with ref or input
            # first find out which ones are refs and inputs
            currentStateIndexes = self.mainWindow.mainToolbar.getSelectedStatesFromPipelines()
            
            if index in currentStateIndexes:
                self.mainWindow.displayWarning("Cannot remove state that is currently selected")
                continue
            
            # remove state
#             self.lattice_list.pop(index)
#             self.filenames_list.pop(index)
#             self.extensions_list.pop(index)
#             self.stackIndex_list.pop(index)
#             self.abspath_list.pop(index)
#             self.displayNames_list.pop(index)
            
            itemWidget = self.systems_list_widget.takeItem(index)
            del itemWidget
            
            self.mainWindow.mainToolbar.removeStateFromPipelines(index)
            
        # select last one in list
        for row in xrange(len(self.lattice_list) - 1):
            self.systems_list_widget.item(row).setSelected(False)
        self.systems_list_widget.item(len(self.lattice_list) - 1).setSelected(True)

