from PySide2.QtWidgets import QLineEdit, QCompleter, QLabel
from PySide2 import QtCore
from PySide2.QtCore import QStringListModel, QTimer
from PySide2.QtGui import QMouseEvent

class CustomLineEdit(QLineEdit):

	mousePressed = QtCore.Property(QMouseEvent)
	tagSelected = QtCore.Signal(str)

	def __init__(self, parent):
		super(self.__class__, self).__init__()
		self.model = QStringListModel()
		self.setCompleter(QCompleter())
		self.completer().setModel(self.model)
		self.completer().setCompletionMode(QCompleter.PopupCompletion)
		self.completer().activated.connect(self.selected)
		self.textEdited.connect(self.slot_text_edited)
		self.parent = parent
		self.setPlaceholderText("Type tags here")

	def slot_text_edited(self, text):
		self.completer().setCompletionMode(QCompleter.UnfilteredPopupCompletion if text == '' else QCompleter.PopupCompletion)

	def selected(self, txt):
		self.tagSelected.emit(txt)

	def set_list(self, qsl):
		self.model.setStringList(qsl)

	def mousePressEvent(self, e):
		self.completer().complete()

	def focusInEvent(self, e):
		self.completer().complete()

	def focusOutEvent(self, e):
		pass