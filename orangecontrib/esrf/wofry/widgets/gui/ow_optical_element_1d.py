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

def initialize_default_propagator_1D():
    propagator = PropagationManager.Instance()

    propagator.add_propagator(Fraunhofer1D())
    propagator.add_propagator(Fresnel1D())
    propagator.add_propagator(FresnelConvolution1D())
    propagator.add_propagator(Integral1D())
    propagator.add_propagator(FresnelZoom1D())
    propagator.add_propagator(FresnelZoomScaling1D())

try:
    initialize_default_propagator_1D()
except:
    pass

class OWWOOpticalElement1D(WofryWidget, WidgetDecorator):

    maintainer = "Luca Rebuffi"
    maintainer_email = "luca.rebuffi(@at@)elettra.eu"
    keywords = ["data", "file", "load", "read"]
    category = "Wofry Optical Elements"

    outputs = [{"name":"WofryData",
                "type":WofryData,
                "doc":"WofryData",
                "id":"WofryData"},
               {"name":"Trigger",
                "type": TriggerIn,
                "doc":"Feedback signal to start a new beam simulation",
                "id":"Trigger"},
               ]

    inputs = [("WofryData", WofryData, "set_input"),
              WidgetDecorator.syned_input_data()[0]]

    oe_name         = Setting("")
    p               = Setting(0.0)
    q               = Setting(0.0)
    angle_radial    = Setting(0.0)
    angle_azimuthal = Setting(0.0)

    shape = Setting(0)
    surface_shape = Setting(0)

    input_data = None
    wavefront_to_plot = None

    propagators_list = ["Fresnel", "Fresnel (Convolution)", "Fraunhofer", "Integral", "Fresnel Zoom","Fresnel Zoom Scaled"]
    # plot_titles = ["Wavefront 1D Intensity", "Wavefront 1D Phase","Wavefront Real(Amplitude)","Wavefront Imag(Amplitude)"]

    propagator = Setting(4)
    magnification_x = Setting(1.0) # For Fresnel Zoom & Integral
    magnification_N = Setting(1.0) # For Integral
    scaled_guess_R = Setting(True) # For Fresnel Zoom Scaled
    scaled_R = Setting(1000.0) # For Fresnel Zoom Scaled
    scaled_Rmax = Setting(100.0) # For Fresnel Zoom Scaled
    scaled_N = Setting(100) # For Fresnel Zoom Scaled

    wavefront_radius = 1.0

    def __init__(self,is_automatic=True, show_view_options=True, show_script_tab=True):
        super().__init__(is_automatic=is_automatic, show_view_options=show_view_options, show_script_tab=show_script_tab)

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
        self.tab_pro = oasysgui.createTabPage(self.tabs_setting, "Propagation Setting")

        oasysgui.lineEdit(self.tab_bas, self, "oe_name", "O.E. Name", labelWidth=260, valueType=str, orientation="horizontal")

        self.coordinates_box = oasysgui.widgetBox(self.tab_bas, "Coordinates", addSpace=True, orientation="vertical")

        oasysgui.lineEdit(self.coordinates_box, self, "p", "Distance from previous Continuation Plane [m]", labelWidth=280, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.coordinates_box, self, "q", "Distance to next Continuation Plane [m]", labelWidth=280, valueType=float, orientation="horizontal")
        # Commented srio (not yet implemented) TODO: implement it!
        # oasysgui.lineEdit(self.coordinates_box, self, "angle_radial", "Incident Angle (to normal) [deg]", labelWidth=280, valueType=float, orientation="horizontal")
        # oasysgui.lineEdit(self.coordinates_box, self, "angle_azimuthal", "Rotation along Beam Axis [deg]", labelWidth=280, valueType=float, orientation="horizontal")

        self.draw_specific_box()

        gui.comboBox(self.tab_pro, self, "propagator", label="Propagator", labelWidth=260,
                     items=self.propagators_list,
                     callback=self.set_Propagator,
                     sendSelectedValue=False, orientation="horizontal")

        # Fresnel
        self.fresnel_box = oasysgui.widgetBox(self.tab_pro, "", addSpace=False, orientation="vertical", height=90)

        # Fraunhoffer
        self.fraunhofer_box = oasysgui.widgetBox(self.tab_pro, "", addSpace=False, orientation="vertical", height=90)

        # Integral
        self.integral_box = oasysgui.widgetBox(self.tab_pro, "", addSpace=False, orientation="vertical", height=90)


        oasysgui.lineEdit(self.integral_box, self, "magnification_x", "Magnification Factor for interval",
                          labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.integral_box, self, "magnification_N", "Magnification Factor for N points",
                          labelWidth=260, valueType=float, orientation="horizontal")

        # Fresnel zoom
        self.zoom_box = oasysgui.widgetBox(self.tab_pro, "", addSpace=False, orientation="vertical", height=90)

        oasysgui.lineEdit(self.zoom_box, self, "magnification_x", "Magnification Factor for interval",
                          labelWidth=260, valueType=float, orientation="horizontal")


        # Fresnel Sacled zoom

        self.zoom_scaled_box = oasysgui.widgetBox(self.tab_pro, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.zoom_scaled_box, self, "magnification_x", "Magnification Factor for interval",
                          labelWidth=260, valueType=float, orientation="horizontal")

        gui.comboBox(self.zoom_scaled_box, self, "scaled_guess_R", label="Guess wavefront curvature", labelWidth=260,
                     items=["No","Yes"],
                     callback=self.set_ScaledGuess,
                     sendSelectedValue=False, orientation="horizontal")

        self.zoom_scaled_box_1 = oasysgui.widgetBox(self.zoom_scaled_box, "", addSpace=False, orientation="vertical", height=90)
        self.zoom_scaled_box_2 = oasysgui.widgetBox(self.zoom_scaled_box, "", addSpace=False, orientation="vertical", height=90)

        oasysgui.lineEdit(self.zoom_scaled_box_1, self, "scaled_R", "Wavefront radius of curvature",
                          labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.zoom_scaled_box_2, self, "scaled_Rmax", "Maximum wavefront radius of curvature",
                          labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.zoom_scaled_box_2, self, "scaled_N", "Number of points for guessing curvature",
                          labelWidth=260, valueType=int, orientation="horizontal")

        self.set_Propagator()


    def set_Propagator(self):
        self.fresnel_box.setVisible(self.propagator <= 1)
        self.fraunhofer_box.setVisible(self.propagator == 2)
        self.integral_box.setVisible(self.propagator == 3)
        self.zoom_box.setVisible(self.propagator == 4)
        self.zoom_scaled_box.setVisible(self.propagator == 5)
        if self.propagator == 5: self.set_ScaledGuess()

    def set_ScaledGuess(self):
        self.zoom_scaled_box_1.setVisible(self.scaled_guess_R==0)
        self.zoom_scaled_box_2.setVisible(self.scaled_guess_R==1)

    def draw_specific_box(self):
        pass

    def check_data(self):
        congruence.checkNumber(self.p, "Distance from previous Continuation Plane")
        congruence.checkNumber(self.q, "Distance to next Continuation Plane")
        congruence.checkAngle(self.angle_radial, "Incident Angle (to normal)")
        congruence.checkAngle(self.angle_azimuthal, "Rotation along Beam Axis")

    def propagate_wavefront(self):

        self.progressBarInit()

        self.wofry_output.setText("")

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        if self.input_data is None: raise Exception("No Input Data")

        self.check_data()

        # propagation to o.e.

        input_wavefront  = self.input_data.get_wavefront()
        beamline         = self.input_data.get_beamline().duplicate()

        optical_element = self.get_optical_element()
        optical_element.name = self.oe_name if not self.oe_name is None else self.windowTitle()

        beamline_element = BeamlineElement(optical_element=optical_element,
                                           coordinates=ElementCoordinates(p=self.p,
                                                                          q=self.q,
                                                                          angle_radial=numpy.radians(self.angle_radial),
                                                                          angle_azimuthal=numpy.radians(self.angle_azimuthal)))

        #
        # this will store the propagation parameters in beamline in order to perform the propagation in the script
        #
        # 1D
        # ==
        #
        # propagators_list = ["Fresnel",    "Fresnel (Convolution)",  "Fraunhofer",    "Integral",    "Fresnel Zoom",    "Fresnel Zoom Scaled"]
        # class_name       = ["Fresnel1D",  "FresnelConvolution1D",   "Fraunhofer1D",  "Integral1D",  "FresnelZoom1D",   "FresnelZoomScaling1D"]
        # handler_name     = ["FRESNEL_1D", "FRESNEL_CONVOLUTION_1D", "FRAUNHOFER_1D", "INTEGRAL_1D", "FRESNEL_ZOOM_1D", "FRESNEL_ZOOM_SCALING_1D"]

        if self.propagator == 0:
            propagator_info = {
                "propagator_class_name": "Fresnel",
                "propagator_handler_name": self.get_handler_name(),
                "propagator_additional_parameters_names": [],
                "propagator_additional_parameters_values": []}
        elif self.propagator == 1:
            propagator_info = {
                "propagator_class_name": "FresnelConvolution1D",
                "propagator_handler_name": self.get_handler_name(),
                "propagator_additional_parameters_names": [],
                "propagator_additional_parameters_values": []}
        elif self.propagator == 2:
            propagator_info = {
                "propagator_class_name": "Fraunhofer1D",
                "propagator_handler_name": self.get_handler_name(),
                "propagator_additional_parameters_names": [],
                "propagator_additional_parameters_values": []}
        elif self.propagator == 3:
            propagator_info = {
                "propagator_class_name": "Integral1D",
                "propagator_handler_name": self.get_handler_name(),
                "propagator_additional_parameters_names": ['magnification_x', 'magnification_N'],
                "propagator_additional_parameters_values": [self.magnification_x, self.magnification_N]}
        elif self.propagator == 4:
            propagator_info = {
                "propagator_class_name": "FresnelZoom1D",
                "propagator_handler_name": self.get_handler_name(),
                "propagator_additional_parameters_names": ['magnification_x'],
                "propagator_additional_parameters_values": [self.magnification_x]}
        elif self.propagator == 5:
            propagator_info = {
                "propagator_class_name": "FresnelZoomScaling1D",
                "propagator_handler_name": self.get_handler_name(),
                "propagator_additional_parameters_names": ['magnification_x','radius'],
                "propagator_additional_parameters_values": [self.magnification_x, self.wavefront_radius]}

        beamline.append_beamline_element(beamline_element, propagator_info)

        propagation_elements = PropagationElements()
        propagation_elements.add_beamline_element(beamline_element)

        propagation_parameters = PropagationParameters(wavefront=input_wavefront.duplicate(),
                                                       propagation_elements=propagation_elements)

        self.set_additional_parameters(propagation_parameters)

        self.setStatusMessage("Begin Propagation")

        propagator = PropagationManager.Instance()

        output_wavefront = propagator.do_propagation(propagation_parameters=propagation_parameters,
                                                     handler_name=self.get_handler_name())

        self.setStatusMessage("Propagation Completed")

        self.wavefront_to_plot = output_wavefront


        if self.view_type > 0:
            self.initializeTabs()
            self.do_plot_results()
        else:
            self.progressBarFinished()

        self.send("WofryData", WofryData(beamline=beamline, wavefront=output_wavefront))
        self.send("Trigger", TriggerIn(new_object=True))



        # try:
        if True:
            self.wofry_python_script.set_code(beamline.to_python_code())
        # except:
        #     pass

        self.setStatusMessage("")


    def get_handler_name(self):
        if self.propagator == 0:
            return Fresnel1D.HANDLER_NAME
        elif self.propagator == 1:
            return FresnelConvolution1D.HANDLER_NAME
        elif self.propagator == 2:
            return Fraunhofer1D.HANDLER_NAME
        elif self.propagator == 3:
            return Integral1D.HANDLER_NAME
        elif self.propagator == 4:
            return FresnelZoom1D.HANDLER_NAME
        elif self.propagator == 5:
            return FresnelZoomScaling1D.HANDLER_NAME

    def set_additional_parameters(self, propagation_parameters):
        if self.propagator <= 2:
            pass
        elif self.propagator == 3:
            propagation_parameters.set_additional_parameters("magnification_x", self.magnification_x)
            propagation_parameters.set_additional_parameters("magnification_N", self.magnification_N)
        elif self.propagator == 4:
            propagation_parameters.set_additional_parameters("magnification_x", self.magnification_x)
        elif self.propagator == 5:
            propagation_parameters.set_additional_parameters("magnification_x", self.magnification_x)
            if self.scaled_guess_R:
                # from srxraylib.plot.gol import plot
                # radii,fig_of_mer = self.input_wavefront.scan_wavefront_curvature(
                #     rmin=-self.scaled_Rmax,rmax=self.scaled_Rmax,rpoints=self.scaled_N)
                # plot(radii,fig_of_mer)
                self.wavefront_radius = self.input_data.get_wavefront().guess_wavefront_curvature(
                    rmin=-self.scaled_Rmax,rmax=self.scaled_Rmax,rpoints=self.scaled_N)
                print("Guess wavefront curvature radius: %f m " % self.wavefront_radius)
            else:
                self.wavefront_radius = self.scaled_R
            propagation_parameters.set_additional_parameters("radius", self.wavefront_radius)

    def get_optical_element(self):
        raise NotImplementedError()

    def set_input(self, wofry_data):
        if not wofry_data is None:
            if isinstance(wofry_data, WofryData):
                self.input_data = wofry_data
            else:
                raise Exception("Only wofry_data allowed as input")

            if self.is_automatic_execution:
                self.propagate_wavefront()

    def get_titles(self):
        return ["Wavefront 1D Intensity",
                "Wavefront 1D Phase",
                "Wavefront Real(Amplitude)",
                "Wavefront Imag(Amplitude)"]

    def initializeTabs(self):
        size = len(self.tab)
        indexes = range(0, size)

        for index in indexes:
            self.tabs.removeTab(size-1-index)

        self.tab = []
        self.plot_canvas = []

        for index in range(0, len(self.get_titles())):
            self.tab.append(gui.createTabPage(self.tabs, self.get_titles()[index]))
            self.plot_canvas.append(None)

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

    def do_plot_results(self, progressBarValue=80):

        if not self.wavefront_to_plot is None:

            self.progressBarSet(progressBarValue)

            self.plot_data1D(x=1e6*self.wavefront_to_plot.get_abscissas(),
                             y=self.wavefront_to_plot.get_intensity(),
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=0,
                             plot_canvas_index=0,
                             title=self.get_titles()[0],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Intensity")


            self.plot_data1D(x=1e6*self.wavefront_to_plot.get_abscissas(),
                             y=self.wavefront_to_plot.get_phase(from_minimum_intensity=0.1,unwrap=1),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=1,
                             plot_canvas_index=1,
                             title=self.get_titles()[1],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Phase [unwrapped, for intensity > 10% of peak] (rad)")

            self.plot_data1D(x=1e6*self.wavefront_to_plot.get_abscissas(),
                             y=numpy.real(self.wavefront_to_plot.get_complex_amplitude()),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=2,
                             plot_canvas_index=2,
                             title=self.get_titles()[2],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Real(Amplitude)")

            self.plot_data1D(x=1e6*self.wavefront_to_plot.get_abscissas(),
                             y=numpy.imag(self.wavefront_to_plot.get_complex_amplitude()),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=3,
                             plot_canvas_index=3,
                             title=self.get_titles()[3],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Imag(Amplitude)")


            # for i in range(len(self.get_titles())):
            #     self.plot_canvas[i].resetZoom()

            self.progressBarFinished()

    def receive_syned_data(self, data):
        if not data is None:
            beamline_element = data.get_beamline_element_at(-1)

            if not beamline_element is None:
                self.oe_name = beamline_element._optical_element._name
                self.p = beamline_element._coordinates._p
                self.q = beamline_element._coordinates._q
                self.angle_azimuthal = round(numpy.degrees(beamline_element._coordinates._angle_azimuthal), 6)
                self.angle_radial = round(numpy.degrees(beamline_element._coordinates._angle_radial), 6)

                self.receive_specific_syned_data(beamline_element._optical_element)
            else:
                raise Exception("Syned Data not correct: Empty Beamline Element")

    def receive_specific_syned_data(self, optical_element):
        raise NotImplementedError()

    def callResetSettings(self):
        if ConfirmDialog.confirmed(parent=self, message="Confirm Reset of the Fields?"):
            try:
                self.resetSettings()
            except:
                pass




#--------------------------------------------------------------

class OWWOOpticalElementWithBoundaryShape1D(OWWOOpticalElement1D):
    # BOUNDARY

    vertical_shift = Setting(0.0)

    height = Setting(0.0)


    def draw_specific_box(self):
        self.shape_box = oasysgui.widgetBox(self.tab_bas, "Boundary Shape", addSpace=True, orientation="vertical")

        # gui.comboBox(self.shape_box, self, "shape", label="Boundary Shape", labelWidth=350,
        #              items=["Rectangle"],
        #              callback=self.set_Shape,
        #              sendSelectedValue=False, orientation="horizontal")

        oasysgui.lineEdit(self.shape_box, self, "vertical_shift", "Shift [m]", labelWidth=260, valueType=float, orientation="horizontal")

        self.rectangle_box = oasysgui.widgetBox(self.shape_box, "", addSpace=False, orientation="vertical", height=60)

        oasysgui.lineEdit(self.rectangle_box, self, "height", "Aperture [m]", labelWidth=260, valueType=float, orientation="horizontal")

        self.circle_box = oasysgui.widgetBox(self.shape_box, "", addSpace=False, orientation="vertical", height=60)

        self.set_Shape()

    def set_Shape(self):
        self.rectangle_box.setVisible(True)
        # self.rectangle_box.setVisible(self.shape == 0)

    def get_boundary_shape(self):
        if self.shape == 0:
            # note that wavefront 1d will be clipped using the first two coordinates!
            boundary_shape = Rectangle(x_left=-0.5*self.height + self.vertical_shift,
                                       x_right=0.5*self.height + self.vertical_shift,
                                       y_bottom=-0.5*self.height + self.vertical_shift,
                                       y_top=0.5*self.height + self.vertical_shift)

        return boundary_shape

    # def get_boundary_shape_python_code(self):
    #     txt = ""
    #
    #     txt += "\nfrom syned.beamline.shape import Rectangle"
    #     txt += "\n# note that wavefront 1d will be clipped using the first two coordinates!"
    #     txt += "\nboundary_shape = Rectangle(x_left=%g,"%(-0.5*self.height + self.vertical_shift)
    #     txt += "x_right=%g,"%(0.5*self.height + self.vertical_shift)
    #     txt += "y_bottom=%g,"%(-0.5*self.height + self.vertical_shift)
    #     txt += "y_top=%g)\n"%(0.5*self.height + self.vertical_shift)
    #
    #     return txt


    def check_data(self):
        super().check_data()

        congruence.checkNumber(self.vertical_shift, "Vertical Shift")
        if self.shape == 0:
            congruence.checkStrictlyPositiveNumber(self.height, "Height")


    def receive_specific_syned_data(self, optical_element):
        if not optical_element is None:
            self.check_syned_instance(optical_element)

            if not optical_element._boundary_shape is None:

                left, right, bottom, top = optical_element._boundary_shape.get_boundaries()

                self.vertical_shift = round(((top + bottom) / 2), 6)

                if isinstance(optical_element._boundary_shape, Rectangle):
                    self.shape = 0

                self.set_Shape()
        else:
            raise Exception("Syned Data not correct: Empty Optical Element")



