import sys
import numpy
from PyQt5.QtWidgets import QApplication, QMessageBox, QSizePolicy

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui, congruence
from oasys.widgets.exchange import DataExchangeObject
from orangecontrib.xoppy.widgets.gui.ow_xoppy_widget import XoppyWidget

from crystalpy.diffraction.GeometryType import BraggDiffraction, LaueDiffraction
from crystalpy.diffraction.DiffractionSetupXraylib import DiffractionSetupXraylib
from crystalpy.diffraction.Diffraction import Diffraction
import scipy.constants as codata
from crystalpy.util.Vector import Vector
from crystalpy.util.Photon import Photon


class Monochromator(XoppyWidget):
    name = "Monochromator"
    id = "orange.widgets.dataxpower"
    description = "Power Absorbed and Transmitted by Optical Elements"
    icon = "icons/id19_monochromator.png"
    priority = 3
    category = ""
    keywords = ["xoppy", "power", "monochromator"]

    inputs = [("ExchangeData", DataExchangeObject, "acceptExchangeData")]

    SOURCE = Setting(2)
    TYPE = Setting(1)
    ENER_SELECTED = Setting(8000)
    H_MILLER = Setting (1)
    K_MILLER = Setting (1)
    L_MILLER = Setting (1)
    THICK = Setting(15)
    ENER_MIN = Setting(7990)
    ENER_MAX = Setting(8010)
    ENER_N = Setting(2000)
    SOURCE_FILE = Setting("?")
    FILE_DUMP = Setting(0)
    METHOD = Setting(0)                # Zachariasen

    def build_gui(self):

        self.leftWidgetPart.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding))
        self.leftWidgetPart.setMaximumWidth(self.CONTROL_AREA_WIDTH + 20)
        self.leftWidgetPart.updateGeometry()

        box_main = oasysgui.widgetBox(self.controlArea, self.name + " Input Parameters", orientation="vertical", width=self.CONTROL_AREA_WIDTH-10)

        idx = -1

        box = oasysgui.widgetBox(box_main, "Input Beam Parameters", orientation="vertical", width=self.CONTROL_AREA_WIDTH-10)
        # widget index 1
        idx += 1
        box1 = gui.widgetBox(box)
        self.box_source = gui.comboBox(box1, self, "SOURCE",
                                       label=self.unitLabels()[idx], addSpace=False,
                                       items=['From Oasys wire', 'Normalized to 1',
                                              'From external file.                '],
                                       valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)


        # widget index 2
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "ENER_MIN",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 3
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "ENER_MAX",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 4
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "ENER_N",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 5 ***********   File Browser ******************
        idx += 1
        box1 = gui.widgetBox(box)
        file_box_id = oasysgui.widgetBox(box1, "", addSpace=False, orientation="horizontal")
        self.file_id = oasysgui.lineEdit(file_box_id, self, "SOURCE_FILE", self.unitLabels()[idx],
                                         labelWidth=100, valueType=str, orientation="horizontal")
        gui.button(file_box_id, self, "...", callback=self.select_input_file, width=25)
        self.show_at(self.unitFlags()[idx], box1)

        box = oasysgui.widgetBox(box_main, "Monochromator", orientation="vertical", width=self.CONTROL_AREA_WIDTH-10)
        # widget index 6
        idx += 1
        box1 = gui.widgetBox(box)
        self.box_source = gui.comboBox(box1, self, "TYPE",
                                       label=self.unitLabels()[idx], addSpace=False,
                                       items=['Empty','Si Bragg (double reflection)','Si Laue (single reflection)','Multilayer (not implemented)'],
                                       valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 7
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "ENER_SELECTED",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 8
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "H_MILLER",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 9
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "K_MILLER",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 10
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "L_MILLER",
                          label=self.unitLabels()[idx], addSpace=False,
                          valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 11
        idx += 1
        box1 = gui.widgetBox(box)
        oasysgui.lineEdit(box1, self, "THICK",
                                       label=self.unitLabels()[idx], addSpace=False,
                                       valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 12
        idx += 1
        box1 = gui.widgetBox(box)
        gui.separator(box1, height=7)

        gui.comboBox(box1, self, "FILE_DUMP",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['No', 'Yes (monochromator.spec)'],
                    valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 13
        idx += 1
        box1 = gui.widgetBox(box)
        gui.comboBox(box1, self, "METHOD",
                     label=self.unitLabels()[idx], addSpace=True,
                     items=["Zachariasen", "Guigay"],
                     orientation="horizontal")
        self.show_at(self.unitFlags()[idx], box1)

        self.input_spectrum = None


    def select_input_file(self):
        self.file_id.setText(oasysgui.selectFileFromDialog(self, self.SOURCE_FILE,
                                    "Open 2-columns file with spectral power",
                                    file_extension_filter="ascii dat (*.dat *.txt *spec)"))



    def unitLabels(self):
         return ['Input beam:',
                 'From energy [eV]:      ',
                 'To energy [eV]:',
                 'Energy points:  ',
                 'File with input beam spectral power:',
                 'Type Monochromator',
                 'Energy Selected [eV]',
                 'miller index h','miller index k','miller index l','Crystal thickness [microns]',
                 "Dump file",
                 "Calculation method"]


    def unitFlags(self):
         return ['True',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  2',
                 'True',
                 'self.TYPE  ==  1 or self.TYPE  ==  2 or self.TYPE  ==  3',
                 'self.TYPE  ==  1 or self.TYPE  ==  2','self.TYPE  ==  1 or self.TYPE  ==  2','self.TYPE  ==  1 or self.TYPE  ==  2',
                 'self.TYPE  ==  2',
                 'True',
                 'True']

    def get_help_name(self):
        return 'Monochromator'

    def selectFile(self):
        self.le_source_file.setText(oasysgui.selectFileFromDialog(self, self.SOURCE_FILE, "Open Source File", file_extension_filter="*.*"))

    def acceptExchangeData(self, exchangeData):

        self.input_spectrum = None
        self.SOURCE = 0

        try:
            if not exchangeData is None:
                if exchangeData.get_program_name() == "XOPPY":
                    no_bandwidth = False
                    if exchangeData.get_widget_name() =="UNDULATOR_FLUX" :
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() == "BM" :
                        if exchangeData.get_content("is_log_plot") == 1:
                            raise Exception("Logaritmic X scale of Xoppy Energy distribution not supported")
                        if exchangeData.get_content("calculation_type") == 0 and exchangeData.get_content("psi") == 0:
                            no_bandwidth = True
                            index_flux = 6
                        else:
                            raise Exception("Xoppy result is not an Flux vs Energy distribution integrated in Psi")
                    elif exchangeData.get_widget_name() =="XWIGGLER" :
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() =="WS" :
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() =="XTUBES" :
                        index_flux = 1
                        no_bandwidth = True
                    elif exchangeData.get_widget_name() =="XTUBE_W" :
                        index_flux = 1
                        no_bandwidth = True
                    elif exchangeData.get_widget_name() =="BLACK_BODY" :
                        no_bandwidth = True
                        index_flux = 2

                    elif exchangeData.get_widget_name() =="UNDULATOR_RADIATION" :
                        no_bandwidth = True
                        index_flux = 1
                    elif exchangeData.get_widget_name() =="POWER" :
                        no_bandwidth = True
                        index_flux = -1
                    elif exchangeData.get_widget_name() =="POWER3D" :
                        no_bandwidth = True
                        index_flux = 1

                    else:
                        raise Exception("Xoppy Source not recognized")

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
        if self.TYPE  ==  1:
            self.ENER_SELECTED = congruence.checkPositiveNumber(self.ENER_SELECTED, "Energy Selected [eV]")
            self.H_MILLER = congruence.checkNumber(self.H_MILLER, "H Miller")
            self.K_MILLER = congruence.checkNumber(self.K_MILLER, "K Miller")
            self.L_MILLER = congruence.checkNumber(self.H_MILLER, "L Miller")
        if self.TYPE == 2:
            self.ENER_SELECTED = congruence.checkPositiveNumber(self.ENER_SELECTED, "Energy Selected [eV]")
            self.H_MILLER = congruence.checkNumber(self.H_MILLER, "H Miller")
            self.K_MILLER = congruence.checkNumber(self.K_MILLER, "K Miller")
            self.L_MILLER = congruence.checkNumber(self.H_MILLER, "L Miller")
            self.THICK = congruence.checkPositiveNumber(self.THICK, "Laue crystal thickness [mm]")
        if self.TYPE == 3:
            self.ENER_SELECTED = congruence.checkPositiveNumber(self.ENER_SELECTED, "Energy Selected [eV]")

        if self.SOURCE == 1:
            self.ENER_MIN = congruence.checkPositiveNumber(self.ENER_MIN, "Energy from")
            self.ENER_MAX = congruence.checkStrictlyPositiveNumber(self.ENER_MAX, "Energy to")
            congruence.checkLessThan(self.ENER_MIN, self.ENER_MAX, "Energy from", "Energy to")
            self.NPOINTS = congruence.checkStrictlyPositiveNumber(self.ENER_N, "Energy Points")
        elif self.SOURCE == 2:
            congruence.checkFile(self.SOURCE_FILE)

    def do_xoppy_calculation(self):
        return self.xoppy_calc_mono()

    def extract_data_from_xoppy_output(self, calculation_output):
        return calculation_output

    def get_data_exchange_widget_name(self):
        return "POWER"

    def getTitles(self):
        return ['Input Beam','Monochromator reflectivity','Transmitted intensity']

    def getXTitles(self):
        return ["Energy [eV]","Energy [eV]","Energy [eV]"]

    def getYTitles(self):
        return ["Source",'Reflectivity','Intensity']


    def getVariablesToPlot(self):
        return [(0, 1),(0, 2),(0, 3)]

    def getLogPlot(self):
        return [(False,False),(False, False),(False, False)]


    def calculate_bragg_dcm(self, h_miller=1, k_miller=1, l_miller=1,
                            energy_setup=8000.0, energies=numpy.linspace(7900, 8100, 200)):

        energy_setup = self.ENER_SELECTED
        r = numpy.zeros_like(energies)
        harmonic = 1

        diffraction_setup_r = DiffractionSetupXraylib(geometry_type=BraggDiffraction(),  # GeometryType object
                                               crystal_name="Si",  # string
                                               thickness=1,  # meters
                                               miller_h=harmonic * h_miller,  # int
                                               miller_k=harmonic * k_miller,  # int
                                               miller_l=harmonic * l_miller,  # int
                                               asymmetry_angle=0,  # 10.0*numpy.pi/180.,            # radians
                                               azimuthal_angle=0.0)  # radians                            # int


        bragg_angle = diffraction_setup_r.angleBragg(energy_setup)
        print("Bragg angle for Si%d%d%d at E=%f eV is %f deg" % (
            h_miller, k_miller, l_miller, energy_setup, bragg_angle * 180.0 / numpy.pi))
        nharmonics = int( energies.max() / energy_setup)

        if nharmonics < 1:
            nharmonics = 1
        print("Calculating %d harmonics" % nharmonics)

        for harmonic in range(1,nharmonics+1,2): # calculate only odd harmonics
            print("\nCalculating harmonic: ", harmonic)
            ri = numpy.zeros_like(energies)
            for i in range(energies.size):
                try:
                    diffraction_setup_r = DiffractionSetupXraylib(geometry_type=BraggDiffraction(),  # GeometryType object
                                                           crystal_name="Si",  # string
                                                           thickness=1,  # meters
                                                           miller_h=harmonic * h_miller,  # int
                                                           miller_k=harmonic * k_miller,  # int
                                                           miller_l=harmonic * l_miller,  # int
                                                           asymmetry_angle=0,  # 10.0*numpy.pi/180.,            # radians
                                                           azimuthal_angle=0.0)  # radians                            # int

                    diffraction = Diffraction()

                    energy = energies[i]
                    deviation = 0.0  # angle_deviation_min + ia * angle_step
                    angle = deviation + bragg_angle

                    # calculate the components of the unitary vector of the incident photon scan
                    # Note that diffraction plane is YZ
                    yy = numpy.cos(angle)
                    zz = - numpy.abs(numpy.sin(angle))
                    photon = Photon(energy_in_ev=energy, direction_vector=Vector(0.0, yy, zz))

                    # perform the calculation
                    coeffs_r = diffraction.calculateDiffractedComplexAmplitudes(diffraction_setup_r, photon, calculation_method=self.METHOD)
                    # note the power 4 to get intensity (**2) for a double reflection (**2)

                    r[i] += numpy.abs( coeffs_r['S'] ) ** 4
                    ri[i] = numpy.abs( coeffs_r['S'] ) ** 4
                except:
                    print("Failed to calculate reflectivity at E=%g eV for %d%d%d reflection" % (energy,
                                            harmonic*h_miller, harmonic*k_miller, harmonic*l_miller))
            print("Max reflectivity: ", ri.max(), " at energy: ", energies[ri.argmax()])
        print("\n\n\n")
        return r

    def calculate_laue_monochromator(self, h_miller=1, k_miller=1, l_miller=1,
                            energy_setup=8000.0, energies=numpy.linspace(7900, 8100, 200)):

        energy_setup = self.ENER_SELECTED
        r = numpy.zeros_like(energies)
        harmonic = 1
        diffraction_setup_r = DiffractionSetupXraylib(geometry_type=LaueDiffraction(),  # GeometryType object
                                               crystal_name="Si",  # string
                                               thickness=self.THICK*1e-6,  # meters
                                               miller_h=harmonic * h_miller,  # int
                                               miller_k=harmonic * k_miller,  # int
                                               miller_l=harmonic * l_miller,  # int
                                               asymmetry_angle=numpy.pi/2,  # 10.0*numpy.pi/180.,            # radians
                                               azimuthal_angle=0)  # radians                            # int


        bragg_angle = diffraction_setup_r.angleBragg(energy_setup)
        print("Bragg angle for Si%d%d%d at E=%f eV is %f deg" % (
            h_miller, k_miller, l_miller, energy_setup, bragg_angle * 180.0 / numpy.pi))
        nharmonics = int( energies.max() / energy_setup)

        if nharmonics < 1:
            nharmonics = 1
        print("Calculating %d harmonics" % nharmonics)

        for harmonic in range(1, nharmonics+1, 2): # calculate only odd harmonics
            print("\nCalculating harmonic: ", harmonic)
            ri = numpy.zeros_like(energies)
            for i in range(energies.size):
                try:
                    diffraction_setup_r = DiffractionSetupXraylib(geometry_type=LaueDiffraction(),  # GeometryType object
                                                           crystal_name="Si",  # string
                                                           thickness=self.THICK*1e-6,  # meters
                                                           miller_h=harmonic * h_miller,  # int
                                                           miller_k=harmonic * k_miller,  # int
                                                           miller_l=harmonic * l_miller,  # int
                                                           asymmetry_angle=numpy.pi/2,  # 10.0*numpy.pi/180.,            # radians
                                                           azimuthal_angle=0)  # radians                            # int

                    diffraction = Diffraction()

                    energy = energies[i]
                    deviation = 0.0  # angle_deviation_min + ia * angle_step
                    angle = deviation + numpy.pi/2 + bragg_angle

                    # calculate the components of the unitary vector of the incident photon scan
                    # Note that diffraction plane is YZ
                    yy = numpy.cos(angle)
                    zz = - numpy.abs(numpy.sin(angle))
                    photon = Photon(energy_in_ev=energy, direction_vector=Vector(0.0, yy, zz))

                    # perform the calculation
                    coeffs_r = diffraction.calculateDiffractedComplexAmplitudes(diffraction_setup_r, photon, calculation_method=self.METHOD)
                    # note the power 2 to get intensity
                    r[i] += numpy.abs( coeffs_r['S'] ) ** 2
                    ri[i] = numpy.abs( coeffs_r['S'] ) ** 2
                except:
                    print("Failed to calculate reflectivity at E=%g eV for %d%d%d reflection" % (energy,
                                            harmonic*h_miller, harmonic*k_miller, harmonic*l_miller))
            print("Max reflectivity: ", ri.max(), " at energy: ", energies[ri.argmax()])
        print("\n\n\n")
        return r

    def xoppy_calc_mono(self):

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


        if self.TYPE==0:
            Mono_Effect = [1] * len(energies)
        elif self.TYPE==1:
            Mono_Effect = self.calculate_bragg_dcm(energies=energies)
        elif self.TYPE==2:
            Mono_Effect = self.calculate_laue_monochromator(energies=energies)
        else: #TODO:
            Mono_Effect = [1] * len(energies)


        Final_Spectrum=List_Product([source,Mono_Effect])

        Output=[]
        Output.append(energies.tolist())
        Output.append(source.tolist())
        Output.append(Mono_Effect)
        Output.append(Final_Spectrum)
        Output=numpy.array(Output)

        if self.FILE_DUMP == 1:
            output_file = "monochromator.spec"
            f = open(output_file, 'w')
            f.write("#S 1\n#N 4\n#L Photon energy [eV]  source  monochromator reflectivity  transmitted intensity\n")
            for i in range(Output.shape[1]):
                f.write("%g  %g  %g  %g\n" % (Output[0,i], Output[1,i], Output[2,i], Output[3,i]) )
            f.close()
            print("File written to disk: %s" % output_file)

        # print results
        I1 = numpy.trapz( numpy.array(source), x=energies, axis=-1)
        I2 = numpy.trapz( numpy.array(Final_Spectrum), x=energies, axis=-1)
        txt  = "      Incoming power: %f\n"%(I1)
        txt += "      Outcoming power: %f\n" % (I2)
        txt += "      Absorbed power: %f\n"%(I1-I2)
        txt += "      Normalized Absorbed power: %f\n"%((I1-I2)/I1)
        print(txt)


        # send exchange
        calculated_data = DataExchangeObject("XOPPY", self.get_data_exchange_widget_name())
        try:
            calculated_data.add_content("xoppy_data", Output.T)
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
        e = numpy.linspace(7900.0, 8100.0, 1500)
        source = e/10
        received_data = DataExchangeObject("XOPPY", "POWER")
        received_data.add_content("xoppy_data", numpy.vstack((e,e,source)).T)
        received_data.add_content("xoppy_code", "US")

    elif input_data_type == "POWER3D":
        # create unulator_radiation xoppy exchange data
        from xoppylib.sources.xoppy_undulators import xoppy_calc_undulator_radiation

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
    w = Monochromator()
    w.acceptExchangeData(received_data)
    w.show()
    app.exec()
    w.saveSettings()
