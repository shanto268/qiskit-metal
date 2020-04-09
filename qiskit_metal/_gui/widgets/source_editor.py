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

"""Main edit source code window,
based on pyqode.python: https://github.com/pyQode/pyqode.python

@author: Zlatko Minev 2020
"""
import logging
from typing import TYPE_CHECKING

from PyQt5 import QtCore, QtGui, QtWidgets


try:
    from pyqode.python.backend import server
    from pyqode.core import api, modes, panels
    from pyqode.python import modes as pymodes, panels as pypanels, widgets
    from pyqode.python.folding import PythonFoldDetector
    from pyqode.python.backend.workers import defined_names
except ImportError as e:
    print('Error could not load pyqode.python; Please install.\n'
          '  >> pip install pyqode.python --upgrade \n\n'
          'See https://github.com/pyQode/pyqode.python \n')

if TYPE_CHECKING:
    from ..main_window import MetalGUI, QMainWindowExtension

import importlib

class MetalSourceEditor(widgets.PyCodeEditBase):
    """
    A source code editor based on pyQode.

    Editor features:
        - syntax highlighting
        - code completion (using jedi)
        - code folding
        - auto indentation
        - auto complete
        - comments mode (ctrl+/)
        - calltips mode
        - linters (pyflakes and pep8) modes + display panel
        - line number panel
        - builtin search and replace panel

    Create with
        gui.component_window.edit_source()

    Access with
        self = gui.component_window.src_widgets[-1].ui.src_editor
    """

    def __init__(self, parent, **kwargs):
        # Foe help, see
        # https://github.com/pyQode/pyqode.python/blob/master/examples/custom.py

        super().__init__(parent, **kwargs)

        self.gui = None  # type: MetalGUI
        self.component_class_name = None  # type: str - 'TransmonPocket'
        self.component_module_name = None  # type: str - 'qiskit_metal.components.qubits.transmon_pocket'
        self.component_module_path = None  # type: str - '/Users/zlatko.minev/qiskit_metal/qiskit_metal/components/qubits/transmon_pocket.py'

        # starts the default pyqode.python server (which enable the jedi code
        # completion worker).
        self.backend.start(server.__file__)

        # some other modes/panels require the analyser mode, the best is to
        # install it first
        self.modes.append(modes.OutlineMode(defined_names))

        # --- core panels
        self.panels.append(panels.FoldingPanel())
        self.panels.append(panels.LineNumberPanel())
        self.panels.append(panels.CheckerPanel())
        self.panels.append(panels.SearchAndReplacePanel(),
                           panels.SearchAndReplacePanel.Position.BOTTOM)
        self.panels.append(panels.EncodingPanel(), api.Panel.Position.TOP)
        # add a context menu separator between editor's
        # builtin action and the python specific actions
        self.add_separator()

        # --- python specific panels
        self.panels.append(pypanels.QuickDocPanel(), api.Panel.Position.BOTTOM)

        # --- core modes
        self.modes.append(modes.CaretLineHighlighterMode())
        self.modes.append(modes.CodeCompletionMode())
        self.modes.append(modes.ExtendedSelectionMode())
        self.modes.append(modes.FileWatcherMode())
        self.modes.append(modes.OccurrencesHighlighterMode())
        # self.modes.append(modes.RightMarginMode())
        self.modes.append(modes.SmartBackSpaceMode())
        self.modes.append(modes.SymbolMatcherMode())
        self.modes.append(modes.ZoomMode())

        # ---  python specific modes
        self.modes.append(pymodes.CommentsMode())
        self.modes.append(pymodes.CalltipsMode())
        self.modes.append(pymodes.PyFlakesChecker())
        # self.modes.append(pymodes.PEP8CheckerMode())
        self.modes.append(pymodes.PyAutoCompleteMode())
        self.modes.append(pymodes.PyAutoIndentMode())
        self.modes.append(pymodes.PyIndenterMode())
        self.modes.append(pymodes.PythonSH(self.document()))
        self.syntax_highlighter.fold_detector = PythonFoldDetector()

        # --- handle modifed text in other application
        # self.textChanged.connect(self.check_modified) # user function

    @property
    def logger(self) -> logging.Logger:
        return self.gui.logger

    def reload_file(self):
        self.file.reload()
        # self.update()
        self.logger.info('Source file reloaded.')

    def save_file(self):
        self.file.save()
        self.logger.info('Source file saved.')

    def open_file(self, filename: str):
        self.file.open(filename)

    def reload_module(self):
        if self.component_module_path:
            module = importlib.import_module(self.component_module_name)
            module = importlib.reload(module)
            new_class = getattr(module, self.component_class_name)

            # components that need
            for instance in filter(lambda k: k.__class__.__name__==self.component_class_name,
                        self.gui.design.components.values()):
                instance.__class__ = new_class

            ### Alternative, but reload will say not in sys.path
            # self = gui.component_window.src_widgets[-1].ui.src_editor
            # spec = importlib.util.spec_from_file_location(self.component_module_name, self.component_module_path) # type: ModuleSpec
            # module = importlib.util.module_from_spec(spec) # type: module e.g.,
            # spec.loader.exec_module(module)
            # importlib.reload(module)

    def rebuild_components(self):
        self.save_file()
        self.reload_module()
        # TODO: only rebuild those that have this type
        # for right now i will do all of tehm just for ease
        self.gui.rebuild()
        self.logger.info('Source file executed rebuild.')

    @property
    def edit_widget(self):
        return self.parent()

    def set_component(self, class_name: str, module_name: str,
            module_path : str):
        self.component_class_name = class_name
        self.component_module_name = module_name
        self.component_module_path = module_path

        self.open_file(module_path)

        edit_widget = self.edit_widget
        edit_widget.ui.lineSrcPath.setText(module_path)
        edit_widget.setWindowTitle(f'{class_name}: Edit Source')