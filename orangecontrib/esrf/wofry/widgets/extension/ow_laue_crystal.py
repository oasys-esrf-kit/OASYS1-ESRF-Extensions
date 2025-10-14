import numpy
import sys
from orangewidget.settings import Setting
from orangewidget import gui

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from syned.beamline.optical_elements.ideal_elements.ideal_lens import IdealLens
from syned.beamline.optical_elements.crystals.crystal import Crystal
from wofry.beamline.decorators import OpticalElementDecorator

from wofryimpl.beamline.optical_elements.ideal_elements.ideal_lens import WOIdealLens1D

from orangecontrib.wofry.widgets.gui.ow_optical_element_1d import OWWOOpticalElement1D
from orangecontrib.esrf.util.laue_crystal_focusing import LaueCrystalFocusing
from wofryimpl.beamline.beamline import WOBeamline
#
#
#
# from PyQt5.QtGui import QPalette, QColor, QFont
# from PyQt5.QtWidgets import QMessageBox
#
# from orangewidget import gui
# from orangewidget import widget
# from orangewidget.settings import Setting
# from oasys.widgets import gui as oasysgui
# from oasys.widgets import congruence
# from oasys.widgets.gui import ConfirmDialog
from oasys.util.oasys_util import EmittingStream, TriggerIn
#
# from syned.widget.widget_decorator import WidgetDecorator
from syned.beamline.element_coordinates import ElementCoordinates
from syned.beamline.beamline_element import BeamlineElement
# from syned.beamline.shape import *
#
# from wofry.propagator.propagator import PropagationManager, PropagationElements, PropagationParameters
# from wofryimpl.propagator.propagators1D import initialize_default_propagator_1D
# from wofryimpl.propagator.propagators1D.fresnel import Fresnel1D
# from wofryimpl.propagator.propagators1D.fresnel_convolution import FresnelConvolution1D
# from wofryimpl.propagator.propagators1D.fraunhofer import Fraunhofer1D
# from wofryimpl.propagator.propagators1D.integral import Integral1D
# from wofryimpl.propagator.propagators1D.fresnel_zoom import FresnelZoom1D
# from wofryimpl.propagator.propagators1D.fresnel_zoom_scaling_theorem import FresnelZoomScaling1D
#
from orangecontrib.wofry.util.wofry_objects import WofryData
# from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget

class WOLaueCrystal1D(Crystal, OpticalElementDecorator):
    def __init__(self, name="",
                 crystal_descriptor="Si",
                 hkl=[1, 1, 1],
                 R=2.0, # m
                 poisson_ratio=0.2201,
                 photon_energy=20000.0,
                 thickness=250e-6,  # m
                 p=2.0,  # m
                 q=0.0,  # m
                 alfa_deg=2.0,  # CAN BE POSITIVE OR NEGATIVE)
                 integration_points=500,
                 npoints_x=100,
                 a_factor=1.0,
                 use_fast_hyp1f1=0,
                 source_flag=1,
                 verbose=1,
                 ):
        Crystal.__init__(self, name)
        self._LaueCrystalFocusing = LaueCrystalFocusing(
            crystal_descriptor=crystal_descriptor,
            hkl=hkl,
            R=R*1e3, # mm
            poisson_ratio=poisson_ratio,
            photon_energy_in_keV=photon_energy*1e-3,
            thickness=thickness*1e3,  # mm
            p=p*1e3,  # mm
            alfa_deg=alfa_deg,  # CAN BE POSITIVE OR NEGATIVE)
            integration_points=integration_points,
            use_fast_hyp1f1=use_fast_hyp1f1,
            verbose=1,
        )
        if verbose: print(self._LaueCrystalFocusing.info())

        self._q = q*1e3 # mm
        self._npoints_x = npoints_x
        self._a_factor  = a_factor
        self._source_flag  = source_flag

    def applyOpticalElement(self, wavefront_in, parameters=None, element_index=None):
        print(">>>>>>> in applyOpticalElement, source_flag = ", self._source_flag)
        print(">>>>>>> wavefront_in = ", wavefront_in)
        if self._source_flag == 0: # external wavefront
            # print(">>>>>>> wavefront in: dim:  ", wavefront_in.get_dimension(), wavefront_in)
            xx, yy_amplitude, wavefront = self._LaueCrystalFocusing.xscan_for_external_wavefront(
                                                                            Phi=wavefront_in.get_complex_amplitude(),
                                                                            Phi_tau=wavefront_in.get_abscissas(),
                                                                            npoints_x=self._npoints_x,
                                                                            a_factor=self._a_factor,
                                                                            a_center=0.0,
                                                                            filename="")
        elif self._source_flag == 1: # point source
            xx, yy_amplitude, wavefront = self._LaueCrystalFocusing.xscan(self._q,
                                                                          npoints_x=self._npoints_x,
                                                                          a_factor=self._a_factor,
                                                                          a_center=0.0,
                                                                          filename="")



        return wavefront

    def qscan(self, qmin=0.0, qmax=10.0, qpoints=100):
        print(">>>>>>> in qscan", qmin, qmax, qpoints, self.info())
        return self._LaueCrystalFocusing.qscan(qmin=qmin*1e3, qmax=qmax*1e3, npoints=qpoints)

    def to_python_code(self, do_plot=False, add_import_section=False):
        txt  = ""
        txt += "\nfrom orangecontrib.esrf.wofry.widgets.extension.ow_laue_crystal import WOLaueCrystal"
        txt += "\n"
        txt += "\noptical_element = WOLaueCrystal(name='%s')"%(self.get_name())
        txt += "\n"
        return txt

    #
    # added
    #
    def get_dimension(self):
        return 1

class OWWOLaueCrystal1D(OWWOOpticalElement1D):

    name = "Laue Crystal 1D"
    description = "Wofry: Laue Crystal 1D"
    icon = "icons/laue_crystal.png"
    priority = 301

    source_flag = Setting(1)

    # crystal
    crystal_descriptor = Setting("Si")
    hkl = Setting("[1, 1, 1]")
    thickness_um = Setting(250)
    alfa_deg = Setting(2.0)
    R = Setting(2.0)

    # positioning
    # p = Setting(29.0)
    # p = Setting(30.0)
    photon_energy = Setting(20000.0)
    npoints_x = Setting(100)
    a_factor = Setting(3.0)


    # advanced
    poisson_ratio = Setting(0.2201)
    integration_points = Setting(500)
    use_fast_hyp1f1 = Setting(0)

    # q-scan
    qscan_flag = Setting(0)
    qmin = Setting(0.0)
    qmax = Setting(10.0)
    qpoints = Setting(100)

    def __init__(self):
        super().__init__()

    def draw_specific_box(self):

        #
        # source
        #
        self.source_box = oasysgui.widgetBox(self.tab_bas, "Source", addSpace=False, orientation="vertical")

        gui.comboBox(self.source_box, self, "source_flag", label="Input wavefront to crystal", labelWidth=350,
                     items=["Oasys wire",
                            "point source (at p = distance from previous Continuation Plane)",
                            ],
                     sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        self.source_items = oasysgui.widgetBox(self.source_box, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.source_items, self, "photon_energy", "Photon energy [eV]",
                          tooltip="photon_energy", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.source_items, self, "npoints_x", "Points in spatial coordinate",
                          tooltip="npoints_x", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(self.source_items, self, "a_factor", "Window width factor (in units of 'a', default=1)",
                          tooltip="a_factor", labelWidth=260, valueType=float, orientation="horizontal")

        #
        # crystal
        #
        self.crystal_box = oasysgui.widgetBox(self.tab_bas, "Laue Crystal Setting", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.crystal_box, self, "crystal_descriptor", "Crystal descriptor",
                          tooltip="crystal_descriptor", labelWidth=260, valueType=str, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "hkl", "Miller indices [h,k,l]",
                          tooltip="hkl", labelWidth=260, valueType=str, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "thickness_um", "Crystal thickness [um]",
                          tooltip="thickness_um", labelWidth=260, valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "alfa_deg", "Asymmetry angle (symmetric=0) [deg]",
                          tooltip="alfa_deg", labelWidth=260, valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "R", "Curved crystal radius [m]",
                          tooltip="R", labelWidth=260, valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "poisson_ratio", "Poisson ratio for crystal material",
                          tooltip="poisson_ratio", labelWidth=260, valueType=float, orientation="horizontal")


        # self.set_visible()


    # overwrite this method to be used for advanced settings
    def create_propagation_setting_tab(self):
        # self.tab_pro = oasysgui.createTabPage(self.tabs_setting, "Propagation Setting")
        # self.zoom_box = oasysgui.widgetBox(self.tab_pro, "", addSpace=False, orientation="vertical", height=90)
        # oasysgui.lineEdit(self.zoom_box, self, "magnification_x", "Magnification Factor for interval",
        #                   labelWidth=260, valueType=float, orientation="horizontal")
        self.tab_adv = oasysgui.createTabPage(self.tabs_setting, "Additional Setting")

        self.adv_box = oasysgui.widgetBox(self.tab_adv, "Calculation parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.adv_box, self, "integration_points", "Number of points for calculating integrals",
                          tooltip="integration_points", labelWidth=260, valueType=float, orientation="horizontal")

        gui.comboBox(self.adv_box, self, "use_fast_hyp1f1", label="Use asymptotic values for hyp1f1", labelWidth=350,
                     items=["No (exact)","Yes (approximated)",],
                     sendSelectedValue=False, orientation="horizontal",
                     )

        q_box0 = oasysgui.widgetBox(self.tab_adv, "q-scan", addSpace=False, orientation="vertical")
        gui.comboBox(q_box0, self, "qscan_flag", label="Plot q-scan (slow)", labelWidth=350,
                     items=["No","Yes",],
                     sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible,
                     )

        self.q_box = oasysgui.widgetBox(q_box0, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.q_box, self, "qmin", "q minimum [m]",
                          tooltip="qmin", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.q_box, self, "qmax", "q maximum [m]",
                          tooltip="qmax", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.q_box, self, "qpoints", "Number of points for q",
                          tooltip="qpoints", labelWidth=260, valueType=int, orientation="horizontal")

        self.set_visible()

    def set_visible(self):
        self.source_items.setVisible(False)
        self.q_box.setVisible(False)
        #
        self.source_items.setVisible(self.source_flag in [1, 2])
        self.q_box.setVisible(self.qscan_flag == 1)


    def get_optical_element(self):


        cleaned = self.hkl.strip('[]')
        actual_list_hkl = [int(item.strip()) for item in cleaned.split(',')]

        oe = WOLaueCrystal1D(name=self.oe_name,
                               crystal_descriptor=self.crystal_descriptor,
                               hkl=actual_list_hkl,
                               R=self.R,  # m
                               poisson_ratio=self.poisson_ratio,
                               photon_energy=self.photon_energy,
                               thickness=self.thickness_um*1e-6,  # m
                               p=self.p,  # m
                               alfa_deg=self.alfa_deg,  # CAN BE POSITIVE OR NEGATIVE)
                               integration_points=self.integration_points,
                               npoints_x=self.npoints_x,
                               a_factor=self.a_factor,
                               q=self.q,
                               use_fast_hyp1f1=self.use_fast_hyp1f1,
                               source_flag=self.source_flag,
                               verbose=1,
                               )
        print(oe.info())
        return oe

    def check_data(self):
        super().check_data()

        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_x), "Horizontal Focal Length")
        congruence.checkStrictlyPositiveNumber(self.thickness_um, "Crystal thickness [um]")


    def receive_specific_syned_data(self, optical_element):
        if not optical_element is None:
            if isinstance(optical_element, Crystal):
                pass
                # self.focal_x = optical_element._focal_x
            else:
                raise Exception("Syned Data not correct: Optical Element is not a Crystal")
        else:
            raise Exception("Syned Data not correct: Empty Optical Element")

    #
    # overwritten methods
    #

    # overwritten method for specific built-in propagator
    # def create_propagation_setting_tab(self):
    #     # self.tab_pro = oasysgui.createTabPage(self.tabs_setting, "Propagation Setting")
    #     # self.zoom_box = oasysgui.widgetBox(self.tab_pro, "", addSpace=False, orientation="vertical", height=90)
    #     # oasysgui.lineEdit(self.zoom_box, self, "magnification_x", "Magnification Factor for interval",
    #     #                   labelWidth=260, valueType=float, orientation="horizontal")
    #     self.tab_adv = oasysgui.createTabPage(self.tabs_setting, "Additional Setting")
    #     self.adv_box = oasysgui.widgetBox(self.tab_adv, "", addSpace=False, orientation="vertical", height=90)


    # overwritten methods to append profile plot
    def get_titles(self):
        titles = super().get_titles()
        titles.append("q-scan")
        return titles

    def do_plot_results(self, progressBarValue=80): # OVERWRITTEN



        super().do_plot_results(progressBarValue, closeProgressBar=False)

        if self.qscan_flag:
            print("\n########################################################")
            print("\n                        Q-scan                          ")
            print("\n########################################################")
            self.progressBarSet(progressBarValue + 5)

            optical_element = self.get_optical_element()
            qq, amplitude = optical_element.qscan(qmin=self.qmin, qmax=self.qmax, qpoints=self.qpoints)

            self.plot_data1D(x=qq,
                             y=numpy.abs(amplitude) ** 2,
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=4,
                             plot_canvas_index=4,
                             calculate_fwhm=False,
                             title=self.get_titles()[4],
                             xtitle="q (distance from crystal) [m]",
                             ytitle="Intensity [a.u.]")
        else:
            # clean
            pass



        # if not self.view_type == 0:
        #     if not self.wavefront_to_plot is None:
        #
        #         self.progressBarSet(progressBarValue)
        #
        #         x, y = self.get_optical_element().get_height_profile(self.input_data.get_wavefront())
        #         self.plot_data1D(x=x,
        #                          y=1e6*y,
        #                          progressBarValue=progressBarValue + 10,
        #                          tabs_canvas_index=4,
        #                          plot_canvas_index=4,
        #                          calculate_fwhm=False,
        #                          title=self.get_titles()[4],
        #                          xtitle="Spatial Coordinate along o.e. [m]",
        #                          ytitle="Profile Height [$\mu$m]")
        #
        #
        #         x, y, amplitude = self.get_optical_element().get_footprint(self.input_data.get_wavefront())
        #         self.plot_data1D(x=x,
        #                          y=numpy.abs(amplitude)**2,
        #                          progressBarValue=progressBarValue + 10,
        #                          tabs_canvas_index=5,
        #                          plot_canvas_index=5,
        #                          calculate_fwhm=False,
        #                          title=self.get_titles()[5],
        #                          xtitle="Spatial Coordinate along o.e. [m]",
        #                          ytitle="Intensity")
        #
        #
        #
        #         self.plot_canvas[0].resetZoom()


        self.progressBarFinished()

    def propagate_wavefront(self):

        self.progressBarInit()

        self.wofry_output.setText("")

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        current_index = self.tabs.currentIndex()


        if 1: # try:
            # if self.input_data is None: raise Exception("No Input Data")

            self.check_data()

            # propagation to o.e.

            # input_wavefront  = self.input_data.get_wavefront()




            optical_element = self.get_optical_element()
            optical_element.name = self.oe_name if not self.oe_name is None else self.windowTitle()

            try:
                beamline = self.input_data.get_beamline().duplicate()
            except:
                beamline = WOBeamline(light_source=optical_element)

            print("beamline: ", beamline)


            beamline_element = BeamlineElement(optical_element=optical_element,
                                               coordinates=ElementCoordinates(p=self.p,
                                                                              q=self.q,
                                                                              angle_radial=numpy.radians(self.angle_radial),
                                                                              angle_azimuthal=numpy.radians(self.angle_azimuthal)))


            # if self.propagator == 0:
            #     propagator_info = {
            #         "propagator_class_name": "Fresnel",
            #         "propagator_handler_name": self.get_handler_name(),
            #         "propagator_additional_parameters_names": [],
            #         "propagator_additional_parameters_values": []}
            # elif self.propagator == 1:
            #     propagator_info = {
            #         "propagator_class_name": "FresnelConvolution1D",
            #         "propagator_handler_name": self.get_handler_name(),
            #         "propagator_additional_parameters_names": [],
            #         "propagator_additional_parameters_values": []}
            # elif self.propagator == 2:
            #     propagator_info = {
            #         "propagator_class_name": "Fraunhofer1D",
            #         "propagator_handler_name": self.get_handler_name(),
            #         "propagator_additional_parameters_names": [],
            #         "propagator_additional_parameters_values": []}
            # elif self.propagator == 3:
            #     propagator_info = {
            #         "propagator_class_name": "Integral1D",
            #         "propagator_handler_name": self.get_handler_name(),
            #         "propagator_additional_parameters_names": ['magnification_x', 'magnification_N'],
            #         "propagator_additional_parameters_values": [self.magnification_x, self.magnification_N]}
            # elif self.propagator == 4:
            #     propagator_info = {
            #         "propagator_class_name": "FresnelZoom1D",
            #         "propagator_handler_name": self.get_handler_name(),
            #         "propagator_additional_parameters_names": ['magnification_x'],
            #         "propagator_additional_parameters_values": [self.magnification_x]}
            # elif self.propagator == 5:
            #     propagator_info = {
            #         "propagator_class_name": "FresnelZoomScaling1D",
            #         "propagator_handler_name": self.get_handler_name(),
            #         "propagator_additional_parameters_names": ['magnification_x','radius'],
            #         "propagator_additional_parameters_values": [self.magnification_x, self.wavefront_radius]}
            #
            # beamline.append_beamline_element(beamline_element, propagator_info)
            #
            # propagation_elements = PropagationElements()
            # propagation_elements.add_beamline_element(beamline_element)
            #
            # propagation_parameters = PropagationParameters(wavefront=input_wavefront.duplicate(),
            #                                                propagation_elements=propagation_elements)
            #
            # self.set_additional_parameters(propagation_parameters)

            self.setStatusMessage("Begin Propagation")

            # propagator = PropagationManager.Instance()

            # output_wavefront = propagator.do_propagation(propagation_parameters=propagation_parameters,
            #                                              handler_name=self.get_handler_name())

            if self.source_flag == 0:
                input_wavefront  = self.input_data.get_wavefront()
                output_wavefront = optical_element.applyOpticalElement(input_wavefront)
            else:
                output_wavefront = optical_element.applyOpticalElement(None)

            self.setStatusMessage("Propagation Completed")

            self.wavefront_to_plot = output_wavefront


            if self.view_type > 0:
                self.initializeTabs()
                self.do_plot_results()
            else:
                self.progressBarFinished()

            self.send("WofryData", WofryData(beamline=beamline, wavefront=output_wavefront))
            self.send("Trigger", TriggerIn(new_object=True))

            self.wofry_python_script.set_code(beamline.to_python_code())

            self.setStatusMessage("")

            try:    self.print_intensities()
            except: pass
        else: # except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

        self.tabs.setCurrentIndex(current_index)


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
    ow = OWWOLaueCrystal1D()
    ow.set_input(get_example_wofry_data())
    ow.p = 29.0

    ow.show()
    a.exec_()
    ow.saveSettings()
