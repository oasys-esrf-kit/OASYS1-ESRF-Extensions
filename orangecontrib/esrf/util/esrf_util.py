__author__ = 'labx'

import sys, os, numpy, platform
import orangecanvas.resources as resources
from PyQt5 import QtGui, QtCore

try:
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from matplotlib import figure as matfig
    import pylab
except ImportError:
    print(sys.exc_info()[1])
    pass


import xraylib

from oasys.widgets import gui

class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

class XoppyPlot:

    @classmethod
    def plot_histo(cls, plot_window, x, y, title, xtitle, ytitle, color='blue', replace=True):
        matplotlib.rcParams['axes.formatter.useoffset']='False'
        plot_window.addCurve(x, y, title, symbol='', color=color, xlabel=xtitle, ylabel=ytitle, replace=replace) #'+', '^', ','
        if not xtitle is None: plot_window.setGraphXLabel(xtitle)
        if not ytitle is None: plot_window.setGraphYLabel(ytitle)
        if not title is None: plot_window.setGraphTitle(title)

        # plot_window.setDrawModeEnabled(True, 'rectangle')
        plot_window.setInteractiveMode('zoom',color='orange')
        plot_window.resetZoom()
        plot_window.replot()

        plot_window.setActiveCurve(title)
