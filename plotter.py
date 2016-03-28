# -*- coding: utf-8 -*-

from subprocess import call
from PySide.QtGui import *
from PySide.QtCore import *
import datetime as dt
import rethinkdb as rdb
import pyqtgraph as pg
import pytz
from dateutil import parser
call("pyside-uic plotdlg.ui > ui_plotdlg.py", shell=True)
from ui_plotdlg import Ui_PlotDlg


CURRENT = "024020cc-28df-4c48-aa93-52e7193c9570"

class Plotter(QObject):
	def __init__(self, conn, sensor, numCanal):
		super(QObject, self).__init__()
		self.conn = conn
		self.sensor = sensor
		self.numCanal = numCanal
		pg.setConfigOptions(antialias=True)
		self.dlg = QDialog()
		self.plotDlg = Ui_PlotDlg()
		self.plotDlg.setupUi(self.dlg)
		self.dlg.setWindowModality(Qt.ApplicationModal)
		self.plot = pg.PlotWidget(parent=None, background='default', labels={'left': ('Temperature', 'ºC')},
		                          axisItems={'bottom': TimeAxisItem(orientation='bottom')})
		self.plot.setObjectName("plot")
		self.plotDlg.verticalLayout.addWidget(self.plot)
		self.dlg.show()
		self.curve = self.plot.plot()
		self.curve.curve.setClickable(True)
		self.plot.showGrid(x=True, y=True, alpha=0.5)

		self.plotDlg.dayButton.clicked.connect(self.dayData)
		self.plotDlg.hourButton.clicked.connect(self.hourData)
		self.plotDlg.weekButton.clicked.connect(self.weekData)
		self.plotDlg.monthButton.clicked.connect(self.monthData)
		self.plotDlg.yearButton.clicked.connect(self.yearData)
		self.plot.sigRangeChanged.connect(self.plotClicked)
		self.plot.scene().sigMouseMoved.connect(self.mouseMoved)
		#self.cpoint = pg.CurvePoint(self.curve)
		#self.plot.addItem(self.cpoint)
		self.label = pg.TextItem(anchor=(0, 0))
		#self.label.setParentItem(self.cpoint)
		self.plot.addItem(self.label)
		self.dayData()

	def getPastData(self, delta):
			cur = rdb.table(self.sensor["table"]).order_by("date").run(self.conn)
			if self.sensor["canales"][self.numCanal]["name"] in ('temp', 'temperatura', 'temperature'):
				self.plot.setLabel('left', text='Temperatura', units='ºC')
			if self.sensor["canales"][self.numCanal]["name"] in ('hum', 'humedad', 'humidity'):
				self.plot.setLabel('left', text='Humidity', units='%')
			if self.sensor["canales"][self.numCanal]["name"] in ('volt', 'vbat', 'bat'):
				self.plot.setLabel('left', text='Volts', units='V')

			x = []
			self.y = []
			icont = 0
			for d in cur:
				timeData = parser.parse(d["date"])
				if timeData > (dt.datetime.now(pytz.timezone('Europe/Madrid')) - delta):
					x.append(self.timestamp(timeData))
					self.y.append(float(d["sensors"][self.numCanal]["value"]))
					icont += 1
			print "selected", icont
			self.curve.setData(x=x, y=self.y)
			self.plotDlg.totalLcd.display(icont)


	def timestamp(self, date):
		epoch = dt.datetime(1970, 1, 1, 0, 0, tzinfo=pytz.utc)
		return int((date - epoch).total_seconds() * 1e6)

	#
	# SLOTS
	#

	@Slot(list)
	def mouseMoved(self, pos):
		p = self.plot.plotItem.vb.mapSceneToView(pos)
		## We need to find curve coordinates for p
		self.label.setText('%0.2f' % p.y())
		self.label.setPos(p)

	@Slot(object, object)
	def plotClicked(self, a, b):
		#print "hol3", a, b
		pass

	def dayData(self):
		self.getPastData(dt.timedelta(days=1))

	def hourData(self):
		self.getPastData(dt.timedelta(hours=1))

	def weekData(self):
		self.getPastData(dt.timedelta(weeks=1))

	def monthData(self):
		self.getPastData(dt.timedelta(weeks=4))

	def yearData(self):
		self.getPastData(dt.timedelta(weeks=52))


class TimeAxisItem(pg.AxisItem):
	def __init__(self, *args, **kwargs):
		pg.AxisItem.__init__(self, *args, **kwargs)

	def int2dt(self,ts):
		return dt.datetime.utcfromtimestamp(float(ts) / 1e6)

	def tickStrings(self, values, scale, spacing):
		return [self.int2dt(value).strftime("%d %H:%M:%S") for value in values]
