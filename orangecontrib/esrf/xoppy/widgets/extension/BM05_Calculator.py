import os, sys
import numpy
from PyQt5.QtWidgets import QApplication, QMessageBox, QSizePolicy

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui, congruence
from oasys.widgets.exchange import DataExchangeObject

from oasys.widgets.exchange import DataExchangeObject
from orangecontrib.xoppy.widgets.gui.ow_xoppy_widget import XoppyWidget

import scipy.constants as codata


class OWBM05Calculator(XoppyWidget):
    name = "BM05_Calculator"
    id = "orange.widgets.dataxpower"
    description = "Calculates some values used for BM05"
    icon = "icons/bm05_calculator.png"
    priority = 1
    category = ""
    keywords = ["xoppy", "power"]

    inputs = [("ExchangeData", DataExchangeObject, "acceptExchangeData")]

    SOURCE = Setting(2)
    ENER_MIN = Setting(1000.0)
    ENER_MAX = Setting(50000.0)
    ENER_N = Setting(100)
    SOURCE_FILE = Setting("?")
    
    BM05_CONFIGURATION = Setting(3)   
    CHOPPER = Setting(100.0)    
    EXTRA_AIR_BEFORE_SAMPLE = Setting(0.0)
    CALCULATION_TYPE = Setting(0)
    PROPAGATION_DISTANCE = Setting(10)
    SCINTILLATOR_EFFICIENCY = Setting(0) #ph/keV
            
    input_spectrum = None
    input_script = None
    output_file = None
    

    def __init__(self):
        
        super().__init__(show_script_tab=True)
        self.main_tabs.removeTab(0)
               

    def build_gui(self):                

        self.leftWidgetPart.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding))
        self.leftWidgetPart.setMaximumWidth(self.CONTROL_AREA_WIDTH + 20)
        self.leftWidgetPart.updateGeometry()

        box = oasysgui.widgetBox(self.controlArea, self.name + " Input Parameters", orientation="vertical", width=self.CONTROL_AREA_WIDTH-10)

        idx = -1 

        #widget index 2 
        idx += 1 
        box1 = gui.widgetBox(box) 
        self.box_source = gui.comboBox(box1, self, "SOURCE",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['From Oasys wire', 'Normalized to 1 W/eV', 'From external file (eV, W/eV)', 'From external file (eV, phot/s/.1%bw)'],
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

        #widget index 9 ***********   File Browser ******************
        idx += 1
        box1 = gui.widgetBox(box)
        file_box_id = oasysgui.widgetBox(box1, "", addSpace=False, orientation="horizontal")
        self.file_id = oasysgui.lineEdit(file_box_id, self, "SOURCE_FILE", self.unitLabels()[idx],
                                    labelWidth=100, valueType=str, orientation="horizontal")
        gui.button(file_box_id, self, "...", callback=self.select_input_file, width=25)
        self.show_at(self.unitFlags()[idx], box1)

        idx += 1 
        box1 = gui.widgetBox(box) 
        self.box_source = gui.comboBox(box1, self, "BM05_CONFIGURATION",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['(0) BM05 ESRF EH2 (0.85T)',
                          '(1) BM18 central axis (1.56T)', '(2) BM18 lateral axis (0.85T)',
                          '(3) BM05 EH2 central axis (0.85T)', '(4) BM05 EH2 side beam (0.39T)',
                          '(5) BM05 EH1 central axis (0.85T)', '(6) BM05 EH1 side beam (0.39T)'
                           ],
                    valueType=int, orientation="horizontal", labelWidth=150)
        self.show_at(self.unitFlags()[idx], box1)              

        #widget index 12 
        idx += 1 
        box1 = gui.widgetBox(box) 
        oasysgui.lineEdit(box1, self, "CHOPPER",
                     label=self.unitLabels()[idx], addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1) 
        
        #widget index 13 
        idx += 1 
        box1 = gui.widgetBox(box) 
        oasysgui.lineEdit(box1, self, "EXTRA_AIR_BEFORE_SAMPLE",
                     label=self.unitLabels()[idx], addSpace=False,
                    valueType=float, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 14 
        idx += 1 
        box1 = gui.widgetBox(box) 
        self.box_source = gui.comboBox(box1, self, "CALCULATION_TYPE",
                     label=self.unitLabels()[idx], addSpace=False,
                    items=['Spectrum at sample surface',
                           'Spectrum after sample',                          
                           'Spectrum at detector level (without sample)',
                           'Spectrum at detector level with sample',
                           'Detected spectrum (without sample)',
                           'Detected spectrum with sample'
                          ],
                    valueType=int, orientation="horizontal", labelWidth=150)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 15
        idx += 1 
        box1 = gui.widgetBox(box) 
        oasysgui.lineEdit(box1, self, "PROPAGATION_DISTANCE",
                     label=self.unitLabels()[idx], addSpace=False,
                    valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        #widget index 15
        idx += 1 
        box1 = gui.widgetBox(box) 
        oasysgui.lineEdit(box1, self, "SCINTILLATOR_EFFICIENCY",
                     label=self.unitLabels()[idx], addSpace=False,
                    valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

    def select_input_file(self):
        self.file_id.setText(oasysgui.selectFileFromDialog(self, self.SOURCE_FILE,
                                    "Open 2-columns file with spectral power",
                                    file_extension_filter="ascii dat (*.dat *.txt *spec)"))         
                

    def set_EL_FLAG(self):
        self.initializeTabs()
    

    def unitLabels(self):
         return ['Input beam:',
                 'From energy [eV]:      ',
                 'To energy [eV]:',
                 'Energy points:  ',
                 'File with input beam spectral power:',
                 'BM05 Configuration: ',                 
                 'Chopper (%):',
                 'Extra air before sample (m):',
                 'Spectral calculation',
                 'Propagation distance (m): ',
                 'Scintillator efficiency (ph/keV):'
                ]


    def unitFlags(self):
         return ['True',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  ==  1',
                 'self.SOURCE  >  1',
                 'True',                 
                 'True',
                 'True',
                 'True',
                 'self.CALCULATION_TYPE >= 2',
                 'self.CALCULATION_TYPE >= 4'
                ]

    def get_help_name(self):
        return 'BM05_Calculator'

    def acceptExchangeData(self, exchangeData):

        self.input_spectrum = None
        self.input_script = None
        self.SOURCE = 0        

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
                        if exchangeData.get_content("calculation_type") == 0 and exchangeData.get_content("psi") in [0,2]:
                            # self.SOURCE_FILE = "xoppy_bm_flux"
                            no_bandwidth = True
                            index_flux = 6
                        else:
                            raise Exception("Xoppy result is not a Flux vs Energy distribution integrated in Psi")
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

                    try:
                        self.input_script = exchangeData.get_content("xoppy_script")
                    except:
                        self.input_script = None

                    self.source_of_previous_element = spectrum[:,1]
                    self.process_showers()
                    self.compute()

        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

    def check_fields(self):

        self.CHOPPER == congruence.checkPositiveNumber(self.CHOPPER, "Chopper")
        self.EXTRA_AIR_BEFORE_SAMPLE == congruence.checkPositiveNumber(self.EXTRA_AIR_BEFORE_SAMPLE, "Extra air before sample")
                        
    def get_values_from_bm05_config(self):

        """ This function is to get the values of sample position, beam_v_size
        and beam_h_size for a given configuration these values were taken from
        the EXCEL file dose_estimator_BM05-BM18_2023.xlsx
        Sample position is in meters and beam sizes in milimeters """

        if self.BM05_CONFIGURATION == 0:
            config_name = '(0) BM05 ESRF EH2 (0.85T)'
            sample_position = 58.0 
            beam_v_size = 5.0 
            beam_h_size = 10.0

        elif self.BM05_CONFIGURATION == 1:
            config_name = '(1) BM18 central axis (1.56T)'
            sample_position = 175 
            beam_v_size = 10.0 
            beam_h_size = 10.0

        elif self.BM05_CONFIGURATION == 2:
            config_name = '(2) BM18 lateral axis  (0.85T)'
            sample_position = 175 
            beam_v_size = 10.0 
            beam_h_size = 10.0

        elif self.BM05_CONFIGURATION == 3:
            config_name = '(3) BM05 EH2 central axis (0.85T)'
            sample_position = 56.5 # meters
            beam_v_size = 5.0 # mm
            beam_h_size = 10.0 #mm

        elif self.BM05_CONFIGURATION == 4:
            config_name = '(4) BM05 EH2 side beam (0.39T)'                      
            sample_position = 56.5 # meters
            beam_v_size = 5.0 # mm
            beam_h_size = 10.0 #mm

        elif self.BM05_CONFIGURATION == 5:
            config_name = '(5) BM05 EH1 central axis (0.85T)'
            sample_position = 44.0 # meters
            beam_v_size = 5.0 # mm
            beam_h_size = 10.0 #mm
        
        elif self.BM05_CONFIGURATION == 6:
            config_name = '(6) BM05 EH1  side beam (0.39T)'
            sample_position = 44.0 # meters
            beam_v_size = 5.0 # mm
            beam_h_size = 10.0 #mm
        
        else:
            raise RuntimeError("ERROR: Sorry this configuration has not been yet implemented")

        return config_name, sample_position, beam_v_size, beam_h_size
    
    def get_label_calculation_type(self):

        if self.CALCULATION_TYPE == 0:
            cal_type_str = "Spectrum at sample surface"

        elif self.CALCULATION_TYPE == 1:
            cal_type_str = 'Spectrum after sample'

        elif self.CALCULATION_TYPE == 2:
            cal_type_str = 'Spectrum at detector level (without sample)'
        
        elif self.CALCULATION_TYPE == 3:                        
            cal_type_str = 'Spectrum at detector level with sample'
        
        elif self.CALCULATION_TYPE == 4:
            cal_type_str = 'Detected spectrum (without sample)'
        
        elif self.CALCULATION_TYPE == 5:
            cal_type_str = 'Detected spectrum with sample'
        else:
            raise RuntimeError("ERROR: Sorry this calculation type has not been yet implemented")

        return cal_type_str

    def do_xoppy_calculation(self):
    
        if self.SOURCE == 0:
            if self.input_spectrum is None:
                raise Exception("No input beam")
            else:
                energies = self.input_spectrum[0,:].copy()
                source = self.input_spectrum[1,:].copy()
                #if self.CALCULATION_TYPE:
                #    absorbed = source - self.input_spectrum[-1,:].copy()
            if self.input_script is None:
                script_previous = '#\n# >> MISSING SCRIPT TO CREATE (energy, spectral_power) <<\n#\n'
            else:
                script_previous = self.input_script
        elif self.SOURCE == 1:
            energies = numpy.linspace(self.ENER_MIN,self.ENER_MAX,self.ENER_N)
            source = numpy.ones(energies.size)
            tmp = numpy.vstack( (energies,source))
            self.input_spectrum = source
            script_previous = "import numpy\nenergy = numpy.linspace(%g,%g,%d)\nspectral_power = numpy.ones(%d)\n" % \
                        (self.ENER_MIN,self.ENER_MAX,self.ENER_N,self.ENER_N)
        elif self.SOURCE == 2:  # file contains energy_eV and spectral power (W/eV)
            source_file = self.SOURCE_FILE
            try:
                tmp = numpy.loadtxt(source_file)
                energies = tmp[:,0]
                source = tmp[:,1]
                self.input_spectrum = source
                script_previous = "import numpy\ntmp = numpy.loadtxt(%s)\nenergy = tmp[:,0]\nspectral_power = tmp[:,1]\n" % \
                                (source_file)
            except:
                print("Error loading file %s "%(source_file))
                raise
        elif self.SOURCE == 4:  # file contains energy_eV and flux (ph/s/0.1%bw
            source_file = self.SOURCE_FILE
            try:
                tmp = numpy.loadtxt(source_file)
                energies = tmp[:,0]
                source = tmp[:,1] * (codata.e * 1e3)
                self.input_spectrum = source
                script_previous = "import numpy\nimport scipy.constants as codata\ntmp = numpy.loadtxt(%s)\nenergy = tmp[:,0]\nspectral_power = tmp[:,1] / (codata.e * 1e3)\n" % \
                                (source_file)
            except:
                print("Error loading file %s "%(source_file))
                raise
        
        # get values from configuration        
        config_name, sample_position, beam_v_size, beam_h_size = self.get_values_from_bm05_config()        

        chopper = self.CHOPPER  # chpper in percentage
        extra_distance = self.EXTRA_AIR_BEFORE_SAMPLE # distance to project the slit
        energy_bin_size = energies[1] - energies[0]

        # we get the flux for typical cases and for detected at the scintillators
        if self.CALCULATION_TYPE < 4:
            flux = source/codata.e/1e3
        else:
            flux = (self.source_of_previous_element - source)/codata.e/1e3 * energies/1000 * self.SCINTILLATOR_EFFICIENCY 

        # calculate the energy scaling factor
        e_scaling_fac = energy_bin_size / (energies / 1e3)

        # considering the propagation distance
        if self.CALCULATION_TYPE >= 2:            
            extra_distance = self.PROPAGATION_DISTANCE  

        calculation_distance = sample_position + extra_distance 
                    
        #flux at the calculation level per mm2
        flux_calc_level = flux * e_scaling_fac / (beam_v_size * beam_h_size) * \
                (chopper/100) * sample_position**2 / (calculation_distance)**2
        
        #Integrated flux per mm2:
        calculation_type = self.get_label_calculation_type()
        total_flux = sum(flux_calc_level)
        pic_energy = energies[numpy.argmax(flux_calc_level)] / 1e3
        integrated_energy = sum(energies * flux_calc_level / sum(flux_calc_level)) / 1e3
                
        print("Calculation for the configuration %s" % (config_name))
        print("Source has been calculated over a slit at %.1f m" % (sample_position))
        print("Slit horizontal aperture of %.1f mm" % (beam_h_size))
        print("Slit vertical aperture of %.1f mm" % (beam_v_size))

        print("________________BM05_Calculator________________")                
        print(calculation_type)
        print("For a distance of %.3f m" % (calculation_distance))
        print("Flux (ph/s/mm2) %.2e" % (total_flux))
        print("Pic energy %.1f keV" % (pic_energy))
        print("Integrated energy %.1f keV" % (integrated_energy))  
        
        # This is for the script   

        dict_parameters = {           
            "config_name"            : config_name,            
            "calculation_type"       : calculation_type,
            "calculation_distance"   : "%s" % (calculation_distance),           
            "total_flux"             : "{:0.2e}".format(total_flux),       
            "pic_energy"             : "%s" % (round(pic_energy, 1)),       
            "integrated_energy"      : "%s" % (round(integrated_energy, 1))                                 
        }          

        out_dictionary = {}

        #This widget does not calculate any spectrum, so just pass the incoming spectrum
        out_dictionary['data'] = [energies, source]                                         

        script_element = self.script_template().format_map(dict_parameters)

        script = script_previous + script_element        

        self.xoppy_script.set_code(script)

        return out_dictionary, script

    def script_template(self):
        return """
#
# script to make the calculations (created by XOPPY:BM05_Calculator)
#
print("________________BM05_Calculator________________") 
print("Calculation for the configuration {config_name}")
print("{calculation_type}")
print("For a distance of {calculation_distance} m")
print("Flux {total_flux} (ph/s/mm2)")
print("Pic energy {pic_energy} keV")
print("Integrated energy {integrated_energy} keV")

#
# end script
#
"""  
    def extract_data_from_xoppy_output(self, calculation_output):

        """ Calculated data """        

        out_dictionary, script = calculation_output

        cumulated_data = {}                
        results = []

        # First, we add the typical: energy axis and input beam        
        results.append((out_dictionary['data'][0]).tolist()) #Pos: 0
        results.append((out_dictionary['data'][1]).tolist()) #Pos: 1

        cumulated_data['data']=numpy.array(results)
                
        calculated_data = DataExchangeObject("XOPPY", self.get_data_exchange_widget_name())
       
        try:
            calculated_data.add_content("xoppy_data", cumulated_data["data"].T)
        except:
            pass
        try:
            calculated_data.add_content("xoppy_script", script)
        except:
            pass
        try:
            calculated_data.add_content("labels", out_dictionary["labels"])
        except:
            pass
        try:
           calculated_data.add_content("info", out_dictionary["info"])
        except:
           pass   
        return calculated_data


    def get_data_exchange_widget_name(self):
        return "POWER"    


if __name__ == "__main__":

    import sys
    input_type = 0

    if input_type == 1:
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
        w = OWBM05Calculator()
        w.acceptExchangeData(received_data)
        w.show()
        app.exec()
        w.saveSettings()

    else:
        app = QApplication(sys.argv)
        w = OWBM05Calculator()
        w.SOURCE = 1
        w.show()
        app.exec()
        w.saveSettings()
