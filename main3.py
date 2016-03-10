## Monitoring system for SmartPoliTech
##
import sys, json, requests, json, time, threading, pprint
sys.path.append('/usr/local/lib/python2.7/site-packages')
import numpy as np
from collections import deque
from PySide.QtCore import *
from PySide.QtGui import *
#from PyQt5.QtCore import *
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

plots ={}
sensors = {}

class MainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		self.setupUi(self)
		global sensors
		global row	

		self.conn = rdb.connect(host="158.49.247.193",port=28015,db="SmartPoliTech",auth_key="smartpolitech2")
		devices = rdb.table("Dispositivos").run(self.conn)
		pp = pprint.PrettyPrinter(indent=4)
		for device in devices:
			ide = device["id"]
			sensors[ide] = device
			table = "D"+ide.replace("-","")
			sensors[ide]["table"] = table
			ndatos = rdb.table(table).count().run(self.conn)
			if ndatos > 0:
				datos = rdb.table(table).max("date").run(self.conn)
				sensors[ide]["canales"]= datos["sensors"]
			sensors[ide]["thread"] = RDBReader(ide, table)
			sensors[ide]["thread"].signalVal.connect(self.slotFromReader)
			sensors[ide]["timer"] = Timer(ide, 1000)
			sensors[ide]["timer"].timeout.connect(self.slotCountDown)
			sensors[ide]["updated"] = 0
			
		print "Tree -----------------------"
		pp = pprint.PrettyPrinter(indent=4)
		pp.pprint(sensors)
		print "-----------------------"
		
		#create UI table
		self.createTable(self.tableWidget, sensors)
		self.show()
		
		#Start threads
		#[ s["thread"].start() for s in sensors.values() ]
		[ s["timer"].start() for s in sensors.values() ]
	
	def createTable(self, tableView, sensors):
		itera=0
		tableView.setColumnCount(3);
		tableView.horizontalHeader().hide()
		tableView.verticalHeader().hide()
		tableView.setWordWrap(True)
		tableView.setTextElideMode(Qt.ElideNone)
		tableView.setShowGrid(False)
				
		for name,sensor in sensors.iteritems():
			tableView.setRowCount(itera+1)
			tableView.setSpan(itera, 0, 1, tableView.columnCount())
			item = QTableWidgetItem(sensor["description"])
			item.setTextAlignment(Qt.AlignLeft)
			font = QFont()
			font.setBold(True)
			item.setFont(font)
			tableView.setItem(itera,0, item)
			itera=itera+1
			tableView.setRowCount(itera+1)
			head=("Name", "Updated", "Value")
			for j in range(len(head)):
				item = QTableWidgetItem(head[j])
				item.setTextAlignment(Qt.AlignCenter)
				tableView.setItem(itera, j, item)
			itera=itera+1
			
			if "canales" not in sensor:
				continue
			
			for j in range(0,len(sensor["canales"])):
				tableView.setRowCount(itera+1)
			
				print sensor["canales"][0]["name"]
				item = QTableWidgetItem(sensor["canales"][j]["name"])  
				item.setTextAlignment(Qt.AlignCenter)
				tableView.setItem(itera, 0, item)				

				item = QTableWidgetItem(str(sensor["updated"]))
				item.setTextAlignment(Qt.AlignCenter)
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
		
	@Slot(str,dict)
	def slotFromReader(self, ident, value ):
		value=json.loads(value)
		print  "valor "+ value["valor"]
		self.tableWidget.clear()
		self.createTable(self.tableWidget, sensors)
		
class Timer(QObject):
	timeout = Signal( str )
	def __init__(self, ident, period):	#milliseconds
		super(Timer,self).__init__()  
		self.ident = ident
		self.period =period

	def start(self):
		try:
			self.timeout.emit(self.ident)
			print "timer", self.ident
		finally:
			QTimer.singleShot(self.period, self.start)
		
#Reader for RethinkDB based sensors
class RDBReader(QThread):
	signalVal = Signal( str, dict )
	def __init__(self, ident, table):
		super(RDBReader, self).__init__()
		
		ioloop.IOLoop.current().add_callback(self.print_changes)
		rdb.set_loop_type('tornado')
		self.ident = ident
		self.table = table
		
	@gen.coroutine
	def print_changes(self):
		conn = yield rdb.connect(host="158.49.247.193",port=28015,db="SmartPoliTech",auth_key="smartpolitech2")
		feed = yield rdb.table(self.table).changes().run(conn)
		while (yield feed.fetch_next()):
			change = yield feed.next()
			#print "siguiente" + str(change)			
			#print "en thread", sensors[self.ident]["countdown"]
			sensors[self.ident]["countdown"]  = 0
			for i in range(0,len(sensors[self.ident]["canales"])):
				j=json.dumps({"valor":change["new_val"]["sensors"][i]["value"],"iter":i})
				self.signalVal.emit(self.ident, j)
				print "RDBReader", change["new_val"]["sensors"][i]["value"]
				
	def run(self):
		ioloop.IOLoop.current().start()
		
#Reader for REST sensors
class RESTReader(QObject):
	signalVal = Signal( str, dict )
	def __init__(self, ident, url, period):
		super(RESTReader,self).__init__()
		self.ident = ident
		self.url = url
		self.period = period
		
	def start(self):
		try:
			f = requests.get(self.url)	
			sensors[self.ident]["countdown"] = 0
			self.signalVal.emit( self.ident, f.text[1:-1] )
			print "rest reader", f.text[1:-1]
		finally:
			 QTimer.singleShot(int(self.period), self.start)
		
if __name__ == '__main__':
	app = QApplication(sys.argv)
	mainWin = MainWindow()
	ret = app.exec_()
	sys.exit( ret )	
