import numpy
import sys

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox
from orangewidget import gui
from orangewidget import widget
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget

from oasys.util.oasys_util import TriggerIn, TriggerOut, EmittingStream
from orangecontrib.xoppy.util.python_script import PythonScript  # TODO: change import from wofry!!!

class OWGenericWavefront1D(WofryWidget):

    name = "Generic Wavefront 1D"
    id = "GenericWavefront1D"
    description = "Generic Wavefront 1D"
    icon = "icons/gw1d.png"
    priority = 1

    category = "Wofry Wavefront Propagation"
    keywords = ["data", "file", "load", "read"]

    outputs = [{"name":"WofryData",
                "type":WofryData,
                "doc":"WofryData",
                "id":"WofryData"}]

    inputs = [("Trigger", TriggerOut, "receive_trigger_signal"),]

    units = Setting(1)
    energy = Setting(1000.0)
    wavelength = Setting(1e-10)
    number_of_points = Setting(1000)
    initialize_from = Setting(0)
    range_from = Setting(-0.0005)
    range_to = Setting(0.0005)
    steps_start = Setting(-0.0005)
    steps_step = Setting(1e-6)

    kind_of_wave = Setting(0)
    initialize_amplitude = Setting(0)
    complex_amplitude_re = Setting(1.0)
    complex_amplitude_im = Setting(0.0)
    radius = Setting(140.0)
    center = Setting(0.0)
    inclination = Setting(0.0)

    gaussian_sigma = Setting(0.001)
    gaussian_amplitude = Setting(1.0)
    gaussian_beta = Setting(1.0)
    mode_index = Setting(0)

    gaussian_shift = Setting(0.0)

    amplitude = Setting(1.0)
    phase = Setting(0.0)
    add_random_phase = Setting(0)

    wavefront1D = None
    titles = ["Wavefront 1D Intensity", "Wavefront 1D Phase","Wavefront Real(Amplitude)","Wavefront Imag(Amplitude)"]

    def __init__(self):
        super().__init__(is_automatic=False, show_view_options=True)

        #
        # add script tab to tabs panel
        #
        script_tab = oasysgui.createTabPage(self.main_tabs, "Script")
        self.wofry_script = PythonScript()
        self.wofry_script.code_area.setFixedHeight(400)
        script_box = gui.widgetBox(script_tab, "Python script", addSpace=True, orientation="horizontal")
        script_box.layout().addWidget(self.wofry_script)

        self.runaction = widget.OWAction("Generate Wavefront", self)
        self.runaction.triggered.connect(self.generate)
        self.addAction(self.runaction)


        gui.separator(self.controlArea)
        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Generate", callback=self.generate)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)

        gui.separator(self.controlArea)

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT + 50)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        self.tab_sou = oasysgui.createTabPage(tabs_setting, "Generic Wavefront 1D Settings")

        box_energy = oasysgui.widgetBox(self.tab_sou, "Energy Settings", addSpace=False, orientation="vertical")

        gui.comboBox(box_energy, self, "units", label="Units in use", labelWidth=350,
                     items=["Electron Volts", "Meters"],
                     callback=self.set_Units,
                     sendSelectedValue=False, orientation="horizontal")

        self.units_box_1 = oasysgui.widgetBox(box_energy, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.units_box_1, self, "energy", "Photon Energy [eV]",
                          labelWidth=300, tooltip="energy", valueType=float, orientation="horizontal")

        self.units_box_2 = oasysgui.widgetBox(box_energy, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.units_box_2, self, "wavelength", "Photon Wavelength [m]",
                          labelWidth=300, tooltip="wavelength", valueType=float, orientation="horizontal")

        self.set_Units()

        box_space = oasysgui.widgetBox(self.tab_sou, "Space Settings", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(box_space, self, "number_of_points", "Number of Points",
                          labelWidth=300, tooltip="number_of_points", valueType=int, orientation="horizontal")

        gui.comboBox(box_space, self, "initialize_from", label="Space Initialization", labelWidth=350,
                     items=["From Range", "From Steps"],
                     callback=self.set_Initialization,
                     sendSelectedValue=False, orientation="horizontal")

        self.initialization_box_1 = oasysgui.widgetBox(box_space, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_from", "From  [m]",
                          labelWidth=300, tooltip="range_from", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_to", "To [m]",
                          labelWidth=300, tooltip="range_to", valueType=float, orientation="horizontal")

        self.initialization_box_2 = oasysgui.widgetBox(box_space, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_start", "Start [m]",
                          labelWidth=300, tooltip="steps_start", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_step", "Step [m]",
                          labelWidth=300, tooltip="steps_step", valueType=float, orientation="horizontal")

        self.set_Initialization()



        box_amplitude = oasysgui.widgetBox(self.tab_sou, "Amplitude and phase Settings", addSpace=False, orientation="vertical")

        gui.comboBox(box_amplitude, self, "kind_of_wave", label="Kind of Wave", labelWidth=350,
                     items=["Plane", "Spherical", "Gaussian", "Gaussian Shell-model"],
                     callback=self.set_KindOfWave,
                     sendSelectedValue=False, orientation="horizontal")


        self.plane_box = oasysgui.widgetBox(box_amplitude, "", addSpace=False, orientation="vertical", height=120)
        self.spherical_box = oasysgui.widgetBox(box_amplitude, "", addSpace=False, orientation="vertical", height=90)
        self.gaussian_box = oasysgui.widgetBox(box_amplitude, "", addSpace=False, orientation="vertical", height=90)
        self.gsm_box = oasysgui.widgetBox(box_amplitude, "", addSpace=False, orientation="vertical", height=120)

        # --- PLANE

        oasysgui.lineEdit(self.plane_box, self, "inclination", "Inclination [rad]",
                          labelWidth=300, tooltip="inclination", valueType=float, orientation="horizontal")

        gui.comboBox(self.plane_box, self, "initialize_amplitude", label="Amplitude Initialization", labelWidth=350,
                     items=["Complex", "Amplitude and Phase"],
                     callback=self.set_Amplitude,
                     sendSelectedValue=False, orientation="horizontal")

        self.amplitude_box_1 = oasysgui.widgetBox(self.plane_box, "", addSpace=False, orientation="horizontal", height=50)

        oasysgui.lineEdit(self.amplitude_box_1, self, "complex_amplitude_re", "Complex Amplitude ",
                          labelWidth=250, tooltip="complex_amplitude_re", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.amplitude_box_1, self, "complex_amplitude_im", " + ",
                          valueType=float, tooltip="complex_amplitude_im", orientation="horizontal")

        oasysgui.widgetLabel(self.amplitude_box_1, "i", labelWidth=15)

        self.amplitude_box_2 = oasysgui.widgetBox(self.plane_box, "", addSpace=False, orientation="vertical", height=50)

        oasysgui.lineEdit(self.amplitude_box_2, self, "amplitude", "Amplitude",
                          labelWidth=300, tooltip="amplitude", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.amplitude_box_2, self, "phase", "Phase",
                          labelWidth=300, tooltip="phase", valueType=float, orientation="horizontal")

        self.set_Amplitude()

        # ------ SPHERIC

        oasysgui.lineEdit(self.spherical_box, self, "radius", "Radius [m]",
                          labelWidth=300, tooltip="radius", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.spherical_box, self, "center", "Center [m]",
                          labelWidth=300, tooltip="center", valueType=float, orientation="horizontal")

        amplitude_box_3 = oasysgui.widgetBox(self.spherical_box, "", addSpace=False, orientation="horizontal", height=50)

        oasysgui.lineEdit(amplitude_box_3, self, "complex_amplitude_re", "Complex Amplitude ",
                          labelWidth=250, tooltip="complex_amplitude_re", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(amplitude_box_3, self, "complex_amplitude_im", " + ",
                          valueType=float, tooltip="complex_amplitude_im", orientation="horizontal")

        oasysgui.widgetLabel(amplitude_box_3, "i", labelWidth=15)

        # ---- GAUSSIAN

        oasysgui.lineEdit(self.gaussian_box, self, "gaussian_sigma", "Sigma I",
                          labelWidth=250, tooltip="gaussian_sigma", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.gaussian_box, self, "gaussian_amplitude", "Amplitude of the Spectral Density",
                          labelWidth=250, tooltip="gaussian_amplitude", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.gaussian_box, self, "gaussian_shift", "Center",
                          labelWidth=250, tooltip="gaussian_shift", valueType=float, orientation="horizontal")

        # ---- GAUSSIAN SHELL MODEL

        oasysgui.lineEdit(self.gsm_box, self, "gaussian_sigma", "Sigma I",
                          labelWidth=250, tooltip="gaussian_sigma", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.gsm_box, self, "gaussian_beta", "beta = Sigma Mu/Sigma I",
                          labelWidth=250, tooltip="gaussian_beta", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.gsm_box, self, "gaussian_amplitude", "Amplitude of the Spectral Density",
                          labelWidth=250, tooltip="gaussian_amplitude", valueType=float, orientation="horizontal")


        mode_index_box = oasysgui.widgetBox(self.gsm_box, "", addSpace=True, orientation="horizontal", ) #width=550, height=50)
        tmp = oasysgui.lineEdit(mode_index_box, self, "mode_index", "Mode",
                          labelWidth=200, tooltip="mode_index", valueType=int, orientation="horizontal")
        gui.button(mode_index_box, self, "+1", callback=self.increase_mode_index)


        oasysgui.lineEdit(self.gsm_box, self, "gaussian_shift", "Center",
                          labelWidth=250, tooltip="gaussian_shift", valueType=float, orientation="horizontal")

        gui.checkBox(box_amplitude, self, "add_random_phase", "Add random phase")


        self.set_KindOfWave()

    def increase_mode_index(self):
        self.mode_index += 1
        self.generate()

    def set_Units(self):
        self.units_box_1.setVisible(self.units == 0)
        self.units_box_2.setVisible(self.units == 1)

    def set_Initialization(self):
        self.initialization_box_1.setVisible(self.initialize_from == 0)
        self.initialization_box_2.setVisible(self.initialize_from == 1)

    def set_Amplitude(self):
        self.amplitude_box_1.setVisible(self.initialize_amplitude == 0)
        self.amplitude_box_2.setVisible(self.initialize_amplitude == 1)

    def set_KindOfWave(self):
        self.plane_box.setVisible(self.kind_of_wave == 0)
        self.spherical_box.setVisible(self.kind_of_wave == 1)
        self.gaussian_box.setVisible(self.kind_of_wave == 2)
        self.gsm_box.setVisible(self.kind_of_wave == 3)

    def initializeTabs(self):
        size = len(self.tab)
        indexes = range(0, size)

        for index in indexes:
            self.tabs.removeTab(size-1-index)

        self.tab = []
        self.plot_canvas = []

        for index in range(0, len(self.titles)):
            self.tab.append(gui.createTabPage(self.tabs, self.titles[index]))
            self.plot_canvas.append(None)

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)


    def check_fields(self):
        if self.units == 0:
            congruence.checkStrictlyPositiveNumber(self.energy, "Energy")
        else:
            congruence.checkStrictlyPositiveNumber(self.wavelength, "Wavelength")
        congruence.checkStrictlyPositiveNumber(self.number_of_points, "Number of Points")

        if self.initialize_from == 0:
            congruence.checkGreaterThan(self.range_to, self.range_from, "Range To", "Range From")
        else:
            congruence.checkStrictlyPositiveNumber(self.steps_step, "Step")

        if self.kind_of_wave == 0:
            congruence.checkPositiveNumber(numpy.abs(self.inclination), "Inclination")
        elif self.kind_of_wave == 1:
            congruence.checkStrictlyPositiveNumber(numpy.abs(self.radius), "Radius")
            congruence.checkPositiveNumber(numpy.abs(self.center), "Center")
        elif self.kind_of_wave > 1:
            congruence.checkStrictlyPositiveNumber(self.gaussian_sigma, "Sigma")
            congruence.checkStrictlyPositiveNumber(self.gaussian_amplitude, "Amplitude of the Gaussian")
            congruence.checkNumber(self.gaussian_shift, "Center of the Gaussian")

            if self.kind_of_wave == 3:
                congruence.checkPositiveNumber(self.mode_index, "Mode")


    def generate(self):
        if True: # try:
            self.wofry_output.setText("")

            self.wofry_output.setText("")

            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            self.progressBarInit()

            self.check_fields()

            if self.initialize_from == 0:
                self.wavefront1D = GenericWavefront1D.initialize_wavefront_from_range(x_min=self.range_from, x_max=self.range_to, number_of_points=self.number_of_points)
            else:
                self.wavefront1D = GenericWavefront1D.initialize_wavefront_from_steps(x_start=self.steps_start, x_step=self.steps_step, number_of_points=self.number_of_points)

            if self.units == 0:
                self.wavefront1D.set_photon_energy(self.energy)
            else:
                self.wavefront1D.set_wavelength(self.wavelength)

            if self.kind_of_wave == 0: #plane
                if self.initialize_amplitude == 0:
                    self.wavefront1D.set_plane_wave_from_complex_amplitude(complex_amplitude=complex(
                        self.complex_amplitude_re, self.complex_amplitude_im), inclination=self.inclination)
                else:
                    self.wavefront1D.set_plane_wave_from_amplitude_and_phase(amplitude=self.amplitude, phase=self.phase,
                                                                             inclination=self.inclination)
            elif self.kind_of_wave == 1: # spheric
                self.wavefront1D.set_spherical_wave(radius=self.radius, center=self.center,
                                    complex_amplitude=complex(self.complex_amplitude_re, self.complex_amplitude_im))
            elif self.kind_of_wave == 2: # gaussian
                self.wavefront1D.set_gaussian(sigma_x=self.gaussian_sigma, amplitude=self.gaussian_amplitude,
                                              shift=self.gaussian_shift)
            elif self.kind_of_wave == 3: # g.s.m.
                self.wavefront1D.set_gaussian_hermite_mode(sigma_x=self.gaussian_sigma, amplitude=self.gaussian_amplitude,
                                                           mode_x=self.mode_index, shift=self.gaussian_shift, beta=self.gaussian_beta)

            if self.add_random_phase:
                self.wavefront1D.add_phase_shifts(2*numpy.pi*numpy.random.random(self.wavefront1D.size()))

            try:
                current_index = self.tabs.currentIndex()
            except:
                current_index = None


            if self.view_type != 0:
                self.initializeTabs()
                self.plot_results()
                if current_index is not None:
                    try:
                        self.tabs.setCurrentIndex(current_index)
                    except:
                        pass
            else:
                self.progressBarFinished()

            self.wofry_script.set_code(self.generate_python_code())

            try:
                self.send("WofryData", WofryData(wavefront=self.wavefront1D))
            except:
                pass
        # except Exception as exception:
        #     QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)
        #
        #     if self.IS_DEVELOP: raise exception
        #
        #     self.progressBarFinished()

    def generate_python_code(self):

        txt = ""

        txt += "#"
        txt += "\n# create input_wavefront\n#"
        txt += "\n#"
        txt += "\nfrom wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D"

        if self.initialize_from == 0:
            txt += "\ninput_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=%g,x_max=%g,number_of_points=%d)"%\
            (self.range_from,self.range_to,self.number_of_points)

        else:
            txt += "\ninput_wavefront = GenericWavefront1D.initialize_wavefront_from_steps(x_start=%g, x_step=%g,number_of_points=%d)"%\
                   (self.steps_start,self.steps_step,self.number_of_points)

        if self.units == 0:
            txt += "\ninput_wavefront.set_photon_energy(%g)"%(self.energy)
        else:
            txt += "\ninput_wavefront.set_wavelength(%g)"%(self.wavelength)



        if self.kind_of_wave == 0: #plane
            if self.initialize_amplitude == 0:
                txt += "\ninput_wavefront.set_plane_wave_from_complex_amplitude(complex_amplitude=complex(%g,%g),inclination=%g)"%\
                       (self.complex_amplitude_re,self.complex_amplitude_im,self.inclination)
            else:
                txt += "\ninput_wavefront.set_plane_wave_from_amplitude_and_phase(amplitude=%g,phase=%g,inclination=%g)"%(self.amplitude,self.phase,self.inclination)
        elif self.kind_of_wave == 1: # spheric
            txt += "\ninput_wavefront.set_spherical_wave(radius=%g,center=%g,complex_amplitude=complex(%g, %g))"%\
                   (self.radius,self.center,self.complex_amplitude_re,self.complex_amplitude_im)
        elif self.kind_of_wave == 2: # gaussian
            txt += "\ninput_wavefront.set_gaussian(sigma_x=%f, amplitude=%f,shift=%f)"%\
                   (self.gaussian_sigma,self.gaussian_amplitude,self.gaussian_shift)
        elif self.kind_of_wave == 3: # g.s.m.
            txt += "\ninput_wavefront.set_gaussian_hermite_mode(sigma_x=%g,amplitude=%g,mode_x=%d,shift=%f,beta=%g)"%\
                   (self.gaussian_sigma, self.gaussian_amplitude, self.mode_index, self.gaussian_shift, self.gaussian_beta)

            #
            # if self.add_random_phase:
            #     self.wavefront1D.add_phase_shifts(2*numpy.pi*numpy.random.random(self.wavefront1D.size()))
        if self.add_random_phase:
            txt += "\ninput_wavefront.add_phase_shifts(2*numpy.pi*numpy.random.random(input_wavefront.size()))"

        txt += "\n\n\nfrom srxraylib.plot.gol import plot"
        txt += "\nplot(input_wavefront.get_abscissas(),input_wavefront.get_intensity())"

        return txt


    def do_plot_results(self, progressBarValue=80):
        if not self.wavefront1D is None:

            self.progressBarSet(progressBarValue)


            self.plot_data1D(x=1e6*self.wavefront1D.get_abscissas(),
                             y=self.wavefront1D.get_intensity(),
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=0,
                             plot_canvas_index=0,
                             calculate_fwhm=True,
                             title=self.titles[0],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Intensity")

            self.plot_data1D(x=1e6*self.wavefront1D.get_abscissas(),
                             y=self.wavefront1D.get_phase(from_minimum_intensity=0.1,unwrap=1),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=1,
                             plot_canvas_index=1,
                             calculate_fwhm=False,
                             title=self.titles[1],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Phase [unwrapped, for intensity > 10% of peak] (rad)")

            self.plot_data1D(x=1e6*self.wavefront1D.get_abscissas(),
                             y=numpy.real(self.wavefront1D.get_complex_amplitude()),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=2,
                             plot_canvas_index=2,
                             calculate_fwhm=False,
                             title=self.titles[2],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Real(Amplitude)")

            self.plot_data1D(x=1e6*self.wavefront1D.get_abscissas(),
                             y=numpy.imag(self.wavefront1D.get_complex_amplitude()),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=3,
                             plot_canvas_index=3,
                             calculate_fwhm=False,
                             title=self.titles[3],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Imag(Amplitude)")


            self.plot_canvas[0].resetZoom()

            self.progressBarFinished()

    def receive_trigger_signal(self, trigger):

        if trigger and trigger.new_object == True:
            if trigger.has_additional_parameter("variable_name"):
                variable_name = trigger.get_additional_parameter("variable_name").strip()
                variable_display_name = trigger.get_additional_parameter("variable_display_name").strip()
                variable_value = trigger.get_additional_parameter("variable_value")
                variable_um = trigger.get_additional_parameter("variable_um")

                if "," in variable_name:
                    variable_names = variable_name.split(",")

                    for variable_name in variable_names:
                        setattr(self, variable_name.strip(), variable_value)
                else:
                    setattr(self, variable_name, variable_value)

                self.generate()

if __name__ == '__main__':

    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    ow = OWGenericWavefront1D()
    ow.show()
    app.exec_()
    ow.saveSettings()
