from PySide.QtSvg import *


class Svg():
    def __init__(self, parent):
        self.render = QSvgWidget()
        self.render.setParent()
        render.load('svg/informatica.svg')
