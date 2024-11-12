#
# Important notice: for the moment we are using wofryimpl stuff, that should be removed if this is installed
# in OASYS1-SYNED.
#


import os, sys
import numpy

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QWidget, QLabel, QSizePolicy
from PyQt5.QtGui import QTextCursor,QFont, QPalette, QColor, QPainter, QBrush, QPen, QPixmap
from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtGui

from silx.gui.plot import Plot2D

import orangecanvas.resources as resources

from orangewidget import gui, widget
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from oasys.util.oasys_objects import OasysSurfaceData
from oasys.util.oasys_util import write_surface_file
from oasys.util.oasys_util import EmittingStream

from wofryimpl.beamline.optical_elements.refractors.lens import WOLens
from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D

# from orangecontrib.esrf.shadow.util.conics_from_factory_parameters import ellipsoid, hyperboloid, \
#     paraboloid_focusing, paraboloid_collimating



class OWLensSurface(OWWidget):
    name = "Lens surface creator"
    id = "Lens surface creator"
    description = "Lens surface generator"
    icon = "icons/lens_surface.png"
    author = "M Sanchez del Rio"
    maintainer_email = "srio@esrf.eu"
    priority = 20
    category = ""
    keywords = ["preprocessor", "surface", "lens"]

    outputs = [{"name": "Surface Data",
                "type": OasysSurfaceData,
                "doc": "Surface Data",
                "id": "Surface Data"},
               ]

    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 650

    #
    # variable list
    #

    lens_profile = Setting(0)

    number_of_curved_surfaces = Setting(2)
    lens_radius = Setting(200e-6)

    surface_shape = Setting(0)
    two_d_lens = Setting(0)
    wall_thickness = Setting(10e-6)
    n_lenses = Setting(1)
    aperture_shape = Setting(0)
    aperture_dimension_v = Setting(1e-3)
    aperture_dimension_h = Setting(1e-3)
    shape = Setting(1)
    radius = Setting(100e-6)

    nx = Setting(101)
    ny = Setting(101)
    semilength_x = Setting(0.001)
    semilength_y = Setting(0.001)
    filename_h5 = Setting("lens.h5")

    #
    #
    #

    tab=[]
    usage_path = os.path.join(resources.package_dirname("orangecontrib.esrf.syned.widgets.extension") , "misc", "lens_surface_usage.png")

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

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)


        tab_calc = oasysgui.createTabPage(tabs_setting, "Calculate")
        tab_usa = oasysgui.createTabPage(tabs_setting, "Use of the Widget")

        #
        #-------------------- calculate
        #

        button = gui.button(tab_calc, self, "Calculate", callback=self.calculate)



        #
        # lens box
        #
        out_calc = oasysgui.widgetBox(tab_calc, "Lens Settings", addSpace=True, orientation="vertical")
        self.draw_lens_settings_box(id=out_calc)
        gui.separator(out_calc)

        #
        # --------------- MESH
        #
        out_calc = oasysgui.widgetBox(tab_calc, "Mesh Parameters", addSpace=True, orientation="vertical")

        oasysgui.lineEdit(out_calc, self, "ny", "Points in Y (tangential)",
                           labelWidth=300, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(out_calc, self, "nx", "Points in X (sagittal)",
                           labelWidth=300, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(out_calc, self, "semilength_y", "Half length Y [m]",
                           labelWidth=300, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(out_calc, self, "semilength_x", "Half length X [m]",
                           labelWidth=300, valueType=float, orientation="horizontal")


        gui.separator(out_calc)

        #
        # --------------- FILE
        #
        out_file = oasysgui.widgetBox(tab_calc, "Output hdf5 file", addSpace=True, orientation="vertical")

        oasysgui.lineEdit(out_file , self, "filename_h5", "Output filename *.h5",
                           labelWidth=150, valueType=str, orientation="horizontal")

        gui.separator(out_file)

        #
        #-------------------- Use
        #

        tab_usa.setStyleSheet("background-color: white;")

        usage_box = oasysgui.widgetBox(tab_usa, "", addSpace=True, orientation="horizontal")

        label = QLabel("")
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setPixmap(QPixmap(self.usage_path))

        usage_box.layout().addWidget(label)

        #
        #
        #
        gui.rubber(self.controlArea)
        self.initializeTabs()
        self.set_visible()
        gui.rubber(self.mainArea)

    def initializeTabs(self):
        self.tabs = oasysgui.tabWidget(self.mainArea)

        self.tab = [oasysgui.createTabPage(self.tabs, "Results"),
                    oasysgui.createTabPage(self.tabs, "Output"),
        ]

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

        self.plot_canvas = [None] * len(self.tab)

        # tab index 1
        self.profileInfo = oasysgui.textArea()
        profile_box = oasysgui.widgetBox(self.tab[1], "", addSpace=True, orientation="horizontal")
        profile_box.layout().addWidget(self.profileInfo)

        for index in range(len(self.tab)):
            try:
                self.tab[index].layout().addWidget(self.plot_canvas[index])
            except:
                pass
        self.tabs.setCurrentIndex(0)

    def draw_lens_settings_box(self, id):

        gui.comboBox(id, self, "surface_shape", label="Lens shape", labelWidth=350,
                     items=["Plane", "Parabolic"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_visible)

        oasysgui.lineEdit(id, self, "wall_thickness", "(t_wall) Wall thickness [m]", labelWidth=260, valueType=float, orientation="horizontal")




        self.lens_id = oasysgui.widgetBox(id, orientation="vertical", height=None)

        gui.comboBox(self.lens_id, self, "number_of_curved_surfaces", label="Number of curved surfaces", labelWidth=350,
                     items=["0 (parallel plate)", "1 (plano-concave)", "2 (bi-concave)"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_visible)


        oasysgui.lineEdit(self.lens_id, self, "lens_radius", "(R) radius of curvature [m]", labelWidth=260,
                          valueType=float, orientation="horizontal",)

        gui.comboBox(self.lens_id, self, "two_d_lens", label="Focusing in", labelWidth=350,
                     items=["2D", "1D (tangential)", "1D (sagittal)"], sendSelectedValue=False, orientation="horizontal")


        gui.comboBox(self.lens_id, self, "aperture_shape", label="Aperture shape", labelWidth=350,
                     items=["Circular", "Rectangular"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_visible)

        oasysgui.lineEdit(self.lens_id, self, "aperture_dimension_v", "Aperture V (height/diameter) [m]", labelWidth=260,
                          valueType=float, orientation="horizontal",)

        self.lens_width_id = oasysgui.widgetBox(id, orientation="vertical", height=None)
        oasysgui.lineEdit(self.lens_width_id, self, "aperture_dimension_h", "Aperture H (width) [m]", labelWidth=260,
                          valueType=float, orientation="horizontal",)

        oasysgui.lineEdit(self.lens_id, self, "n_lenses", "Number of lenses",
                          labelWidth=300, valueType=int, orientation="horizontal")

    def set_visible(self):
        self.lens_id.setVisible(self.surface_shape == 1)
        self.lens_width_id.setVisible(self.aperture_shape == 1)

    def check_fields(self):
        self.nx = congruence.checkStrictlyPositiveNumber(self.nx, "Points X")
        self.ny = congruence.checkStrictlyPositiveNumber(self.ny, "Points Y")
        self.semilength_x = congruence.checkStrictlyPositiveNumber(self.semilength_x, "Half length X")
        self.semilength_y = congruence.checkStrictlyPositiveNumber(self.semilength_y, "Half length Y")
        # self.source_ow = congruence.checkNumber(self.source_oe, "Distance source-mirror")
        # self.oe_image = congruence.checkNumber(self.oe_image, "Distance mirror-image")
        # self.radius = congruence.checkStrictlyPositiveNumber(self.radius, "radius of curvature at tip")
        # self.n_lenses = congruence.checkStrictlyPositiveNumber(self.n_lenses, "Number of lenses")
        # self.thickness = congruence.checkNumber(self.thickness, "Thickness")

    def writeStdOut(self, text="", initialize=False):
        cursor = self.profileInfo.textCursor()
        if initialize:
            self.profileInfo.setText(text)
        else:
            cursor.movePosition(QtGui.QTextCursor.End)
            cursor.insertText(text)

    def calculate(self):
        self.writeStdOut(initialize=True)
        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        self.check_fields()

        x = numpy.linspace(-self.semilength_x, self.semilength_x, self.nx)
        y = numpy.linspace(-self.semilength_y, self.semilength_y, self.ny)

        if self.surface_shape == 0: # plane
            Z = numpy.ones((self.nx, self.ny)) * self.wall_thickness
            title = "Cumulated lens profile [m]"

        else: # parabolic
            optical_element = WOLens.create_from_keywords(
                name='Real Lens 2D',
                number_of_curved_surfaces=self.number_of_curved_surfaces,
                two_d_lens=self.two_d_lens,
                surface_shape=0,
                wall_thickness=self.wall_thickness,
                lens_radius=self.lens_radius,
                material='', # self.get_material_name(index=self.material),
                refraction_index_delta=0.0, # self.refraction_index_delta,
                att_coefficient=0.0, # self.att_coefficient,
                n_lenses=self.n_lenses,
                aperture_shape=self.aperture_shape,
                aperture_dimension_h=self.aperture_dimension_h,
                aperture_dimension_v=self.aperture_dimension_v,)

            title = "Cumulated lens profile [m] R:%6.3f $\mu$m" % (1e6 * self.radius)

            output_wavefront = GenericWavefront2D.initialize_wavefront_from_range(x_min=-self.semilength_x, x_max=self.semilength_x,
                                                                                  y_min=-self.semilength_y, y_max=self.semilength_y,
                                                                                  number_of_points=(self.nx, self.ny))

            xx, yy, Z = optical_element.get_surface_thickness_mesh(output_wavefront)



        #
        # display results
        #
        write_surface_file(Z.T, x, y, self.filename_h5, overwrite=True)
        print("\nHDF5 file %s written to disk." % self.filename_h5)

        self.plot_data2D(Z, x, y, self.tab[0],
                         title=title,
                         xtitle="x (sagittal) [m] (%d pixels)" % x.size,
                         ytitle="y (tangential) [m] (%d pixels)" % y.size)

        self.send("Surface Data",
                  OasysSurfaceData(xx=x,
                                   yy=y,
                                   zz=Z.T,
                                   surface_data_file=self.filename_h5))


    def plot_data2D(self, data2D, dataX, dataY, canvas_widget_id, title="title", xtitle="X", ytitle="Y"):
        try:
            canvas_widget_id.layout().removeItem(canvas_widget_id.layout().itemAt(0))
        except:
            pass

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

        canvas_widget_id.layout().addWidget(tmp)



if __name__ == "__main__":

    app = QApplication(sys.argv)
    w = OWLensSurface()
    w.show()
    app.exec()
    w.saveSettings()

    # x = numpy.linspace(-10e-3, 10e-3, 101)
    # y = numpy.linspace(-100e-3, 100e-3, 1001)
    #
    # Z, X, Y =  diaboloid_exact_point_to_segment(p=29.3,q=19.53,theta=4.5e-3,x=x,y=y,)
    # Z0, X, Y = diaboloid_approximated_point_to_segment(p=29.3, q=19.53, theta=4.5e-3, x=x, y=y, detrend=1)
    #
    # from srxraylib.plot.gol import plot_image, plot
    # plot_image((Z0) * 1e-6, x * 1e-3, y * 1e-3, xtitle="X/mm", ytitle="Y/mm", title="Z (approximated)/um", aspect="auto")
    # plot_image((Z) * 1e-6, x * 1e-3, y * 1e-3, xtitle="X/mm", ytitle="Y/mm", title="Z (exact)/um", aspect="auto")
    # plot_image((Z-Z0) * 1e-6, x * 1e-3, y * 1e-3, xtitle="X/mm", ytitle="Y/mm", title="Z (exact)-Z(approximated)/um", aspect="auto")
    #
    # ZZ0 = Z0[:, y.size//2]
    # ZZ  = Z[:, y.size//2]
    # plot(x, ZZ0 - ZZ0.min(),
    #      x,  ZZ - ZZ.min(),
    #      xtitle="X", ytitle="Z", legend=["Z (approximated)","Z (exact)"])
    #
    # ZZ0 = Z0[x.size//2, :]
    # ZZ  = Z[x.size//2, :]
    # plot(y,  ZZ0 - ZZ0.min(),
    #      y,   ZZ - ZZ.min(),
    #      xtitle="Y", ytitle="Z", legend=["Z (approximated)","Z (exact)"])