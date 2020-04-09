# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Main module that handles a component  inside the main window.
@author: Zlatko Minev
@date: 2020
"""

import ast
import inspect
from inspect import getfile, signature
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PyQt5 import Qt, QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtWidgets import (QApplication, QFileDialog, QLabel, QMainWindow,
                             QMessageBox, QTabWidget)

from .. import logger
from .component_widget_ui import Ui_ComponentWidget
from .widgets.source_editor_widget import create_source_edit_widget
from ._handle_qt_messages import catch_exception_slot_pyqt

if TYPE_CHECKING:
    from .main_window import MetalGUI, QMainWindowExtension

try:  # For source doc
    import pygments
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
except ImportError as e:
    logger.error(
        f'Error: Could not load python package \'pygments\'; Error: {e}')
    highlight = None
    HtmlFormatter = None
    get_lexer_by_name = None


def create_QTextDocument(doc: QtWidgets.QTextEdit) -> QtGui.QTextDocument:
    """For source doc
    """
    document = QtGui.QTextDocument()

    # Style doc
    doc.setDocument(document)
    doc.setStyleSheet("background-color: rgb(250, 250, 250);")

    # Style documents monoscaped font
    font = document.defaultFont()
    font.setFamily("monospace")
    document.setDefaultFont(font)

    return document


class ComponentWidget(QTabWidget):
    """
    This is just a handler (container) for the UI; it a child object of the main gui.

    PyQt5 Signal / Slots Extensions:
        The UI can call up to this class to execeute button clicks for instance
        Extensiosn in qt designer on signals/slots are linked to this class
    """

    def __init__(self, gui: 'MetalGUI', parent: QtWidgets.QWidget):
        # Q Main WIndow
        super().__init__(parent)

        # Parent GUI related
        self.gui = gui
        self.logger = gui.logger
        self.statusbar_label = gui.statusbar_label

        # UI
        self.ui = Ui_ComponentWidget()
        self.ui.setupUi(self)

        self.component_name = None  # type: str

        # Parametr model
        self.model = ComponentTableModel(gui, self)
        self.ui.tableView.setModel(self.model)

        # Source Code
        self.src_doc = create_QTextDocument(
            self.ui.textSource)  # QtGui.QTextDocument
        self._html_css_lex = None  # type: pygments.formatters.html.HtmlFormatter
        self.src_widgets = []  # type: List[QtWidgets.QWidget]

    @property
    def design(self):
        return self.gui.design

    @property
    def component(self):
        if self.design:
            return self.design.components.get(self.component_name, None)

    def set_component(self, name: str):
        self.component_name = name

        component = self.component
        self.ui.labelComponentName.setText(str(component.name))

        self._set_source()
        self._set_help()

        self.force_refresh()

    def force_refresh(self):
        self.model.refresh()

    def _set_help(self):
        """Called when we need to set a new help"""
        pass  # TODO:

    def _set_source(self):
        """Called when we need to set a new help"""
        filepath = getfile(self.component.__class__)
        self.ui.lineSourcePath.setText(filepath)

        document = self.src_doc

        text = Path(filepath).read_text()

        if not (highlight is None):
            lexer = get_lexer_by_name("python", stripall=True)
            formatter = HtmlFormatter(linenos='inline')
            self._html_css_lex = formatter.get_style_defs('.highlight')

            document.setDefaultStyleSheet(self._html_css_lex)
            text_html = highlight(text, lexer, formatter)
            document.setHtml(text_html)

        else:
            document.setPlainText(text)
    # @catch_exception_slot_pyqt()

    def edit_source(self, parent=None):
        """Calls the edit source window
        gui.component_window.edit_source()
        """
        if self.component is not None:
            class_name = self.component.__class__.__name__
            module_name = self.component.__class__.__module__
            module_path = inspect.getfile(self.component.__class__)
            self.src_widgets += [
                create_source_edit_widget(
                    self.gui, class_name, module_name, module_path, parent=parent)
            ]
            self.logger.info('Edit sources window created. '
                             'Please find on your screen.')
        else:
            QtWidgets.QMessageBox.warning(self,
                                          "Missing Selected Component",
                                          "Please first select a component to edit, by clicking "
                                          "one in the desing components menu.")


class ComponentTableModel(QAbstractTableModel):

    """
    Table model for the options of a given component.

    MVC class
    See https://doc.qt.io/qt-5/qabstracttablemodel.html
    """
    # __timer_interval = 500  # ms

    def __init__(self, gui: 'MetalGUI', parent: ComponentWidget = None):
        super().__init__(parent=parent)
        self.logger = gui.logger
        self.gui = gui
        self._row_count = -1

        # self._create_timer()
        self.columns = ['Name', 'Value']

    @property
    def design(self):
        return self.gui.design

    @property
    def component(self):
        return self.parent().component

    def refresh(self):
        """Force refresh.   Completly rebuild the model."""
        self.modelReset.emit()

    def rowCount(self, parent=None):  # =QtCore.QModelIndex()):
        if self.component is None:
            return 0
        return len(self.component.options)  # TODO:

    def columnCount(self, parent=None):  # =QtCore.QModelIndex()):
        return 2

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """ Set the headers to be displayed. """

        if (role != QtCore.Qt.DisplayRole) or (self.component is None):
            return None

        if orientation == QtCore.Qt.Horizontal:
            if section < self.columnCount():
                return self.columns[section]

    def flags(self, index: QtCore.QModelIndex):
        """ Set the item flags at the given index. Seems like we're
            implementing this function just to see how it's done, as we
            manually adjust each tableView to have NoEditTriggers.
        """
        # https://doc.qt.io/qt-5/qt.html#ItemFlag-enum

        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        # Returns the item flags for the given index.
        # The base class implementation returns a combination of flags that enables
        # the item (ItemIsEnabled) and allows it to be selected (ItemIsSelectable).
        flags = QAbstractTableModel.flags(self, index)
        if index.column() == 1:
            flags |= QtCore.Qt.ItemIsEditable

        return QtCore.Qt.ItemFlags(flags)

    # https://doc.qt.io/qt-5/qt.html#ItemDataRole-enum
    def data(self, index: Qt.QModelIndex, role=QtCore.Qt.DisplayRole):
        """ Depending on the index and role given, return data. If not
            returning data, return None (PySide equivalent of QT's
            "invalid QVariant").
        """

        if not index.isValid():
            return
        # if not 0 <= index.row() < self.rowCount():
        #    return None

        if self.component is None:
            return

        # The key data to be rendered in the form of text. (QString)
        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            column = index.column()
            data = self.component.options
            # There's probably a better way to access the data here
            if column == 0:
                data = list(data.keys())
            elif column == 1:
                data = list(data.values())
            return str(data[row])

        # The data in a form suitable for editing in an editor.  (QString)
        elif role == QtCore.Qt.EditRole:
            return self.data(index, QtCore.Qt.DisplayRole)

        # The font used for items rendered with the default delegate. (QFont)
        elif role == QtCore.Qt.FontRole:
            if index.column() == 0:
                font = QtGui.QFont()
                font.setBold(True)
                return font

    def setData(self, index: QtCore.QModelIndex,
                value: Qt.QVariant,
                role=QtCore.Qt.EditRole):
        """Sets the role data for the item at index to value.
        Returns true if successful; otherwise returns false.
        The dataChanged() signal should be emitted if the data was successfully set.

        Arguments:
            index {QtCore.QModelIndex} -- [description]
            value {str} -- [description]

        Keyword Arguments:
            role {[type]} -- [description] (default: {Qt.EditRole})

        Returns:
            [type] -- [description]
        """

        # TODO: handle nested dicitonaries
        # See v0.1: get_nested_dict_item, pop_nested_dict_item
        # TODO: ability to add dictionary such as to add connectors
        if not index.isValid():
            return ""

        elif role == QtCore.Qt.EditRole:
            if index.column() == 1:
                self._value = value  # QString
                value = str(value)

                data = self.component.options  # type: dict
                key, old_val = list(data.items())[index.row()]

                # When we do nothing
                if isinstance(old_val, dict):
                    self.logger.error('You selected a dicitonary this'
                                      'cannot be edited directly edit its items.')
                    return False

                if old_val == value:
                    return False

                # When we do something to change the value

                # try:
                # TODO: should w etry and if eror then reset the value
                if 1:
                    self.logger.info(
                        f'Componention options: Old value={old_val}; New value={value};')
                    if isinstance(old_val, str):
                        data[key] = str(value)
                    else:
                        processed_value, used_ast = parse_param_from_str(value)
                        self.logger.info(f'  Used paring:  Old value type={type(old_val)}; '
                                         f'New value type={type(processed_value)};  New value={processed_value};'
                                         f'; Used ast={used_ast}')
                        data[key] = processed_value

                    self.component.rebuild()
                    self.gui.refresh()

                # except and finally restore the value
                return True

        # elif role == Qt.CheckStateRole:

        return False


def parse_param_from_str(text):
    """Attempt to parse a value from a string using ast"""
    text = str(text).strip()
    value = text
    used_ast = False
    try:  # crude way to handle list and values
        value = ast.literal_eval(text)
        used_ast = True
    except Exception as exception:
        pass
        # print(exception)
    return value, used_ast