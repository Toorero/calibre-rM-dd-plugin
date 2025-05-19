# SPDX-License-Identifier: EUPL-1.2

from calibre.utils.config import JSONConfig
from PyQt5.Qt import QWidget, QLabel, QLineEdit, QGridLayout

prefs = JSONConfig("plugins/rmapi_device_plugin")
prefs.defaults["rmapi"] = "rmapi"
prefs.defaults["export_path"] = "calibre_export"


class ConfigWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QGridLayout()
        self.layout.setSpacing(10)

        # rMAPI path
        self.rmapi_label = QLabel("rMAPI Path:")
        self.layout.addWidget(self.rmapi_label, 1, 0)
        self.rmapi_label_edit = QLineEdit(self)
        self.rmapi_label_edit.setText(prefs["rmapi"])
        self.layout.addWidget(self.rmapi_label_edit, 1, 1)

        # Export path
        self.export_path_label = QLabel("rMAPI Path:")
        self.layout.addWidget(self.export_path_label, 2, 0)
        self.export_path_label_edit = QLineEdit(self)
        self.export_path_label_edit.setText(prefs["export_path"])
        self.layout.addWidget(self.export_path_label_edit, 2, 1)

        self.setLayout(self.layout)
        self.setGeometry(150, 150, 150, 150)
        self.setWindowTitle("rMAPI Device Driver Config")

    def save_settings(self):
        prefs["rmapi"] = self.rmapi_label_edit.text()
        prefs["export_path"] = self.export_path_label_edit.text()
