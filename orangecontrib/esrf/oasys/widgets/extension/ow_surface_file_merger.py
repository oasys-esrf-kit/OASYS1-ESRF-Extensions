import numpy
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication, QMessageBox

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui

from oasys.util.oasys_objects import OasysPreProcessorData, OasysErrorProfileData, OasysSurfaceData

import oasys.util.oasys_util as OU

from silx.gui.plot import Plot2D
from PyQt5 import QtGui

from scipy import interpolate

class OWSurfaceFileReader(OWWidget):
    name = "ESRF Surface File Merger"  # TODO: remove ESRF when replacing oasys merger
    id = "surface_file_merger"
    description = "Surface File Merger"
    icon = "icons/surface_merger.png"
    author = "Luca Rebuffi and Manuel Sanchez del Rio"
    maintainer_email = "lrebuffi@anl.gov"
    priority = 5
    category = ""
    keywords = ["surface_file_mberger"]

    inputs = [("Surface Data #1", object, "set_input_1"),
              ("Surface Data #2", object, "set_input_2"),
              ]

    outputs = [{"name": "PreProcessor_Data",
                "type": OasysPreProcessorData,
                "doc": "PreProcessor Data",
                "id": "PreProcessor_Data"},
               {"name": "Surface_Data",
                "type": OasysSurfaceData,
                "doc": "Surface Data",
                "id": "Surface_Data"}]


    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 618

    xx = None
    yy = None
    zz = None

    xx_1 = None
    yy_1 = None
    zz_1 = None

    xx_2 = None
    yy_2 = None
    zz_2 = None

    surface_data = None
    preprocessor_data = None


    surface_file_name = Setting('merged_surface.hdf5')
    unmatched_surfaces = Setting(1)
    interpolated_length_x = Setting(0.1)
    interpolated_length_y = Setting(1.0)
    interpolated_nx = Setting(500)
    interpolated_ny = Setting(50)
    factor_surface1 = Setting(1.0)
    factor_surface2 = Setting(1.0)

    def __init__(self):
        super().__init__()

        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width() * 0.05),
                               round(geom.height() * 0.05),
                               round(min(geom.width() * 0.98, self.MAX_WIDTH)),
                               round(min(geom.height() * 0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Merge", callback=self.compute)

        button.setFixedHeight(45)

        input_box = oasysgui.widgetBox(self.controlArea, "Input", addSpace=True, orientation="vertical",
                                         height=self.TABS_AREA_HEIGHT)


        #
        oasysgui.lineEdit(input_box, self, "factor_surface1",
                     label="Factor for surface1", addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)

        oasysgui.lineEdit(input_box, self, "factor_surface2",
                     label="Factor for surface2", addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)


        #
        gui.comboBox(input_box, self, "unmatched_surfaces", label="if unmatched surfaces", labelWidth=250,
                                     items=["Do nothing (error)", "Use intersection grid", "Customized grid"],
                                     sendSelectedValue=False, orientation="horizontal",
                                     callback=self.set_visible)



        self.interpoleted_id = oasysgui.widgetBox(input_box, "", addSpace=True, orientation="vertical")

        oasysgui.lineEdit(self.interpoleted_id, self, "interpolated_length_x",
                     label="Interpolated width (X)", addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)

        oasysgui.lineEdit(self.interpoleted_id, self, "interpolated_length_y",
                     label="Interpolated length (Y)", addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)

        oasysgui.lineEdit(self.interpoleted_id, self, "interpolated_nx",
                     label="Interpolated points along with (X)", addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)

        oasysgui.lineEdit(self.interpoleted_id, self, "interpolated_ny",
                     label="Interpolated points along with (Y)", addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)


        # file
        input_box_l = oasysgui.widgetBox(input_box, "", addSpace=True, orientation="horizontal", height=self.TABS_AREA_HEIGHT)

        self.le_surface_file_name = oasysgui.lineEdit(input_box_l, self, "surface_file_name", "Surface File Name",
                                                        labelWidth=120, valueType=str, orientation="horizontal")

        gui.button(input_box_l, self, "...", callback=self.selectSurfaceFile)



        #
        # tabs results
        #
        tabs_setting = oasysgui.tabWidget(self.mainArea)

        self.tab_surface1 = oasysgui.createTabPage(tabs_setting, "Surface input 1")
        self.tab_surface2 = oasysgui.createTabPage(tabs_setting, "Surface input 2")
        self.tab_surfaceR = oasysgui.createTabPage(tabs_setting, "Surface Result")
        tab_output = oasysgui.createTabPage(tabs_setting, "Output")

        self.info_id = oasysgui.textArea(height=self.IMAGE_HEIGHT - 35)
        info_box = oasysgui.widgetBox(tab_output, "", addSpace=True, orientation="horizontal",
                                      height=self.IMAGE_HEIGHT - 20, width=self.IMAGE_WIDTH - 20)
        info_box.layout().addWidget(self.info_id)

        gui.rubber(self.mainArea)

        self.set_visible()

    def clean_widgets(self, surface_index):
        if surface_index == 1:
            layout = self.tab_surface1.layout()
        else:
            layout = self.tab_surface2.layout()
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        layout = self.tab_surfaceR.layout()
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        self.writeStdOut("", initialize=True)


    def set_input_1(self, data):
        self.writeStdOut("\nCalled set_input_1 with " + str(data))
        if data is None:
            self.xx_1 = None
            self.yy_1 = None
            self.zz_1 = None
            self.clean_widgets(1)
        else:
            if isinstance(data, OasysPreProcessorData):
                self.xx_1 = data.error_profile_data.surface_data.xx
                self.yy_1 = data.error_profile_data.surface_data.yy
                self.zz_1 = data.error_profile_data.surface_data.zz
                self.plot_surface1()
            elif isinstance(data, OasysSurfaceData):
                self.xx_1 = data.xx
                self.yy_1 = data.yy
                self.zz_1 = data.zz
                self.plot_surface1()
            else:
                QMessageBox.critical(self, "Error",
                                     "Data Type #1 not recognized",
                                     QMessageBox.Ok)


    def set_input_2(self, data):
        self.writeStdOut("\nCalled set_input_2 with " + str(data))
        if data is None:
            self.xx_2 = None
            self.yy_2 = None
            self.zz_2 = None
            self.clean_widgets(2)

        else:
            if isinstance(data, OasysPreProcessorData):
                self.xx_2 = data.error_profile_data.surface_data.xx
                self.yy_2 = data.error_profile_data.surface_data.yy
                self.zz_2 = data.error_profile_data.surface_data.zz
                self.plot_surface2()
            elif isinstance(data, OasysSurfaceData):
                self.xx_2 = data.xx
                self.yy_2 = data.yy
                self.zz_2 = data.zz
                self.plot_surface2()
            else:
                QMessageBox.critical(self, "Error",
                                     "Data Type #2 not recognized",
                                     QMessageBox.Ok)

    def set_visible(self):
        if self.unmatched_surfaces == 2:
            self.interpoleted_id.setVisible(True)
        else:
            self.interpoleted_id.setVisible(False)

    def writeStdOut(self, text="", initialize=False):
        cursor = self.info_id.textCursor()
        if initialize:
            self.info_id.setText(text)
        else:
            cursor.movePosition(QtGui.QTextCursor.End)
            cursor.insertText(text)

    def plot_data2D(self, data2D, dataX, dataY, tab_canvas, title="", xtitle=None, ytitle=None, vmax=None):

        layout = tab_canvas.layout()
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        if xtitle is None:
            xtitle = "X (%d pixels)" % dataX.size
        if ytitle is None:
            ytitle = "Y (%d pixels)" % dataY.size

        origin = (dataX[0], dataY[0])
        scale = (dataX[1] - dataX[0], dataY[1] - dataY[0])

        if vmax is None:
            colormap = {"name": "temperature", "normalization": "linear",
                        "autoscale": True, "vmin": 0, "vmax": 0, "colors": 256}
        else:
            colormap = {"name": "temperature", "normalization": "linear",
                        "autoscale": False, "vmin": 0, "vmax": vmax, "colors": 256}

        tmp = Plot2D()
        tmp.resetZoom()
        tmp.setXAxisAutoScale(True)
        tmp.setYAxisAutoScale(True)
        tmp.setGraphGrid(False)
        tmp.setKeepDataAspectRatio(True)
        tmp.yAxisInvertedAction.setVisible(False)
        tmp.setXAxisLogarithmic(False)
        tmp.setYAxisLogarithmic(False)
        tmp.getMaskAction().setVisible(False)
        tmp.getRoiAction().setVisible(False)
        tmp.getColormapAction().setVisible(True)
        tmp.setKeepDataAspectRatio(False)
        tmp.addImage(data2D,legend="1",scale=scale,origin=origin,colormap=colormap,replace=True)
        tmp.setActiveImage("1")
        tmp.setGraphXLabel(xtitle)
        tmp.setGraphYLabel(ytitle)
        tmp.setGraphTitle(title)

        layout.addWidget(tmp)

    def plot_surface1(self, vmax=None):
        self.plot_data2D(self.zz_1 * self.factor_surface1, self.xx_1, self.yy_1, self.tab_surface1,
                         vmax=vmax, title="input surface 1 * %g" % self.factor_surface1)

    def plot_surface2(self, vmax=None):
        self.plot_data2D(self.zz_2 * self.factor_surface2, self.xx_2, self.yy_2, self.tab_surface2,
                         vmax=vmax, title="input surface 2 * %g" % self.factor_surface2)


    def compute(self, plot_data=True):
        try:
            if not self.xx_1 is None and not self.xx_2 is None:
                xx_1 = self.xx_1
                yy_1 = self.yy_1
                zz_1 = self.zz_1

                xx_2 = self.xx_2
                yy_2 = self.yy_2
                zz_2 = self.zz_2

                self.writeStdOut("",initialize=True)
                self.writeStdOut("Surface 1 dimensions: X: %f (%d pixels), Y: %f (%d pixels)\n" %
                                 (numpy.abs(xx_1[-1]-xx_1[0]), xx_1.size, numpy.abs(yy_1[-1]-yy_1[0]), yy_1.size,), initialize=False)
                self.writeStdOut("Surface 2 dimensions: X: %f (%d pixels), Y: %f (%d pixels)\n" %
                                 (numpy.abs(xx_2[-1]-xx_2[0]), xx_2.size, numpy.abs(yy_2[-1]-yy_2[0]), yy_2.size,), initialize=False)

                if numpy.array_equal(xx_1,xx_2) and numpy.array_equal(yy_1,yy_2):
                    self.writeStdOut("Surface 1 and 2 grids do match\n", initialize=False)
                    match = 1
                else:
                    self.writeStdOut("Surface 1 and 2 grids DO NOT match\n", initialize=False)
                    match = 0


                if match:
                    xx = xx_2.copy()
                    yy = yy_2.copy()
                    zz = zz_2 * self.factor_surface2 + zz_1 * self.factor_surface1
                else:
                    if self.unmatched_surfaces == 0:
                        self.writeStdOut("Aborted \n", initialize=False)
                        raise ValueError("The two surfaces cannot be merged: dimensions or binning incompatible")
                    else:
                        if self.unmatched_surfaces == 1:
                            xx_min = numpy.max((xx_1[0], xx_2[0]))
                            xx_max = numpy.min((xx_1[-1], xx_2[-1]))
                            xx_n = numpy.min((xx_1.size, xx_2.size))
                            yy_min = numpy.max((yy_1[0], yy_2[0]))
                            yy_max = numpy.min((yy_1[-1], yy_2[-1]))
                            yy_n = numpy.min((yy_1.size, yy_2.size))
                            xx = numpy.linspace(xx_min, xx_max, xx_n)
                            yy = numpy.linspace(yy_min, yy_max, yy_n)
                        elif self.unmatched_surfaces == 2:
                            xx = numpy.linspace(-0.5 * self.interpolated_length_x,
                                                0.5 * self.interpolated_length_x,
                                                int(self.interpolated_nx))
                            yy = numpy.linspace(-0.5 * self.interpolated_length_y,
                                                0.5 * self.interpolated_length_y,
                                                int(self.interpolated_ny))


                        XX = numpy.outer(xx, numpy.ones_like(yy))
                        YY = numpy.outer(numpy.ones_like(xx), yy)
                        XX_1 = numpy.outer(xx_1, numpy.ones_like(yy_1))
                        YY_1 = numpy.outer(numpy.ones_like(xx_1), yy_1)
                        XX_2 = numpy.outer(xx_2, numpy.ones_like(yy_2))
                        YY_2 = numpy.outer(numpy.ones_like(xx_2), yy_2)
                        print(XX_1.shape, YY_1.shape, zz_1.shape, XX_2.shape, YY_2.shape, zz_2.shape, XX.shape, YY.shape)
                        zz_1i = interpolate.griddata(
                            (XX_1.flatten(), YY_1.flatten()),
                            (zz_1.T).flatten(),
                            (XX, YY), method='cubic', fill_value=0.0, rescale=True)
                        zz_2i = interpolate.griddata(
                            (XX_2.flatten(), YY_2.flatten()),
                            (zz_2.T).flatten(),
                            (XX, YY), method='cubic', fill_value=0.0, rescale=True)
                        zz = zz_1i.T * self.factor_surface1 + zz_2i.T * self.factor_surface2
                        print(zz.shape)

                self.writeStdOut("Result Surface dimensions: X: %f (%d pixels), Y: %f (%d pixels)\n" %
                                         (numpy.abs(xx[-1] - xx[0]), xx.size, numpy.abs(yy[-1] - yy[0]), yy.size,),
                                         initialize=False)

                self.writeStdOut("Surface 1\n   X from %f to %f\n   Y from %f to %f\n   Zmax %g\n   Zmax * factor: %g\n" %
                                         (xx_1[0], xx_1[-1], yy_1[0], yy_1[-1], zz_1.max(), zz_1.max() * self.factor_surface1),
                                         initialize=False)
                if match == 0:
                    self.writeStdOut("Surface 1 interpolated\n   X from %f to %f\n   Y from %f to %f\n   Zmax %g\n   Zmax * factor: %g\n" %
                                             (xx[0], xx[-1], yy[0], yy[-1], zz_1i.max(), zz_1i.max() * self.factor_surface1),
                                             initialize=False)
                self.writeStdOut("Surface 2\n   X from %f to %f\n   Y from %f to %f\n   Zmax %g\n   Zmax * factor: %g\n" %
                                         (xx_2[0], xx_2[-1], yy_2[0], yy_2[-1], zz_2.max(), zz_2.max() * self.factor_surface2),
                                         initialize=False)
                if match == 0:
                    self.writeStdOut("Surface 2 interpolated\n   X from %f to %f\n   Y from %f to %f\n   Zmax %g\n   Zmax * factor: %g\n" %
                                             (xx[0], xx[-1], yy[0], yy[-1], zz_2i.max(), zz_2i.max() * self.factor_surface2),
                                             initialize=False)
                self.writeStdOut("Surface Result\n   X from %f to %f\n   Y from %f to %f\n   Zmax: %g\n" %
                                         (xx[0], xx[-1], yy[0], yy[-1], zz.max()),
                                         initialize=False)
                        #...

                zmax = numpy.max( (zz_1.max() * self.factor_surface1, zz_2.max() * self.factor_surface2, zz.max() ))
                self.plot_surface1(vmax=zmax)
                self.plot_surface2(vmax=zmax)
                self.plot_data2D(zz,xx,yy,self.tab_surfaceR,vmax=zmax)


                if not (self.surface_file_name.endswith("hd5") or self.surface_file_name.endswith("hdf5") or self.surface_file_name.endswith("hdf")):
                    self.surface_file_name += ".hdf5"

                OU.write_surface_file(zz, xx, yy, self.surface_file_name)
                self.writeStdOut("File written to disk: %s \n" % self.surface_file_name, initialize=False)

                error_profile_x_dim = abs(xx[-1] - xx[0])
                error_profile_y_dim = abs(yy[-1] - yy[0])


                self.send("PreProcessor_Data", OasysPreProcessorData(error_profile_data=OasysErrorProfileData(surface_data=OasysSurfaceData(xx=xx,
                                                                                                                                            yy=yy,
                                                                                                                                            zz=zz,
                                                                                                                                            surface_data_file=self.surface_file_name),
                                                                                                              error_profile_x_dim=error_profile_x_dim,
                                                                                                              error_profile_y_dim=error_profile_y_dim)))
                self.send("Surface_Data", OasysSurfaceData(xx=xx,
                                                           yy=yy,
                                                           zz=zz,
                                                           surface_data_file=self.surface_file_name))

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception



    def selectSurfaceFile(self):
        self.le_surface_file_name.setText(oasysgui.selectFileFromDialog(self, self.surface_file_name, "Select Input File", file_extension_filter="HDF5 Files (*.hdf5)"))


if __name__ == "__main__":
    import sys

    def get_surface(nx=100, ny=200, Lx = 0.2, Ly = 2.0):
        xx1 = numpy.linspace(-0.5 * Lx, 0.5 * Lx, nx)
        yy1 = numpy.linspace(-0.5 * Ly, 0.5 * Ly, ny)
        XX1 = numpy.outer(xx1,numpy.ones_like(yy1))
        YY1 = numpy.outer(numpy.ones_like(xx1), yy1)
        ZZ1 = numpy.exp( - XX1 ** 2 / (2 * 0.01**2) ) * \
              numpy.exp(- YY1 ** 2 / (2 * 0.5 ** 2))
        zz1 = ZZ1.T

        error_profile_x_dim = abs(xx1[-1] - xx1[0])
        error_profile_y_dim = abs(yy1[-1] - yy1[0])

        input1 = OasysPreProcessorData(error_profile_data=OasysErrorProfileData(surface_data=OasysSurfaceData(xx=xx1,
                                                                                                              yy=yy1,
                                                                                                              zz=zz1,
                                                                                                              surface_data_file=""),
                                                                                error_profile_x_dim=error_profile_x_dim,
                                                                                error_profile_y_dim=error_profile_y_dim))
        return input1

    input1 = get_surface(Ly=2.0,Lx=0.2,ny=200,nx=100)
    input2 = get_surface(Ly=2.0,Lx=0.2,ny=200,nx=100)
    # input2 = get_surface(Ly=1.0,Lx=0.1,ny=100,nx=50)



    a = QApplication(sys.argv)
    ow = OWSurfaceFileReader()

    ow.set_input_1(input1)
    ow.set_input_2(input2)
    # ow.compute()


    ow.show()

    a.exec_()
    ow.saveSettings()
