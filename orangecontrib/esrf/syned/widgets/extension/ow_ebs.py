import sys, numpy,  scipy.constants as codata

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from syned.storage_ring.magnetic_structures.undulator import Undulator

from orangecontrib.syned.widgets.gui import ow_insertion_device

from PyQt5.QtWidgets import QTextEdit


#############


import os, sys

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox
from orangewidget import gui
from orangewidget import widget
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from syned.storage_ring.magnetic_structures import insertion_device

from orangecontrib.syned.widgets.gui import ow_light_source

#############


import os, sys

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import QRect

from orangewidget import gui
from orangewidget import widget
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog

from syned.storage_ring.light_source import LightSource, ElectronBeam
from syned.beamline.beamline import Beamline
from syned.util.json_tools import load_from_json_file, load_from_json_url


#####################
m2ev = codata.c * codata.h / codata.e

VERTICAL = 1
HORIZONTAL = 2
BOTH = 3



class OWEBS(OWWidget):


    maintainer = "Luca Rebuffi"
    maintainer_email = "luca.rebuffi(@at@)elettra.eu"
    category = "Syned Light Sources"
    keywords = ["data", "file", "load", "read"]

    outputs = [{"name":"SynedData",
                "type":Beamline,
                "doc":"Syned Beamline",
                "id":"data"}]

    syned_file_name = Setting("Select *.json file")

    source_name         = Setting("Undefined")

    electron_energy_in_GeV = Setting(2.0)
    electron_energy_spread = Setting(0.001)
    ring_current           = Setting(0.4)
    number_of_bunches      = Setting(400)

    moment_xx           = Setting(0.0)
    moment_xxp          = Setting(0.0)
    moment_xpxp         = Setting(0.0)
    moment_yy           = Setting(0.0)
    moment_yyp          = Setting(0.0)
    moment_ypyp         = Setting(0.0)

    electron_beam_size_h       = Setting(0.0)
    electron_beam_divergence_h = Setting(0.0)
    electron_beam_size_v       = Setting(0.0)
    electron_beam_divergence_v = Setting(0.0)

    electron_beam_emittance_h = Setting(0.0)
    electron_beam_emittance_v = Setting(0.0)
    electron_beam_beta_h = Setting(0.0)
    electron_beam_beta_v = Setting(0.0)
    electron_beam_alpha_h = Setting(0.0)
    electron_beam_alpha_v = Setting(0.0)
    electron_beam_eta_h = Setting(0.0)
    electron_beam_eta_v = Setting(0.0)
    electron_beam_etap_h = Setting(0.0)
    electron_beam_etap_v = Setting(0.0)


    type_of_properties = Setting(0)

    want_main_area=0

    MAX_WIDTH = 460
    MAX_HEIGHT = 700

    TABS_AREA_HEIGHT = 625
    CONTROL_AREA_WIDTH = 450


    #########################
    name = "Undulator Light Source"
    description = "Syned: Undulator Light Source"
    icon = "icons/undulator.png"
    priority = 2

    auto_energy = Setting(0.0)
    auto_harmonic_number = Setting(1)

    K_horizontal       = Setting(1.0)
    K_vertical         = Setting(1.0)
    period_length      = Setting(0.010)
    number_of_periods  = Setting(10)


    def __init__(self):
        # super().__init__()

        self.runaction = widget.OWAction("Send Data", self)
        self.runaction.triggered.connect(self.send_data)
        self.addAction(self.runaction)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Send Data", callback=self.send_data)
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

        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width()*0.05),
                               round(geom.height()*0.05),
                               round(min(geom.width()*0.98, self.MAX_WIDTH)),
                               round(min(geom.height()*0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        self.tabs_setting = oasysgui.tabWidget(self.controlArea)
        self.tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        self.tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        self.tab_sou = oasysgui.createTabPage(self.tabs_setting, "Light Source Setting")

        box_json =  oasysgui.widgetBox(self.tab_sou, "Read/Write File", addSpace=False, orientation="vertical")

        file_box = oasysgui.widgetBox(box_json, "", addSpace=False, orientation="horizontal")

        self.le_syned_file_name = oasysgui.lineEdit(file_box, self, "syned_file_name", "Syned File Name/URL",
                                                    labelWidth=150, valueType=str, orientation="horizontal")

        gui.button(file_box, self, "...", callback=self.select_syned_file, width=25)

        button_box = oasysgui.widgetBox(box_json, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Read Syned File", callback=self.read_syned_file)
        button.setFixedHeight(25)

        button = gui.button(button_box, self, "Write Syned File", callback=self.write_syned_file)
        button.setFixedHeight(25)


        oasysgui.lineEdit(self.tab_sou, self, "source_name", "Light Source Name", labelWidth=260, valueType=str, orientation="horizontal")

        self.electron_beam_box = oasysgui.widgetBox(self.tab_sou, "Electron Beam/Machine Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.electron_beam_box, self, "electron_energy_in_GeV", "Energy [GeV]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.electron_beam_box, self, "electron_energy_spread", "Energy Spread", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.electron_beam_box, self, "ring_current", "Ring Current [A]", labelWidth=260, valueType=float, orientation="horizontal")

        gui.comboBox(self.electron_beam_box, self, "type_of_properties", label="Electron Beam Properties", labelWidth=350,
                     items=["From 2nd Moments", "From Size/Divergence", "From Twiss papameters","Zero emittance"],
                     callback=self.set_TypeOfProperties,
                     sendSelectedValue=False, orientation="horizontal")

        self.left_box_2_1 = oasysgui.widgetBox(self.electron_beam_box, "", addSpace=False, orientation="vertical", height=150)

        oasysgui.lineEdit(self.left_box_2_1, self, "moment_xx",   "<x x>   [m^2]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_1, self, "moment_xxp",  "<x x'>  [m.rad]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_1, self, "moment_xpxp", "<x' x'> [rad^2]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_1, self, "moment_yy",   "<y y>   [m^2]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_1, self, "moment_yyp",  "<y y'>  [m.rad]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_1, self, "moment_ypyp", "<y' y'> [rad^2]", labelWidth=260, valueType=float, orientation="horizontal")


        self.left_box_2_2 = oasysgui.widgetBox(self.electron_beam_box, "", addSpace=False, orientation="vertical", height=150)

        oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_size_h",       "Horizontal Beam Size \u03c3x [m]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_size_v",       "Vertical Beam Size \u03c3y [m]",  labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_divergence_h", "Horizontal Beam Divergence \u03c3'x [rad]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_divergence_v", "Vertical Beam Divergence \u03c3'y [rad]", labelWidth=260, valueType=float, orientation="horizontal")

        self.left_box_2_3 = oasysgui.widgetBox(self.electron_beam_box, "", addSpace=False, orientation="horizontal",height=150)
        self.left_box_2_3_l = oasysgui.widgetBox(self.left_box_2_3, "", addSpace=False, orientation="vertical")
        self.left_box_2_3_r = oasysgui.widgetBox(self.left_box_2_3, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_emittance_h", "\u03B5x [m.rad]",labelWidth=75, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_alpha_h",     "\u03B1x",        labelWidth=75, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_beta_h",      "\u03B2x [m]",    labelWidth=75, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_eta_h",       "\u03B7x",        labelWidth=75, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_etap_h",      "\u03B7'x",       labelWidth=75, valueType=float, orientation="horizontal")


        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_emittance_v", "\u03B5y [m.rad]",labelWidth=75, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_alpha_v",     "\u03B1y",        labelWidth=75,valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_beta_v",      "\u03B2y [m]",    labelWidth=75, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_eta_v",       "\u03B7y",        labelWidth=75, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_etap_v",      "\u03B7'y",       labelWidth=75, valueType=float, orientation="horizontal")

        self.set_TypeOfProperties()

        gui.rubber(self.controlArea)

        ###################




        left_box_1 = oasysgui.widgetBox(self.tab_sou, "ID Parameters", addSpace=True, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "K_horizontal", "Horizontal K", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "K_vertical", "Vertical K", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "period_length", "Period Length [m]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "number_of_periods", "Number of Periods", labelWidth=260, valueType=float, orientation="horizontal")


        ####################################################

        tab_util = oasysgui.createTabPage(self.tabs_setting, "Utility")

        left_box_0 = oasysgui.widgetBox(tab_util, "Undulator calculated parameters", addSpace=False, orientation="vertical", height=450)
        gui.button(left_box_0, self, "Update info", callback=self.update_info)

        self.info_id = oasysgui.textArea(height=380, width=415, readOnly=True)
        left_box_0.layout().addWidget(self.info_id)

        left_box_1 = oasysgui.widgetBox(tab_util, "Auto Setting of Undulator", addSpace=False, orientation="vertical", height=120)

        oasysgui.lineEdit(left_box_1, self, "auto_energy", "Set Undulator at Energy [eV]",
                          labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "auto_harmonic_number", "As Harmonic #",  labelWidth=250, valueType=int, orientation="horizontal")

        button_box = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="horizontal")

        gui.button(button_box, self, "Set Kv value", callback=self.auto_set_undulator_V)
        gui.button(button_box, self, "Set Kh value", callback=self.auto_set_undulator_H)
        gui.button(button_box, self, "Set Both K values", callback=self.auto_set_undulator_B)


    def check_magnetic_structure(self):
        congruence.checkPositiveNumber(self.K_horizontal, "Horizontal K")
        congruence.checkPositiveNumber(self.K_vertical, "Vertical K")
        congruence.checkStrictlyPositiveNumber(self.period_length, "Period Length")
        congruence.checkStrictlyPositiveNumber(self.number_of_periods, "Number of Periods")

    def get_magnetic_structure(self):
        return insertion_device.InsertionDevice(K_horizontal=self.K_horizontal,
                                                K_vertical=self.K_vertical,
                                                period_length=self.period_length,
                                                number_of_periods=self.number_of_periods)

    def update_info(self):

        syned_light_source = self.get_light_source()
        syned_electron_beam = syned_light_source.get_electron_beam()
        syned_undulator = syned_light_source.get_magnetic_structure()

        gamma = self.gamma()

        info_parameters = {
            "electron_energy_in_GeV":self.electron_energy_in_GeV,
            "gamma":"%8.3f"%self.gamma(),
            "ring_current":"%4.3f "%syned_electron_beam.current(),
            "K_horizontal":syned_undulator.K_horizontal(),
            "K_vertical": syned_undulator.K_vertical(),
            "period_length": syned_undulator.period_length(),
            "number_of_periods": syned_undulator.number_of_periods(),
            "undulator_length": syned_undulator.length(),
            "resonance_energy":"%6.3f"%syned_undulator.resonance_energy(gamma,harmonic=1),
            "resonance_energy3": "%6.3f" % syned_undulator.resonance_energy(gamma,harmonic=3),
            "resonance_energy5": "%6.3f" % syned_undulator.resonance_energy(gamma,harmonic=5),
            "B_horizontal":"%4.2F"%syned_undulator.magnetic_field_horizontal(),
            "B_vertical": "%4.2F" % syned_undulator.magnetic_field_vertical(),
            "cc_1": "%4.2f" % (1e6*syned_undulator.gaussian_central_cone_aperture(gamma,1)),
            "cc_3": "%4.2f" % (1e6*syned_undulator.gaussian_central_cone_aperture(gamma,3)),
            "cc_5": "%4.2f" % (1e6*syned_undulator.gaussian_central_cone_aperture(gamma,5)),
            # "cc_7": "%4.2f" % (self.gaussian_central_cone_aperture(7)*1e6),
            "sigma_rad": "%5.2f"        % (1e6*syned_undulator.get_sigmas_radiation(gamma,harmonic=1)[0]),
            "sigma_rad_prime": "%5.2f"  % (1e6*syned_undulator.get_sigmas_radiation(gamma,harmonic=1)[1]),
            "sigma_rad3": "%5.2f"       % (1e6*syned_undulator.get_sigmas_radiation(gamma,harmonic=3)[0]),
            "sigma_rad_prime3": "%5.2f" % (1e6*syned_undulator.get_sigmas_radiation(gamma,harmonic=3)[1]),
            "sigma_rad5": "%5.2f" % (1e6 * syned_undulator.get_sigmas_radiation(gamma, harmonic=5)[0]),
            "sigma_rad_prime5": "%5.2f" % (1e6 * syned_undulator.get_sigmas_radiation(gamma, harmonic=5)[1]),
            "first_ring_1": "%5.2f" % (1e6*syned_undulator.get_resonance_ring(gamma, harmonic=1, ring_order=1)),
            "first_ring_3": "%5.2f" % (1e6*syned_undulator.get_resonance_ring(gamma, harmonic=3, ring_order=1)),
            "first_ring_5": "%5.2f" % (1e6*syned_undulator.get_resonance_ring(gamma, harmonic=5, ring_order=1)),
            "Sx": "%5.2f"  % (1e6*syned_undulator.get_photon_sizes_and_divergences(syned_electron_beam)[0]),
            "Sy": "%5.2f"  % (1e6*syned_undulator.get_photon_sizes_and_divergences(syned_electron_beam)[1]),
            "Sxp": "%5.2f" % (1e6*syned_undulator.get_photon_sizes_and_divergences(syned_electron_beam)[2]),
            "Syp": "%5.2f" % (1e6*syned_undulator.get_photon_sizes_and_divergences(syned_electron_beam)[3]),
            "und_power": "%5.2f" % syned_undulator.undulator_full_emitted_power(gamma,syned_electron_beam.current()),
            "CF_h": "%4.3f" % syned_undulator.approximated_coherent_fraction_horizontal(syned_electron_beam,harmonic=1),
            "CF_v": "%4.3f" % syned_undulator.approximated_coherent_fraction_vertical(syned_electron_beam,harmonic=1),
            "CF": "%4.3f" % syned_undulator.approximated_coherent_fraction(syned_electron_beam,harmonic=1),
            }

        self.info_id.setText(self.info_template().format_map(info_parameters))


    def info_template(self):
        return \
"""

================ input parameters ===========
Electron beam energy [GeV]: {electron_energy_in_GeV}
Electron current:           {ring_current}
Period Length [m]:          {period_length}
Number of Periods:          {number_of_periods}

Horizontal K:               {K_horizontal}
Vertical K:                 {K_vertical}
==============================================

Electron beam gamma:                {gamma}
Undulator Length [m]:               {undulator_length}
Horizontal Peak Magnetic field [T]: {B_horizontal}
Vertical Peak Magnetic field [T]:   {B_vertical}

Total power radiated by the undulator [W]: {und_power}

Resonances:

Photon energy [eV]: 
       for harmonic 1 : {resonance_energy}
       for harmonic 3 : {resonance_energy3}
       for harmonic 3 : {resonance_energy5}

Central cone (RMS urad):
       for harmonic 1 : {cc_1}
       for harmonic 3 : {cc_3}
       for harmonic 5 : {cc_5}

First ring at (urad):
       for harmonic 1 : {first_ring_1}
       for harmonic 3 : {first_ring_3}
       for harmonic 5 : {first_ring_5}

Sizes and divergences of radiation :
    at 1st harmonic: sigma: {sigma_rad} um, sigma': {sigma_rad_prime} urad
    at 3rd harmonic: sigma: {sigma_rad3} um, sigma': {sigma_rad_prime3} urad
    at 5th harmonic: sigma: {sigma_rad5} um, sigma': {sigma_rad_prime5} urad
    
Sizes and divergences of photon source (convolution) at resonance (1st harmonic): :
    Sx: {Sx} um
    Sy: {Sy} um,
    Sx': {Sxp} urad
    Sy': {Syp} urad
    
Approximated coherent fraction at 1st harmonic: 
    Horizontal: {CF_h}  Vertical: {CF_v} 
    Coherent fraction 2D (HxV): {CF} 

"""

    def get_magnetic_structure(self):
        return Undulator(K_horizontal=self.K_horizontal,
                         K_vertical=self.K_vertical,
                         period_length=self.period_length,
                         number_of_periods=self.number_of_periods)


    def check_magnetic_structure_instance(self, magnetic_structure):
        if not isinstance(magnetic_structure, Undulator):
            raise ValueError("Magnetic Structure is not a Undulator")

    def populate_magnetic_structure(self, magnetic_structure):
        self.K_horizontal = magnetic_structure._K_horizontal
        self.K_vertical = magnetic_structure._K_vertical
        self.period_length = magnetic_structure._period_length
        self.number_of_periods = magnetic_structure._number_of_periods

    def auto_set_undulator_V(self):
        self.auto_set_undulator(VERTICAL)

    def auto_set_undulator_H(self):
        self.auto_set_undulator(HORIZONTAL)

    def auto_set_undulator_B(self):
        self.auto_set_undulator(BOTH)

    def auto_set_undulator(self, which=VERTICAL):
        congruence.checkStrictlyPositiveNumber(self.auto_energy, "Set Undulator at Energy")
        congruence.checkStrictlyPositiveNumber(self.auto_harmonic_number, "As Harmonic #")
        congruence.checkStrictlyPositiveNumber(self.electron_energy_in_GeV, "Energy")
        congruence.checkStrictlyPositiveNumber(self.period_length, "Period Length")

        wavelength = self.auto_harmonic_number*m2ev/self.auto_energy
        K = round(numpy.sqrt(2*(((wavelength*2*self.gamma()**2)/self.period_length)-1)), 6)

        if which == VERTICAL:
            self.K_vertical = K
            self.K_horizontal = 0.0

        if which == BOTH:
            Kboth = round(K / numpy.sqrt(2), 6)
            self.K_vertical =  Kboth
            self.K_horizontal = Kboth

        if which == HORIZONTAL:
            self.K_horizontal = K
            self.K_vertical = 0.0

        self.update_info()

    def gamma(self):
        return 1e9*self.electron_energy_in_GeV / (codata.m_e *  codata.c**2 / codata.e)




    def set_TypeOfProperties(self):
        self.left_box_2_1.setVisible(self.type_of_properties == 0)
        self.left_box_2_2.setVisible(self.type_of_properties == 1)
        self.left_box_2_3.setVisible(self.type_of_properties == 2)




    def check_data(self):
        congruence.checkStrictlyPositiveNumber(self.electron_energy_in_GeV , "Energy")
        congruence.checkStrictlyPositiveNumber(self.electron_energy_spread, "Energy Spread")
        congruence.checkStrictlyPositiveNumber(self.ring_current, "Ring Current")

        if self.type_of_properties == 0:
            congruence.checkPositiveNumber(self.moment_xx   , "Moment xx")
            congruence.checkPositiveNumber(self.moment_xpxp , "Moment xpxp")
            congruence.checkPositiveNumber(self.moment_yy   , "Moment yy")
            congruence.checkPositiveNumber(self.moment_ypyp , "Moment ypyp")
        elif self.type_of_properties == 1:
            congruence.checkPositiveNumber(self.electron_beam_size_h       , "Horizontal Beam Size")
            congruence.checkPositiveNumber(self.electron_beam_divergence_h , "Vertical Beam Size")
            congruence.checkPositiveNumber(self.electron_beam_size_v       , "Horizontal Beam Divergence")
            congruence.checkPositiveNumber(self.electron_beam_divergence_v , "Vertical Beam Divergence")
        elif self.type_of_properties == 2:
            congruence.checkPositiveNumber(self.electron_beam_emittance_h, "Horizontal Beam Emittance")
            congruence.checkPositiveNumber(self.electron_beam_emittance_v, "Vertical Beam Emittance")
            congruence.checkNumber(self.electron_beam_alpha_h, "Horizontal Beam Alpha")
            congruence.checkNumber(self.electron_beam_alpha_v, "Vertical Beam Alpha")
            congruence.checkNumber(self.electron_beam_beta_h, "Horizontal Beam Beta")
            congruence.checkNumber(self.electron_beam_beta_v, "Vertical Beam Beta")
            congruence.checkNumber(self.electron_beam_eta_h, "Horizontal Beam Dispersion Eta")
            congruence.checkNumber(self.electron_beam_eta_v, "Vertical Beam Dispersion Eta")
            congruence.checkNumber(self.electron_beam_etap_h, "Horizontal Beam Dispersion Eta'")
            congruence.checkNumber(self.electron_beam_etap_v, "Vertical Beam Dispersion Eta'")

        self.check_magnetic_structure()


    def send_data(self):
        try:
            self.check_data()

            self.send("SynedData", Beamline(light_source=self.get_light_source()))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)

            self.setStatusMessage("")
            self.progressBarFinished()


    def get_light_source(self):
        electron_beam = ElectronBeam(energy_in_GeV=self.electron_energy_in_GeV,
                                     energy_spread=self.electron_energy_spread,
                                     current=self.ring_current,
                                     number_of_bunches=self.number_of_bunches)

        if self.type_of_properties == 0:
            electron_beam.set_moments_horizontal(self.moment_xx,self.moment_xxp,self.moment_xpxp)
            electron_beam.set_moments_vertical(self.moment_yy, self.moment_yyp, self.moment_ypyp)

        elif self.type_of_properties == 1:
            electron_beam.set_sigmas_all(sigma_x=self.electron_beam_size_h,
                                         sigma_y=self.electron_beam_size_v,
                                         sigma_xp=self.electron_beam_divergence_h,
                                         sigma_yp=self.electron_beam_divergence_v)

        elif self.type_of_properties == 2:
            electron_beam.set_twiss_horizontal(self.electron_beam_emittance_h,
                                             self.electron_beam_alpha_h,
                                             self.electron_beam_beta_h,
                                             self.electron_beam_eta_h,
                                             self.electron_beam_etap_h)
            electron_beam.set_twiss_vertical(self.electron_beam_emittance_v,
                                             self.electron_beam_alpha_v,
                                             self.electron_beam_beta_v,
                                             self.electron_beam_eta_v,
                                             self.electron_beam_etap_v)

        elif self.type_of_properties == 3:
            electron_beam.set_moments_all(0,0,0,0,0,0)

        return LightSource(name=self.source_name,
                           electron_beam = electron_beam,
                           magnetic_structure = self.get_magnetic_structure())


    def callResetSettings(self):
        if ConfirmDialog.confirmed(parent=self, message="Confirm Reset of the Fields?"):
            try:
                self.resetSettings()
            except:
                pass

    def select_syned_file(self):
        self.le_syned_file_name.setText(oasysgui.selectFileFromDialog(self, self.syned_file_name, "Open Syned File"))

    def read_syned_file(self):
        try:
            congruence.checkEmptyString(self.syned_file_name, "Syned File Name/Url")

            if (len(self.syned_file_name) > 7 and self.syned_file_name[:7] == "http://") or \
                (len(self.syned_file_name) > 8 and self.syned_file_name[:8] == "https://"):
                congruence.checkUrl(self.syned_file_name)
                is_remote = True
            else:
                congruence.checkFile(self.syned_file_name)
                is_remote = False

            try:
                if is_remote:
                    content = load_from_json_url(self.syned_file_name)
                else:
                    content = load_from_json_file(self.syned_file_name)

                if isinstance(content, LightSource):
                    self.populate_fields(content)
                elif isinstance(content, Beamline) and not content._light_source is None:
                    self.populate_fields(content._light_source)
                else:
                    raise Exception("json file must contain a SYNED LightSource")
            except Exception as e:
                raise Exception("Error reading SYNED LightSource from file: " + str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)


    def populate_fields(self, light_source):
        electron_beam = light_source._electron_beam
        magnetic_structure = light_source._magnetic_structure

        self.check_magnetic_structure_instance(magnetic_structure)

        self.source_name = light_source._name

        self.electron_energy_in_GeV = electron_beam._energy_in_GeV
        self.electron_energy_spread = electron_beam._energy_spread
        self.ring_current = electron_beam._current
        self.number_of_bunches = electron_beam._number_of_bunches

        self.type_of_properties = 0

        self.moment_xx   = electron_beam._moment_xx
        self.moment_xxp  = electron_beam._moment_xxp
        self.moment_xpxp = electron_beam._moment_xpxp
        self.moment_yy   = electron_beam._moment_yy
        self.moment_yyp  = electron_beam._moment_yyp
        self.moment_ypyp = electron_beam._moment_ypyp

        x, xp, y, yp = electron_beam.get_sigmas_all()

        self.electron_beam_size_h = x
        self.electron_beam_size_v = y
        self.electron_beam_divergence_h = xp
        self.electron_beam_divergence_v = yp

        self.populate_magnetic_structure(magnetic_structure)

        self.set_TypeOfProperties()

    def check_magnetic_structure_instance(self, magnetic_structure):
        raise NotImplementedError()

    def populate_magnetic_structure(self, magnetic_structure):
        raise NotImplementedError()

    def write_syned_file(self):
        try:
            congruence.checkDir(self.syned_file_name)

            self.get_light_source().to_json(self.syned_file_name)

            QMessageBox.information(self, "File Read", "JSON file correctly written to disk", QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)


from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = OWEBS()
    ow.show()
    a.exec_()
