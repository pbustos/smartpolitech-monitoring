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
from tornado import ioloop, gen

# Generate GUI form .ui file
call("pyside-uic smartsensors.ui > ui_smartsensors.py", shell=True)
#call("pyuic5 smartsensors.ui > ui_smartsensors.py", shell=True)
from ui_smartsensors import Ui_MainWindow

plots = {}
sensors = {}

class MainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		self.setupUi(self)
		global sensors
		global row

		self.conn = rdb.connect(host="158.49.247.193", port=28015, db="SmartPoliTech", auth_key="smartpolitech2")
		devices = rdb.table("Dispositivos").run(self.conn)
		pp = pprint.PrettyPrinter(indent=4)

		#Init the DB reader thread
		self.reader = RDBReader()
		self.reader.signalVal.connect(self.slotFromReader)
		self.reader.start()

		for device in devices:
			ide = device["id"]
			sensors[ide] = device
			table = "D" + ide.replace("-", "")
			sensors[ide]["table"] = table
			if rdb.table(table).is_empty().run(self.conn) is False:
				datos = rdb.table(table).max("date").run(self.conn)
				sensors[ide]["canales"] = datos["sensors"]
			sensors[ide]["timer"] = Timer(ide, 1000)
			sensors[ide]["timer"].timeout.connect(self.slotCountDown)
			sensors[ide]["timer"].timeout.connect(self.plotUpdate)
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
		self.tableWidget.itemClicked.connect(self.on_graphClicked)
		self.show()

		#Plots
		self.curve = self.plot1.plot()
		self.data = deque(maxlen=100)
		lastData = rdb.table("D7fddae8e897711e0bc11003048c3b1f2").order_by(rdb.desc("date")).limit(100).run(self.conn)
		self.icont=0
		for d in lastData:
			self.data.append({'x': self.icont, 'y': float(d["sensors"][0]["value"])})
			self.icont += 1
		x = [item['x'] for item in self.data]
		y = [item['y'] for item in self.data]
		self.curve.setData(x=x, y=y)

		#Start timers
		#[s["thread"].start() for s in sensors.values()]
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

	@Slot(QTreeWidgetItem, int)
	def on_itemClicked(self, item, column):
		if item.child(0).text(0) in sensors:                ##Connection to model
			if sensors[item.child(0).text(0)]["active"] is True:
				item.setIcon(1, QIcon("icons/redBall.png"))
				sensors[item.child(0).text(0)]["active"] = False
			else:
				item.setIcon(1, QIcon("icons/greenBall.png"))
				sensors[item.child(0).text(0)]["active"] = True
		self.tableWidget.clear()
		self.createTable(self.tableWidget, sensors)

	@Slot(QTableWidgetItem, int)
	def on_graphClicked(self, item):
		print "graph clicked", item
		#check if is a valid spot
		#create a popup with a graph
		#keep updating the graph until closed


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
			#item.setFont(font)
			tableView.setItem(itera, 0, item)
			itera = itera + 1
			tableView.setRowCount(itera + 1)
			head = ("Name", "Updated", "Value", "Graph")
			for j in range(len(head)):
				item = QTableWidgetItem(head[j])
				item.setTextAlignment(Qt.AlignCenter)
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
				sensor["canales"][j]["counterPos"] = (itera, 1)

				item = QTableWidgetItem(sensor["canales"][j]["value"])
				item.setTextAlignment(Qt.AlignCenter)
				tableView.setItem(itera, 2, item)

				item = QTableWidgetItem()
				item.setIcon(QIcon("icons/graph3.png"))
				tableView.setItem(itera, 3, item)

				itera = itera + 1

			tableView.resizeColumnsToContents()
			#tableView.horizontalHeader().setResizeMode(QHeaderView.Stretch);

	@Slot(str)
	def plotUpdate(self, ident):
		if ident == "7fddae8e-8977-11e0-bc11-003048c3b1f2":
			self.data.append({'x': 	self.icont, 'y': float(sensors[ident]["canales"][0]["value"])})
			x = [item['x'] for item in self.data]
			y = [item['y'] for item in self.data]
			self.curve.setData(x=x, y=y)
			self.icont += 1

	@Slot(str)
	def slotCountDown(self, ident):
		sensors[ident]["updated"] += 1
		for canal in sensors[ident]["canales"]:
			row, col = canal["counterPos"]
			self.tableWidget.item(row, col).setText(str(sensors[ident]["updated"]))

	@Slot(str)
	def slotFromReader(self, ident):
		self.tableWidget.clear()
		self.createTable(self.tableWidget, sensors)

class Timer(QObject):
	timeout = Signal(str)

	def __init__(self, ident, period):  #milliseconds
		super(Timer, self).__init__()
		self.ident = ident
		self.period = period

	def start(self):
		try:
			self.timeout.emit(self.ident)
		finally:
			QTimer.singleShot(self.period, self.start)

#Reader for RethinkDB based sensors
class RDBReader(QThread):
	signalVal = Signal(str)
	def __init__(self):
		super(RDBReader, self).__init__()
		rdb.set_loop_type('tornado')
		self.conn = rdb.connect(host="158.49.247.193", port=28015, db="SmartPoliTech", auth_key="smartpolitech2")

	def addTable(self, ident, table):
		ioloop.IOLoop.current().add_callback(self.changes, self.conn, ident, table)

	@gen.coroutine
	def changes(self, conn, ident, table):
		connection = yield conn
		feed = yield rdb.table(table).changes().run(connection)
		while (yield feed.fetch_next()):
			change = yield feed.next()
			sensors[ident]["updated"] = 0
			sensors[ident]["canales"] = change["new_val"]["sensors"]
			self.signalVal.emit(ident)

	def run(self):
		ioloop.IOLoop.current().start()


if __name__ == '__main__':
	app = QApplication(sys.argv)
	mainWin = MainWindow()
	ret = app.exec_()
	sys.exit(ret)
