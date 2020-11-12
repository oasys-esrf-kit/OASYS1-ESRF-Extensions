import numpy
import sys
import scipy.constants as codata

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox
from orangewidget import gui
from orangewidget import widget
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import TriggerOut, EmittingStream

from syned.beamline.beamline import Beamline
from syned.storage_ring.magnetic_structures.undulator import Undulator

from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D
from wofry.propagator.util.gaussian_schell_model import GaussianSchellModel2D

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.esrf.wofry.util.wofry_light_source import WOLightSource
from orangecontrib.esrf.wofry.widgets.gui.ow_wofry_widget import WofryWidget # TODO: from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget
from orangecontrib.esrf.wofry.util.wofry_beamline import WOBeamline # TODO: from wofry...



class OWUndulatorGaussianShellModel2D(WofryWidget):

    name = "Undulator Gaussian Shell-model 2D"
    id = "UndulatorGSM2D"
    description = "Undulator approximated by Gaussian Shell-model 2D"
    icon = "icons/undulator_gsm_2d.png"
    priority = 20

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

    number_of_points_h = Setting(100)
    number_of_points_v = Setting(100)

    initialize_from = Setting(0)

    range_from_h  = Setting(-0.00005)
    range_to_h    = Setting(0.00005)
    steps_start_h = Setting(-0.0005)
    steps_step_h  = Setting(1e-6)
    range_from_v  = Setting(-0.00005)
    range_to_v    = Setting(0.00005)
    steps_start_v = Setting(-0.0005)
    steps_step_v  = Setting(1e-6)

    sigma_h=Setting(3.01836e-05)
    sigma_v=Setting(3.63641e-06)
    sigma_divergence_h=Setting(4.36821e-06)
    sigma_divergence_v=Setting(1.37498e-06)

    photon_energy=Setting(15000.0)
    undulator_length=Setting(4.0)

    use_emittances = Setting(1)
    mode_index = Setting(0)

    spectral_density_threshold = Setting(0.99)

    wavefront2D = None
    _gsm_2d = None

    def __init__(self):
        super().__init__(is_automatic=False, show_view_options=True, show_script_tab=True)

        self.runaction = widget.OWAction("Generate Wavefront", self)
        self.runaction.triggered.connect(self.generate)
        self.addAction(self.runaction)

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


        box_space = oasysgui.widgetBox(self.tab_sou, "Wavefront Sampling", addSpace=False, orientation="vertical")

        number_of_points_box = oasysgui.widgetBox(box_space, "", addSpace=False, orientation="horizontal")

        oasysgui.lineEdit(number_of_points_box, self, "number_of_points_h", "Number of Points                    (H)",
                          labelWidth=200, tooltip="number_of_points_h",
                          valueType=int, orientation="horizontal")
        oasysgui.lineEdit(number_of_points_box, self, "number_of_points_v", "x (V)",
                          tooltip="number_of_points_v", valueType=int, orientation="horizontal")

        gui.comboBox(box_space, self, "initialize_from", label="Space Initialization", labelWidth=350,
                     items=["From Range", "From Steps"],
                     callback=self.set_Initialization,
                     sendSelectedValue=False, orientation="horizontal")

        self.initialization_box_1 = oasysgui.widgetBox(box_space, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_from_h", "(H) From [m]",
                          labelWidth=300, tooltip="range_from_h", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_to_h", "          To [m]",
                          labelWidth=300, tooltip="range_to_h", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_from_v", "(V) From [m]",
                          labelWidth=300, tooltip="range_from_v", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_to_v", "          To [m]",
                          labelWidth=300, tooltip="range_to_v", valueType=float, orientation="horizontal")

        self.initialization_box_2 = oasysgui.widgetBox(box_space, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_start_h", "(H) Start [m]",
                          labelWidth=300, tooltip="steps_start_h", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_step_h", "      Step [m]",
                          labelWidth=300, tooltip="steps_step_h", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_start_v", "(V) Start [m]",
                          labelWidth=300, tooltip="steps_start_v", valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_step_v", "      Step [m]",
                          labelWidth=300, tooltip="steps_step_v", valueType=float, orientation="horizontal")

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
                     items=["No (coherent Gaussian Source)", "Yes (Gaussian Shell-model)"],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.mode_index_box = oasysgui.widgetBox(left_box_4, "", addSpace=True, orientation="vertical", )

        left_box_5 = oasysgui.widgetBox(self.mode_index_box, "", addSpace=True, orientation="horizontal", )
        oasysgui.lineEdit(left_box_5, self, "mode_index", "Mode", valueType=int,
                        labelWidth=200, tooltip = "mode_index",
                        orientation="horizontal")

        gui.button(left_box_5, self, "+1", callback=self.increase_mode_index, width=30)
        gui.button(left_box_5, self, "-1", callback=self.decrease_mode_index, width=30)
        gui.button(left_box_5, self,  "0", callback=self.reset_mode_index, width=30)

        oasysgui.lineEdit(self.mode_index_box, self, "spectral_density_threshold",
                          "Spectral Density Threshold (e.g. 0.99)",
                          labelWidth=250, tooltip="spectral_density_threshold",
                          valueType=float, orientation="horizontal")



        self.emittances_box = oasysgui.widgetBox(self.tab_emit, "Electron beam sizes", addSpace=True,
                                                 orientation="vertical")

        self.le_sigma_h = oasysgui.lineEdit(self.emittances_box, self, "sigma_h", "Size RMS H",
                                            labelWidth=250, tooltip="sigma_h",
                                            valueType=float, orientation="horizontal")
        self.le_sigma_v = oasysgui.lineEdit(self.emittances_box, self, "sigma_v", "Size RMS V",
                                            labelWidth=250, tooltip="sigma_v",
                                            valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.emittances_box, self, "sigma_divergence_h", "Divergence RMS H [rad]",
                          labelWidth=250, tooltip="sigma_divergence_h",
                          valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.emittances_box, self, "sigma_divergence_v", "Divergence RMS V [rad]",
                          labelWidth=250, tooltip="sigma_divergence_v",
                          valueType=float, orientation="horizontal")

        self.set_visible()

    def set_visible(self):
        self.emittances_box.setVisible(self.use_emittances == 1)
        self.mode_index_box.setVisible(self.use_emittances == 1)

    def increase_mode_index(self):
        self.mode_index += 1
        try:
            nmax = (self._n_h) * (self._n_v) - 1
            if self.mode_index > nmax: self.mode_index = nmax
        except:
            pass
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

        titles = ["Wavefront 2D","Cumulated occupation", "Eigenvalues map"]
        self.tab = []
        self.plot_canvas = []

        for index in range(0, len(titles)):
            self.tab.append(gui.createTabPage(self.tabs, titles[index]))
            self.plot_canvas.append(None)

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)


    def check_fields(self):
        congruence.checkStrictlyPositiveNumber(self.photon_energy, "Photon Energy")


        congruence.checkStrictlyPositiveNumber(self.number_of_points_h, "Number of Points (H)")
        congruence.checkStrictlyPositiveNumber(self.number_of_points_v, "Number of Points (V)")

        if self.initialize_from == 0:
            congruence.checkGreaterThan(self.range_to_h, self.range_from_h, "(H) Range To", "Range From")
            congruence.checkGreaterThan(self.range_to_v, self.range_from_v, "(V) Range To", "Range From")
        else:
            congruence.checkStrictlyPositiveNumber(self.steps_step_h, "Step (H)")
            congruence.checkStrictlyPositiveNumber(self.steps_step_v, "Step (V)")

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


    def calculate_gsm_parameters(self):

        wavelength = codata.h * codata.c / codata.e / self.photon_energy

        sigma_r = 2.740 / 4 / numpy.pi * numpy.sqrt(wavelength * self.undulator_length)
        sigma_r_prime = 0.69 * numpy.sqrt(wavelength / self.undulator_length)

        print("Radiation values at photon energy=%f eV:" % self.photon_energy)
        print("   intensity sigma      : %6.3f um,  FWHM: %6.3f um" % (sigma_r * 1e6, sigma_r * 2.355e6))
        print("   intensity sigmaprime: %6.3f urad, FWHM: %6.3f urad" % (sigma_r_prime * 1e6, sigma_r_prime * 2.355e6))

        if self.use_emittances == 0:
            sigmaI_h = sigma_r
            sigmaI_v = sigma_r
            beta_h, beta_v, ih, iv = 0, 0, 0, 0

        elif self.use_emittances == 1:
            Sx = numpy.sqrt(sigma_r ** 2 + self.sigma_h ** 2)
            Sxp = numpy.sqrt(sigma_r_prime ** 2 + self.sigma_divergence_h ** 2)
            Sy = numpy.sqrt(sigma_r ** 2 + self.sigma_v ** 2)
            Syp = numpy.sqrt(sigma_r_prime ** 2 + self.sigma_divergence_v ** 2)

            print("\nElectron beam values:")
            print("   sigma_h : %6.3f um, sigma_v: %6.3f um\n" % (self.sigma_h * 1e6, self.sigma_v * 1e6))
            print("\nPhoton beam values (convolution):")
            print("   SIGMA_H p: %6.3f um, SIGMA_V: %6.3f um\n" % (Sx * 1e6, Sy * 1e6))
            print("   SIGMA_H' : %6.3f urad, SIGMA_V': %6.3f urad\n" % (Sxp * 1e6, Syp * 1e6))

            cf_h = sigma_r * sigma_r_prime / Sx / Sxp
            cf_v = sigma_r * sigma_r_prime / Sy / Syp

            print("\nCoherence fraction (from emittances):")
            print("    CF_H: %6.5f, CF_V:%6.5f " % (cf_h, cf_v))

            beta_h = cf_h / numpy.sqrt(1 - cf_h)
            beta_v = cf_v / numpy.sqrt(1 - cf_v)

            sigmaI_h = Sx
            sigmaI_v = Sy
            sigmaMu_h = beta_h * sigmaI_h
            sigmaMu_v = beta_v * sigmaI_v

            print("\nGaussian Shell-model (matching coherence fraction):")
            print("    Horizontal:")
            print("       beta: %6.3f" % beta_h)
            print("       sigmaI : %6.3f um" % (sigmaI_h * 1e6))
            print("       sigmaMu: %6.3f um" % (sigmaMu_h * 1e6))
            print("    Vertical:")
            print("       beta: %6.3f" % beta_v)
            print("       sigmaI : %6.3f um" % (sigmaI_v * 1e6))
            print("       sigmaMu: %6.3f um" % (sigmaMu_v * 1e6))

            q_h = 1.0 / (1 + beta_h ** 2 / 2 + beta_h * numpy.sqrt(1 + (beta_h / 2) ** 2))
            q_v = 1.0 / (1 + beta_v ** 2 / 2 + beta_v * numpy.sqrt(1 + (beta_v / 2) ** 2))

            self._n_h = int(numpy.log(1.0 - self.spectral_density_threshold) / numpy.log(q_h))
            self._n_v = int(numpy.log(1.0 - self.spectral_density_threshold) / numpy.log(q_v))

            if self._n_h < 1: self._n_h = 1
            if self._n_v < 1: self._n_v = 1

            print(
                "\nTo consider %f of spectral density in each direction we need %d (H) x %d (V) modes (% d total modes)." % \
                (self.spectral_density_threshold, self._n_h, self._n_v, self._n_h * self._n_v))

            # this avoids to recalculate the eigenvalues map (time consuming) if only mode indices are changed
            if self._gsm_2d is None:
                self._gsm_2d = GaussianSchellModel2D(1.0, sigmaI_h, sigmaMu_h, sigmaI_v, sigmaMu_v)
            else:
                if (self._gsm_2d._mode_x._sigma_s == sigmaI_h) and \
                        (self._gsm_2d._mode_x._sigma_g == sigmaMu_h) and \
                        (self._gsm_2d._mode_y._sigma_s == sigmaI_v) and \
                        (self._gsm_2d._mode_y._sigma_g == sigmaMu_v) and \
                        (self._spectral_density_threshold_backup == self.spectral_density_threshold):
                    pass
                else:
                    self._gsm_2d = GaussianSchellModel2D(1.0, sigmaI_h, sigmaMu_h, sigmaI_v, sigmaMu_v)

            ih, iv = self._gsm_2d.sortedModeIndices(self.mode_index, n_points=self._n_h * self._n_v)

            print("2D mode index %d corresponds to (H,V)=(%d,%d) modes." % (self.mode_index, ih, iv))

        return sigmaI_h, sigmaI_v, beta_h, beta_v, ih, iv

    def get_light_source(self, sigmaI_h, sigmaI_v, beta_h, beta_v, ih, iv):

        return WOLightSource(
            name                = self.name                ,
            # electron_beam       = None  ,
            # magnetic_structure  = None  ,
            dimension           = 2           ,
            initialize_from     = self.initialize_from     ,
            range_from_h        = self.range_from_h        ,
            range_to_h          = self.range_to_h          ,
            range_from_v        = self.range_from_v       ,
            range_to_v          = self.range_to_v       ,
            steps_start_h       = self.steps_start_h       ,
            steps_step_h        = self.steps_step_h        ,
            steps_start_v       = self.steps_start_v       ,
            steps_step_v        = self.steps_step_v       ,
            number_of_points_h  = self.number_of_points_h  ,
            number_of_points_v  = self.number_of_points_v  ,
            energy              = self.photon_energy       ,
            sigma_h             = sigmaI_h             ,
            sigma_v             = sigmaI_v             ,
            amplitude           = 1.0           ,
            kind_of_wave        = (3 if (self.use_emittances > 0) else 2)  ,
            n_h                 = ih                 ,
            n_v                 = iv                 ,
            beta_h              = beta_h              ,
            beta_v              = beta_v          ,
            units               = 0,
            # wavelength          = 0,
            # initialize_amplitude= 0,
            # complex_amplitude_re= 0,
            # complex_amplitude_im= 0,
            # phase               = 0,
            # radius              = 0,
            # center              = 0,
            # inclination         = 0,
            # gaussian_shift      = 0,
            # add_random_phase    = 0,
        )


    def generate(self):

        try:
            self.wofry_output.setText("")

            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            self.progressBarInit()

            self.check_fields()

            if self.initialize_from == 0:
                self.wavefront2D = GenericWavefront2D.initialize_wavefront_from_range(
                    x_min=self.range_from_h, x_max=self.range_to_h,
                    y_min=self.range_from_v, y_max=self.range_to_v,
                    number_of_points=(self.number_of_points_h, self.number_of_points_v))
            else:
                self.wavefront2D = GenericWavefront2D.initialize_wavefront_from_steps(
                    x_start=self.steps_start_h, x_step=self.steps_step_h,
                    y_start=self.steps_start_v, y_step=self.steps_step_v,
                    number_of_points=(self.number_of_points_h, self.number_of_points_v))

            self.wavefront2D.set_photon_energy(self.photon_energy)

            sigmaI_h, sigmaI_v, beta_h, beta_v, ih, iv = self.calculate_gsm_parameters()

            light_source = self.get_light_source(sigmaI_h, sigmaI_v, beta_h, beta_v, ih, iv)
            self.wavefront2D = light_source.get_wavefront()


            if self.view_type > 0: # skip if no plots
                if self.use_emittances == 0:
                    self._cumulated_occupation = numpy.array([1.0])
                    self._eigenvalues_map = numpy.ones((1,1))
                else:
                    N = self._n_h * self._n_v
                    # compute cumulated occupation and eigenvalue map
                    sorted_array = []
                    for i in range(N):
                        ihh, ivv = self._gsm_2d.sortedModeIndices(i, n_points=N)
                        sorted_array.append([ihh, ivv])


                    eigenvalues_x = numpy.array([self._gsm_2d._mode_x.beta(i) for i in range(N)])
                    eigenvalues_y = numpy.array([self._gsm_2d._mode_y.beta(i) for i in range(N)])

                    eigenvalues = numpy.zeros(N)
                    for i in range(eigenvalues.size):
                        eigenvalues[i] = eigenvalues_x[sorted_array[i][0]] * \
                                         eigenvalues_y[sorted_array[i][1]]

                    self._cumulated_occupation = numpy.cumsum(eigenvalues)
                    self._eigenvalues_map = numpy.outer(eigenvalues_x[0:self._n_h],eigenvalues_y[0:self._n_v])
                    self._spectral_density_threshold_backup = self.spectral_density_threshold


            self.initializeTabs()
            self.plot_results()



            beamline = WOBeamline(light_source=light_source)

            try:
                self.wofry_script.set_code(beamline.to_python_code())
            except:
                pass

            self.send("WofryData", WofryData(wavefront=self.wavefront2D, beamline=beamline))

        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

            self.progressBarFinished()

    # def generate_python_code(self,sigmaI_h,sigmaI_v,ih,iv,beta_h,beta_v):
    #
    #
    #
    #     txt = "#"
    #     txt += "\n# create input_wavefront\n#"
    #     txt += "\n#"
    #     txt += "\nfrom wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D"
    #
    #     if self.initialize_from == 0:
    #         txt += "\ninput_wavefront = GenericWavefront2D.initialize_wavefront_from_range(x_min=%g,x_max=%g,y_min=%g,y_max=%g,number_of_points=(%d,%d))"%\
    #         (self.range_from_h,self.range_to_h,self.range_from_v,self.range_to_v,self.number_of_points_h, self.number_of_points_v)
    #
    #     else:
    #         txt += "\ninput_wavefront = GenericWavefront2D.initialize_wavefront_from_steps(x_start=%g, x_step=%g,y_start=%g,y_step=%g,"+\
    #                "number_of_points=(%d,%d))"%\
    #                (self.steps_start_h,self.steps_step_h,self.steps_start_v,self.steps_step_v,self.number_of_points_h,self.number_of_points_v)
    #
    #     txt += "\ninput_wavefront.set_photon_energy(%g)"%(self.photon_energy)
    #
    #     txt += "\ninput_wavefront.set_gaussian_hermite_mode(sigma_x=%g,sigma_y=%g,amplitude=1.0,nx=%d,ny=%d,betax=%g,betay=%g)"%\
    #             (sigmaI_h,sigmaI_v,ih,iv,beta_h,beta_v)
    #
    #     txt += "\n\n\nfrom srxraylib.plot.gol import plot_image"
    #     txt += "\nplot_image(input_wavefront.get_intensity(), input_wavefront.get_coordinate_x(),input_wavefront.get_coordinate_y())"
    #
    #     return txt

    def do_plot_results(self, progressBarValue):
        if not self.wavefront2D is None:

            self.progressBarSet(progressBarValue)

            titles = ["Wavefront 2D Intensity", "Cumulated occupation", "Eigenvalues map"]
            try:
                ih, iv = self._gsm_2d.sortedModeIndices(self.mode_index, n_points=self._n_h * self._n_v)
            except:
                ih, iv = 0, 0

            self.plot_data2D(data2D=self.wavefront2D.get_intensity(),
                             dataX=1e6 * self.wavefront2D.get_coordinate_x(),
                             dataY=1e6 * self.wavefront2D.get_coordinate_y(),
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=0,
                             plot_canvas_index=0,
                             title=titles[0] + "; mode index = %d = (%d, %d)" % (self.mode_index, ih, iv), xtitle="Horizontal [$\mu$m] ( %d pixels)" % (self.wavefront2D.get_coordinate_x().size),
                             ytitle="Vertical [$\mu$m] ( %d pixels)" % (self.wavefront2D.get_coordinate_y().size))

            self.plot_data1D(numpy.arange(self._cumulated_occupation.size),
                             self._cumulated_occupation / self._cumulated_occupation[-1],
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=1,
                             plot_canvas_index=1,
                             title=titles[1],
                             xtitle="mode index",
                             ytitle="Cumulated normalized occupation",
                             calculate_fwhm=False)


            nx, ny = self._eigenvalues_map.shape
            if nx > 1:
                dataX = numpy.arange(nx) * nx / (nx - 1)
            else:
                dataX = numpy.array([0,2])

            if ny > 1:
                dataY = numpy.arange(ny) * ny / (ny - 1)
            else:
                dataY = numpy.array([0,2])


            self.plot_data2D(data2D=self._eigenvalues_map / self._eigenvalues_map[0,0],
                             dataX=dataX,
                             dataY=dataY,
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=2,
                             plot_canvas_index=2,
                             title="Eigenvalue(n,m) / Eigenvalue(0,0)",
                             xtitle="H mode index n",
                             ytitle="V mode index m")


            self.progressBarFinished()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    a = QApplication(sys.argv)
    ow = OWUndulatorGaussianShellModel2D()

    ow.show()
    a.exec_()
    ow.saveSettings()
