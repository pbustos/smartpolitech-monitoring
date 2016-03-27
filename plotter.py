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
	def __init__(self, conn, sensors):
		super(QObject, self).__init__()
		self.conn = conn
		self.sensors = sensors
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

		self.dayData()

	def getPastData(self, delta):
			cur = rdb.table(self.sensors[CURRENT]["table"]).order_by("date").run(self.conn)
			x = []
			y = []
			icont = 0
			for d in cur:
				timeData = parser.parse(d["date"])
				if timeData > (dt.datetime.now(pytz.timezone('Europe/Madrid')) - delta):
					x.append(self.timestamp(timeData))
					y.append(float(d["sensors"][0]["value"]))
					icont += 1
			print "selected", icont
			self.curve.setData(x=x, y=y)
			self.plotDlg.totalLcd.display(icont)

	def timestamp(self, date):
		epoch = dt.datetime(1970, 1, 1, 0, 0, tzinfo=pytz.utc)
		return int((date - epoch).total_seconds() * 1e6)

	#
	# SLOTS
	#

	@Slot(object, object)
	def plotClicked(self, a, b):
		print "hol3", a, b

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
