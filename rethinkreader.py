#Reader for RethinkDB based sensors

from PySide.QtCore import *
import rethinkdb as rdb
from tornado import ioloop, gen

class RDBReader(QThread):
	signalVal = Signal(str)
	def __init__(self, connData, sensors):
		super(RDBReader, self).__init__()
		self.sensors = sensors
		rdb.set_loop_type('tornado')
		self.conn = rdb.connect(host=connData["host"], port=connData["port"], db=connData["db"], auth_key=connData["auth_key"])

	def addTable(self, ident, table):
		ioloop.IOLoop.current().add_callback(self.changes, self.conn, ident, table, self.sensors)

	@gen.coroutine
	def changes(self, conn, ident, table, sensors):
		connection = yield conn
		feed = yield rdb.table(table).changes().run(connection)
		while (yield feed.fetch_next()):
			change = yield feed.next()
			sensors[ident]["updated"] = 0
			sensors[ident]["canales"] = change["new_val"]["sensors"]
			self.signalVal.emit(ident)

	def run(self):
		ioloop.IOLoop.current().start()

