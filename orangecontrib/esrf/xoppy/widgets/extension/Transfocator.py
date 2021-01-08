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

class Transfocator(XoppyWidget):
    name = "Transfocator"
    id = "orange.widgets.dataxpower"
    description = "Power Absorbed and Transmitted by Optical Elements"
    icon = "icons/id19_trasnfocator.png"
    priority = 10
    category = ""
    keywords = ["xoppy", "power", "Transfocator"]

    inputs = [("ExchangeData", DataExchangeObject, "acceptExchangeData")]

    SOURCE = Setting(2)
    NUMBER_LENS = Setting(26)
    SUBSTANCE = Setting('Be')
    THICK = Setting(0.05)
    DENS = Setting('?')
    ENER_MIN = Setting(10000.0)
    ENER_MAX = Setting(200000.0)
    ENER_N = Setting(2000)
    SOURCE_FILE = Setting("?")
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
        self.box_source = gui.comboBox(box1, self, "SOURCE",
                                       label=self.unitLabels()[idx], addSpace=False,
                                       items=['From Oasys wire', 'Normalized to 1',
                                              'From external file.                '],
                                       valueType=int, orientation="horizontal", labelWidth=150)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 2
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "NUMBER_LENS",
                                       label=self.unitLabels()[idx], addSpace=False,
                                       valueType=int,  orientation="horizontal", labelWidth=150)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 3
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "SUBSTANCE",
                          label=self.unitLabels()[idx], addSpace=False, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 4
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "THICK",
                                       label=self.unitLabels()[idx], addSpace=False,
                                       valueType=float,  orientation="horizontal", labelWidth=150)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 5
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "DENS",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=150)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 6
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "ENER_MIN",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 7
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "ENER_MAX",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 8
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
        gui.separator(box1, height=7)

        gui.comboBox(box1, self, "FILE_DUMP",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['No', 'Yes (transfo.spec)'],
                    valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        self.input_spectrum = None




    def select_input_file(self):
        self.file_id.setText(oasysgui.selectFileFromDialog(self, self.SOURCE_FILE,
                                    "Open 2-columns file with spectral power",
                                    file_extension_filter="ascii dat (*.dat *.txt *spec)"))



    def unitLabels(self):
         return ['Input beam:', 'Number of Lens','Element','Thickness [mm]',
                 'Density g/cm^3',
                 'From energy [eV]:      ',
                 'To energy [eV]:',
                 'Energy points:  ',
                 'File with input beam spectral power:',"Dump file"]


    def unitFlags(self):
         return ['True','True','True','True',
                 'True',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  2',
                 'True']

    def get_help_name(self):
        return 'Transfocator'

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
        self.NUMBER_LENS = congruence.checkStrictlyPositiveNumber(self.NUMBER_LENS, "Number of Lens")
        self.THICK = congruence.checkStrictlyPositiveNumber(self.THICK, "Thickness")
        if self.SOURCE == 1:
            self.ENER_MIN = congruence.checkPositiveNumber(self.ENER_MIN, "Energy from")
            self.ENER_MAX = congruence.checkStrictlyPositiveNumber(self.ENER_MAX, "Energy to")
            congruence.checkLessThan(self.ENER_MIN, self.ENER_MAX, "Energy from", "Energy to")
            self.NPOINTS = congruence.checkStrictlyPositiveNumber(self.ENER_N, "Energy Points")
        elif self.SOURCE == 2:
            congruence.checkFile(self.SOURCE_FILE)

    def do_xoppy_calculation(self):
        return self.xoppy_calc_xpower()

    def extract_data_from_xoppy_output(self, calculation_output):
        return calculation_output


    def get_data_exchange_widget_name(self):
        return "POWER"



    def getTitles(self):
        return ['Input Beam','Transmitivity','Absorption','Intensity']

    def getXTitles(self):
        return ["Energy [eV]","Energy [eV]","Energy [eV]","Energy [eV]"]

    def getYTitles(self):
        return ["Source",'Transmitivity','Absorption',"Intensity"]


    def getVariablesToPlot(self):
        return [(0, 1),(0, 2),(0, 3),(0, 4)]

    def getLogPlot(self):
        return [(False,False),(False, False),(False, False),(False,False) ]




    def xoppy_calc_xpower(self):

        Result=[]
        Result_Absorption = []
        list=[]
        cumulated_data = {}

        substance = []
        thick = []
        dens = []
        flags = []

        for k in range (self.NUMBER_LENS) :
            substance.append(self.SUBSTANCE)
            thick.append(self.THICK)
            dens.append(self.DENS)
            flags.append(0)



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
            output_file = "Transfo.spec"

        out_dictionary = xpower_calc(energies=energies, source=source, substance=substance,
                                     flags=flags, dens=dens, thick=thick, angle=[], roughness=[],
                                     output_file=output_file)

        try:
            print(out_dictionary["info"])
        except:
            pass

        #calculate attenuators total
        Result.append((out_dictionary['data'][0]).tolist())
        Result.append((out_dictionary['data'][1]).tolist())
        for k in range(self.NUMBER_LENS):
            list.append(out_dictionary['data'][4 + 5*k])
        Result.append(List_Product(list))

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
    w = Transfocator()
    w.acceptExchangeData(received_data)
    w.show()
    app.exec()
    w.saveSettings()
