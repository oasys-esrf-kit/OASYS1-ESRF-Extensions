

# class ALSFiniteElementReader(ALSShadowWidget):

import os, sys
import numpy

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QRect, Qt

from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtGui import QPixmap

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets.widget import OWWidget
from oasys.util.oasys_objects import OasysSurfaceData

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from oasys.util.oasys_util import EmittingStream

from orangecontrib.esrf.syned.util.FEA_File import FEA_File
import orangecanvas.resources as resources
from silx.gui.plot import Plot2D



class FiniteElementReader(OWWidget): #ow_automatic_element.AutomaticElement):

    name = "Finite Element reader"
    description = "Syned: Finite Element reader"
    icon = "icons/hhlo.png"
    maintainer = "M. Sanchez del Rio"
    maintainer_email = "srio@esrf.eu"
    priority = 1
    category = "Data File Tools"
    keywords = ["data", "file", "load", "read", "FEA", "Finite Elements"]

    outputs = [{"name": "Surface Data",
                "type": OasysSurfaceData,
                "doc": "Surface Data",
                "id": "Surface Data"},
               {"name": "DABAM 1D Profile",
                "type": numpy.ndarray,
                "doc": "numpy.ndarray",
                "id": "numpy.ndarray"},
               ]

    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 650

    file_in = Setting("")
    file_in_type = Setting(0)
    file_factor_x = Setting(1.0)
    file_factor_y = Setting(1.0)
    file_factor_z = Setting(1.0)

    file_in_skiprows = Setting(0)
    replicate_raw_data_flag = Setting(0)  # 0=None, 1=axis0, 2=axis1, 3=both axis
    # raw_render_option = Setting(2)

    file_out = Setting("") # copied from file_in and changed extension to h5
    n_axis_0 = Setting(801) #301)
    n_axis_1 = Setting(500) #51)

    detrended = Setting(0)
    detrended_fit_range = Setting(1.0)
    reset_height_method = Setting(2)
    remove_nan = Setting(0)
    invert_axes_names = Setting(1)
    extract_profile1D = Setting(0)
    coordinate_profile1D = Setting(0.0)
    sigma_flag = Setting(0)
    sigma_axis0 = Setting(10)
    sigma_axis1 = Setting(10)

    fea_file_object = FEA_File()

    usage_path = os.path.join(resources.package_dirname("orangecontrib.esrf.syned.widgets.extension") , "misc", "finite_element_usage.png")

    def __init__(self, show_automatic_box=False):
        # super().__init__(show_automatic_box=show_automatic_box)
        super().__init__()

        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width() * 0.05),
                               round(geom.height() * 0.05),
                               round(min(geom.width() * 0.98, self.MAX_WIDTH)),
                               round(min(geom.height() * 0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        #
        # tabs input panel
        #
        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)


        tab_calc = oasysgui.createTabPage(tabs_setting, "Calculate")
        tab_out = oasysgui.createTabPage(tabs_setting, "Output")
        tab_usa = oasysgui.createTabPage(tabs_setting, "Use of the Widget")
        #
        # tabs for results
        #
        self.tabs_setting = oasysgui.tabWidget(self.mainArea)
        self.tabs_setting.setFixedHeight(self.IMAGE_HEIGHT + 5)
        self.tabs_setting.setFixedWidth(self.IMAGE_WIDTH)
        self.create_tabs_results()



        #
        # parameters panel
        #

        gui.button(tab_calc, self, "Calculate Interpolated File", callback=self.calculate) #, height=45)

        # gui.separator(tab_calc, height=20)

        #
        #
        data_file_box = oasysgui.widgetBox(tab_calc, "Data file", addSpace=True,
                                         orientation="vertical",)


        figure_box = oasysgui.widgetBox(data_file_box, "", addSpace=True, orientation="horizontal") #width=550, height=50)
        self.le_beam_file_name = oasysgui.lineEdit(figure_box, self, "file_in", "FEA File:",
                                                    labelWidth=90, valueType=str, orientation="horizontal")
        gui.button(figure_box, self, "...", callback=self.selectFile)


        data_file_box2 = oasysgui.widgetBox(data_file_box, "", addSpace=True, orientation="horizontal",)

        gui.comboBox(data_file_box2, self, "file_in_type", label="File content", labelWidth=220,
                     items=["ALS cols: A X Y Z DX DY DZ","ESRF cols: X,Y,Z,DX,DY,DZ",],
                     sendSelectedValue=False, orientation="horizontal")


        oasysgui.lineEdit(data_file_box2, self, "file_in_skiprows", "Skip rows:", labelWidth=300, valueType=int,
                          orientation="horizontal")

        data_file_expansion_box = oasysgui.widgetBox(data_file_box, "", addSpace=False,
                                                     orientation="horizontal")
        oasysgui.widgetLabel(data_file_expansion_box, label="Expansion factor")
        oasysgui.lineEdit(data_file_expansion_box, self, "file_factor_x", "X", labelWidth=10, controlWidth=35,
                          valueType=float, orientation="horizontal")
        oasysgui.lineEdit(data_file_expansion_box, self, "file_factor_y", "Y", labelWidth=10, controlWidth=35,
                          valueType=float, orientation="horizontal")
        oasysgui.lineEdit(data_file_expansion_box, self, "file_factor_z", "Z", labelWidth=10, controlWidth=35,
                          valueType=float, orientation="horizontal")


        gui.comboBox(data_file_box, self, "replicate_raw_data_flag", label="Replicate raw data", labelWidth=220,
                     items=["No","Along axis 0","Along axis 1","Along axes 0 and 1"],
                     sendSelectedValue=False, orientation="horizontal")

        #
        # interpolation
        #
        interpolation_box = oasysgui.widgetBox(tab_calc, "Interpolation", addSpace=True,
                                         orientation="vertical")


        interpolation_box2 = oasysgui.widgetBox(interpolation_box, "", addSpace=False,
                                         orientation="horizontal")

        oasysgui.lineEdit(interpolation_box2, self, "n_axis_0", "Pixels (axis 0)",
                          labelWidth=260, valueType=int, orientation="horizontal")

        oasysgui.lineEdit(interpolation_box2, self, "n_axis_1", "pixels (axis 1)",
                          labelWidth=260, valueType=int, orientation="horizontal")

        gui.comboBox(interpolation_box, self, "remove_nan", label="Remove interp NaN", labelWidth=220,
                     items=["No", "Yes (replace by min height)", "Yes (replace by zero)"],
                     sendSelectedValue=False, orientation="horizontal")




        #
        # post process
        #
        postprocess_box = oasysgui.widgetBox(tab_calc, "PostProcess", addSpace=True,
                                         orientation="vertical")



        gui.comboBox(postprocess_box, self, "detrended", label="Detrend profile", labelWidth=220,
                     items=["None", "Straight line (along axis 0)", "Straight line (along axis 1)",
                            "Best circle (along axis 0)", "Best circle (along axis 1)"],
                     sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        self.detrended_fit_range_id = oasysgui.widgetBox(postprocess_box, "", addSpace=True,
                                         orientation="vertical",)
        oasysgui.lineEdit(self.detrended_fit_range_id, self, "detrended_fit_range", "detrend fit up to [m]",
                          labelWidth=220, valueType=float, orientation="horizontal")

        gui.comboBox(postprocess_box, self, "reset_height_method", label="Reset zero height", labelWidth=220,
                     items=["No", "To height minimum", "To center"],
                     sendSelectedValue=False, orientation="horizontal")


        gui.comboBox(postprocess_box, self, "sigma_flag", label="Gaussian filter", labelWidth=220,
                     items=["None", "Yes"],
                     sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        self.sigma_id = oasysgui.widgetBox(postprocess_box, "", addSpace=True, orientation="horizontal",)


        oasysgui.widgetLabel(self.sigma_id, label="Gaussian sigma [pixels] axis",labelWidth=350)
        oasysgui.lineEdit(self.sigma_id, self, "sigma_axis0", "0:",
                          labelWidth=0, controlWidth=50, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.sigma_id, self, "sigma_axis1", "1:",
                          labelWidth=0, controlWidth=50, valueType=float, orientation="horizontal")




        gui.comboBox(postprocess_box, self, "invert_axes_names", label="Invert axes", labelWidth=120,
                     items=['No','Yes'],
                     sendSelectedValue=False, orientation="horizontal")

        #
        # output tab
        #

        profile1D_box = oasysgui.widgetBox(tab_out, "1D profile", addSpace=True,
                                         orientation="vertical",)
        gui.comboBox(profile1D_box, self, "extract_profile1D", label="Extract and send 1D profile", labelWidth=220,
                     items=["horizontal", "vertical"],
                     sendSelectedValue=False, orientation="horizontal")

        oasysgui.lineEdit(profile1D_box, self, "coordinate_profile1D", "At coordinate [m]:", labelWidth=260, valueType=float,
                          orientation="horizontal")

        gui.separator(tab_out, height=20)

        file_info_box = oasysgui.widgetBox(tab_out, "Info", addSpace=True,
                                         orientation="vertical",)

        tmp = oasysgui.lineEdit(file_info_box, self, "file_out", "Output file name",
                          labelWidth=150, valueType=str, orientation="horizontal")
        tmp.setEnabled(False)

        #
        # usage
        #
        tab_usa.setStyleSheet("background-color: white;")

        usage_box = oasysgui.widgetBox(tab_usa, "", addSpace=True, orientation="horizontal")

        label = QLabel("")
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setPixmap(QPixmap(self.usage_path))

        usage_box.layout().addWidget(label)

        self.set_visible()

    def set_visible(self):
        if self.detrended == 0:
            self.detrended_fit_range_id.setVisible(False)
        else:
            self.detrended_fit_range_id.setVisible(True)

        if self.sigma_flag == 0:
            self.sigma_id.setVisible(False)
        else:
            self.sigma_id.setVisible(True)

    def create_tabs_results(self):

        tabs_setting = self.tabs_setting
        tmp = oasysgui.createTabPage(tabs_setting, "Result")
        self.result_id = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.result_id.setFixedHeight(self.IMAGE_HEIGHT - 30)
        self.result_id.setFixedWidth(self.IMAGE_WIDTH - 20)

        tmp = oasysgui.createTabPage(tabs_setting, "Interpolation")
        self.interpolation_id = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.interpolation_id.setFixedHeight(self.IMAGE_HEIGHT - 30)
        self.interpolation_id.setFixedWidth(self.IMAGE_WIDTH - 20)

        tmp = oasysgui.createTabPage(tabs_setting, "Triangulation")
        self.triangulation_id = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.triangulation_id.setFixedHeight(self.IMAGE_HEIGHT - 30)
        self.triangulation_id.setFixedWidth(self.IMAGE_WIDTH - 20)

        tmp = oasysgui.createTabPage(tabs_setting, "Raw Data")
        self.rawdata_id = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.rawdata_id.setFixedHeight(self.IMAGE_HEIGHT - 30)
        self.rawdata_id.setFixedWidth(self.IMAGE_WIDTH - 20)

        tmp = oasysgui.createTabPage(tabs_setting, "1D profile")
        self.profile1D_id = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.profile1D_id.setFixedHeight(self.IMAGE_HEIGHT - 30)
        self.profile1D_id.setFixedWidth(self.IMAGE_WIDTH - 20)

        tmp = oasysgui.createTabPage(tabs_setting, "1D slope")
        self.slope1D_id = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.slope1D_id.setFixedHeight(self.IMAGE_HEIGHT - 30)
        self.slope1D_id.setFixedWidth(self.IMAGE_WIDTH - 20)

        #
        tmp = oasysgui.createTabPage(tabs_setting, "Output")
        self.info_id = oasysgui.textArea(height=self.IMAGE_HEIGHT - 35)
        info_box = oasysgui.widgetBox(tmp, "", addSpace=True, orientation="horizontal",
                                      height=self.IMAGE_HEIGHT - 20, width=self.IMAGE_WIDTH - 20)
        info_box.layout().addWidget(self.info_id)

    def set_input_file(self,filename):
        self.le_beam_file_name.setText(filename)

    def selectFile(self):
        filename = oasysgui.selectFileFromDialog(self,
                previous_file_path=self.file_in, message="Open FEA Raw ASCII File",
                start_directory=".", file_extension_filter="*.*")

        self.le_beam_file_name.setText(filename)
        self.set_file_out()

    def load_raw_data(self):
        self.fea_file_object = FEA_File()
        self.fea_file_object.set_filename(self.file_in)

        self.fea_file_object.load_multicolumn_file(skiprows=self.file_in_skiprows,
                                                   file_in_type=self.file_in_type,
                                                   factorX=self.file_factor_x,
                                                   factorY=self.file_factor_y,
                                                   factorZ=self.file_factor_z)

        self.fea_file_object.replicate_raw_data(self.replicate_raw_data_flag)

    def writeStdOut(self, text="", initialize=False):
        cursor = self.info_id.textCursor()
        if initialize:
            self.info_id.setText(text)
        else:
            cursor.movePosition(QtGui.QTextCursor.End)
            cursor.insertText(text)

    def set_file_out(self):
        file_out = os.path.splitext(self.file_in)[0]+'.h5'
        # if self.file_out[0:4] == "http":
        #     self.file_out = "tmp.h5" # self.file_out.split(os.sep)[-1]
        # print(">>>>>>>>>>>>>>>>>>>",self.file_out)

        if file_out[0:4] == "http":
            file_out = file_out.split(os.sep)[-1]

        self.file_out = file_out

    def calculate(self):
        self.writeStdOut(initialize=True)

        # sys.stdout = EmittingStream(textWritten=self.writeStdOut)
        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        self.load_raw_data()

        self.fea_file_object.triangulate()

        # add 3 pixels to match requested pixels after edge removal
        self.fea_file_object.interpolate(self.n_axis_0 + 3, self.n_axis_1 + 3, remove_nan=self.remove_nan)

        if self.fea_file_object.does_interpolated_have_nan():
            self.fea_file_object.remove_borders_in_interpolated_data()

        if self.sigma_flag == 1:
            self.fea_file_object.gaussian_filter(sigma_axis0=self.sigma_axis0,sigma_axis1=self.sigma_axis1)

        if self.detrended == 0:
            pass
        elif self.detrended == 1:
            self.fea_file_object.detrend_straight_line(axis=0, fitting_domain_ratio=self.detrended_fit_range)
        elif self.detrended == 2:
            self.fea_file_object.detrend_straight_line(axis=1, fitting_domain_ratio=self.detrended_fit_range)
        elif self.detrended == 3:
            self.fea_file_object.detrend_best_circle(axis=0, fitting_domain_ratio=self.detrended_fit_range)
        elif self.detrended == 4:
            self.fea_file_object.detrend_best_circle(axis=1, fitting_domain_ratio=self.detrended_fit_range)

        if self.reset_height_method == 0:
            pass
        elif self.reset_height_method == 1:
            self.fea_file_object.reset_height_to_minimum()
        elif self.reset_height_method == 2:
            self.fea_file_object.reset_height_to_central_value()

        self.set_file_out()
        self.fea_file_object.write_h5_surface(filename=self.file_out, invert_axes_names=self.invert_axes_names)

        print("File %s written to disk.\n" % self.file_out)

        self.plot_and_send_results()


    def plot_and_send_results(self):
        #
        # result
        #
        if self.invert_axes_names:
            self.plot_data2D(self.fea_file_object.Z_INTERPOLATED,
                           self.fea_file_object.x_interpolated,
                           self.fea_file_object.y_interpolated,self.result_id,
                       title="file: %s, axes names INVERTED from ANSYS"%self.file_in,
                       xtitle="Y [m] (%d pixels, max:%f)"%(self.fea_file_object.x_interpolated.size,
                                                       self.fea_file_object.x_interpolated.max()),
                       ytitle="X [m] (%d pixels, max:%f)"%(self.fea_file_object.y_interpolated.size,
                                                       self.fea_file_object.y_interpolated.max()) )
        else:
            self.plot_data2D(self.fea_file_object.Z_INTERPOLATED,
                           self.fea_file_object.x_interpolated,
                           self.fea_file_object.y_interpolated,self.result_id,
                       title="file: %s, axes as in ANSYS"%self.file_in,
                       xtitle="X [m] (%d pixels, max:%f)"%(self.fea_file_object.x_interpolated.size,
                                                       self.fea_file_object.x_interpolated.max()),
                       ytitle="Y [m] (%d pixels, max:%f)"%(self.fea_file_object.y_interpolated.size,
                                                       self.fea_file_object.y_interpolated.max()) )

        #
        # interpolation plot
        #
        self.interpolation_id.layout().removeItem(self.interpolation_id.layout().itemAt(1))
        self.interpolation_id.layout().removeItem(self.interpolation_id.layout().itemAt(0))

        f = self.fea_file_object.plot_interpolated(show=0)
        figure_canvas = FigureCanvasQTAgg(f)
        toolbar = NavigationToolbar(figure_canvas, self)

        self.interpolation_id.layout().addWidget(toolbar)
        self.interpolation_id.layout().addWidget(figure_canvas)


        #
        # triangulation plot
        #
        self.triangulation_id.layout().removeItem(self.triangulation_id.layout().itemAt(1))
        self.triangulation_id.layout().removeItem(self.triangulation_id.layout().itemAt(0))

        f = self.fea_file_object.plot_triangulation(show=0)
        figure_canvas = FigureCanvasQTAgg(f)
        toolbar = NavigationToolbar(figure_canvas, self)

        self.triangulation_id.layout().addWidget(toolbar)
        self.triangulation_id.layout().addWidget(figure_canvas)

        #
        # raw data
        #
        self.rawdata_id.layout().removeItem(self.rawdata_id.layout().itemAt(1))
        self.rawdata_id.layout().removeItem(self.rawdata_id.layout().itemAt(0))

        xs, ys, zs = self.fea_file_object.get_deformed()

        xs *= 1e3
        ys *= 1e3
        zs *= 1e6

        fig = Figure()
        self.axis = fig.add_subplot(111, projection='3d')

        # For each set of style and range settings, plot n random points in the box
        # defined by x in [23, 32], y in [0, 100], z in [zlow, zhigh].
        # for m, zlow, zhigh in [('o', -50, -25), ('^', -30, -5)]:
        for m, zlow, zhigh in [('o', zs.min(), zs.max())]:
            self.axis.scatter(xs, ys, zs, marker=m)

        self.axis.set_xlabel('X [mm]')
        self.axis.set_ylabel('Y [mm]')
        self.axis.set_zlabel('Z [um]')


        figure_canvas = FigureCanvasQTAgg(fig)
        toolbar = NavigationToolbar(figure_canvas, self)

        self.rawdata_id.layout().addWidget(toolbar)
        self.rawdata_id.layout().addWidget(figure_canvas)

        self.axis.mouse_init()

        #
        # result
        #

        mesh = self.fea_file_object.Z_INTERPOLATED
        mesh_shape = mesh.shape
        x = self.fea_file_object.x_interpolated
        y = self.fea_file_object.y_interpolated

        if self.extract_profile1D == 0:
            abscissas = x
            perp_abscissas = y
            index0 = numpy.argwhere(perp_abscissas >= self.coordinate_profile1D)
            try:
                index0 = index0[0][0]
            except:
                index0 = -1
            profile1D = mesh[:, index0]
            if self.invert_axes_names:
                title = "profile at X[%d] = %f" % (index0, perp_abscissas[index0])
                titleS = "slope at X[%d] = %f" % (index0, perp_abscissas[index0])
                xtitle = "Y [m] "
            else:
                title = "profile at Y[%d] = %f" % (index0, perp_abscissas[index0])
                titleS = "profile at Y[%d] = %f" % (index0, perp_abscissas[index0])
                xtitle = "X [m] "
            self.plot_data1D(abscissas, 1e6*profile1D, self.profile1D_id, title=title, xtitle=xtitle, ytitle="Z [um] ")
            self.plot_data1D(abscissas, 1e6*numpy.gradient(profile1D,abscissas), self.slope1D_id, title=titleS, xtitle=xtitle, ytitle="Z' [urad]")
        else:
            abscissas = y
            perp_abscissas = x
            index0 = numpy.argwhere(perp_abscissas >= self.coordinate_profile1D)
            try:
                index0 = index0[0][0]
            except:
                index0 = -1
            profile1D = mesh[index0, :]
            if self.invert_axes_names:
                title = "profile at Y[%d] = %f" % (index0, perp_abscissas[index0])
                titleS = "slopes at Y[%d] = %f" % (index0, perp_abscissas[index0])
                xtitle = "X [m] "
            else:
                title = "profile at X[%d] = %f" % (index0, perp_abscissas[index0])
                titleS = "slopes at X[%d] = %f" % (index0, perp_abscissas[index0])
                xtitle = "Y [m] "
            self.plot_data1D(abscissas, profile1D, self.profile1D_id, title=title, xtitle=xtitle, ytitle="Z [m] ")
            self.plot_data1D(abscissas, numpy.gradient(profile1D,abscissas), self.slope1D_id, title=titleS, xtitle=xtitle, ytitle="Z'")

        if self.invert_axes_names:
            self.send("Surface Data",
                      OasysSurfaceData(xx=self.fea_file_object.y_interpolated,
                                       yy=self.fea_file_object.x_interpolated,
                                       zz=self.fea_file_object.Z_INTERPOLATED,
                                       surface_data_file=self.file_out))
        else:
            self.send("Surface Data",
                      OasysSurfaceData(xx=self.fea_file_object.x_interpolated,
                                       yy=self.fea_file_object.y_interpolated,
                                       zz=self.fea_file_object.Z_INTERPOLATED.T,
                                       surface_data_file=self.file_out))

        dabam_profile = numpy.zeros((profile1D.size, 2))
        dabam_profile[:, 0] = abscissas
        dabam_profile[:, 1] = profile1D
        self.send("DABAM 1D Profile", dabam_profile)



    def plot_data2D(self, data2D, dataX, dataY, tabs_canvas_index, title="title", xtitle="X",ytitle="Y"):


        tabs_canvas_index.layout().removeItem(tabs_canvas_index.layout().itemAt(0))

        origin = (dataX[0], dataY[0])
        scale = (dataX[1] - dataX[0], dataY[1] - dataY[0])

        colormap = {"name": "temperature", "normalization": "linear",
                    "autoscale": True, "vmin": 0, "vmax": 0, "colors": 256}

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
        tmp.addImage(data2D.T,legend="1",scale=scale,origin=origin,colormap=colormap,replace=True)
        tmp.setActiveImage("1")
        tmp.setGraphXLabel(xtitle)
        tmp.setGraphYLabel(ytitle)
        tmp.setGraphTitle(title)
        tabs_canvas_index.layout().addWidget(tmp)

    def plot_data1D(self, dataX, dataY, tabs_canvas_index, title="", xtitle="", ytitle=""):

        tabs_canvas_index.layout().removeItem(tabs_canvas_index.layout().itemAt(0))

        tmp = oasysgui.plotWindow()
        tmp.addCurve(dataX, dataY)
        tmp.resetZoom()
        tmp.setXAxisAutoScale(True)
        tmp.setYAxisAutoScale(True)
        tmp.setGraphGrid(False)
        tmp.setXAxisLogarithmic(False)
        tmp.setYAxisLogarithmic(False)
        tmp.setGraphXLabel(xtitle)
        tmp.setGraphYLabel(ytitle)
        tmp.setGraphTitle(title)

        tabs_canvas_index.layout().addWidget(tmp)


if __name__ == "__main__":
    import sys



    a = QApplication(sys.argv)
    ow = FiniteElementReader()

    # ALS
    # ow.set_input_file("/users/srio/Oasys/s4.txt")
    # ow.file_in_type = 0
    # ow.replicate_raw_data_flag = 0
    # ESRF
    # ow.set_input_file("/users/srio/Oasys/ANSYS/ID03-DMM-LC3-E20.25keV-th0.245deg-Wc8mm.out")
    ow.set_input_file("https://raw.githubusercontent.com/oasys-esrf-kit/OasysWorkspaces/master/ANSYS/ID03-DMM-LC3-E20.25keV-th0.245deg-Wc8mm.out")
    ow.file_in_type = 1
    ow.file_in_skiprows = 9
    ow.replicate_raw_data_flag = 1
    ow.file_factor_x = 1e-3
    ow.file_factor_y = 1e-3
    ow.file_factor_z = 1e-3


    ow.show()
    a.exec_()
    ow.saveSettings()


    from srxraylib.plot.gol import plot_image, set_qt, plot
    # import os
    #
    # import numpy
    # example_file = "https://raw.githubusercontent.com/oasys-esrf-kit/OasysWorkspaces/master/ANSYS/ID03-DMM-LC3-E20.25keV-th0.245deg-Wc8mm.out"
    #
    # node = numpy.loadtxt(example_file, skiprows=9, delimiter=',', dtype=numpy.float64)
    # print(">>>",node.shape)
    #

    # o1 = FEA_File.process_file(example_file, n_axis_0=301, n_axis_1=51,
    #              filename_out=example_file+".h5", invert_axes_names=True,
    #              detrend=False, reset_height_method=0, skiprows=9, file_in_type=1, do_plot=True)



    # o1 = FEA_File.process_file("73water_side_cooled_notches_best_LH.txt", n_axis_0=1001, n_axis_1=101,
    #              filename_out="/home/manuel/Oasys/water_side_cooled_notches_best_LH.h5", invert_axes_names=True,
    #              detrend=True, reset_height_method=2,
    #              replicate_raw_data_flag=3,do_plot=False)

    # o1 = FEA_File.process_file("73water_side_cooled_notches_best_LV.txt", n_axis_0=1001, n_axis_1=101,
    #              filename_out="/home/manuel/Oasys/water_side_cooled_notches_best_LV.h5", invert_axes_names=True,
    #              detrend=False, reset_height_method=0,
    #              replicate_raw_data_flag=3,do_plot=False)

    #
    # o1.plot_triangulation()
    # o1.plot_interpolated()
    # o1.plot_surface_image()