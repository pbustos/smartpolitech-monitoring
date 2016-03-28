from PySide.QtSvg import *
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtXml import *

docName = 'svg/informatica.svg'

class Svg():
	def __init__(self, parent, svgLayout):
		self.scene = QGraphicsScene()
		self.view = QGraphicsView(self.scene, parent)
		svgLayout.addWidget(self.view)
		#self.renderer = QSvgRenderer(docName)
		self.draw = QGraphicsSvgItem(docName)
		self.renderer = self.draw.renderer()
		self.scene.addItem(self.draw)
		#self.draw.setScale(0.7)
		self.draw.boundingRect().setSize(parent.size())
		self.view.show()

		doc = QDomDocument('informatica')
		file = QFile(docName)
		if not file.open(QIODevice.ReadOnly):
			return
		if not doc.setContent(file):
			file.close()
			return
		file.close()

		# print out the element names of all elements that are direct children of the outermost element.
		docElem = doc.documentElement()
		l = doc.elementsByTagName("path")
		print "there are", l.length(), "path elements"
		# for i in range(l.length()):
		# 	if l.item(i).isElement():
		# 		print l.item(i).toElement().tagName()


		# n = docElem.firstChild()
		# while not n.isNull():
		# 	e = n.toElement() # try to convert the node to an element.
		# 	if not e.isNull():
		# 		print e.tagName() # the node really is an element.
		# 	n = n.nextSibling()
