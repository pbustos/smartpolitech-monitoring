#Timer for RethinkDB based sensors

from PySide.QtCore import *

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

