import numpy
import sys

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox

from orangewidget import gui
from orangewidget import widget
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import TriggerIn, TriggerOut, EmittingStream

from syned.beamline.beamline import Beamline
from syned.storage_ring.magnetic_structures.undulator import Undulator

from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D
from wofry.propagator.util.gaussian_schell_model import GaussianSchellModel1D

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget
from orangecontrib.xoppy.util.python_script import PythonScript  # TODO: change import from wofry!!!


class OWUndulatorGaussianShellModel1D(WofryWidget):

    name = "Undulator Gaussian Shell-model 1D"
    id = "UndulatorGSM1D"
    description = "Undulator approximated by Gaussian Shell-model 1D"
    icon = "icons/undulator_gsm_1d.png"
    priority = 3

    category = "Wofry Wavefront Propagation"
    keywords = ["data", "file", "load", "read"]

    inputs = [
                ("SynedData", Beamline, "receive_syned_data"),
                ("Trigger", TriggerOut, "receive_trigger_signal"),
                ]
    outputs = [
               {"name":"WofryData",
                "type":WofryData,
                "doc":"WofryData",
                "id":"WofryData"}
                ]

    number_of_points = Setting(1000)
    initialize_from  = Setting(0)
    range_from       = Setting(-0.00005)
    range_to         = Setting(0.00005)
    steps_start      = Setting(-0.00005)
    steps_step       = Setting(1e-7)


    sigma_h = Setting(3.01836e-05)
    sigma_v = Setting(3.63641e-06)
    sigma_divergence_h = Setting(4.36821e-06)
    sigma_divergence_v = Setting(1.37498e-06)

    photon_energy = Setting(15000.0)
    undulator_length = Setting(4.0)

    use_emittances = Setting(1)
    mode_index = Setting(0)

    spectral_density_threshold = Setting(0.99)
    correction_factor = Setting(1.0)

    wavefront1D = None

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

        self.tab_sou = oasysgui.createTabPage(tabs_setting, "Settings")
        self.tab_emit = oasysgui.createTabPage(tabs_setting, "Emittances")


        box_space = oasysgui.widgetBox(self.tab_sou, "Wavefront sampling", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(box_space, self, "number_of_points", "Number of Points",
                          labelWidth=300, tooltip="number_of_points",
                          valueType=int, orientation="horizontal")

        gui.comboBox(box_space, self, "initialize_from", label="Space Initialization",
                     labelWidth=350,
                     items=["From Range", "From Steps"],
                     callback=self.set_Initialization,
                     sendSelectedValue=False, orientation="horizontal")

        self.initialization_box_1 = oasysgui.widgetBox(box_space, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_from", "From  [m]",
                          labelWidth=300, tooltip="range_from",
                          valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_to", "To [m]",
                          labelWidth=300, tooltip="range_to",
                          valueType=float, orientation="horizontal")

        self.initialization_box_2 = oasysgui.widgetBox(box_space, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_start", "Start [m]",
                          labelWidth=300, tooltip="steps_start",
                          valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_step", "Step [m]",
                          labelWidth=300, tooltip="steps_step",
                          valueType=float, orientation="horizontal")

        self.set_Initialization()


        left_box_3 = oasysgui.widgetBox(self.tab_sou, "Undulator Parameters", addSpace=True, orientation="vertical")

        oasysgui.lineEdit(left_box_3, self, "photon_energy", "Photon Energy [eV]",
                          labelWidth=250, tooltip="photon_energy",
                          valueType=float, orientation="horizontal")


        oasysgui.lineEdit(left_box_3, self, "undulator_length", "Undulator Length [m]",
                          labelWidth=250, tooltip="undulator_length",
                          valueType=float, orientation="horizontal")


        left_box_4 = oasysgui.widgetBox(self.tab_sou, "Working conditions", addSpace=True, orientation="vertical")

        gui.comboBox(left_box_4, self, "use_emittances", label="Use emittances", labelWidth=350,
                     items=["No (coherent Gaussian Source)",
                            "Yes (GSM H emittance)",
                            "Yes (GSM V emittance)"
                            ],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.mode_index_box = oasysgui.widgetBox(left_box_4, "", addSpace=True, orientation="vertical", )

        left_box_5 = oasysgui.widgetBox(self.mode_index_box, "", addSpace=True, orientation="horizontal", )
        tmp = oasysgui.lineEdit(left_box_5, self, "mode_index", "Mode",
                        labelWidth=200, valueType=int, tooltip = "mode_index",
                        orientation="horizontal")

        gui.button(left_box_5, self, "+1", callback=self.increase_mode_index, width=30)
        gui.button(left_box_5, self, "-1", callback=self.decrease_mode_index, width=30)
        gui.button(left_box_5, self,  "0", callback=self.reset_mode_index, width=30)

        oasysgui.lineEdit(self.mode_index_box, self, "spectral_density_threshold",
                          "Spectral Density Threshold (e.g. 0.99)",
                          labelWidth=300, tooltip="coherent_fraction_threshold",
                          valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.mode_index_box, self, "correction_factor",
                          "Correction factor for sigmaI (default 1.0)",
                          labelWidth=300, tooltip="correction_factor", valueType=float, orientation="horizontal")

        self.emittances_box_h = oasysgui.widgetBox(self.tab_emit, "Electron Horizontal beam sizes",
                                            addSpace=True, orientation="vertical")
        self.emittances_box_v = oasysgui.widgetBox(self.tab_emit, "Electron Vertical beam sizes",
                                            addSpace=True, orientation="vertical")


        self.le_sigma_h = oasysgui.lineEdit(self.emittances_box_h, self, "sigma_h", "Size RMS H",
                            labelWidth=250, tooltip="sigma_h",
                            valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.emittances_box_h, self, "sigma_divergence_h", "Divergence RMS H [rad]",
                            labelWidth=250, tooltip="sigma_divergence_h",
                            valueType=float, orientation="horizontal")


        self.le_sigma_v = oasysgui.lineEdit(self.emittances_box_v, self, "sigma_v", "Size RMS V",
                            labelWidth=250, tooltip="sigma_v",
                            valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.emittances_box_v, self, "sigma_divergence_v", "Divergence RMS V [rad]",
                            labelWidth=250, tooltip="sigma_divergence_v",
                            valueType=float, orientation="horizontal")

        self.set_visible()


    def set_visible(self):
        self.emittances_box_h.setVisible(self.use_emittances == 1)
        self.emittances_box_v.setVisible(self.use_emittances == 2)
        self.mode_index_box.setVisible(self.use_emittances >= 1)

    def increase_mode_index(self):
        self.mode_index += 1
        self.generate()

    def decrease_mode_index(self):
        self.mode_index -= 1
        if self.mode_index < 0: self.mode_index = 0
        self.generate()

    def reset_mode_index(self):
        self.mode_index = 0
        self.generate()

    def set_Initialization(self):
        self.initialization_box_1.setVisible(self.initialize_from == 0)
        self.initialization_box_2.setVisible(self.initialize_from == 1)


    def initializeTabs(self):
        size = len(self.tab)
        indexes = range(0, size)

        for index in indexes:
            self.tabs.removeTab(size-1-index)

        self.titles = ["Wavefront 1D","Cumulated occupation"]
        self.tab = []
        self.plot_canvas = []

        for index in range(0, len(self.titles)):
            self.tab.append(gui.createTabPage(self.tabs, self.titles[index]))
            self.plot_canvas.append(None)

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)


    def check_fields(self):
        congruence.checkStrictlyPositiveNumber(self.photon_energy, "Photon Energy")

        if self.initialize_from == 0:
            congruence.checkGreaterThan(self.range_to, self.range_from, "Range To", "Range From")
        else:
            congruence.checkStrictlyPositiveNumber(self.steps_step, "Step")

        congruence.checkStrictlyPositiveNumber(self.number_of_points, "Number of Points")

        congruence.checkNumber(self.mode_index, "Mode index")


    def receive_syned_data(self, data):
        if not data is None:
            if isinstance(data, Beamline):
                if not data._light_source is None:
                    if isinstance(data._light_source._magnetic_structure, Undulator):
                        light_source = data._light_source

                        self.photon_energy =  round(light_source._magnetic_structure.resonance_energy(light_source._electron_beam.gamma()), 3)

                        x, xp, y, yp = light_source._electron_beam.get_sigmas_all()

                        self.sigma_h = x
                        self.sigma_v = y
                        self.sigma_divergence_h = xp
                        self.sigma_divergence_v = yp
                        self.undulator_length = light_source._magnetic_structure._period_length*light_source._magnetic_structure._number_of_periods # in meter
                    else:
                        raise ValueError("Syned light source not congruent")
                else:
                    raise ValueError("Syned data not correct: light source not present")
            else:
                raise ValueError("Syned data not correct")

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

    def generate(self):
        try:
            self.wofry_output.setText("")

            sys.stdout = EmittingStream(textWritten=self.writeStdOut)


            self.progressBarInit()

            self.check_fields()

            if self.initialize_from == 0:
                self.wavefront1D = GenericWavefront1D.initialize_wavefront_from_range(x_min=self.range_from, x_max=self.range_to, number_of_points=self.number_of_points)
            else:
                self.wavefront1D = GenericWavefront1D.initialize_wavefront_from_steps(x_start=self.steps_start, x_step=self.steps_step, number_of_points=self.number_of_points)

            self.wavefront1D.set_photon_energy(self.photon_energy)
            wavelength = self.wavefront1D.get_wavelength()


            sigma_r = 2.740 / 4 / numpy.pi * numpy.sqrt(wavelength * self.undulator_length)
            sigma_r_prime = 0.69 * numpy.sqrt(wavelength / self.undulator_length)


            print("Radiation values at photon energy=%f eV:" % self.photon_energy)
            print("   intensity sigma      : %6.3f um,  FWHM: %6.3f um" % (sigma_r * 1e6, sigma_r * 2.355e6))
            print("   intensity sigmaprime: %6.3f urad, FWHM: %6.3f urad" % (sigma_r_prime * 1e6, sigma_r_prime * 2.355e6))

            if self.use_emittances == 0:
                sigmaI = sigma_r
                self.wavefront1D.set_gaussian(sigmaI, amplitude=1.0)
                beta = None

            else:
                Sx  = numpy.sqrt( sigma_r**2       + self.sigma_h**2)
                Sxp = numpy.sqrt( sigma_r_prime**2 + self.sigma_divergence_h**2)
                Sy  = numpy.sqrt( sigma_r**2       + self.sigma_v**2)
                Syp = numpy.sqrt( sigma_r_prime**2 + self.sigma_divergence_v**2)
                print("\nElectron beam values:")
                print("   sigma_h : %6.3f um, sigma_v: %6.3f um\n" % (self.sigma_h * 1e6, self.sigma_v * 1e6))
                print("\nPhoton beam values (convolution):")
                print("   SIGMA_H p: %6.3f um, SIGMA_V: %6.3f um\n" % (Sx * 1e6, Sy * 1e6))
                print("   SIGMA_H' : %6.3f urad, SIGMA_V': %6.3f urad\n" % (Sxp * 1e6, Syp * 1e6))

                labels = ["", "H", "V"]
                if self.use_emittances == 1:
                    cf = sigma_r * sigma_r_prime / Sx / Sxp
                    sigmaI = Sx
                elif self.use_emittances == 2:
                    cf = sigma_r * sigma_r_prime / Sy / Syp
                    sigmaI = Sy

                print("\nCoherence fraction (from %s emittance): %f" % (labels[self.use_emittances], cf))

                sigmaI *= self.correction_factor
                beta = cf / numpy.sqrt(1 - cf)
                sigmaMu = beta * sigmaI

                print("\nGaussian Shell-model (matching coherence fraction in %s direction):" % \
                      labels[self.use_emittances])
                print("       beta: %6.3f" % beta)
                print("       sigmaI : %6.3f um" % (sigmaI  * 1e6))
                print("       sigmaMu: %6.3f um" % (sigmaMu * 1e6))

                q = 1.0 / (1 + beta ** 2 / 2 + beta * numpy.sqrt(1 + (beta / 2) ** 2))

                # print(">>>>", cumulated_occupation, 1.0 - cumulated_occupation)
                _n = int(numpy.log(1.0 - self.spectral_density_threshold) / numpy.log(q))


                if _n < 1: _n = 1

                print("\nTo consider %f of spectral density in %s we need %d modes." % \
                      (self.spectral_density_threshold, labels[self.use_emittances], _n))

                _gsm_1d = GaussianSchellModel1D(1.0, sigmaI, sigmaMu)

                self.wavefront1D.set_gaussian_hermite_mode(
                    sigmaI, self.mode_index, amplitude=1.0, shift=0.0, beta=beta)


            if self.use_emittances == 0:
                self._cumulated_occupation = numpy.array([1.0])
            else:
                indices = numpy.arange(_n)
                self._cumulated_occupation = (1.0 - q ** (indices+1))

            if self.view_type != 0:
                self.initializeTabs()
                self.plot_results()
            else:
                self.progressBarFinished()

            self.wofry_script.set_code(self.generate_python_code(sigmaI,beta))

            self.send("WofryData", WofryData(wavefront=self.wavefront1D))

        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

            self.progressBarFinished()

    def generate_python_code(self,sigmaI,beta=1.0):

        txt = "#"
        txt += "\n# create input_wavefront\n#"
        txt += "\n#"
        txt += "\nfrom wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D"

        if self.initialize_from == 0:
            txt += "\ninput_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=%g,x_max=%g,number_of_points=%d)"%\
            (self.range_from,self.range_to,self.number_of_points)

        else:
            txt += "\ninput_wavefront = GenericWavefront1D.initialize_wavefront_from_steps(x_start=%g, x_step=%g,number_of_points=%d)"%\
                   (self.steps_start,self.steps_step,self.number_of_points)

        txt += "\ninput_wavefront.set_photon_energy(%g)"%(self.photon_energy)

        if self.use_emittances == 0:
            txt += "\ninput_wavefront.set_gaussian(%g, amplitude=1.0)"%(sigmaI)
        else:
            txt += "\ninput_wavefront.set_gaussian_hermite_mode(%g, %d, amplitude=1.0, shift=0.0, beta=%g)" % \
                    (sigmaI, self.mode_index, beta)

        txt += "\n\n\nfrom srxraylib.plot.gol import plot"
        txt += "\nplot(input_wavefront.get_abscissas(),input_wavefront.get_intensity())"

        return txt

    def do_plot_results(self, progressBarValue):
        if not self.wavefront1D is None:

            self.progressBarSet(progressBarValue)

            self.plot_data1D(1e6 * self.wavefront1D.get_abscissas(),
                             self.wavefront1D.get_intensity(),
                             # self._cumulated_occupation / self._cumulated_occupation[-1],
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=0,
                             plot_canvas_index=0,
                             title=self.titles[0],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Intensity",
                             calculate_fwhm=True)


            self.plot_data1D(numpy.arange(self._cumulated_occupation.size),
                             # self.wavefront1D.get_intensity(),
                             self._cumulated_occupation,
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=1,
                             plot_canvas_index=1,
                             title=self.titles[1],
                             xtitle="mode index",
                             ytitle="Cumulated occupation",
                             calculate_fwhm=False)


            #
            #
            # nx, ny = self._eigenvalues_map.shape
            #
            # tx = 1
            # ty = 1
            # if nx > 1:
            #     dataX = numpy.arange(nx) * nx / (nx - 1)
            # else:
            #     dataX = numpy.array([0,2])
            #
            # if ny > 1:
            #     dataY = numpy.arange(ny) * ny / (ny - 1)
            # else:
            #     dataY = numpy.array([0,2])
            #
            #
            # self.plot_data2D(data2D=self._eigenvalues_map / self._eigenvalues_map[0,0],
            #                  dataX=dataX,
            #                  dataY=dataY,
            #                  progressBarValue=progressBarValue,
            #                  tabs_canvas_index=2,
            #                  plot_canvas_index=2,
            #                  title="Eigenvalue(n,m) / Eigenvalue(0,0)",
            #                  xtitle="H mode index n",
            #                  ytitle="V mode index m")


            self.progressBarFinished()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    a = QApplication(sys.argv)
    ow = OWUndulatorGaussianShellModel1D()

    ow.show()
    a.exec_()
    ow.saveSettings()
