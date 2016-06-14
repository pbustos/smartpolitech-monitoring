#Reader for RethinkDB based sensors

from PySide.QtCore import *
import rethinkdb as rdb
from tornado import ioloop, gen
import datetime as dt

class RDBReader(QThread):
	signalVal = Signal(str)
	def __init__(self, connData, sensors):
		super(RDBReader, self).__init__()
		self.sensors = sensors
		rdb.set_loop_type('tornado')
		#self.conn = rdb.connect(host=connData["host"], port=connData["port"], db=connData["db"], auth_key=connData["auth_key"])
		self.conn = rdb.connect(host=connData["host"], port=connData["port"], db=connData["db"])

	def addTable(self, ident):
		ioloop.IOLoop.current().add_callback(self.changes, self.conn, ident, self.sensors)

	@gen.coroutine
	def changes(self, conn, ident, sensors):
		connection = yield conn
		feed = yield rdb.table(ident).changes().run(connection)
		while (yield feed.fetch_next()):
			change = yield feed.next()
			sensors[ident]["updated"] = dt.timedelta(seconds=0)
			sensors[ident]["canales"] = list()
			#sensors[ident]["canales"] = change["new_val"]["data"]
			for k,v in change["new_val"]["data"].iteritems():
					sensors[ident]["canales"].append({"name": k, "value": v})
			self.signalVal.emit(ident)

	def run(self):
		ioloop.IOLoop.current().start()

