##
## Monitoring system for SmartPoliTech
##

import sys, json, requests, json, time, pprint
import numpy as np
from collections import deque
from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtSvg import *
from collections import deque
import pyqtgraph as pg
from subprocess import call
import rethinkdb as rdb
import datetime as dt
from rethinkreader import RDBReader
from timer import Timer
from dateutil import parser
from plotter import Plotter
from svg import Svg
import pytz

# Generate GUI form .ui file
call("pyside-uic smartsensors.ui > ui_smartsensors.py", shell=True)
call("pyside-uic plotdlg.ui > ui_plotdlg.py", shell=True)
#call("pyuic5 smartsensors.ui > ui_smartsensors.py", shell=True)
from ui_smartsensors import Ui_MainWindow
from ui_plotdlg import Ui_PlotDlg

plots = {}
sensors = {}
connData = {"host":"158.49.247.126", "port":"28015", "db":"smartpolitech", "auth_key":"smartpolitech2"}
CURRENT = "UEXCC_INF_P00_AUL030_SEN001_THC"
CURRENT_TABLE = "UEXCC_INF_P00_AUL030_SEN001_THC"

class MainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		self.setupUi(self)
		global sensors, CURRENT_TABLE
		#self.conn = rdb.connect(host=connData["host"], port=connData["port"], db=connData["db"], auth_key=connData["auth_key"])
		self.conn = rdb.connect(host=connData["host"], port=connData["port"], db=connData["db"])
		# Set a changefeed for "Dispositivos" with initial state reading
		devices = rdb.table("devices").run(self.conn)
		pp = pprint.PrettyPrinter(indent=4)

		# Init the DB reader thread
		self.reader = RDBReader(connData, sensors)
		self.reader.signalVal.connect(self.slotFromReader)
		self.reader.start()

		for device in list(devices):
			#if device["id"] == CURRENT:
			ide = device["id"]
			sensors[ide] = device
			#table = "D" + ide.replace("-", "")
			#sensors[ide]["table"] = table
			# Poner todos como OFF y hacer esto en background
			if rdb.table(ide).is_empty().run(self.conn) is False:
				datos = rdb.table(ide).max("created_at").run(self.conn)
				sensors[ide]["canales"] = list()
				for k,v in datos["data"].iteritems():
					sensors[ide]["canales"].append({"name":k,"value":v})
			sensors[ide]["timer"] = Timer(ide, 1000)
			sensors[ide]["timer"].timeout.connect(self.slotCountDown)
			#secs = (dt.datetime.now(pytz.utc) - parser.parse(datos["created_at"])).total_seconds()
			secs = (dt.datetime.now(pytz.utc) - datos["created_at"]).total_seconds()
			sensors[ide]["updated"] = dt.timedelta(seconds=secs)
			sensors[ide]["active"] = True
			self.reader.addTable(ide)

		# print "Tree -----------------------"
		# pp = pprint.PrettyPrinter(indent=4)
		# pp.pprint(sensors)
		# print "-----------------------"
		
		# create Tree
		self.createTree()
		self.treeWidget.itemClicked.connect(self.on_itemClicked)
		
		# create UI table
		self.createTable(self.tableWidget)
		self.tableWidget.cellClicked.connect(self.on_graphClicked)
		self.show()
		
		# Start timers
		# self.reader.addTable("8c3450b7-9a74-4149-9ed3-a4098f4f88b3", "D8c3450b79a7441499ed3a4098f4f88b3")
		[s["timer"].start() for s in sensors.values()]
		
		# Svg rendering
		self.svg = Svg(self.tabWidget.widget(1), self.svgLayout)
		#self.tabWidget.currentChanged.connect(self.doSvg)

		# Flip button
		self.flipButton.clicked.connect(self.flipAll)

	#Slot to flip all devices to off/on
	def flipAll(self):
		print "hola", self.flipButton.isChecked()
		if self.flipButton.isChecked():
			for v in sensors.itervalues():
				v["active"] = False
		else:
			for v in sensors.itervalues():
				v["active"] = True
		self.treeWidget.clear()
		self.createTree()
		self.tableWidget.clear()
		self.createTable(self.tableWidget)

	# @Slot(int)
	# def doSvg(self, index):
	# 	print "now we are"
	# 	if index is not 2:
	# 		return

	def createTree(self):
		self.treeWidget.setColumnCount(2)
		self.treeWidget.setHeaderLabels(["On/off", "Dispositivo"])
		self.treeWidget.header().setResizeMode(0, QHeaderView.ResizeToContents)
		#self.treeWidget.header().setResizeMode(1, QHeaderView.Fixed)
		for s in sensors.values():
			top = QTreeWidgetItem(self.treeWidget)
			#name.setText(0, s["description"] + "   ( " + s["id"] + " )")
			top.setText(1, s["Description"])
			if s["active"] is True:
				top.setIcon(0, QIcon("icons/greenBall.png"))
			else:
				top.setIcon(0, QIcon("icons/redBall.png"))
			child = QTreeWidgetItem(top)
			child.setText(1, s["id"])
			#child = QTreeWidgetItem(top)
			#child.setText(1, s["type"])
			#child = QTreeWidgetItem(top)
			#child.setText(1, s["location"])

	def createTable(self, tableView):
		itera = 0
		tableView.setColumnCount(4)
		tableView.horizontalHeader().hide()
		tableView.verticalHeader().hide()
		tableView.setWordWrap(True)
		tableView.setTextElideMode(Qt.ElideNone)
		#tableView.setShowGrid(False)

		for name, sensor in sensors.iteritems():
			if sensor["active"] is False:
				continue
			tableView.setRowCount(itera + 1)
			tableView.setSpan(itera, 0, 1, tableView.columnCount())
			item = QTableWidgetItem(sensor["Description"] + "   ( " + sensor["id"] + " )")
			item.setTextAlignment(Qt.AlignLeft)
			font = QFont()
			font.setPointSize(13)
			font.setBold(True)
			item.setFont(font)
			tableView.setItem(itera, 0, item)
			itera += 1
			tableView.setRowCount(itera + 1)
			head = ("Name", "Updated", "Value", "Graph")
			for h, j in zip(head, range(len(head))):
				item = QTableWidgetItem(h)
				item.setTextAlignment(Qt.AlignCenter)
				font.setPointSize(11)
				item.setForeground(Qt.blue)
				item.setFont(font)
				tableView.setItem(itera, j, item)
			itera += 1

			if "canales" not in sensor:
				continue

			for j in range(0, len(sensor["canales"])):
				tableView.setRowCount(itera + 1)

				item = QTableWidgetItem(sensor["canales"][j]["name"])

				item.setTextAlignment(Qt.AlignCenter)
				tableView.setItem(itera, 0, item)

				item = QTableWidgetItem("{:0>8}".format(sensor["updated"]).split('.', 1)[0])
				item.setTextAlignment(Qt.AlignCenter)
				if sensor["updated"].seconds < 600:
					item.setForeground(QBrush(Qt.green))
				else:
					item.setForeground(QBrush(Qt.red))
				tableView.setItem(itera, 1, item)

				#Add position of counter
				sensor["canales"][j]["counterPos"] = (itera, 1)

				item = QTableWidgetItem(sensor["canales"][j]["value"])
				item.setTextAlignment(Qt.AlignCenter)
				tableView.setItem(itera, 2, item)

				pix = QPixmap("icons/graph4.png").scaled(30, 30, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
				lab = QLabel()
				lab.setPixmap(pix)
				lab.setAlignment(Qt.AlignCenter)
				tableView.setCellWidget(itera, 3, lab)

				#Add widget
				sensor["canales"][j]["widget"] = item

				itera += 1

			tableView.resizeColumnsToContents()
			tableView.horizontalHeader().setResizeMode(QHeaderView.Stretch);

#
#SLOTS
#

	@Slot(QTreeWidgetItem, int)
	def on_itemClicked(self, item, col):
		disp = item.child(0).text(1)
		if disp in sensors:                ##Connection to model
			if sensors[disp]["active"] is True:
				item.setIcon(0, QIcon("icons/redBall.png"))
				sensors[disp]["active"] = False
			else:
				item.setIcon(0, QIcon("icons/greenBall.png"))
				sensors[disp]["active"] = True
		self.tableWidget.clear()
		self.createTable(self.tableWidget)

	@Slot(int, int)
	def on_graphClicked(self, row, col):
		print "graph clicked", row, col
		#check if is a valid spot
		if col is not 3:
			return
		found = False
		for k, s in sensors.items():
			for c, pos in zip(s["canales"], range(len(s["canales"]))):
				#Check if clicked row is on of the stored rows
				if c["counterPos"][0] == row:
					self.p = Plotter(self.conn, k, s, pos)
					break

	@Slot(str)
	def plotUpdate(self, ident):
		if ident == CURRENT:
			self.data.append({'x': 	self.icont, 'y': float(sensors[ident]["canales"][0]["value"])})
			x = [item['x'] for item in self.data]
			y = [item['y'] for item in self.data]
			self.curve.setData(x=x, y=y)
			self.icont += 1

	@Slot(str)
	def slotCountDown(self, ident):
		sensors[ident]["updated"] += dt.timedelta(seconds=1)
		if sensors[ident]["active"] is False:
			return
		for canal in sensors[ident]["canales"]:
			if "counterPos" in canal:
				row, col = canal["counterPos"]
				self.tableWidget.item(row, col).setText("{:0>8}".format(sensors[ident]["updated"]).split('.', 1)[0])


	@Slot(str)
	def slotFromReader(self, ident):
		self.tableWidget.clear()
		self.createTable(self.tableWidget)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	mainWin = MainWindow()
	ret = app.exec_()
	sys.exit(ret)
