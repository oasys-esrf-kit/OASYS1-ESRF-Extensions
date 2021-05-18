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
from syned.storage_ring.electron_beam import ElectronBeam
from syned.storage_ring.magnetic_structures.undulator import Undulator


from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D

from wofryimpl.beamline.beamline import WOBeamline
from orangecontrib.esrf.wofry.util.light_source import WOPySRULightSource # TODO: from wofryimpl...

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget

from scipy.ndimage.filters import gaussian_filter1d as gaussian_filter1d


class OWUndulatorPySRU(WofryWidget):

    name = "Undulator pySRU"
    id = "UndulatorPySRU"
    description = "Undulator pySRU"
    icon = "icons/undulator.png"
    priority = 201

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

    gapH          = Setting(0.001)
    gapV          = Setting(0.001)
    h_slit_points = Setting(51)
    v_slit_points = Setting(51)
    distance      = Setting(30.0)

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

    scan_direction = Setting(0)

    flag_send_wavefront_dimension = Setting(0)

    calculated_wavefront = None

    def __init__(self):

        super().__init__(is_automatic=False, show_view_options=True, show_script_tab=True)

        self.runaction = widget.OWAction("Generate Wavefront", self)
        self.runaction.triggered.connect(self.calculate)
        self.addAction(self.runaction)


        gui.separator(self.controlArea)
        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Calculate", callback=self.calculate)
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
        self.tab_lightsource = oasysgui.createTabPage(tabs_setting, "Convolution parameters")

        #
        # Settings
        #
        box_wavefront = oasysgui.widgetBox(self.tab_settings, "Sampling wavefront", addSpace=False, orientation="vertical")



        oasysgui.lineEdit(box_wavefront, self, "distance", "distance from source origin [m]",
                          labelWidth=300, tooltip="distance",
                          valueType=float, orientation="horizontal")

        oasysgui.lineEdit(box_wavefront, self, "gapH", "H aperture [m]",
                          labelWidth=300, tooltip="gapH",
                          valueType=float, orientation="horizontal")

        oasysgui.lineEdit(box_wavefront, self, "gapV", "V aperture [m]",
                          labelWidth=300, tooltip="gapV",
                          valueType=float, orientation="horizontal")

        oasysgui.lineEdit(box_wavefront, self, "h_slit_points", "Number of Points in H",
                          labelWidth=300, tooltip="h_slit_points",
                          valueType=int, orientation="horizontal")

        oasysgui.lineEdit(box_wavefront, self, "v_slit_points", "Number of Points in V",
                          labelWidth=300, tooltip="v_slit_points",
                          valueType=int, orientation="horizontal")

        left_box_33 = oasysgui.widgetBox(box_wavefront, "", addSpace=True, orientation="horizontal")
        oasysgui.lineEdit(left_box_33, self, "photon_energy", "Photon Energy [eV]",
                          labelWidth=200, tooltip="photon_energy",
                          valueType=float, orientation="horizontal")
        gui.button(left_box_33, self, "set from K", callback=self.set_photon_energy, width=80)

        #
        # Light Source
        #
        box_ring = oasysgui.widgetBox(self.tab_settings, "Storage ring", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(box_ring, self, "electron_energy_in_GeV", "Energy [GeV]",  labelWidth=260, valueType=float, orientation="horizontal", callback=self.update)
        oasysgui.lineEdit(box_ring, self, "ring_current", "Ring Current [A]",        labelWidth=260, valueType=float, orientation="horizontal", callback=self.update)

        #
        # Undulator
        #
        box_und = oasysgui.widgetBox(self.tab_settings, "Undulator", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(box_und, self, "period_length", "Period Length [m]", labelWidth=260,
                          valueType=float, orientation="horizontal", callback=self.update)
        oasysgui.lineEdit(box_und, self, "number_of_periods", "Number of Periods", labelWidth=260,
                          valueType=float, orientation="horizontal", callback=self.update)

        oasysgui.lineEdit(box_und, self, "K_vertical", "Vertical K", labelWidth=260,
                          valueType=float, orientation="horizontal")


        box_send = oasysgui.widgetBox(self.tab_settings, "Send wavefront", addSpace=True, orientation="vertical")
        gui.comboBox(box_send, self, "flag_send_wavefront_dimension", label="Send Wavefront", labelWidth=350,
                     items=["2D",
                            "1D Horizontal",
                            "1D Vertical",
                            ],
                     # callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        #
        # second tab
        #

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





    def initializeTabs(self):
        size = len(self.tab)
        indexes = range(0, size)

        for index in indexes:
            self.tabs.removeTab(size-1-index)

        self.titles = ["Intensity",
                       "Phase",
                       "Intensity with convolution"]
        self.tab = []
        self.plot_canvas = []

        for index in range(0, len(self.titles)):
            self.tab.append(gui.createTabPage(self.tabs, self.titles[index]))
            self.plot_canvas.append(None)

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

    def set_photon_energy(self):
        light_source = self.get_light_source()
        su = light_source.get_magnetic_structure()
        ebeam = light_source.get_electron_beam()
        self.photon_energy = numpy.round(su.resonance_energy(ebeam.gamma(), harmonic=1.0), 3)

    def check_fields(self):
        congruence.checkStrictlyPositiveNumber(self.photon_energy, "Photon Energy")

        congruence.checkGreaterOrEqualThan(self.distance, self.number_of_periods * self.period_length,
                                           "distance", "undulator length")

        congruence.checkStrictlyPositiveNumber(self.v_slit_points, "Number of Points V")
        congruence.checkStrictlyPositiveNumber(self.h_slit_points, "Number of Points H")

        congruence.checkNumber(self.gapH, "gapH")
        congruence.checkNumber(self.gapV, "gapV")

        congruence.checkStrictlyPositiveNumber(self.electron_energy_in_GeV, "electron_energy_in_GeV")
        congruence.checkNumber(self.ring_current, "ring_current")
        congruence.checkStrictlyPositiveNumber(self.period_length, "period_length")
        congruence.checkStrictlyPositiveNumber(self.number_of_periods, "number_of_periods")
        congruence.checkStrictlyPositiveNumber(self.K_vertical, "K_vertical")


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

                self.calculate()

    def get_light_source(self):

        return WOPySRULightSource.initialize_from_keywords(
            name="Undefined",
            energy_in_GeV=self.electron_energy_in_GeV,
            current=self.ring_current,
            K_vertical=self.K_vertical,
            period_length=self.period_length,
            number_of_periods=self.number_of_periods,
            distance=self.distance,
            gapH=self.gapH,
            gapV=self.gapV,
            photon_energy=self.photon_energy,
            h_slit_points=self.h_slit_points,
            v_slit_points=self.v_slit_points,
            flag_send_wavefront_dimension=self.flag_send_wavefront_dimension,
        )

    def do_plot_results(self, progressBarValue):


        #
        # plot intensity
        #
        wf = self.calculated_wavefront
        if isinstance(wf, GenericWavefront2D):
            self.progressBarSet(progressBarValue)
            self.plot_data2D(wf.get_intensity(),
                             1e6 * wf.get_coordinate_x(),
                             1e6 * wf.get_coordinate_y(),
                             20, 0, 0,
                             title=self.titles[0],
                             xtitle="Spatial Coordinate H [$\mu$m]",
                             ytitle="Spatial Coordinate V [$\mu$m]")

            #
            # plot phase
            #
            self.plot_data2D(wf.get_phase(),
                             1e6 * wf.get_coordinate_x(),
                             1e6 * wf.get_coordinate_y(),
                             20, 1, 1,
                             title=self.titles[1],
                             xtitle="Spatial Coordinate H [$\mu$m]",
                             ytitle="Spatial Coordinate V [$\mu$m]")

            #
            # plot convolution
            #

            #
            # convolution for non zero emittance
            #

            intensArray = self.calculated_wavefront.get_intensity()
            wf = self.calculated_wavefront

            hArray = wf.get_coordinate_x()
            vArray = wf.get_coordinate_y()

            SigmaH = numpy.sqrt(self.sigma_h ** 2 + (self.distance * self.sigma_divergence_h) ** 2)
            SigmaV = numpy.sqrt(self.sigma_v ** 2 + (self.distance * self.sigma_divergence_v) ** 2)

            print("\nFor the Convolution Tab, convolving with SigmaH: %g, SigmaV: %g" % ( SigmaH, SigmaV))
            print("\n**NOTE that the Convolution Tab is for info only. This is not considered in the wavefront")
            intensArray = gaussian_filter1d(intensArray, SigmaH / (hArray[1] - hArray[0]), axis=0)
            intensArray = gaussian_filter1d(intensArray, SigmaV / (vArray[1] - vArray[0]), axis=1)


            self.plot_data2D(intensArray,
                             1e6 * hArray,
                             1e6 * vArray,
                             20, 2, 2,
                             title=self.titles[2],
                             xtitle="Spatial Coordinate H [$\mu$m]",
                             ytitle="Spatial Coordinate V [$\mu$m]")

    def calculate(self):

        self.wofry_output.setText("calculating...")

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)


        self.progressBarInit()

        self.check_fields()

        self.progressBarSet(10.0)

        # main calculation
        ls = self.get_light_source()
        self.calculated_wavefront = ls.get_wavefront()

        # ii = self.calculated_wavefront.get_integrated_intensity()
        deltaX = 1e3 * (self.calculated_wavefront.get_coordinate_x()[1] - self.calculated_wavefront.get_coordinate_x()[0])
        deltaY = 1e3 * (self.calculated_wavefront.get_coordinate_y()[1] - self.calculated_wavefront.get_coordinate_y()[0])

        pixel_angle = deltaX * deltaY / self.distance**2
        print("\n\ndeltaX: %g mm, deltaY: %g mm, distance: %g m" % (deltaX, deltaY, self.distance))
        print("Pixel angle: %g mrad2" % pixel_angle)
        ii = self.calculated_wavefront.get_intensity().sum()
        print("Integrated intensity (raw): %g " % (ii))
        print("Integrated intensity (normalized): %g photons/s/0.1bw" % (ii * pixel_angle))


        # plots
        if self.view_type != 0:
            self.initializeTabs()
            self.do_plot_results(90.0)

        self.progressBarFinished()

        try:
            beamline = WOBeamline(light_source=ls)
            self.wofry_python_script.set_code(beamline.to_python_code())
        except:
            pass


        # beamline = WOBeamline(light_source=ls)
        print(">>> sending wavefront ")

        if self.flag_send_wavefront_dimension == 0:
            self.send("WofryData", WofryData(
                wavefront=self.calculated_wavefront,
                beamline=WOBeamline(light_source=ls)))
        elif self.flag_send_wavefront_dimension == 1: # H
            self.send("WofryData", WofryData(
                wavefront=self.calculated_wavefront.get_Wavefront1D_from_profile(0, 0.0),
                beamline=WOBeamline(light_source=ls)))
        elif self.flag_send_wavefront_dimension == 2: # V
            self.send("WofryData", WofryData(
                wavefront=self.calculated_wavefront.get_Wavefront1D_from_profile(1, 0.0),
                beamline=WOBeamline(light_source=ls)))


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    a = QApplication(sys.argv)
    ow = OWUndulatorPySRU()

    ow.show()
    a.exec_()
    ow.saveSettings()

