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

from shadow4.optical_surfaces.s4_conic import S4Conic

from orangecontrib.esrf.shadow.util.conics_from_factory_parameters import ellipsoid, hyperboloid, \
    paraboloid_focusing, paraboloid_collimating

from orangecontrib.esrf.shadow.util.conics_from_factory_parameters import ken_ellipsoid, ken_hyperboloid, \
    ken_paraboloid_focusing, ken_paraboloid_collimating

from orangecontrib.esrf.shadow.util.conic_penelope import ellipsoid as p_ellipsoid
from orangecontrib.esrf.shadow.util.conic_penelope import paraboloid as p_paraboloid
from orangecontrib.esrf.shadow.util.conic_penelope import sphere as p_sphere
from orangecontrib.esrf.shadow.util.conic_penelope import hyperboloid as p_hyperboloid

# from orangecontrib.syned.util.diaboloid_tools import diaboloid_approximated_point_to_segment
# from orangecontrib.syned.util.diaboloid_tools import diaboloid_approximated_segment_to_point
# from orangecontrib.syned.util.diaboloid_tools import diaboloid_exact_point_to_segment
# from orangecontrib.syned.util.diaboloid_tools import diaboloid_exact_segment_to_point
# from orangecontrib.syned.util.diaboloid_tools import parabolic_cone_point_to_segment
# from orangecontrib.syned.util.diaboloid_tools import parabolic_cone_segment_to_point
# from orangecontrib.syned.util.diaboloid_tools import parabolic_cone_linearized_point_to_segment
# from orangecontrib.syned.util.diaboloid_tools import parabolic_cone_linearized_segment_to_point
# from orangecontrib.syned.util.diaboloid_tools import toroid_point_to_segment, toroid_segment_to_point

class OWConic(OWWidget):
    name = "Conic surface"
    id = "conic"
    description = "Conic surface generator"
    icon = "icons/conic.png"
    author = "M Sanchez del Rio"
    maintainer_email = "srio@esrf.eu"
    priority = 15
    category = ""
    keywords = ["preprocessor", "surface", "conic"]

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

    configuration = Setting(5)
    calculation_method = Setting(0)
    source_oe = Setting(3.0)
    oe_image = Setting(10.0)
    theta = Setting(0.003) # mrad
    ny = Setting(1001)
    nx = Setting(101)
    semilength_x = Setting(0.015)
    semilength_y = Setting(0.25)
    # detrend_toroid = Setting(0)
    filename_h5 = Setting("conic.h5")

    cylindrize = Setting(0)

    #
    #
    #

    tab=[]
    usage_path = os.path.join(resources.package_dirname("orangecontrib.esrf.syned.widgets.extension") , "misc", "conic_usage.png")

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

        out_calc = oasysgui.widgetBox(tab_calc, "Conic Surface Parameters", addSpace=True, orientation="vertical")

        gui.comboBox(out_calc, self, "configuration", label="Focusing configuration", labelWidth=300,
                     items=self.get_surface_list(),
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(out_calc, self, "calculation_method", label="calculation method", labelWidth=300,
                     items=["s4_conic", "penelope", "mathematica", "Ken"], sendSelectedValue=False, orientation="horizontal")


        oasysgui.lineEdit(out_calc, self, "source_oe", "distance source to mirror [m]",
                           labelWidth=300, valueType=float, orientation="horizontal")

        oasysgui.lineEdit(out_calc, self, "oe_image", "distance mirror to image [m]",
                           labelWidth=300, valueType=float, orientation="horizontal")

        oasysgui.lineEdit(out_calc, self, "theta", "grazing angle [rad]",
                           labelWidth=300, valueType=float, orientation="horizontal")


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

        #
        # --------------- MODIFICATIONS
        #
        out_calc = oasysgui.widgetBox(tab_calc, "Modify surface", addSpace=True, orientation="vertical")
        gui.comboBox(out_calc, self, "cylindrize", label="Cylindrize", labelWidth=300,
                     items=["No [default]", "Yes [meridional]", "Yes [sagittal]"], sendSelectedValue=False,
                     orientation="horizontal")

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
        gui.rubber(self.mainArea)

    def get_surface_list(self):
        return ["Plane",
                "Paraboloid (collimating)",
                "Paraboloid (focusing)",
                "Sphere",
                "Ellipsoid",
                "Hyperboloid",
                ]
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

    def check_fields(self):
        self.nx = congruence.checkStrictlyPositiveNumber(self.nx, "Points X")
        self.ny = congruence.checkStrictlyPositiveNumber(self.ny, "Points Y")
        self.theta = congruence.checkStrictlyPositiveNumber(self.theta, "Grazing angle")
        self.semilength_x = congruence.checkStrictlyPositiveNumber(self.semilength_x, "Half length X")
        self.semilength_y = congruence.checkStrictlyPositiveNumber(self.semilength_y, "Half length Y")
        self.source_ow = congruence.checkNumber(self.source_oe, "Distance source-mirror")
        self.oe_image = congruence.checkNumber(self.oe_image, "Distance mirror-image")

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

        X = numpy.outer(x, numpy.ones_like(y))
        Y = numpy.outer(numpy.ones_like(x), y)

        p = self.source_oe
        q = self.oe_image
        theta = self.theta
        print("Inputs: p=%g m, q=%g m, theta=%g rad: " % (p, q, theta))

        # "Plane",
        # "Paraboloid (collimating)",
        # "Paraboloid (focusing)",
        # "Sphere",
        # "Ellipsoid",
        # "Hyperboloid",

        mirror_txt = "Conic"
        if self.get_surface_list()[self.configuration] == "Plane": #
            print("Method=s4_conic(**fixed**)")
            s4 = S4Conic.initialize_as_plane()
        elif self.get_surface_list()[self.configuration] == "Paraboloid (collimating)":  #
            if self.calculation_method == 0:
                print("Method=s4_conic")
                s4 = S4Conic.initialize_as_paraboloid_from_focal_distances(self.source_oe, 1e10, self.theta,
                                                            cylindrical=0, cylangle=0.0, switch_convexity=0)
            elif self.calculation_method == 1:
                print("Method=penelope")
                ccc = p_paraboloid(ssour=self.source_oe, simag=1e10, theta_grazing=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc['ccc'])
            elif self.calculation_method == 2:
                print("Method=mathematica")
                ccc = paraboloid_collimating(p=self.source_oe, theta=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc)
            elif self.calculation_method == 3:
                print("Method=ken")
                ccc = ken_paraboloid_collimating(p=self.source_oe, theta=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc)
        elif self.get_surface_list()[self.configuration] == "Paraboloid (focusing)":  #
            if self.calculation_method == 0:
                print("Method=s4_conic")
                s4 = S4Conic.initialize_as_paraboloid_from_focal_distances(1e10, self.oe_image, self.theta,
                                                        cylindrical=0, cylangle=0.0, switch_convexity=0)
            elif self.calculation_method == 1:
                print("Method=penelope")
                ccc = p_paraboloid(ssour=1e10, simag=self.oe_image, theta_grazing=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc['ccc'])
            elif self.calculation_method == 2:
                print("Method=mathematica")
                ccc = paraboloid_focusing(q=self.oe_image, theta=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc)
            elif self.calculation_method == 3:
                print("Method=ken")
                ccc = ken_paraboloid_focusing(q=self.oe_image, theta=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc)
        elif self.get_surface_list()[self.configuration] == "Sphere":  #
            if self.calculation_method == 1:
                print("Method=penelope")
                ccc = p_sphere(ssour=self.source_oe, simag=self.oe_image, theta_grazing=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc['ccc'])
            else:
                print("Method=s4_conic(**fixed**)")
                s4 = S4Conic.initialize_as_sphere_from_focal_distances(self.source_oe, self.oe_image, self.theta,
                                                        cylindrical=0, cylangle=0.0, switch_convexity=0)
        elif self.get_surface_list()[self.configuration] == "Ellipsoid":  #
            if self.calculation_method == 0:
                print("Method=s4_conic")
                s4 = S4Conic.initialize_as_ellipsoid_from_focal_distances(self.source_oe, self.oe_image, self.theta,
                                                        cylindrical=0, cylangle=0.0, switch_convexity=0)
            elif self.calculation_method == 1:
                print("Method=penelope")
                ccc = p_ellipsoid(ssour=self.source_oe, simag=self.oe_image, theta_grazing=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc['ccc'])
            elif self.calculation_method == 2:
                print("Method=mathematica")
                ccc = ellipsoid(p=self.source_oe, q=self.oe_image, theta=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc)
            elif self.calculation_method == 3:
                print("Method=ken")
                ccc = ken_ellipsoid(p=self.source_oe, q=self.oe_image, theta=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc)
        elif self.get_surface_list()[self.configuration] == "Hyperboloid":  #
            if self.calculation_method == 0:
                print("Method=s4_conic")
                s4 = S4Conic.initialize_as_hyperboloid_from_focal_distances(self.source_oe, self.oe_image, self.theta,
                                                        cylindrical=0, cylangle=0.0, switch_convexity=0)
            elif self.calculation_method == 1:
                print("Method=penelope")
                ccc = p_hyperboloid(ssour=self.source_oe, simag=self.oe_image, theta_grazing=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc['ccc'])
            elif self.calculation_method == 2:
                print("Method=mathematica")
                ccc = hyperboloid(p=self.source_oe, q=self.oe_image, theta=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc)
            elif self.calculation_method == 3:
                print("Method=ken")
                ccc = ken_hyperboloid(p=self.source_oe, q=self.oe_image, theta=self.theta)
                s4 = S4Conic.initialize_from_coefficients(ccc)
        else:
            raise Exception("Not implemented")

        #
        # cyl?
        #
        if self.cylindrize == 0:
            pass
        elif self.cylindrize == 1:
            s4.set_cylindrical(0)
        elif self.cylindrize == 2:
            s4.set_cylindrical(numpy.pi/2)

        #
        # display coeffs
        #
        ccc = s4.get_coefficients()
        print("\n\n\nConic coefficients: ")
        for i in range(10):
            print("    ccc[%d] = %20.12g" % (i, ccc[i]))

        print("\nConic coefficients (normalized): ")
        for i in range(10):
            print("    ccc[%d] = %20.12g" % (i, ccc[i]/ccc[0]))

        #
        # numerical surface
        #

        Z = s4.height(y=Y, x=X, return_solution=0)

        write_surface_file(Z.T, x, y, self.filename_h5, overwrite=True)
        print("\nHDF5 file %s written to disk." % self.filename_h5)



        # Z -= Ztor
        #

        #
        #
        # if self.detrend_toroid == 0:
        #     Ztor = 0
        # elif self.detrend_toroid == 1:  # detrend toroid
        #     mirror_txt += " (sphere removed)"
        #     Ztor = 0
        # else:
        #     raise Exception("Not implemented")


        self.plot_data2D(Z, x, y, self.tab[0],
                         title="%s p:%6.3f m, q:%6.3f %6.3f mrad" %
                               (mirror_txt, self.source_oe, self.oe_image, self.theta),
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
    w = OWConic()
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