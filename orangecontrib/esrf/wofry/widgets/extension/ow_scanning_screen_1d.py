from orangecontrib.wofry.widgets.gui.ow_optical_element_1d import OWWOOpticalElement1D
from syned.beamline.optical_elements.ideal_elements.screen import Screen

from orangewidget.settings import Setting

from wofryimpl.beamline.optical_elements.ideal_elements.screen import WOScreen1D

#################
import numpy, sys

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox

from orangewidget import gui
from orangewidget import widget
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog
from oasys.util.oasys_util import EmittingStream, TriggerIn

from syned.widget.widget_decorator import WidgetDecorator
from syned.beamline.element_coordinates import ElementCoordinates
from syned.beamline.beamline_element import BeamlineElement
from syned.beamline.shape import *

from wofry.propagator.propagator import PropagationManager, PropagationElements, PropagationParameters
from wofryimpl.propagator.propagators1D.fresnel import Fresnel1D
from wofryimpl.propagator.propagators1D.fresnel_convolution import FresnelConvolution1D
from wofryimpl.propagator.propagators1D.fraunhofer import Fraunhofer1D
from wofryimpl.propagator.propagators1D.integral import Integral1D
from wofryimpl.propagator.propagators1D.fresnel_zoom import FresnelZoom1D
from wofryimpl.propagator.propagators1D.fresnel_zoom_scaling_theorem import FresnelZoomScaling1D

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget
#################

from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget
from oasys.util.oasys_util import get_fwhm

class OWWOScanningScreen1D(OWWOOpticalElement1D):

    name = "Scanning Screen 1D"
    description = "Wofry: Scanning Screen 1D"
    # icon = "icons/scanningscreen1d.png"
    icon = "icons/caustic.png"
    priority = 200

    q_min = Setting(1.0)
    q_max = Setting(2.0)
    q_points = Setting(2)
    file_flag = Setting(0)
    file_name = Setting("tmp.h5")

    def __init__(self,is_automatic=True, show_view_options=True, show_script_tab=True):
        WofryWidget.__init__(self,is_automatic=is_automatic, show_view_options=show_view_options, show_script_tab=show_script_tab)

        self.runaction = widget.OWAction("Propagate Wavefront", self)
        self.runaction.triggered.connect(self.propagate_wavefront)
        self.addAction(self.runaction)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Propagate Wavefront", callback=self.propagate_wavefront)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)

        button = gui.button(button_box, self, "Reset Fields", callback=self.callResetSettings)
        font = QFont(button.font())
        font.setItalic(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Red'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)
        button.setFixedWidth(150)

        gui.separator(self.controlArea)

        self.tabs_setting = oasysgui.tabWidget(self.controlArea)
        self.tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        self.tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)


        self.tab_bas = oasysgui.createTabPage(self.tabs_setting, "O.E. Setting")


        oasysgui.lineEdit(self.tab_bas, self, "oe_name", "O.E. Name", labelWidth=260, valueType=str, orientation="horizontal")

        self.coordinates_box = oasysgui.widgetBox(self.tab_bas, "Coordinates", addSpace=True, orientation="vertical")

        tmp = oasysgui.lineEdit(self.coordinates_box, self, "p", "Distance from previous Continuation Plane [m]", labelWidth=280, valueType=float, orientation="horizontal")
        tmp.setToolTip("p")
        tmp = oasysgui.lineEdit(self.coordinates_box, self, "q_min", "Min distance to next Continuation Plane [m]", labelWidth=280, valueType=float, orientation="horizontal")
        tmp.setToolTip("q_min")
        tmp = oasysgui.lineEdit(self.coordinates_box, self, "q_max", "Max distance to next Continuation Plane [m]", labelWidth=280, valueType=float, orientation="horizontal")
        tmp.setToolTip("q_max")
        tmp = oasysgui.lineEdit(self.coordinates_box, self, "q_points", "scanning points in p", labelWidth=280, valueType=int, orientation="horizontal")
        tmp.setToolTip("q_points")


        gui.comboBox(self.coordinates_box, self, "file_flag", label="Dump file", labelWidth=260,
                     items=["No","Yes"],
                     callback=self.set_file_flag,
                     sendSelectedValue=False, orientation="horizontal")

        self.file_box = oasysgui.widgetBox(self.coordinates_box, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.file_box, self, "file_name", "File name [.h5]", labelWidth=280, valueType=int, orientation="horizontal")
        tmp.setToolTip("file_name")


        self.draw_specific_box()

        self.create_propagation_setting_tab()

        self.set_file_flag()

    def set_file_flag(self):
        self.file_box.setVisible(self.file_flag == 0)
        self.file_box.setVisible(self.file_flag == 1)

    def get_optical_element(self):
        return WOScreen1D(name=self.oe_name)

    def check_syned_instance(self, optical_element):
        if not isinstance(optical_element, Screen):
            raise Exception("Syned Data not correct: Optical Element is not a Screen")

    def propagate_wavefront(self):

        qs = numpy.linspace(self.q_min, self.q_max, self.q_points)

        view_type_old = self.view_type
        self.view_type = 0

        wavefronts = []
        peak = numpy.zeros(self.q_points)
        fwhm = numpy.zeros(self.q_points)
        integral = numpy.zeros(self.q_points)

        for i,q in enumerate(qs):
            self.q = q
            super().propagate_wavefront()
            wavefronts.append(self.wavefront_to_plot)
            if i == 0:
                intensities = numpy.zeros((self.q_points,self.wavefront_to_plot.get_abscissas().size))
                x = self.wavefront_to_plot.get_abscissas()

            active_profile = self.wavefront_to_plot.get_intensity()

            intensities[i,:] = active_profile

            peak[i] = numpy.max(active_profile)
            try:
                fwhm[i], _, _ = get_fwhm(active_profile, x)
                print("fwhm: ", i, fwhm[i])
            except:
                fwhm[i] = 0.0
                print("bad fwhm: ", i, fwhm[i])

        if self.file_flag:
            from srxraylib.util.h5_simple_writer import H5SimpleWriter
            h5w = H5SimpleWriter.initialize_file(self.file_name, overwrite=1)
            for i, q in enumerate(qs):
                if i == 0:
                    # from srxraylib.util.h5_simple_writer import H5SimpleWriter
                    # h5w = H5SimpleWriter.initialize_file(self.file_name, creator="h5_basic_writer.py")


                    wavefronts[i].save_h5_file(self.file_name, subgroupname="wfr%03d" % i,
                                                        intensity=True, phase=False, overwrite=True, verbose=False)
                else:
                    wavefronts[i].save_h5_file(self.file_name, subgroupname="wfr%03d" % i,
                                                            intensity=True, phase=False, overwrite=False, verbose=False)


            h5w.add_dataset(qs, peak, dataset_name="peak", entry_name=None, title_x="q [m]", title_y="peak")
            h5w.add_dataset(qs, fwhm*1e6, dataset_name="fwhm", entry_name=None, title_x="q [m]", title_y="fwhm [$\mu$m]")
            h5w.add_image(intensities, image_x=qs,image_y=x*1e6,image_name="scan",entry_name=None,title_x="q [m]",
                          title_y="Spatial Coordinate [$\mu$m]")
            print("\nFile %s written to disk." % self.file_name)

        print("\nNumber of wavefronts generated: ", len(wavefronts))

        self.view_type = view_type_old
        if self.view_type > 0:
            self.initializeTabs()
            self.do_plot_results(closeProgressBar=False)
            #


            self.plot_data1D(x=qs,
                             y=peak,
                             progressBarValue=97,
                             tabs_canvas_index=4,
                             plot_canvas_index=4,
                             calculate_fwhm=False,
                             title="peak evolution q_points=%s" % self.q_points,
                             xtitle="q [m]",
                             ytitle="Peak Intensity")

            self.plot_data1D(x=qs,
                             y=1e6*fwhm,
                             progressBarValue=98,
                             tabs_canvas_index=5,
                             plot_canvas_index=5,
                             calculate_fwhm=False,
                             title="FWHM evolution q_points=%s" % self.q_points,
                             xtitle="q [m]",
                             ytitle="FWHM [$\mu$m]")

            self.plot_data2D(intensities, qs, 1e6*wavefronts[-1].get_abscissas(),
                             progressBarValue=99,
                             tabs_canvas_index=6,
                             plot_canvas_index=6,
                             title="q_points=%s" % self.q_points,
                             xtitle="q [m]",
                             ytitle="Spatial Coordinate [$\mu$m]",
                             )
            self.progressBarFinished()

    def initializeTabs(self):
        super().initializeTabs()

        self.tab.append(gui.createTabPage(self.tabs, "Peak"))
        self.plot_canvas.append(None)
        self.tab[-1].setFixedHeight(self.IMAGE_HEIGHT)
        self.tab[-1].setFixedWidth(self.IMAGE_WIDTH)

        self.tab.append(gui.createTabPage(self.tabs, "FWHM"))
        self.plot_canvas.append(None)
        self.tab[-1].setFixedHeight(self.IMAGE_HEIGHT)
        self.tab[-1].setFixedWidth(self.IMAGE_WIDTH)

        self.tab.append(gui.createTabPage(self.tabs, "Scan"))
        self.plot_canvas.append(None)
        self.tab[-1].setFixedHeight(self.IMAGE_HEIGHT)
        self.tab[-1].setFixedWidth(self.IMAGE_WIDTH)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    def get_example_wofry_data():
        from wofryimpl.propagator.light_source import WOLightSource
        from wofryimpl.beamline.beamline import WOBeamline
        from orangecontrib.wofry.util.wofry_objects import WofryData

        light_source = WOLightSource(dimension=1,
                                     initialize_from=0,
                                     range_from_h=-0.001,
                                     range_to_h=0.001,
                                     number_of_points_h=500,
                                     energy=10000.0,
                                     )

        return WofryData(wavefront=light_source.get_wavefront(),
                           beamline=WOBeamline(light_source=light_source))

    a = QApplication(sys.argv)
    ow = OWWOScanningScreen1D()
    ow.set_input(get_example_wofry_data())

    ow.show()
    a.exec_()
    ow.saveSettings()
