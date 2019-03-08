import sys

from PySide2 import QtCore, QtWidgets, QtGui

try:
    import hou
    import tbautils.houdini
    reload(tbautils.houdini) # REMOVE THIS FOR PRODUCTION
    APP = 'houdini'
except:
    APP = 'standalone'

import re

sys.dont_write_bytecode = True  # Avoid writing .pyc files

class TBA_publish_hda_UI(QtWidgets.QDialog):

    dlg_instance = None

    label_edited = False

    @classmethod
    def show_dialog(cls):
        if not cls.dlg_instance:
            cls.dlg_instance = TBA_publish_hda_UI(houdini_main_window())

        if cls.dlg_instance.isHidden():
            cls.dlg_instance.show()
        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()


    def __init__(self, parent=None):
        super(TBA_publish_hda_UI, self).__init__(parent)

        #self.setStyleSheet(hou.qt.styleSheet())

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        self.location_label = QtWidgets.QLabel('Location:')

        self.radio_site = QtWidgets.QRadioButton('Site')
        self.radio_job = QtWidgets.QRadioButton('Job')
        self.radio_shot = QtWidgets.QRadioButton('Shot')
        self.radio_shot.setChecked(True)

        self.radio_group_location = QtWidgets.QButtonGroup()
        self.radio_group_location.addButton(self.radio_site)
        self.radio_group_location.addButton(self.radio_job)
        self.radio_group_location.addButton(self.radio_shot)

        self.version_label = QtWidgets.QLabel('Version Update:')

        self.radio_major= QtWidgets.QRadioButton('Major')
        self.radio_major.setChecked(True)
        self.radio_minor = QtWidgets.QRadioButton('Minor')

        self.radio_group_version = QtWidgets.QButtonGroup()
        self.radio_group_version.addButton(self.radio_major)
        self.radio_group_version.addButton(self.radio_minor)

        self.publish_btn = QtWidgets.QPushButton('Publish')

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        main_layout.addWidget(self.location_label)

        main_layout.addWidget(self.radio_site)
        main_layout.addWidget(self.radio_job)
        main_layout.addWidget(self.radio_shot)

        main_layout.addWidget(self.version_label)

        main_layout.addWidget(self.radio_major)
        main_layout.addWidget(self.radio_minor)

        main_layout.addWidget(self.publish_btn)

    def create_connections(self):
        self.publish_btn.clicked.connect(self.publish_hda)

    def publish_hda(self):
        # pass major or minor version and lcoation as arguments
        tbautils.houdini.publish_hda(self.radio_major.isChecked(), self.radio_group_location.checkedButton().text().lower())

class TBA_create_hda_UI(QtWidgets.QDialog):

    dlg_instance = None

    label_edited = False

    @classmethod
    def show_dialog(cls):
        if not cls.dlg_instance:
            cls.dlg_instance = TBA_create_hda_UI(houdini_main_window())

        if cls.dlg_instance.isHidden():
            cls.dlg_instance.show()
        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()


    def __init__(self, parent=None):
        super(TBA_create_hda_UI, self).__init__(parent)

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        self.name_le = QtWidgets.QLineEdit()
        self.label_le = QtWidgets.QLineEdit()

        self.version_label = QtWidgets.QLabel('Versions')

        self.min_inputs = QtWidgets.QLineEdit('1')
        self.min_inputs.setValidator(QtGui.QIntValidator(0,10))

        self.max_inputs = QtWidgets.QLineEdit('1')
        self.max_inputs.setValidator(QtGui.QIntValidator(0,10))

        self.major_le = QtWidgets.QLineEdit('1')
        self.major_le.setValidator(QtGui.QIntValidator(0,99))

        self.minor_le = QtWidgets.QLineEdit('0')
        self.minor_le.setValidator(QtGui.QIntValidator(0,99))

        self.create_btn = QtWidgets.QPushButton('Create')
        self.create_btn.setDisabled(True)

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QFormLayout()

        form_layout.addRow('File Name:', self.name_le)
        form_layout.addRow('Asset Label:', self.label_le)

        inputs_layout = QtWidgets.QHBoxLayout()

        inputs_layout.addWidget(self.min_inputs)
        inputs_layout.addWidget(self.max_inputs)

        versions_layout = QtWidgets.QHBoxLayout()

        versions_layout.addWidget(self.major_le)
        versions_layout.addWidget(self.minor_le)

        form_layout.addRow('Min/Max Inputs:', inputs_layout)
        #form_layout.addRow('Major/Minor Versions:', versions_layout)

        main_layout.addLayout(form_layout)

        main_layout.addWidget(self.create_btn)

    def create_connections(self):
        self.name_le.textEdited.connect(self.on_name_changed)
        self.label_le.textEdited.connect(self.on_label_changed)

        self.min_inputs.textEdited.connect(self.on_inputs_changed)
        self.max_inputs.textEdited.connect(self.on_inputs_changed)

        self.major_le.textEdited.connect(self.validate_button)
        self.minor_le.textEdited.connect(self.validate_button)

        self.create_btn.clicked.connect(self.create_hda)

    def on_name_changed(self, text):
        name = text.replace(' ','_')
        self.name_le.setText(name)

        # get loaded hdas, diable button if name already exists
        #hdas = hou.hda.loadedFiles()

        if not self.label_edited:
            label = re.sub("([a-z])([A-Z])","\g<1> \g<2>", text.replace('_',' '))
            self.label_le.setText(label.title())

        self.validate_button()

    def on_label_changed(self):
        self.label_edited = True
        self.validate_button()

    def on_inputs_changed(self):
        self.max_inputs.setText(max(self.max_inputs.text(),self.min_inputs.text()))
        self.validate_button()

    def validate_button(self):
        if not self.name_le.text() or not self.major_le.text() or not self.minor_le.text() or not self.min_inputs.text() or not self.max_inputs.text():
            self.create_btn.setDisabled(True)
        else:
            self.create_btn.setDisabled(False)

    def create_hda(self):
        reload(tbautils.houdini) # REMOVE THIS FOR PRODUCTION
        name = self.name_le.text().replace(' ','_')
        label = self.label_le.text().replace(' ','_')
        min_inputs = int(self.min_inputs.text())
        max_inputs = int(self.max_inputs.text())
        major = self.major_le.text()
        minor = self.minor_le.text()

        tbautils.houdini.create_hda(label=label, name=name, min_inputs=min_inputs, max_inputs=max_inputs, major=major, minor=minor)

    def camelCase(self, st):
        if not st.strip():
            return st

        output = ''.join(x for x in st.title() if x.isalnum())
        return output[0].lower() + output[1:]

    def snake_case(self, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def houdini_main_window():
    return hou.qt.mainWindow()

if __name__=="__main__":
    print('TBA :: Run Standalone')

    app = QtWidgets.QApplication(sys.argv)

    # pass houdini's main window
    tba_hda_ui = TBA_create_hda_UI()
    tba_hda_ui.show()

    sys.exit(app.exec_())
