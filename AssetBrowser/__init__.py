import os
import pymongo
import hou
from fnmatch import fnmatch
from pprint import pprint
from design import Ui_AssetBrowser
from PySide2.QtWidgets import QDialog, QWidget, QApplication, QCompleter, QLineEdit, QLabel, QHBoxLayout, QFrame, QTableWidgetItem, QRadioButton, QButtonGroup
from PySide2.QtCore import QStringListModel, QTimer, QEvent, QRectF, Qt
from PySide2.QtGui import QMouseEvent, QPainter, QBrush, QColor
from PySide2 import QtCore
from textwrap import dedent

# TBA Imports
from ..houdini import importHoudiniAsset
from ..config import mongo

class AssetCell(QWidget):
	filepath = ''
	obj_id = ''

	def __init__(self, ver, filepath, obj_id):
		super(self.__class__, self).__init__()
		self.filepath = filepath
		self.obj_id = obj_id
		ly_root = QHBoxLayout()
		self.rad_sel = QRadioButton()
		lbl_ver = QLabel(ver)
		lbl_ver.setAttribute(Qt.WA_TranslucentBackground)
		ly_root.addWidget(self.rad_sel, 1)
		ly_root.addWidget(lbl_ver, 5)
		self.setLayout(ly_root)

	def getObjId(self):
		return self.obj_id

	def getFilepath(self):
		return self.filepath

	def getRad(self):
		return self.rad_sel


class TagLabel(QWidget):
	tagClicked = QtCore.Signal(str)
	name = ''

	def __init__(self, name):
		super(self.__class__, self).__init__()
		self.name = name
		ly_tag = QHBoxLayout()
		lbl_tag = QLabel(name)
		lbl_tag.setAttribute(Qt.WA_TranslucentBackground)
		ly_tag.addWidget(lbl_tag)
		self.setLayout(ly_tag)

	# Needed for rounded edges
	def paintEvent(self, ev):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.setPen(Qt.NoPen)
		painter.setBrush(QBrush(QColor(255, 205, 42)))
		painter.drawRoundedRect(self.rect(), 10.0, 10.0)

	def mousePressEvent(self, e):
		self.tagClicked.emit(self.name)


class AssetBrowser(QDialog, Ui_AssetBrowser):

	mongo_host = mongo['hostname']
	mongo_port = mongo['port']
	mongo_db = 'tag_model'
	selected_tags = []
	job = {}
	jobs = []

	job_name = None
	stage_name = None
	entity_name = None

	asset_tags = {}
	asset_grps = {}

	stages = [
		'build',
		'rnd',
		'previs',
		'shots'
	]
	entities = []

	def __init__(self, current_path=None):
		super(self.__class__, self).__init__()
		self.setupUi(self)

		# Create button group
		self.grp_buttons = QButtonGroup()
		self.btn_import.released.connect(self.import_asset)

		self.initDB()
		self.getJobs()
		self.parseJobPath(current_path)
		self.initJob()

		self.populateStages()
		self.populateEntities()

		# Pre-set combo boxes
		self.cmb_stages.setCurrentIndex(self.stages.index(self.stage_name))
		self.cmb_jobs.setCurrentIndex(self.jobs.index(self.job_name))
		self.cmb_entities.setCurrentIndex(self.entities.index(self.entity_name))

		self.le_in.tagSelected.connect(self.activate_tag)
		self.cmb_jobs.currentIndexChanged.connect(self.change_job)
		self.cmb_stages.currentIndexChanged.connect(self.change_stage)
		self.cmb_entities.currentIndexChanged.connect(self.change_entity)
		self.refresh_asset_list()

		# Set stylesheet
		self.setStyleSheet(hou.qt.styleSheet())
		self.show()


	def change_entity(self):
		self.entity = self.cmb_entities.currentText()
		self.refresh_asset_list()


	#
	# Init database object
	#
	def initDB(self):
		client = pymongo.MongoClient(self.mongo_host, self.mongo_port)
		self.db = client[self.mongo_db]
		self.setWindowTitle('{} [{}:{}]'.format(self.windowTitle(), self.mongo_host, self.mongo_port))


	# Get list of jobs
	def getJobs(self):
		jobs = self.db.jobs.find({})
		for job in jobs:
			self.jobs.append(job['name'])
			self.cmb_jobs.addItem(job['name'])


	def populateStages(self):
		for stage in self.stages:
			self.cmb_stages.addItem(stage)


	# Validate current_path
	def parseJobPath(self, current_path):
		try:
			job_path = current_path.split('/')
			vfx_index = job_path.index('vfx')
			self.job_name = job_path[vfx_index-1]

			# Try to set stage, but if we are not deep enough, default to build
			try:
				self.stage_name = job_path[vfx_index+1]
			except IndexError:
				self.stage_name = 'shots'

			# Same with entity
			try:
				self.entity_name = job_path[vfx_index+2]
			except IndexError:
				self.entity_name = 'sh0001'

		except:
			print "VFX Directory not found. No valid jobs detected"
			self.stage_name = 'shots'
			self.entity_name = 'sh0001'


	def change_job(self, i):
		self.job_name = self.cmb_jobs.currentText()
		self.initJob()
		self.populateEntities()
		self.refresh_asset_list()


	def change_stage(self, i):
		self.stage_name = self.cmb_stages.currentText()

		# Trigger rebuilding of entity combo box list
		self.populateEntities()
		self.refresh_asset_list()


	def populateEntities(self):

		self.cmb_entities.clear()
		self.entities = []

		entity_root = '{}/vfx/{}'.format(self.job['path'], self.stage_name)
		entities = [x for x in os.listdir(entity_root) if x[0] is not '_']
		for entity in entities:
			self.entities.append(entity)
			self.cmb_entities.addItem(entity)


	#
	# Initialize job variables and derive JobID from job path as well as
	# asset details attached to job
	#
	def initJob(self):

		# Reset
		self.asset_grps = {}
		self.asset_tags = {}
		self.selected_tags = []

		# Pick up job_name
		if self.job_name is not None:
			self.job = self.db['jobs'].find_one({ "name": self.job_name })
		else:
			self.job = self.db['jobs'].find_one({})
			self.job_name = self.job['name']

		# Get all assets matching the job_id
		self.assets = [x for x in self.db.assets_curr.find({ "job_id": self.job['_id'] })]

		# Resolve tag_ids
		for i, asset in enumerate(self.assets):
			if 'tags' in self.assets[i].keys():
				self.assets[i]['tags'] = [self.job['pooled_asset_tags'][x] for x in asset['tags']]

		# Consolidate asset entries by name
		for asset in self.assets:
			if asset['name'] not in self.asset_grps:
				self.asset_grps[asset['name']] = []
			self.asset_grps[asset['name']].append(asset)

		# Bring tags to top level of dict
		for k, grp in self.asset_grps.iteritems():
			flt = [x for x in grp if x.get('tags') is not None]
			self.asset_tags[k] = {tag for sublist in [x.get('tags') for x in flt] for tag in sublist}

		self.le_in.set_list(self.job['pooled_asset_tags'])
		self.rebuild_tags()


	def rebuild_tags(self):
		for i in range(0, self.ly_in.count()-1):
			self.ly_in.itemAt(i).widget().close()

		# Repopulate tag list
		for j, tag in enumerate(self.selected_tags):
			tl = TagLabel(tag)
			tl.tagClicked.connect(self.remove_tag)
			self.ly_in.insertWidget(j, tl)


	#
	# When completion is clicked, add tag to selected tags list and redraw
	# tags in QHBoxLayout
	#
	def activate_tag(self, text):

		if text not in self.selected_tags:

			# Add to list of selected tags and update completion model
			self.selected_tags.append(text)
			self.rebuild_tags()
			self.le_in.set_list([x for x in self.le_in.model.stringList() if x not in self.selected_tags])
			self.refresh_asset_list()


	def remove_tag(self, txt):
		self.selected_tags.remove(txt)
		self.rebuild_tags()
		current_model = self.le_in.model.stringList()
		current_model.append(txt)
		self.le_in.set_list(current_model)
		self.refresh_asset_list()


	def refresh_asset_list(self):
		types = {
			'model':	1,
			'layout':	2,
			'anim':		3,
			'fx_prep':	4,
			'fx_sim':	5,
			'shader':	6
		}

		# Match tags
		matched_assets = [
			k for k,v in self.asset_tags.iteritems()
			if all(y in v for y in self.selected_tags)
		]

		# Filter: all models from build
		# Clear table
		while self.tbl_assets.rowCount() > 0:
			self.tbl_assets.removeRow(0)


		# Filter assets based on our rules:
		# 1. Include all build+models+shaders
		# 2. Include all build+shaders
		# 3. Filter everything else based on stage/entity
		filtered_assets = {}

		for key,grp in self.asset_grps.iteritems():
			filtered_assets[key] = []
			if key in matched_assets:
				for asset in grp:
					if asset['stage'] == 'build' and asset['type'] == 'model':
						filtered_assets[key].append(asset)
					elif asset['stage'] == 'build' and asset['type'] == 'shader':
						filtered_assets[key].append(asset)
					elif asset['stage'] == self.cmb_stages.currentText() and asset['entity'] == self.cmb_entities.currentText():
						filtered_assets[key].append(asset)

		for asset_name in matched_assets:

			self.tbl_assets.insertRow(0)
			item = QTableWidgetItem(asset_name)
			item.setFlags(QtCore.Qt.ItemIsEnabled)
			self.tbl_assets.setItem(0, 0, item)
			asset = filtered_assets[asset_name]

			for sub_asset in asset:

				# Safely grab column index based on asset type. Default
				# to 1 if no type is present.
				tbl_pos = types.get(sub_asset.get('type'))
				if tbl_pos is None:
					tbl_pos = 1

				rad = AssetCell('v{}'.format(str(sub_asset['version'])), sub_asset['filepath'], sub_asset['_id'])
				self.grp_buttons.addButton(rad.getRad())
				self.tbl_assets.setCellWidget(0, tbl_pos, rad)


	def import_asset(self):
		# Get currently selected AssetCell in QButtonGroup
		print self.grp_buttons.checkedButton().parent().getFilepath()
		obj_id = self.grp_buttons.checkedButton().parent().getObjId()
		importHoudiniAsset(self.db, obj_id)