## Monitoring system for SmartPoliTech
##

import cv2, sys, requests, json, time
import numpy as np
from collections import deque
from PySide.QtCore import *
from PySide.QtGui import *
import pyqtgraph as pg
from subprocess import call
import rethinkdb as rdb
import datetime as dt
from tornado import ioloop, gen
import threading

# Generate GUI form .ui file
call("pyside-uic smartsensors.ui > ui_smartsensors.py", shell=True)
from ui_smartsensors import Ui_MainWindow

plots ={}
sensors = {}

class MainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		self.setupUi(self)
		
		#read sensor's configuration file
		sensorFile = self.readJSONFile("sensors.json")
		sensors = sensorFile["sensores"]
		r=4
		for name,s in sensors.iteritems():
			if s["source"] == "RETHINK":
				s["thread"] = RDBReader(str(name), s["table"])
				s["thread"].signalVal.connect(self.slotFromReader)
				s["timer"] = Timer(1000, name)
				s["timer"].timeout.connect(self.slotCountDown)
				s["countdown"] = 0
				s["row"] = r
				r=r+1
			
				
			#if s["source"] == "EMONCMS":
				#s["thread"] = RESTReader(name, s["url"], s["period"])
				#s["thread"].signalVal.connect(self.slotFromReader)
				#s["timer"] = Timer(1000, name)
				#s["timer"].timeout.connect(self.slotCountDown)
				#s["countdown"] = 0
				#s["row"] = r
				#r = r+1
				
		#create UI table
		self.createTable(self.tableWidget)
		self.setTableRows(sensors, self.tableWidget)
		
		self.show()
		
		#Start threads
		sensors["devSalon"]["thread"].start()	
	#	[ s["thread"].start() for s in sensors.values() ]
	#	[ s["timer"].start() for s in sensors.values() ]

		
	def readJSONFile(self, fileName, imprimir = False):
		with open(fileName, 'r') as fileJson:
			data = json.load(fileJson)
                if imprimir == True:
                    pprint(data)
		return data

	def createTable(self, tableView):
		tableView.setRowCount(10);
		tableView.setColumnCount(6);
		tableView.horizontalHeader().hide()
		tableView.verticalHeader().hide()
		tableView.setWordWrap(True)
		tableView.setTextElideMode(Qt.ElideNone)
		tableView.setShowGrid(False)
		
		NROW = 1
		tableView.setSpan(NROW, 0, 1, tableView.columnCount())
		item = QTableWidgetItem("Feeds")
		item.setTextAlignment(Qt.AlignLeft)
		brush = QBrush(QColor(28, 128, 128))
		brush.setStyle(Qt.SolidPattern)
		item.setBackground(brush)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(14)
		font.setBold(True)
		item.setFont(font)
		tableView.setItem(NROW,0, item)
		
		NROW = 2
		tableView.setSpan(NROW, 0, 1, tableView.columnCount())
		item = QTableWidgetItem("  Device 0")
		item.setTextAlignment(Qt.AlignLeft)
		brush = QBrush(QColor(128, 28, 128))
		brush.setStyle(Qt.SolidPattern)
		item.setBackground(brush)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(12)
		item.setFont(font)
		tableView.setItem(NROW,0, item)
		
		NROW = 3
		head=("Name", "Location", "Source", "Units", "Updated", "Value")
		for i in range(len(head)):
			item = QTableWidgetItem(head[i])
			item.setTextAlignment(Qt.AlignCenter)
			brush = QBrush(Qt.darkGreen)
			brush.setStyle(Qt.SolidPattern)
			item.setBackground(brush)
			font = QFont()
			font.setFamily(u"DejaVu Sans")
			font.setPointSize(11)
			font.setBold(True)
			item.setFont(font)
			tableView.setItem(NROW, i, item)
		
		tableView.horizontalHeader().setStretchLastSection(True)
		tableView.horizontalHeader().setResizeMode(QHeaderView.Stretch);
		
	def setTableRows(self, sensors, tableView):
		NROW = 4
		brushB = QBrush(QColor(250, 250, 250))
		brushF = QBrush(Qt.black)
		brushB.setStyle(Qt.SolidPattern)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(10)
		font.setBold(True)
		row = NROW
		for name, sensor in sensors.iteritems():
			item = QTableWidgetItem(sensor["name"])
			item.setTextAlignment(Qt.AlignCenter)
			item.setBackground(brushB)
			item.setForeground(brushF)
			
			item.setFont(font)
			tableView.setItem(row, 0, item)
			
			item = QTableWidgetItem(sensor["ubicacion"])
			item.setTextAlignment(Qt.AlignCenter)
			item.setBackground(brushB)
			item.setForeground(brushF)
			item.setFont(font)
			tableView.setItem(row, 1, item)
			
			item = QTableWidgetItem(sensor["source"])
			item.setTextAlignment(Qt.AlignCenter)
			item.setBackground(brushB)
			item.setForeground(brushF)
			item.setFont(font)
			tableView.setItem(row, 2, item)
			
			item = QTableWidgetItem(sensor["units"])
			item.setTextAlignment(Qt.AlignCenter)
			item.setBackground(brushB)
			item.setForeground(brushF)
			item.setFont(font)
			tableView.setItem(row, 3, item)
			
			row = row + 1
		tableView.resizeColumnsToContents()
			
	def updateTableRows(self):
		NROW = 4
		brushB = QBrush(QColor(250, 250, 250))
		brushF = QBrush(Qt.black)
		brushB.setStyle(Qt.SolidPattern)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(10)
		font.setBold(True)
		row = NROW
		for sensor in sensors["sensores"]:
			if sensor["source"]=="EMON":
				f = requests.get(sensor["url"])	
				#analyze response
				delayed = 7
				item = QTableWidgetItem(str(delayed))
				item.setTextAlignment(Qt.AlignCenter)
				item.setBackground(brushB)
				item.setForeground(brushF)
				item.setFont(font)
				self.tableWidget.setItem(row, 4, item)
			
				item = QTableWidgetItem(f.text[1:-1])
				item.setTextAlignment(Qt.AlignCenter)
				item.setBackground(brushB)
				item.setForeground(brushF)
				item.setFont(font)
				self.tableWidget.setItem(row, 5, item)
				
			row = row + 1
	
	@Slot(str)
	def slotCountDown(self, ident):
		brushB = QBrush(QColor(250, 250, 250))
		brushF = QBrush(Qt.darkGreen)
		brushB.setStyle(Qt.SolidPattern)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(10)
		font.setBold(True)
		
		sensors[ident]["countdown"] = sensors[ident]["countdown"] + 1
		item = QTableWidgetItem(str(sensors[ident]["countdown"]))
		item.setTextAlignment(Qt.AlignCenter)
		item.setBackground(brushB)
		item.setForeground(brushF)
		item.setFont(font)
		self.tableWidget.setItem( sensors[ident]["row"], 4, item)
		
	@Slot(str,dict)
	def slotFromReader(self, ident, value ):
		brushB = QBrush(QColor(250, 250, 250))
		brushF = QBrush(Qt.black)
		brushB.setStyle(Qt.SolidPattern)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(10)
		font.setBold(True)
			
		item = QTableWidgetItem(value)
		item.setTextAlignment(Qt.AlignCenter)
		item.setBackground(brushB)
		item.setForeground(brushF)
		item.setFont(font)
		print sensors
		print ident
		self.tableWidget.setItem(sensors[ident]["row"], 5, item)
				
	
	def compute(self):
		pass
				

class Timer(QThread):
	timeout = Signal( str )
	def __init__(self, period, ident):
		super(Timer,self).__init__()
		self.ident = ident
		self.period = period
		
	def run(self):
		time.sleep(self.period*0.001)
		self.timeout.emit(self.ident)

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
		print "thread"
		conn = yield rdb.connect(host="azure",port=28015,db="cyber")
		feed = yield rdb.table(self.table).changes().run(conn)
		while (yield feed.fetch_next()):
			change = yield feed.next()
			count = 0
			self.signalVal.emit(self.ident, change["new_val"]["temp"][0:4])
		
	def run(self):
		ioloop.IOLoop.current().start()
		
class RESTReader(QThread):
	signalVal = Signal( str, dict )
	def __init__(self, ident, url, period):
		super(RESTReader, self).__init__()
		self.ident = ident
		self.url = url
		self.period = period
		
	def run(self):
		f = requests.get(self.url)	
		#sensors[self.ident]["countdown"] = 0
		self.signalVal.emit( self.ident, f.text[1:-1] )
		time.sleep( float(self.period) )
		
		
if __name__ == '__main__':
	app = QApplication(sys.argv)
	mainWin = MainWindow()
	ret = app.exec_()
	sys.exit( ret )	
    
