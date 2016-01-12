## Monitoring system for SmartPoliTech
##

import cv2, sys, requests, json
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

class MainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		self.setupUi(self)
		
		#read sensor's configuration file
		self.sensors = self.readJSONFile("sensors.json")
		
		#create UI table
		self.createTable(self.sensors, self.tableWidget)
		self.setTableRows(self.sensors, self.tableWidget)
		
		self.show()

		#connect to Rethink server
	
		#rethink = rdb.connect(host="azure",port=28015,db="cyber") #.repl()
		
		reader = Reader()
		reader.signalVal.connect(self.slotFromReader)
		reader.start()
			
		#start timers	
		timerS.timeout.connect( self.updateTableRows ) 
		#timer.timeout.connect( self.compute ) 
		timer.start(70)
		timerS.start(1000)
		
		
	def readJSONFile(self, fileName, imprimir = False):
		with open(fileName, 'r') as fileJson:
			data = json.load(fileJson)
                if imprimir == True:
                    pprint(data)
		return data

	def createTable(self, sensors, tableView):
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
		for sensor in sensors["sensores"]:
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
		for sensor in self.sensors["sensores"]:
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
	
	@Slot(dict)
	def slotFromReader(self, value):
		NROW = 5
		brushB = QBrush(QColor(250, 250, 250))
		brushF = QBrush(Qt.black)
		brushB.setStyle(Qt.SolidPattern)
		font = QFont()
		font.setFamily(u"DejaVu Sans")
		font.setPointSize(10)
		font.setBold(True)
		row = NROW
		
		delayed = 7
		item = QTableWidgetItem(str(delayed))
		item.setTextAlignment(Qt.AlignCenter)
		item.setBackground(brushB)
		item.setForeground(brushF)
		item.setFont(font)
		self.tableWidget.setItem(row, 4, item)
			
		#print float(value["temp"])
		item = QTableWidgetItem(value["temp"])
		item.setTextAlignment(Qt.AlignCenter)
		item.setBackground(brushB)
		item.setForeground(brushF)
		item.setFont(font)
		self.tableWidget.setItem(row, 5, item)
				
	
	def compute(self):
		pass
				

class Reader(QThread):
	signalVal = Signal( dict )
	def __init__(self):
		super(Reader, self).__init__()
		ioloop.IOLoop.current().add_callback(self.print_changes)
		
	@gen.coroutine
	def print_changes(self):
		print "thread"
		rdb.set_loop_type('tornado')
		conn = yield rdb.connect(host="azure",port=28015,db="cyber")
		feed = yield rdb.table("devSalon").changes().run(conn)
		while (yield feed.fetch_next()):
			change = yield feed.next()
			print(change)	
			self.signalVal.emit(change["new_val"])
		
	def run(self):
		ioloop.IOLoop.current().start()
		
if __name__ == '__main__':
	app = QApplication(sys.argv)
	timer = QTimer()
	timerS = QTimer()
	mainWin = MainWindow()
	ret = app.exec_()
	sys.exit( ret )	
    

