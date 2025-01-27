# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PhotosequenceDialog
                                 A QGIS plugin
 générateur de photoséquence
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2025-01-08
        git sha              : $Format:%H$
        copyright            : (C) 2025 by Jules Rosier
        email                : jules.rosier@ensg.eu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from PyQt5.QtGui import QIntValidator
from .photosequence_gen_dialog_UI import Ui_Photosequence_gen


class PhotosequenceDialog(QtWidgets.QDialog, Ui_Photosequence_gen):
    def __init__(self, parent=None):
        """Constructor."""
        super(PhotosequenceDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        epsg_validator = QIntValidator(1024, 32767, self)
        self.le_epsg.setValidator(epsg_validator)
