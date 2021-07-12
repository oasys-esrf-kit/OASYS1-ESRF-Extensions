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

from syned.storage_ring.magnetic_structures.undulator import Undulator
from syned.beamline.beamline import Beamline

from wofryimpl.propagator.light_source import WOLightSource
from wofryimpl.beamline.beamline import WOBeamline

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget

import scipy.constants as codata

from wofryimpl.propagator.util.undulator_coherent_mode_decomposition_1d import UndulatorCoherentModeDecomposition1D
from syned.storage_ring.electron_beam import ElectronBeam
from syned.storage_ring.magnetic_structures.undulator import Undulator
from orangecontrib.esrf.wofry.util.light_source import WOLightSourceCMD


class OWUndulatorCoherentModeDecomposition1D(WofryWidget):

    name = "Undulator Coherent Mode Decomposition 1D"
    id = "UndulatorCMD1D"
    description = "Undulator Coherent Mode Decomposition 1D"
    icon = "icons/undulator_cmd_1d.png"
    priority = 0.4

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

    number_of_points = Setting(200)
    initialize_from  = Setting(0)
    range_from       = Setting(-0.000125)
    range_to         = Setting( 0.000125)
    steps_start      = Setting(-0.00005)
    steps_step       = Setting(1e-7)


    sigma_h = Setting(3.01836e-05)
    sigma_v = Setting(3.63641e-06)
    sigma_divergence_h = Setting(4.36821e-06)
    sigma_divergence_v = Setting(1.37498e-06)

    photon_energy = Setting(10000.0)

    period_length = Setting(0.020)
    number_of_periods = Setting(100)
    K_vertical = Setting(1.19)
    electron_energy_in_GeV = Setting(6.0)
    ring_current = Setting(0.2)
    # sigma_h sigma_divergence_h sigma_v sigma_divergence_v




    flag_gsm = Setting(0)
    scan_direction_flag = Setting(0)
    mode_index = Setting(0)

    spectral_density_threshold = Setting(0.99)
    correction_factor = Setting(1.0)

    # to store calculations
    coherent_mode_decomposition = None
    coherent_mode_decomposition_results = None

    def __init__(self):

        super().__init__(is_automatic=False, show_view_options=True, show_script_tab=True)

        self.runaction = widget.OWAction("Generate Wavefront", self)
        self.runaction.triggered.connect(self.calculate_and_send_mode)
        self.addAction(self.runaction)


        gui.separator(self.controlArea)
        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Calculate and Send mode", callback=self.calculate_and_send_mode)
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

        self.tab_settings = oasysgui.createTabPage(tabs_setting, "Settings")
        self.tab_lightsource = oasysgui.createTabPage(tabs_setting, "Light Source")

        #
        # Settings
        #
        box_space = oasysgui.widgetBox(self.tab_settings, "Sampling coordinates", addSpace=False, orientation="vertical")

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
                          labelWidth=200, tooltip="range_from",
                          valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_1, self, "range_to", "To [m]",
                          labelWidth=200, tooltip="range_to",
                          valueType=float, orientation="horizontal")

        self.initialization_box_2 = oasysgui.widgetBox(box_space, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_start", "Start [m]",
                          labelWidth=300, tooltip="steps_start",
                          valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.initialization_box_2, self, "steps_step", "Step [m]",
                          labelWidth=300, tooltip="steps_step",
                          valueType=float, orientation="horizontal")

        self.set_Initialization()


        left_box_3 = oasysgui.widgetBox(self.tab_settings, "Setting", addSpace=True, orientation="vertical")

        left_box_33 = oasysgui.widgetBox(left_box_3, "", addSpace=True, orientation="horizontal")
        oasysgui.lineEdit(left_box_33, self, "photon_energy", "Photon Energy [eV]",
                          labelWidth=200, tooltip="photon_energy",
                          valueType=float, orientation="horizontal")
        gui.button(left_box_33, self, "set from K", callback=self.set_photon_energy, width=80)


        gui.comboBox(left_box_3, self, "flag_gsm", label="Decomposition", labelWidth=120,
                     items=["Undulator Coherent Mode Decomposition",
                            "Gaussian Shell-model approximation",
                            ],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(left_box_3, self, "scan_direction_flag", label="Direction", labelWidth=350,
                     items=["Horizontal",
                            "Vertical"
                            ],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        left_box_3 = oasysgui.widgetBox(self.tab_settings, "Send Wavefront", addSpace=True, orientation="vertical")
        self.mode_index_box = oasysgui.widgetBox(left_box_3, "", addSpace=True, orientation="vertical", )

        left_box_5 = oasysgui.widgetBox(self.mode_index_box, "", addSpace=True, orientation="horizontal", )
        tmp = oasysgui.lineEdit(left_box_5, self, "mode_index", "Send mode",
                        labelWidth=200, valueType=int, tooltip = "mode_index",
                        orientation="horizontal", callback=self.send_mode)

        gui.button(left_box_5, self, "+1", callback=self.increase_mode_index, width=30)
        gui.button(left_box_5, self, "-1", callback=self.decrease_mode_index, width=30)
        gui.button(left_box_5, self,  "0", callback=self.reset_mode_index, width=30)

        #
        # Light Source
        #

        storage_ring_box = oasysgui.widgetBox(self.tab_lightsource, "Storage Ring",
                                            addSpace=True, orientation="vertical")

        oasysgui.lineEdit(storage_ring_box, self, "electron_energy_in_GeV", "Energy [GeV]",  labelWidth=260, valueType=float, orientation="horizontal", callback=self.update)
        oasysgui.lineEdit(storage_ring_box, self, "ring_current", "Ring Current [A]",        labelWidth=260, valueType=float, orientation="horizontal", callback=self.update)




        self.emittances_box_h = oasysgui.widgetBox(self.tab_lightsource, "Electron Horizontal beam sizes",
                                            addSpace=True, orientation="vertical")
        self.emittances_box_v = oasysgui.widgetBox(self.tab_lightsource, "Electron Vertical beam sizes",
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





        # oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_size_h",       "Horizontal Beam Size \u03c3x [m]",          labelWidth=260, valueType=float, orientation="horizontal",  callback=self.update)
        # oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_size_v",       "Vertical Beam Size \u03c3y [m]",            labelWidth=260, valueType=float, orientation="horizontal",  callback=self.update)
        # oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_divergence_h", "Horizontal Beam Divergence \u03c3'x [rad]", labelWidth=260, valueType=float, orientation="horizontal",  callback=self.update)
        # oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_divergence_v", "Vertical Beam Divergence \u03c3'y [rad]",   labelWidth=260, valueType=float, orientation="horizontal",  callback=self.update)

        ###################


        left_box_1 = oasysgui.widgetBox(self.tab_lightsource, "ID Parameters", addSpace=True, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "period_length", "Period Length [m]", labelWidth=260,
                          valueType=float, orientation="horizontal", callback=self.update)
        oasysgui.lineEdit(left_box_1, self, "number_of_periods", "Number of Periods", labelWidth=260,
                          valueType=float, orientation="horizontal", callback=self.update)

        oasysgui.lineEdit(left_box_1, self, "K_vertical", "Vertical K", labelWidth=260,
                          valueType=float, orientation="horizontal")


        self.set_visible()


    def set_visible(self):
        self.emittances_box_h.setVisible(self.scan_direction_flag == 0)
        self.emittances_box_v.setVisible(self.scan_direction_flag == 1)

    def increase_mode_index(self):
        self.mode_index += 1
        if self.coherent_mode_decomposition is None:
            self.calculate()
        else:
            self.send_mode()

    def decrease_mode_index(self):
        self.mode_index -= 1
        if self.mode_index < 0: self.mode_index = 0
        if self.coherent_mode_decomposition is None:
            self.calculate()
        else:
            self.send_mode()

    def reset_mode_index(self):
        self.mode_index = 0
        if self.coherent_mode_decomposition is None:
            self.calculate()
        else:
            self.send_mode()

    def set_Initialization(self):
        self.initialization_box_1.setVisible(self.initialize_from == 0)
        self.initialization_box_2.setVisible(self.initialize_from == 1)


    def initializeTabs(self):
        size = len(self.tab)
        indexes = range(0, size)

        for index in indexes:
            self.tabs.removeTab(size-1-index)

        self.titles = ["Emission size",
                       "Cross Spectral Density",
                       "Cumulated occupation",
                       "Eigenfunctions",
                       "Spectral Density",
                       "Sent mode"]
        self.tab = []
        self.plot_canvas = []

        for index in range(0, len(self.titles)):
            self.tab.append(gui.createTabPage(self.tabs, self.titles[index]))
            self.plot_canvas.append(None)

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

    def set_photon_energy(self):
        ebeam = ElectronBeam(energy_in_GeV=self.electron_energy_in_GeV,
                             current=self.ring_current)
        su = Undulator.initialize_as_vertical_undulator(K=self.K_vertical,
                                                        period_length=self.period_length,
                                                        periods_number=self.number_of_periods)
        self.photon_energy = numpy.round(su.resonance_energy(ebeam.gamma(), harmonic=1.0), 3)

    def check_fields(self):
        congruence.checkStrictlyPositiveNumber(self.photon_energy, "Photon Energy")

        if self.initialize_from == 0:
            congruence.checkGreaterThan(self.range_to, self.range_from, "Range To", "Range From")
        else:
            congruence.checkStrictlyPositiveNumber(self.steps_step, "Step")

        congruence.checkStrictlyPositiveNumber(self.number_of_points, "Number of Points")

        congruence.checkNumber(self.mode_index, "Mode index")

        congruence.checkStrictlyPositiveNumber(self.spectral_density_threshold, "Threshold")

        congruence.checkStrictlyPositiveNumber(self.correction_factor, "Correction factor for SigmaI")


    def receive_syned_data(self, data):
        if not data is None:
            if isinstance(data, Beamline):
                if not data._light_source is None:
                    if isinstance(data._light_source._magnetic_structure, Undulator):
                        light_source = data._light_source
                        ebeam = light_source.get_electron_beam()
                        und = light_source.get_magnetic_structure()

                        x, xp, y, yp = ebeam.get_sigmas_all()
                        self.sigma_h = x
                        self.sigma_v = y
                        self.sigma_divergence_h = xp
                        self.sigma_divergence_v = yp
                        self.electron_energy_in_GeV = ebeam.energy()
                        self.ring_current = ebeam.current()

                        self.number_of_periods = und.number_of_periods()
                        self.period_length = und.period_length()
                        self.photon_energy =  round(und.resonance_energy(ebeam.gamma()), 3)
                        self.K_vertical = und.K_vertical()


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

                self.send_mode()

    def get_light_source(self):
        return WOLightSourceCMD(name="name", undulator_coherent_mode_decomposition_1d=self.coherent_mode_decomposition)

    def generate(self):
        pass

    def calculate_and_send_mode(self):
        self.calculate()
        self.send_mode()

    def calculate(self):

        self.wofry_output.setText("")

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)


        self.progressBarInit()

        self.check_fields()


        if self.scan_direction_flag == 0:
            scan_direction = "H"
            sigmaxx=self.sigma_h
            sigmaxpxp=self.sigma_divergence_h
        else:
            scan_direction = "V"
            sigmaxx=self.sigma_v
            sigmaxpxp=self.sigma_divergence_v

        if self.flag_gsm == 0:
            useGSMapproximation = False
        elif self.flag_gsm == 1:
            useGSMapproximation = True

        # main calculation
        self.coherent_mode_decomposition = UndulatorCoherentModeDecomposition1D(
            electron_energy=self.electron_energy_in_GeV,
            electron_current=self.ring_current,
            undulator_period=self.period_length,
            undulator_nperiods=self.number_of_periods,
            K=self.K_vertical,
            photon_energy=self.photon_energy,
            abscissas_interval=self.range_to - self.range_from,
            number_of_points=self.number_of_points,
            distance_to_screen=100.0,
            scan_direction=scan_direction,
            sigmaxx=sigmaxx,
            sigmaxpxp=sigmaxpxp,
            useGSMapproximation=useGSMapproximation)
        # make calculation
        self.coherent_mode_decomposition_results = self.coherent_mode_decomposition.calculate()

        if self.view_type != 0:
            self.initializeTabs()
            self.plot_results()
        else:
            self.progressBarFinished()

        try:
            beamline = WOBeamline(light_source=self.get_light_source())
            self.wofry_python_script.set_code(beamline.to_python_code())
        except:
            pass

        # self.send_mode()

    def send_mode(self):

        if self.coherent_mode_decomposition is None:
            self.calculate()

        if self.view_type != 0:
            self.do_plot_send_mode()

        beamline = WOBeamline(light_source=self.get_light_source())
        print(">>> sending mode: ", int(self.mode_index))
        self.send("WofryData", WofryData(
            wavefront=self.coherent_mode_decomposition.get_eigenvector_wavefront(int(self.mode_index)),
            beamline=beamline))

    def do_plot_send_mode(self):
        if not self.coherent_mode_decomposition is None:

            #
            # plot mode to send
            #
            abscissas = self.coherent_mode_decomposition_results["abscissas"]
            wf = self.coherent_mode_decomposition.get_eigenvector_wavefront(self.mode_index)

            xtitle = "Photon energy [keV]"
            ytitle = "wavefront intensity"

            self.plot_data1D(1e6 * abscissas,
                             wf.get_intensity(),
                             progressBarValue=90.0,
                             tabs_canvas_index=5,
                             plot_canvas_index=5,
                             title=self.titles[5],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Intensity",
                             calculate_fwhm=True)

            self.progressBarFinished()

    def do_plot_results(self, progressBarValue):
        if not self.coherent_mode_decomposition is None:

            self.progressBarSet(progressBarValue)

            #
            # plot emission size
            #
            if self.flag_gsm:
                abscissas = self.coherent_mode_decomposition.abscissas
                indices = numpy.arange(abscissas.size)
                intensity = self.coherent_mode_decomposition.CSD[indices,indices]
            else:
                abscissas = self.coherent_mode_decomposition.abscissas
                intensity = self.coherent_mode_decomposition.output_wavefront.get_intensity()
            self.plot_data1D(1e6 * abscissas,
                             intensity,
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=0,
                             plot_canvas_index=0,
                             title=self.titles[0],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Intensity",
                             calculate_fwhm=True)

            #
            # plot CSD
            #
            abscissas = self.coherent_mode_decomposition_results["abscissas"]
            CSD = self.coherent_mode_decomposition_results["CSD"]
            self.plot_data2D(numpy.abs(CSD),
                             1e6 * abscissas,
                             1e6 * abscissas,
                             progressBarValue, 1, 1,
                             title=self.titles[1],
                             xtitle="Spatial Coordinate x1 [$\mu$m]",
                             ytitle="Spatial Coordinate x1 [$\mu$m]")

            #
            # plot cumulated occupation
            #
            eigenvalues  = self.coherent_mode_decomposition_results["eigenvalues"]
            eigenvectors = self.coherent_mode_decomposition_results["eigenvectors"]


            nmodes = self.number_of_points
            x = numpy.arange(eigenvalues.size)
            occupation = eigenvalues[0:nmodes] / (eigenvalues.sum())
            cumulated_occupation = numpy.cumsum(occupation)

            self.plot_data1D(x,
                             cumulated_occupation,
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=2,
                             plot_canvas_index=2,
                             title=self.titles[2],
                             xtitle="mode index",
                             ytitle="Cumulated occupation",
                             calculate_fwhm=False)


            #
            # plot eigenfunctions
            #
            xtitle = "Photon energy [keV]"
            ytitle = "eigenfunction"
            colors = ['green', 'black', 'red', 'brown', 'orange', 'pink']
            y_list = []
            for i in range(6):
                y_list.append(numpy.real(eigenvectors[i,:]).copy())
            ytitles = []
            for i in range(6):
                ytitles.append("eigenvalue %d" % i)

            self.plot_multi_data1D(1e6*abscissas,
                             y_list,
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=3,
                             plot_canvas_index=3,
                             title=self.titles[3],
                             xtitle="x [um]",
                             ytitles=ytitles,
                             colors=colors,
                             yrange=[-eigenvectors.max(), eigenvectors.max()])

            #
            # plot spectral density
            #
            xtitle = "Photon energy [keV]"
            ytitle = "spectral density"
            colors = ['green', 'black', 'red', 'brown', 'orange', 'pink']

            SD = numpy.zeros_like(abscissas)
            for i in range(SD.size):
                SD[i] = numpy.real(CSD[i, i])

            # restore spectral density from modes
            y = numpy.zeros_like(abscissas, dtype=complex)
            nmodes = abscissas.size
            for i in range(nmodes):
                y += eigenvalues[i] * numpy.conjugate(eigenvectors[i, :]) * eigenvectors[i, :]

            self.plot_multi_data1D(1e6 * abscissas,
                             [SD,numpy.real(y)],
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=4,
                             plot_canvas_index=4,
                             title=self.titles[4],
                             xtitle="x [um]",
                             ytitles=["SD from CSD","SD from modes"],
                             colors=colors)


            #
            # plot mode to be sent and close progress bar
            #
            self.do_plot_send_mode()




if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    a = QApplication(sys.argv)
    ow = OWUndulatorCoherentModeDecomposition1D()

    ow.show()
    a.exec_()
    ow.saveSettings()
