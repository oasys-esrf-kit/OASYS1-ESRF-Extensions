import sys
import numpy
from PyQt5.QtWidgets import QApplication, QMessageBox, QSizePolicy

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui, congruence
from oasys.widgets.exchange import DataExchangeObject
from orangecontrib.xoppy.util.xoppy_xraylib_util import xpower_calc

from oasys.widgets.exchange import DataExchangeObject
from orangecontrib.xoppy.widgets.gui.ow_xoppy_widget import XoppyWidget


import scipy.constants as codata

class OWID19AttenuatorsBox(XoppyWidget):
    name = "ID19AttenuatorsBox"
    id = "orange.widgets.dataxpower"
    description = "Power Absorbed and Transmitted by Optical Elements"
    icon = "icons/id19_attenuator.png"
    priority = 2
    category = ""
    keywords = ["xoppy", "power"]

    inputs = [("ExchangeData", DataExchangeObject, "acceptExchangeData")]

    FLAG = Setting(0)
    SOURCE = Setting(2)
    ENER_MIN = Setting(1000.0)
    ENER_MAX = Setting(50000.0)
    ENER_N = Setting(100)
    SOURCE_FILE = Setting("?")
    ATT11 = Setting(0)
    ATT12 = Setting(3)
    ATT13 = Setting(3)
    ATT14 = Setting(3)
    ATT15 = Setting(3)
    ATT21 = Setting(3)
    ATT22 = Setting(3)
    ATT23 = Setting(3)
    ATT24 = Setting(3)
    ATT25 = Setting(3)
    C = Setting(1.4)
    Al = Setting(1.4)
    Cu = Setting(0.0)
    Mo = Setting(0.0)
    W = Setting(0.0)
    Au = Setting(0.14)
    PLOT_SETS = Setting(2)
    FILE_DUMP = 0


    def build_gui(self):

        self.leftWidgetPart.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding))
        self.leftWidgetPart.setMaximumWidth(self.CONTROL_AREA_WIDTH + 20)
        self.leftWidgetPart.updateGeometry()

        box = oasysgui.widgetBox(self.controlArea, self.name + " Input Parameters", orientation="vertical", width=self.CONTROL_AREA_WIDTH-10)

        idx = -1


        # widget index 1
        idx += 1
        box1 = gui.widgetBox(box)
        self.box_source = gui.comboBox(box1, self, "FLAG",
                                       label=self.unitLabels()[idx], addSpace=False,
                                       items=['Attenuators Box', 'Attenuators list'],
                                       valueType=int, orientation="horizontal", labelWidth=150, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)


        #widget index 2 
        idx += 1 
        box1 = gui.widgetBox(box) 
        self.box_source = gui.comboBox(box1, self, "SOURCE",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['From Oasys wire', 'Normalized to 1', 'From external file.                '],
                    valueType=int, orientation="horizontal", labelWidth=150)
        self.show_at(self.unitFlags()[idx], box1)
        
        #widget index 6 
        idx += 1 
        box1 = gui.widgetBox(box) 
        oasysgui.lineEdit(box1, self, "ENER_MIN",
                     label=self.unitLabels()[idx], addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1) 
        
        #widget index 7 
        idx += 1 
        box1 = gui.widgetBox(box) 
        oasysgui.lineEdit(box1, self, "ENER_MAX",
                     label=self.unitLabels()[idx], addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1) 
        
        #widget index 8 
        idx += 1 
        box1 = gui.widgetBox(box) 
        oasysgui.lineEdit(box1, self, "ENER_N",
                     label=self.unitLabels()[idx], addSpace=False,
                    valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1) 


        # widget index 9 ***********   File Browser ******************
        idx += 1
        box1 = gui.widgetBox(box)
        file_box_id = oasysgui.widgetBox(box1, "", addSpace=False, orientation="horizontal")
        self.file_id = oasysgui.lineEdit(file_box_id, self, "SOURCE_FILE", self.unitLabels()[idx],
                                         labelWidth=100, valueType=str, orientation="horizontal")
        gui.button(file_box_id, self, "...", callback=self.select_input_file, width=25)
        self.show_at(self.unitFlags()[idx], box1)


        #widget index 10
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT11",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['101 : None', '102 : Diam, 1.4mm','103 : Diam, 2.8mm', '104 : Diam, 1mm'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)



        #widget index 11
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT12",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['201 : Al, 0.7mm', '202 : Al, 1.4mm','203 : Al, 2.8mm', '204 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 12
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT13",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['301 : Cu, 4mm', '302 : Cu, 6mm','303 : Cu, 8mm', '304 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 13
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT14",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['401 : Al, 0.7mm', '402 : Al, 1.4mm','403 : Al, 2.8mm', '404 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 14
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT15",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['501 : Cu, 0.14mm', '502 : Cu, 0.35mm','503 : Cu, 1.4mm', '504 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 15
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT21",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['601 : Cu, 0.7mm', '602 : Cu, 1.4mm','603 : Cu, 2.8mm', '604 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 16
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT22",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['701 : Mo, 0.14mm', '702 : Mo, 0.35mm','703 : Mo, 0.7mm', '704 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 17
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT23",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['801 : W, 0.3mm', '802 : W, 0.5mm','803 : W, 1.0mm', '804 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 18
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT24",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['901 : W, 0.07mm', '902 : W, 0.14mm','903 : W, 0.28mm', '904 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 19
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "ATT25",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['1001 : Au, 0.07mm', '1002 : Au, 0.14mm','1003 : Au, 0.28mm', '1004 : None'],
                    valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 20
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "C",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 21
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "Al",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 22
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "Cu",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 23
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "Mo",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 24
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "W",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 25
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "Au",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 41
        idx += 1
        box1 = gui.widgetBox(box)
        gui.separator(box1, height=7)

        gui.comboBox(box1, self, "PLOT_SETS",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['Local properties', 'Cumulated intensity', 'All'],
                    valueType=int, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 42
        idx += 1
        box1 = gui.widgetBox(box)
        gui.separator(box1, height=7)

        gui.comboBox(box1, self, "FILE_DUMP",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['No', 'Yes (power.spec)'],
                    valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        self.input_spectrum = None





    def select_input_file(self):
        self.file_id.setText(oasysgui.selectFileFromDialog(self, self.SOURCE_FILE,
                                    "Open 2-columns file with spectral power",
                                    file_extension_filter="ascii dat (*.dat *.txt *spec)"))



    def set_EL_FLAG(self):
        self.initializeTabs()

    def unitLabels(self):
         return ['Box or List','Input beam:',
                 'From energy [eV]:      ',
                 'To energy [eV]:',
                 'Energy points:  ',
                 'File with input beam spectral power:',
                 'Att11','Att12','Att13','Att14','Att15','Att21','Att22','Att23','Att24','Att25',
                 'thickness of the C attenuator (mm) [diamond]', 'thickness of the Al attenuator (mm)',
                 'thickness of the Cu attenuator (mm)', 'thickness of the Mo attenuator (mm)',
                 'thickness of the W attenuator (mm)', 'thickness of the Au attenuator (mm)',
                 'Plot','Dump file']


    def unitFlags(self):
         return ['True','True',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  2',
                 'self.FLAG  ==  0','self.FLAG  ==  0','self.FLAG  ==  0','self.FLAG  ==  0','self.FLAG  ==  0','self.FLAG  ==  0','self.FLAG  ==  0','self.FLAG  ==  0','self.FLAG  ==  0','self.FLAG  ==  0',
                 'self.FLAG  ==  1','self.FLAG  ==  1','self.FLAG  ==  1','self.FLAG  ==  1','self.FLAG  ==  1','self.FLAG  ==  1',
                 'True','True']

    def get_help_name(self):
        return 'ID19AttenuatorsBox'

    def selectFile(self):
        self.le_source_file.setText(oasysgui.selectFileFromDialog(self, self.SOURCE_FILE, "Open Source File", file_extension_filter="*.*"))

    def acceptExchangeData(self, exchangeData):

        self.input_spectrum = None
        self.SOURCE = 0
        # self.box_source.setCurrentIndex(self.SOURCE)

        try:
            if not exchangeData is None:
                if exchangeData.get_program_name() == "XOPPY":
                    no_bandwidth = False
                    if exchangeData.get_widget_name() =="UNDULATOR_FLUX" :
                        # self.SOURCE_FILE = "xoppy_undulator_flux"
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() == "BM" :
                        if exchangeData.get_content("is_log_plot") == 1:
                            raise Exception("Logaritmic X scale of Xoppy Energy distribution not supported")
                        if exchangeData.get_content("calculation_type") == 0 and exchangeData.get_content("psi") == 0:
                            # self.SOURCE_FILE = "xoppy_bm_flux"
                            no_bandwidth = True
                            index_flux = 6
                        else:
                            raise Exception("Xoppy result is not an Flux vs Energy distribution integrated in Psi")
                    elif exchangeData.get_widget_name() =="XWIGGLER" :
                        # self.SOURCE_FILE = "xoppy_xwiggler_flux"
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() =="WS" :
                        # self.SOURCE_FILE = "xoppy_xwiggler_flux"
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() =="XTUBES" :
                        # self.SOURCE_FILE = "xoppy_xtubes_flux"
                        index_flux = 1
                        no_bandwidth = True
                    elif exchangeData.get_widget_name() =="XTUBE_W" :
                        # self.SOURCE_FILE = "xoppy_xtube_w_flux"
                        index_flux = 1
                        no_bandwidth = True
                    elif exchangeData.get_widget_name() =="BLACK_BODY" :
                        # self.SOURCE_FILE = "xoppy_black_body_flux"
                        no_bandwidth = True
                        index_flux = 2

                    elif exchangeData.get_widget_name() =="UNDULATOR_RADIATION" :
                        # self.SOURCE_FILE = "xoppy_undulator_radiation"
                        no_bandwidth = True
                        index_flux = 1
                    elif exchangeData.get_widget_name() =="POWER" :
                        # self.SOURCE_FILE = "xoppy_undulator_power"
                        no_bandwidth = True
                        index_flux = -1
                    elif exchangeData.get_widget_name() =="POWER3D" :
                        # self.SOURCE_FILE = "xoppy_power3d"
                        no_bandwidth = True
                        index_flux = 1

                    else:
                        raise Exception("Xoppy Source not recognized")

                    # self.SOURCE_FILE += "_" + str(id(self)) + ".dat"


                    spectrum = exchangeData.get_content("xoppy_data")

                    if exchangeData.get_widget_name() =="UNDULATOR_RADIATION" or \
                        exchangeData.get_widget_name() =="POWER3D":
                        [p, e, h, v ] = spectrum
                        tmp = p.sum(axis=2).sum(axis=1)*(h[1]-h[0])*(v[1]-v[0])*codata.e*1e3
                        spectrum = numpy.vstack((e,p.sum(axis=2).sum(axis=1)*(h[1]-h[0])*(v[1]-v[0])*
                                                 codata.e*1e3))
                        self.input_spectrum = spectrum
                    else:

                        if not no_bandwidth:
                            spectrum[:,index_flux] /= 0.001*spectrum[:,0]

                        self.input_spectrum = numpy.vstack((spectrum[:,0],spectrum[:,index_flux]))

                    self.process_showers()
                    self.compute()

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                       str(exception),
                QMessageBox.Ok)

            #raise exception




    def check_fields(self):

        if self.SOURCE == 1:
            self.ENER_MIN = congruence.checkPositiveNumber(self.ENER_MIN, "Energy from")
            self.ENER_MAX = congruence.checkStrictlyPositiveNumber(self.ENER_MAX, "Energy to")
            congruence.checkLessThan(self.ENER_MIN, self.ENER_MAX, "Energy from", "Energy to")
            self.NPOINTS = congruence.checkStrictlyPositiveNumber(self.ENER_N, "Energy Points")
        elif self.SOURCE == 2:
            congruence.checkFile(self.SOURCE_FILE)
        if self.FLAG == 1:
            self.C=congruence.checkPositiveNumber(self.C,'thickness of the C attenuator (mm)')
            self.Al = congruence.checkPositiveNumber(self.Al, 'thickness of the Al attenuator (mm)')
            self.Cu = congruence.checkPositiveNumber(self.Cu, 'thickness of the Cu attenuator (mm)')
            self.Mo = congruence.checkPositiveNumber(self.Mo, 'thickness of the Mo attenuator (mm)')
            self.W = congruence.checkPositiveNumber(self.W, 'thickness of the W attenuator (mm)')
            self.Au = congruence.checkPositiveNumber(self.Au, 'thickness of the Au attenuator (mm)')


    def do_xoppy_calculation(self):
        return self.xoppy_calc_xpower()

    def extract_data_from_xoppy_output(self, calculation_output):
        return calculation_output


    def get_data_exchange_widget_name(self):
        return "POWER"

    def do_plot_local(self):
        out = False
        if self.PLOT_SETS == 0: out = True
        if self.PLOT_SETS == 2: out = True
        return out

    def do_plot_intensity(self):
        out = False
        if self.PLOT_SETS == 1: out = True
        if self.PLOT_SETS == 2: out = True
        return out


    def getTitles(self):
        titles = []

        if self.do_plot_intensity(): titles.append("Input beam")
        #if self.do_plot_local(): titles.append("Total CS")
        #if self.do_plot_local(): titles.append("Mu")
        if self.do_plot_local(): titles.append("Transmitivity")
        if self.do_plot_local(): titles.append("Absorption")
        if self.do_plot_intensity(): titles.append("Intensity")
        return titles

    def getXTitles(self):

        xtitles = []

        if self.do_plot_intensity(): xtitles.append("Photon Energy [eV]")
        #if self.do_plot_local(): xtitles.append("Photon Energy [eV]")
        #if self.do_plot_local(): xtitles.append("Photon Energy [eV]")
        if self.do_plot_local(): xtitles.append("Photon Energy [eV]")
        if self.do_plot_local(): xtitles.append("Photon Energy [eV]")
        if self.do_plot_intensity(): xtitles.append("Photon Energy [eV]")
        return xtitles

    def getYTitles(self):
        ytitles = []
        if self.do_plot_intensity(): ytitles.append("Source")
        #if self.do_plot_local(): ytitles.append(" Total CS cm2/g")
        #if self.do_plot_local(): ytitles.append(" Mu cm^-1")
        if self.do_plot_local(): ytitles.append(" Transmitivity")
        if self.do_plot_local(): ytitles.append(" Absorption")
        if self.do_plot_intensity(): ytitles.append("Intensity")

        return ytitles

    def getVariablesToPlot(self):
        variables = []

        if self.do_plot_intensity(): variables.append((0, 1))  # start plotting the source
        #if self.do_plot_local(): variables.append((0, 2))
        #if self.do_plot_local(): variables.append((0, 3))
        if self.do_plot_local(): variables.append((0, 2))
        if self.do_plot_local(): variables.append((0, 3))
        if self.do_plot_intensity(): variables.append((0, 4))

        return variables

    def getLogPlot(self):
        logplot = []

        if self.do_plot_intensity(): logplot.append((False,False))
        #if self.do_plot_local(): logplot.append((False, True))
        #if self.do_plot_local(): logplot.append((False, True))
        if self.do_plot_local(): logplot.append((False, False))
        if self.do_plot_local(): logplot.append((False, False))
        if self.do_plot_intensity(): logplot.append((False, False))

        return logplot




    def Attenuators_Thickness(self):
        thick=[]
        if self.FLAG == 0 :
            if self.ATT11== 0: thick.append(0.0)
            if self.ATT11== 1: thick.append(1.4)
            if self.ATT11== 2: thick.append(2.8)
            if self.ATT11== 3: thick.append(1.0)
            if self.ATT12== 0: thick.append(0.7)
            if self.ATT12== 1: thick.append(1.4)
            if self.ATT12== 2: thick.append(2.8)
            if self.ATT12== 3: thick.append(0.0)
            if self.ATT13== 0: thick.append(4.0)
            if self.ATT13== 1: thick.append(6.0)
            if self.ATT13== 2: thick.append(8.0)
            if self.ATT13== 3: thick.append(0.0)
            if self.ATT14== 0: thick.append(0.7)
            if self.ATT14== 1: thick.append(1.4)
            if self.ATT14== 2: thick.append(2.8)
            if self.ATT14== 3: thick.append(0.0)
            if self.ATT15== 0: thick.append(0.14)
            if self.ATT15== 1: thick.append(0.35)
            if self.ATT15== 2: thick.append(1.4)
            if self.ATT15== 3: thick.append(0.0)
            if self.ATT21== 0: thick.append(0.7)
            if self.ATT21== 1: thick.append(1.4)
            if self.ATT21== 2: thick.append(2.8)
            if self.ATT21== 3: thick.append(0.0)
            if self.ATT22== 0: thick.append(0.14)
            if self.ATT22== 1: thick.append(0.35)
            if self.ATT22== 2: thick.append(0.7)
            if self.ATT22== 3: thick.append(0.0)
            if self.ATT23== 0: thick.append(0.3)
            if self.ATT23== 1: thick.append(0.5)
            if self.ATT23== 2: thick.append(1.0)
            if self.ATT23== 3: thick.append(0.0)
            if self.ATT24== 0: thick.append(0.07)
            if self.ATT24== 1: thick.append(0.14)
            if self.ATT24== 2: thick.append(0.28)
            if self.ATT24== 3: thick.append(0.0)
            if self.ATT25== 0: thick.append(0.07)
            if self.ATT25== 1: thick.append(0.14)
            if self.ATT25== 2: thick.append(0.28)
            if self.ATT25== 3: thick.append(0.0)
        if self.FLAG == 1:
            thick=[self.C,self.Al,self.Cu,self.Mo,self.W,self.Au]

        return(thick)



    def xoppy_calc_xpower(self):

        #
        # prepare input for xpower_calc
        # Note that the input for xpower_calc accepts any number of elements.
        #
        if self.FLAG == 0:
            substance = ['C','Al','Cu','Al','Cu','Cu','Mo','W','W','Au']
            thick     = self.Attenuators_Thickness()
            dens      = [3.508,2.7,8.96,2.7,8.96,8.96,10.20,19.3,19.3,19.3]
            flags     =  [0,0,0,0,0,0,0,0,0,0]
        if self.FLAG == 1:
            substance = ['C', 'Al', 'Cu','Mo', 'W','Au']
            thick = self.Attenuators_Thickness()
            dens = [3.508, 2.7, 8.96, 10.20, 19.3, 19.3]
            flags = [0, 0, 0, 0, 0, 0]

        cumulated_data = {}
        Result=[]
        Result_Absorption=[]

        if self.SOURCE == 0:
            if self.input_spectrum is None:
                raise Exception("No input beam")
            else:
                energies = self.input_spectrum[0,:].copy()
                source = self.input_spectrum[1,:].copy()
        elif self.SOURCE == 1:
            energies = numpy.linspace(self.ENER_MIN,self.ENER_MAX,self.ENER_N)
            source = numpy.ones(energies.size)
            tmp = numpy.vstack( (energies,source))
            self.input_spectrum = source
        elif self.SOURCE == 2:
            if self.SOURCE == 2: source_file = self.SOURCE_FILE
            try:
                tmp = numpy.loadtxt(source_file)
                energies = tmp[:,0]
                source = tmp[:,1]
                self.input_spectrum = source
            except:
                print("Error loading file %s "%(source_file))
                raise

        if self.FILE_DUMP == 0:
            output_file = None
        else:
            output_file = "power.spec"
        out_dictionary = xpower_calc(energies=energies,source=source,substance=substance,
                                     flags=flags,dens=dens,thick=thick,angle=[],roughness=[],output_file=output_file)


        try:
            print(out_dictionary["info"])
        except:
            pass
        #calculate attenuators total
        Result.append((out_dictionary['data'][0]).tolist())
        Result.append((out_dictionary['data'][1]).tolist())
        #list2=[]
        #list3=[]
        list4=[]
        for k in range(len(substance)):
            #list2.append(out_dictionary['data'][2 + 5*k])
            #list3.append(out_dictionary['data'][3 + 5*k])
            list4.append(out_dictionary['data'][4 + 5*k])
        #Result.append(List_Product(list2))
        #Result.append(List_Product(list3))
        Result.append(List_Product(list4))

        for k in range(len(Result[0])):
            Result_Absorption.append(1-Result[-1][k])
        Result.append(Result_Absorption)

        Result.append((out_dictionary['data'][5*len(substance)+1]).tolist())
        cumulated_data['data']=numpy.array(Result)

        #send exchange
        calculated_data = DataExchangeObject("XOPPY", self.get_data_exchange_widget_name())
        try:
            calculated_data.add_content("xoppy_data", cumulated_data["data"].T)
        except:
            pass
        return calculated_data

def List_Product(list):
    L = []
    l = 1
    for k in range(len(list[0])):
        for i in range(len(list)):
            l = l * list[i][k]
        L.append(l)
        l = 1
    return (L)

if __name__ == "__main__":


    from oasys.widgets.exchange import DataExchangeObject



    input_data_type = "POWER"

    if input_data_type == "POWER":
        # create fake UNDULATOR_FLUX xoppy exchange data
        e = numpy.linspace(1000.0, 10000.0, 100)
        source = e/10
        received_data = DataExchangeObject("XOPPY", "POWER")
        received_data.add_content("xoppy_data", numpy.vstack((e,e,source)).T)
        received_data.add_content("xoppy_code", "US")

    elif input_data_type == "POWER3D":
        # create unulator_radiation xoppy exchange data
        from orangecontrib.xoppy.util.xoppy_undulators import xoppy_calc_undulator_radiation

        e, h, v, p, code = xoppy_calc_undulator_radiation(ELECTRONENERGY=6.04,ELECTRONENERGYSPREAD=0.001,ELECTRONCURRENT=0.2,\
                                           ELECTRONBEAMSIZEH=0.000395,ELECTRONBEAMSIZEV=9.9e-06,\
                                           ELECTRONBEAMDIVERGENCEH=1.05e-05,ELECTRONBEAMDIVERGENCEV=3.9e-06,\
                                           PERIODID=0.018,NPERIODS=222,KV=1.68,DISTANCE=30.0,
                                           SETRESONANCE=0,HARMONICNUMBER=1,
                                           GAPH=0.001,GAPV=0.001,\
                                           HSLITPOINTS=41,VSLITPOINTS=41,METHOD=0,
                                           PHOTONENERGYMIN=7000,PHOTONENERGYMAX=8100,PHOTONENERGYPOINTS=20,
                                           USEEMITTANCES=1)
        received_data = DataExchangeObject("XOPPY", "POWER3D")
        received_data = DataExchangeObject("XOPPY", "UNDULATOR_RADIATION")
        received_data.add_content("xoppy_data", [p, e, h, v])
        received_data.add_content("xoppy_code", code)




    app = QApplication(sys.argv)
    w = OWID19AttenuatorsBox()
    w.acceptExchangeData(received_data)
    w.show()
    app.exec()
    w.saveSettings()
