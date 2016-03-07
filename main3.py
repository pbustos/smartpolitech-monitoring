## Monitoring system for SmartPoliTech
##
import sys
import json
sys.path.append('/usr/local/lib/python2.7/site-packages')
import requests, json, time
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
import threading

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

		self.readFromDB()

		#read sensor's configuration file
		sensorFile = self.readJSONFile("sensors3.json")
		sensors = sensorFile["sensores"]
		r=4
		row=2   #para calcular el numero de filas de forma dinamica
		for name,s in sensors.iteritems():
			if s["source"] == "RETHINK":
				s["thread"] = RDBReader(str(name), s["table"])
				s["thread"].signalVal.connect(self.slotFromReader)
				s["timer"] = Timer(name, 1000)
				s["timer"].timeout.connect(self.slotCountDown)
				s["countdown"] = 0
				for i in range(0,len(s["canales"])):				
					s["row"+str(i)] = r
					r=r+1
					
					row=row + len(s["canales"]) +2 
				r=r+2
			
		
			if s["source"] == "EMONCMS":
				s["thread"] = RESTReader(name, s["url"], s["period"])
				s["thread"].signalVal.connect(self.slotFromReader)
				s["timer"] = Timer(name, 1000)
				s["timer"].timeout.connect(self.slotCountDown)
				s["countdown"] = 0
				s["row"] = r
				r = r+1
		
		#create UI table
		self.createTable(self.tableWidget,sensors)
		#self.setTableRows(sensors, self.tableWidget)
		
		self.show()
		
		#Start threads
		[ s["thread"].start() for s in sensors.values() ]
		[ s["timer"].start() for s in sensors.values() ]
	

	#read for RTDB devices
	def readFromDB(self):
		conn = rdb.connect(host="158.49.247.193",port=28015,db="SmartPoliTech",auth_key="smartpolitech2")
		devices = rdb.table("Dispositivos").run(conn)
		for device in devices:
			print device["description"], device["id"]


	def readJSONFile(self, fileName, imprimir = False):
		with open(fileName, 'r') as fileJson:
			data = json.load(fileJson)
                if imprimir == True:
                    pprint(data)
		return data

	def createTable(self, tableView,sensors):

		itera=2 #para iterar y numero de fila
		

		tableView.setRowCount(row);
		tableView.setColumnCount(6);
		tableView.horizontalHeader().hide()
		tableView.verticalHeader().hide()
		tableView.setWordWrap(True)
		tableView.setTextElideMode(Qt.ElideNone)
		tableView.setShowGrid(False)
		
		NROW = 1
		tableView.setSpan(NROW, 1, 1, tableView.columnCount())
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
		
		for name,sensor in sensors.iteritems():
			 
			NROW = itera
			tableView.setSpan(NROW, 0, 1, tableView.columnCount())
			item = QTableWidgetItem(sensor["name"])
			item.setTextAlignment(Qt.AlignLeft)
			brush = QBrush(QColor(164, 125, 144))
			brush.setStyle(Qt.SolidPattern)
			item.setBackground(brush)
			font = QFont()
			font.setFamily(u"DejaVu Sans")
			font.setPointSize(12)
			item.setFont(font)
			tableView.setItem(NROW,0, item)
			itera=itera+1

			NROW = itera
			head=("Name", "Location", "Source", "Units", "Updated", "Value")
			for j in range(len(head)):
				item = QTableWidgetItem(head[j])
				item.setTextAlignment(Qt.AlignCenter)
				brush = QBrush(Qt.darkGreen)
				brush.setStyle(Qt.SolidPattern)
				item.setBackground(brush)
				font = QFont()
				font.setFamily(u"DejaVu Sans")
				font.setPointSize(11)
				font.setBold(True)
				item.setFont(font)
				tableView.setItem(NROW, j, item)
			itera=itera+1

			

			self.setTableRows(sensor, tableView,itera)
			itera=itera+len(sensor["canales"])					
			tableView.horizontalHeader().setStretchLastSection(True)
			tableView.horizontalHeader().setResizeMode(QHeaderView.Stretch);
			
			
			


		
	def setTableRows(self, sensor, tableView,itera):
		NROW = itera
		brushB = QBrush(QColor(250, 250, 250))
		brushF = QBrush(Qt.black)
		brushB.setStyle(Qt.SolidPattern)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(10)
		font.setBold(True)
		row = NROW
		

		for j in range(0,len(sensor["canales"])):
			
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
		
			print sensor["canales"][0]["name"]
			item = QTableWidgetItem(sensor["canales"][j]["name"])  
			item.setTextAlignment(Qt.AlignCenter)
			item.setBackground(brushB)
			item.setForeground(brushF)
		
			item.setFont(font)
			tableView.setItem(row, 0, item)				

			item = QTableWidgetItem(sensor["canales"][j]["units"]) 
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
		sensors[ident]["countdown"] += 1
		for i in range(0,len(sensors[ident]["canales"])):
				 
			item = QTableWidgetItem(str(sensors[ident]["countdown"]))
			item.setTextAlignment(Qt.AlignCenter)
			item.setBackground(brushB)
			item.setForeground(brushF)
			item.setFont(font)
			
			self.tableWidget.setItem(sensors[ident]["row"+str(i)], 4, item)
		
	@Slot(str,dict)
	def slotFromReader(self, ident, value ):
		
		brushB = QBrush(QColor(250, 250, 250))
		brushF = QBrush(Qt.black)
		brushB.setStyle(Qt.SolidPattern)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(10)
		font.setBold(True)
		value=json.loads(value)
		print  "valor "+ value["valor"]
		
		item = QTableWidgetItem((value["valor"]))
		item.setTextAlignment(Qt.AlignCenter)
		item.setBackground(brushB)
		item.setForeground(brushF)
		item.setFont(font)
		self.tableWidget.setItem(sensors[ident]["row"+str(value["iter"])], 5, item)		#inserta en la ultima columna
			

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
			print "en thread", sensors[self.ident]["countdown"]
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
