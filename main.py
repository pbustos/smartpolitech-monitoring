## Monitoring system for SmartPoliTech
##
import sys, json, requests, json, time, threading, pprint

sys.path.append('/usr/local/lib/python2.7/site-packages')
import numpy as np
from collections import deque
from PySide.QtCore import *
from PySide.QtGui import *
# from PyQt5.QtCore import *
#from PyQt5.QtGui import *
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
		for device in devices:
			ide = device["id"]
			#if ide == "e0507f7c-2e90-41a3-8e74-eb74c6da5e21":
			sensors[ide] = device
			table = "D" + ide.replace("-", "")
			sensors[ide]["table"] = table
			ndatos = rdb.table(table).count().run(self.conn)
			if ndatos > 0:
				datos = rdb.table(table).max("date").run(self.conn)
				sensors[ide]["canales"] = datos["sensors"]
			sensors[ide]["thread"] = RDBReader(ide, table)
			sensors[ide]["thread"].signalVal.connect(self.slotFromReader)
			sensors[ide]["timer"] = Timer(ide, 1000)
			sensors[ide]["timer"].timeout.connect(self.slotCountDown)
			sensors[ide]["updated"] = 0
			sensors[ide]["active"] = True

		print "Tree -----------------------"
		pp = pprint.PrettyPrinter(indent=4)
		pp.pprint(sensors)
		print "-----------------------"

		#create Tree
		self.createTree()
		self.treeWidget.itemClicked.connect(self.on_itemClicked)

		#create UI table
		self.createTable(self.tableWidget, sensors)
		self.show()

		#Start threads
		[s["thread"].start() for s in sensors.values()]
		[s["timer"].start() for s in sensors.values()]

	def createTree(self):
		self.treeWidget.setColumnCount(2)
		self.treeWidget.setHeaderLabels(["Dispositivo" , "On/off"])
		self.treeWidget.header().setResizeMode(0, QHeaderView.ResizeToContents)
		#self.treeWidget.setColumnWidth(1, 4)
		#self.treeWidget.header().setResizeMode(1, QHeaderView.Fixed)
		#items = []
		for s in sensors.values():
			top = QTreeWidgetItem(self.treeWidget)
			#name.setText(0, s["description"] + "   ( " + s["id"] + " )")
			top.setText(0, s["description"])
			#top.setText(1, s["id"])
			top.setIcon(1,QIcon("greenBall.png"))
			child = QTreeWidgetItem(top)
			child.setText(0, s["id"])
			child = QTreeWidgetItem(top)
			child.setText(0, s["type"])
			child = QTreeWidgetItem(top)
			child.setText(0, s["location"])

	@Slot(QTreeWidgetItem, int)
	def on_itemClicked(self, item, column):
		if item.child(0).text(0) in sensors:                ##Connection to model
			if sensors[item.child(0).text(0)]["active"] is True:
				item.setIcon(1, QIcon("redBall.png"))
				sensors[item.child(0).text(0)]["active"] = False
			else:
				item.setIcon(1, QIcon("greenBall.png"))
				sensors[item.child(0).text(0)]["active"] = True
		self.tableWidget.clear()
		self.createTable(self.tableWidget, sensors)
		#treeWidget.currentItem().setBackground(1, brush_green)

	def createTable(self, tableView, sensors):
		itera = 0
		tableView.setColumnCount(3)
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
			head = ("Name", "Updated", "Value")
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

				item = QTableWidgetItem(sensor["canales"][j]["value"])
				item.setTextAlignment(Qt.AlignCenter)
				tableView.setItem(itera, 2, item)

				itera = itera + 1
			tableView.resizeColumnsToContents()
			tableView.horizontalHeader().setResizeMode(QHeaderView.Stretch);

	@Slot(str)
	def slotCountDown(self, ident):
		sensors[ident]["updated"] += 1
		self.tableWidget.clear()
		self.createTable(self.tableWidget, sensors)

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

	def __init__(self, ident, table):
		super(RDBReader, self).__init__()
		ioloop.IOLoop.current().add_callback(self.print_changes)
		rdb.set_loop_type('tornado')
		self.ident = ident
		self.table = table

	@gen.coroutine
	def print_changes(self):
		conn = yield rdb.connect(host="158.49.247.193", port=28015, db="SmartPoliTech", auth_key="smartpolitech2")
		feed = yield rdb.table(self.table).changes().run(conn)
		while (yield feed.fetch_next()):
			change = yield feed.next()
			sensors[self.ident]["updated"] = 0
			sensors[self.ident]["canales"] = change["new_val"]["sensors"]
			self.signalVal.emit(self.ident)

	def run(self):
		ioloop.IOLoop.current().start()


#Reader for REST sensors
class RESTReader(QObject):
	signalVal = Signal(str, dict)

	def __init__(self, ident, url, period):
		super(RESTReader, self).__init__()
		self.ident = ident
		self.url = url
		self.period = period

	def start(self):
		try:
			f = requests.get(self.url)
			sensors[self.ident]["countdown"] = 0
			self.signalVal.emit(self.ident, f.text[1:-1])
			print "rest reader", f.text[1:-1]
		finally:
			QTimer.singleShot(int(self.period), self.start)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	mainWin = MainWindow()
	ret = app.exec_()
	sys.exit(ret)
