
from oasys.widgets import gui as oasysgui
from silx.gui.plot import Plot2D


def plot_data2D(data2D, dataX, dataY, title="", xtitle="", ytitle=""):
    origin = (dataX[0], dataY[0])
    scale = (dataX[1] - dataX[0], dataY[1] - dataY[0])

    colormap = {"name": "temperature", "normalization": "linear", "autoscale": True, "vmin": 0, "vmax": 0,
                "colors": 256}

    plot_canvas = Plot2D()
    plot_canvas.resetZoom()
    plot_canvas.setXAxisAutoScale(True)
    plot_canvas.setYAxisAutoScale(True)
    plot_canvas.setGraphGrid(False)
    plot_canvas.setKeepDataAspectRatio(True)
    plot_canvas.yAxisInvertedAction.setVisible(False)
    plot_canvas.setXAxisLogarithmic(False)
    plot_canvas.setYAxisLogarithmic(False)
    plot_canvas.getMaskAction().setVisible(False)
    plot_canvas.getRoiAction().setVisible(False)
    plot_canvas.getColormapAction().setVisible(True)
    plot_canvas.setKeepDataAspectRatio(False)
    #
    #
    #
    plot_canvas.addImage(data2D.T,
                         legend="",
                         scale=scale,
                         origin=origin,
                         colormap=colormap,
                         replace=True)
    plot_canvas.setActiveImage("")
    plot_canvas.setGraphXLabel(xtitle)
    plot_canvas.setGraphYLabel(ytitle)
    plot_canvas.setGraphTitle(title)
    # try:
    #     image_box.layout().removeItem(image_box.layout().itemAt(0))
    # except:
    #     pass
    # image_box.layout().addWidget(plot_canvas)
    return plot_canvas


def plot_data1D(x, y, x2=None, y2=None,
                title="", xtitle="", ytitle="",
                log_x=False, log_y=False, color='blue', replace=True, control=False,
                xrange=None, yrange=None, symbol=''):



    plot_widget_id = oasysgui.plotWindow(parent=None,
                                         backend=None,
                                         resetzoom=True,
                                         autoScale=False,
                                         logScale=True,
                                         grid=True,
                                         curveStyle=True,
                                         colormap=False,
                                         aspectRatio=False,
                                         yInverted=False,
                                         copy=True,
                                         save=True,
                                         print_=True,
                                         control=control,
                                         position=True,
                                         roi=False,
                                         mask=False,
                                         fit=False)


    plot_widget_id.setDefaultPlotLines(True)
    plot_widget_id.setActiveCurveColor(color='blue')
    plot_widget_id.setGraphXLabel(xtitle)
    plot_widget_id.setGraphYLabel(ytitle)


    plot_widget_id.addCurve(x, y, title, symbol=symbol, color=color, xlabel=xtitle, ylabel=ytitle, replace=replace)  # '+', '^', ','
    if x2 is not None and y2 is not None:
        plot_widget_id.addCurve(x2, y2)


    if not xtitle is None: plot_widget_id.setGraphXLabel(xtitle)
    if not ytitle is None: plot_widget_id.setGraphYLabel(ytitle)
    if not title is None:  plot_widget_id.setGraphTitle(title)

    plot_widget_id.resetZoom()
    plot_widget_id.replot()
    plot_widget_id.setActiveCurve(title)


    plot_widget_id.setXAxisLogarithmic(log_x)
    plot_widget_id.setYAxisLogarithmic(log_y)

    print(">>>>>>>>>>>>>>>>>>>>>>>", yrange)
    if xrange is not None:
        plot_widget_id.setGraphXLimits(xrange[0] ,xrange[1])
    if yrange is not None:
        plot_widget_id.setGraphYLimits(yrange[0] ,yrange[1])

    print(">>>>>>>>>>>>>>>>>>>>>>>",yrange)
    # if min(y) < 0:
    #     if log_y:
    #         plot_widget_id.setGraphYLimits(min(y ) *1.2, max(y ) *1.2)
    #     else:
    #         plot_widget_id.setGraphYLimits(min(y ) *1.01, max(y ) *1.01)
    # else:
    #     if log_y:
    #         plot_widget_id.setGraphYLimits(min(y), max(y ) *1.2)
    #     else:
    #         plot_widget_id.setGraphYLimits(min(y ) *0.99, max(y ) *1.01)

    return plot_widget_id

