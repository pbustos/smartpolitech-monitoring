## Monitoring system for SmartPoliTech
##
import sys, json, requests, json, time, threading, pprint
import numpy as np
from collections import deque
from PySide.QtCore import *
from PySide.QtGui import *
from collections import deque
import pyqtgraph as pg
from subprocess import call
import rethinkdb as rdb
import datetime as dt
from rethinkreader import RDBReader
from timer import Timer

# Generate GUI form .ui file
call("pyside-uic smartsensors.ui > ui_smartsensors.py", shell=True)
call("pyside-uic plotdlg.ui > ui_plotdlg.py", shell=True)
#call("pyuic5 smartsensors.ui > ui_smartsensors.py", shell=True)
from ui_smartsensors import Ui_MainWindow
from ui_plotdlg import Ui_PlotDlg

plots = {}
sensors = {}
connData = {"host":"158.49.247.193", "port":"28015", "db":"SmartPoliTech", "auth_key":"smartpolitech2"}
CURRENT = "024020cc-28df-4c48-aa93-52e7193c9570"
CURRENT_TABLE = "D024020cc28df4c48aa9352e7193c9570"

class MainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		self.setupUi(self)
		global sensors, row, CURRENT_TABLE
		self.conn = rdb.connect(host=connData["host"], port=connData["port"], db=connData["db"], auth_key=connData["auth_key"])
		devices = rdb.table("Dispositivos").run(self.conn)
		pp = pprint.PrettyPrinter(indent=4)

		#Init the DB reader thread
		self.reader = RDBReader(connData, sensors)
		self.reader.signalVal.connect(self.slotFromReader)
		self.reader.start()

		for device in devices:
			if device["id"] == CURRENT:
				ide = device["id"]
				sensors[ide] = device
				table = "D" + ide.replace("-", "")
				sensors[ide]["table"] = table
				if rdb.table(table).is_empty().run(self.conn) is False:
					datos = rdb.table(table).max("date").run(self.conn)
					sensors[ide]["canales"] = datos["sensors"]
				sensors[ide]["timer"] = Timer(ide, 1000)
				sensors[ide]["timer"].timeout.connect(self.slotCountDown)
				#sensors[ide]["timer"].timeout.connect(self.plotUpdate)
				sensors[ide]["updated"] = 0
				sensors[ide]["active"] = True
				self.reader.addTable(ide, table)

		# print "Tree -----------------------"
		# pp = pprint.PrettyPrinter(indent=4)
		# pp.pprint(sensors)
		# print "-----------------------"

		#create Tree
		self.createTree()
		self.treeWidget.itemClicked.connect(self.on_itemClicked)

		#create UI table
		self.createTable(self.tableWidget, sensors)
		self.tableWidget.cellClicked.connect(self.on_graphClicked)
		self.show()

		#Plots
		# self.curve = self.plot1.plot()
		# self.data = deque(maxlen=100)
		# lastData = rdb.table(CURRENT_TABLE).order_by(rdb.desc("date")).limit(100).run(self.conn)
		# self.icont=0
		# for d in lastData:
		# 	self.data.append({'x': self.icont, 'y': float(d["sensors"][0]["value"])})
		#  	self.icont += 1
		# x = [item['x'] for item in self.data]
		# y = [item['y'] for item in self.data]
		# self.curve.setData(x=x, y=y)

		#Start timers
		#self.reader.addTable("8c3450b7-9a74-4149-9ed3-a4098f4f88b3", "D8c3450b79a7441499ed3a4098f4f88b3")
		[s["timer"].start() for s in sensors.values()]

	def createTree(self):
		self.treeWidget.setColumnCount(2)
		self.treeWidget.setHeaderLabels(["On/off", "Dispositivo"])
		self.treeWidget.header().setResizeMode(0, QHeaderView.ResizeToContents)
		#self.treeWidget.header().setResizeMode(1, QHeaderView.Fixed)
		for s in sensors.values():
			top = QTreeWidgetItem(self.treeWidget)
			#name.setText(0, s["description"] + "   ( " + s["id"] + " )")
			top.setText(1, s["description"])
			#top.setText(1, s["id"])
			top.setIcon(0, QIcon("icons/greenBall.png"))
			child = QTreeWidgetItem(top)
			child.setText(1, s["id"])
			child = QTreeWidgetItem(top)
			child.setText(1, s["type"])
			child = QTreeWidgetItem(top)
			child.setText(1, s["location"])

	def createTable(self, tableView, sensors):
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
			item = QTableWidgetItem(sensor["description"] + "   ( " + sensor["id"] + " )")
			item.setTextAlignment(Qt.AlignLeft)
			font = QFont()
			font.setPointSize(13)
			font.setBold(True)
			item.setFont(font)
			tableView.setItem(itera, 0, item)
			itera = itera + 1
			tableView.setRowCount(itera + 1)
			head = ("Name", "Updated", "Value", "Graph")
			for h, j in zip(head, range(len(head))):
				item = QTableWidgetItem(h)
				item.setTextAlignment(Qt.AlignCenter)
				font.setPointSize(11)
				item.setForeground(Qt.blue)
				item.setFont(font)
				tableView.setItem(itera, j, item)
			itera = itera + 1

			if "canales" not in sensor:
				continue

			for j in range(0, len(sensor["canales"])):
				tableView.setRowCount(itera + 1)

				item = QTableWidgetItem(sensor["canales"][j]["name"])
				item.setTextAlignment(Qt.AlignCenter)
				tableView.setItem(itera, 0, item)

				item = QTableWidgetItem(str(sensor["updated"]))
				item.setTextAlignment(Qt.AlignCenter)
				if sensor["updated"] < 30:
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

				itera = itera + 1

			tableView.resizeColumnsToContents()
			tableView.horizontalHeader().setResizeMode(QHeaderView.Stretch);

#
#SLOTS
#

	@Slot(QTreeWidgetItem, int)
	def on_itemClicked(self, item, col):
		print item.child(0).text(1)
		if item.child(0).text(1) in sensors:                ##Connection to model
			if sensors[item.child(0).text(1)]["active"] is True:
				item.setIcon(0, QIcon("icons/redBall.png"))
				sensors[item.child(0).text(1)]["active"] = False
			else:
				item.setIcon(0, QIcon("icons/greenBall.png"))
				sensors[item.child(0).text(1)]["active"] = True
		self.tableWidget.clear()
		self.createTable(self.tableWidget, sensors)

	@Slot(int, int)
	def on_graphClicked(self, row, col):
		print "graph clicked", row, col
		#check if is a valid spot
		found = False
		for k, s in sensors.iteritems():
			for c, pos in zip(s["canales"], range(len(s["canales"]))):
				if c["counterPos"][0] == row and col == 3:
					found = True
					break
		if found:
			# modal window for sensors[k]
			self.drawModalGraph(sensors[k], pos)

		#create a popup with a graph
		#keep updating the graph until closed

	def drawModalGraph(self, sensor, canal):
		self.dlg = QDialog()
		plotDlg = Ui_PlotDlg()
		plotDlg.setupUi(self.dlg)
		self.dlg.setWindowModality(Qt.ApplicationModal)
		self.dlg.show()
		self.curve = plotDlg.plot.plot()
		self.data = deque(maxlen=100)
		lastData = rdb.table(sensor["table"]).order_by(rdb.desc("date")).limit(100).run(self.conn)
		for d, icont in zip(lastData, range(len(lastData))):
			self.data.append({'x': icont, 'y': float(d["sensors"][canal]["value"])})
		x = [item['x'] for item in self.data]
		y = [item['y'] for item in self.data]
		self.curve.setData(x=x, y=y)

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
		sensors[ident]["updated"] += 1
		for canal in sensors[ident]["canales"]:
			if "counterPos" in canal:
				row, col = canal["counterPos"]
				self.tableWidget.item(row, col).setText(str(sensors[ident]["updated"]))

	@Slot(str)
	def slotFromReader(self, ident):
		self.tableWidget.clear()
		self.createTable(self.tableWidget, sensors)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	mainWin = MainWindow()
	ret = app.exec_()
	sys.exit(ret)
