import os, sys
import numpy
from PyQt5.QtWidgets import QApplication, QMessageBox, QSizePolicy

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui, congruence
from oasys.widgets.exchange import DataExchangeObject

from xoppylib.power.xoppy_calc_power import xoppy_calc_power

from oasys.widgets.exchange import DataExchangeObject
from orangecontrib.xoppy.widgets.gui.ow_xoppy_widget import XoppyWidget
import json
import orangecanvas.resources as resources

import scipy.constants as codata

import xraylib
from dabax.dabax_xraylib import DabaxXraylib
import urllib

class OWAttenuatorsBox(XoppyWidget):
    name = "Attenuators Box"
    id = "orange.widgets.dataxpower"
    description = "Power Absorbed and Transmitted by Attenuators Box"
    icon = "icons/attenuators_box.png"
    priority = 1
    category = ""
    keywords = ["xoppy", "power"]

    inputs = [("ExchangeData", DataExchangeObject, "acceptExchangeData")]

    SOURCE = Setting(2)
    ENER_MIN = Setting(1000.0)
    ENER_MAX = Setting(100000.0)
    ENER_N = Setting(500)
    SOURCE_FILE = Setting("?")
    Att1 = Setting(0)
    Att2 = Setting(0)
    Att3 = Setting(0)
    Att4 = Setting(0)
    Att5 = Setting(0)
    n_att = Setting(4) # 4 means max index of 5 attenuators (maximum); this variable is hidden to the user

    PLOT_SETS = Setting(0)
    FILE_DUMP = 0

    MATERIAL_CONSTANT_LIBRARY_FLAG = Setting(0)
    file_json = '' # os.path.join(resources.package_dirname("orangecontrib.esrf.xoppy.data"), 'bm05_wb_attenuators.json')
    input_spectrum = None
    input_script = None
    att_dic = Setting(None) # use Setting() to store the dictionary with the box configuration in the workspace!

    wids = []

    def __init__(self):
        super().__init__(show_script_tab=True)

    def build_gui(self):
        # self.get_att_dictionary()

        self.leftWidgetPart.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding))
        self.leftWidgetPart.setMaximumWidth(self.CONTROL_AREA_WIDTH + 20)
        self.leftWidgetPart.updateGeometry()

        box = oasysgui.widgetBox(self.controlArea, self.name + " Input Parameters", orientation="vertical",
                                 width=self.CONTROL_AREA_WIDTH - 10)

        idx = -1

        # widget index 2
        idx += 1
        box1 = gui.widgetBox(box)
        self.box_source = gui.comboBox(box1, self, "SOURCE",
                                       label=self.unitLabels()[idx], addSpace=False,
                                       items=['From Oasys wire', 'Normalized to 1 W/eV',
                                              'From external file (eV, W/eV)', 'From external file (eV, phot/s/.1%bw)'],
                                       valueType=int, orientation="horizontal", labelWidth=150)
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

        # widget index 10 - Attenuators axis
        # for key in self.att_dic.keys():
        #     idx += 1
        #     box1 = gui.widgetBox(box)
        #     items = []
        #     for filter in self.att_dic[key].keys():
        #         items.append(self.att_dic[key][filter]['name'])
        #     gui.comboBox(box1, self, key,
        #                  label=self.unitLabels()[idx], addSpace=False,
        #                  items=items,
        #                  valueType=str, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        #     self.show_at(self.unitFlags()[idx], box1)

        box1 = gui.widgetBox(box, orientation="horizontal")
        gui.button(box1, self, "load box config json file...", callback=self.load_config_from_json_file, width=215)
        gui.button(box1, self, "write config file...", callback=self.write_config_file, width=125)

        for i in range(5):
            idx += 1
            box1 = gui.widgetBox(box)
            items = ['Empty']
            tmp = gui.comboBox(box1, self, 'Att%d' % (i+1),
                         label=self.unitLabels()[idx], addSpace=False,
                         items=items,
                         valueType=str, orientation="horizontal", labelWidth=50, callback=self.set_EL_FLAG,
                         editable=True)
            self.wids.append(tmp)
            self.show_at(self.unitFlags()[idx], box1)

        # widget index 15
        idx += 1
        box1 = gui.widgetBox(box)
        gui.separator(box1, height=7)

        gui.comboBox(box1, self, "PLOT_SETS",
                     label=self.unitLabels()[idx], addSpace=False,
                     items=['Total Attenuation', 'Axis Attenuation'],
                     valueType=int, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 16
        idx += 1
        box1 = gui.widgetBox(box)
        gui.separator(box1, height=7)

        gui.comboBox(box1, self, "MATERIAL_CONSTANT_LIBRARY_FLAG",
                     label=self.unitLabels()[idx], addSpace=False,
                     items=['Xraylib', 'DabaxXraylib'],
                     valueType=int, orientation="horizontal", labelWidth=250, callback=self.set_EL_FLAG)
        self.show_at(self.unitFlags()[idx], box1)

        # widget index 17
        idx += 1
        box1 = gui.widgetBox(box)
        gui.separator(box1, height=7)

        gui.comboBox(box1, self, "FILE_DUMP",
                     label=self.unitLabels()[idx], addSpace=False,
                     items=['No', 'Yes (power.spec)'],
                     valueType=int, orientation="horizontal", labelWidth=250)
        self.show_at(self.unitFlags()[idx], box1)

        self.configure_att_combox()


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
                'Att1', 'Att2', 'Att3', 'Att4', 'Att5',
                'Plot', 'Material data library', 'Dump file']

    def unitFlags(self):
        return ['True',
                'self.SOURCE  ==  1',
                'self.SOURCE  ==  1',
                'self.SOURCE  ==  1',
                'self.SOURCE  >  1',
                'self.n_att >= 0', 'self.n_att >= 1', 'self.n_att >= 2', 'self.n_att >= 3', 'self.n_att >= 4',
                'True', 'True', 'True']

    def load_config_from_json_file(self):
        file_name = oasysgui.selectFileFromDialog(self, '', "Open json File")
        if file_name is None: return
        if file_name == "": return

        try:
            congruence.checkEmptyString(file_name, "plane json File Name/Url")

            if (len(file_name) > 7  and file_name[:7] == "http://") or \
                (len(file_name) > 8 and file_name[:8] == "https://"):
                congruence.checkUrl(file_name)
                is_remote = True
            else:
                congruence.checkFile(file_name)
                is_remote = False

            try:
                if is_remote:
                    # raise Exception("URL not implemented for plane json files")
                    response = urllib.request.urlopen(file_name)
                    att_dic = json.load(response)
                else:
                    with open(file_name) as att_file:
                        att_dic = json.load(att_file)
                self.att_dic = att_dic
                self.configure_att_combox()

            except Exception as e:
                raise Exception("Error reading filter box from plane json file: " + str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)

    def configure_att_combox(self):
        if self.att_dic is None: return

        n_keys = 0
        keys = []
        for key in self.att_dic.keys():
            n_keys += 1
            keys.append(key)

        if n_keys > 5: raise Exception('No more than 5 attenuator blocks are allowed.')

        self.n_att = n_keys - 1 # max index
        # update combo boxes
        for i in range(n_keys):
            items = []
            for filter in self.att_dic[keys[i]].keys():
                if filter[0] != "_":
                    item = self.att_dic[keys[i]][filter]['name']
                    items.append(item)

            self._update_combo(self.wids[i], items)

    def _update_combo(self, id, new_input):
        n_old = id.count()
        n = len(new_input)
        for i in range(n):
            if i >= n_old:
                id.addItem(new_input[i])
            else:
                id.setItemText(i, new_input[i])

    def write_config_file(self):
        try:
            filename = oasysgui.selectSaveFileFromDialog(self, message="Save File", default_file_name="", file_extension_filter="*.*")
            if filename is not None:
                jsn1 = json.dumps(self.att_dic, indent=4, separators=(',', ': '))
                f = open(filename, 'w')
                f.write(jsn1)
                f.close()
                print("File written to disk: %s" % (filename))
                QMessageBox.information(self, "File Save", "JSON file %s correctly written to disk" % filename, QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)

    def get_help_name(self):
        return 'Attenuators Box'

    def selectFile(self):
        self.le_source_file.setText(
            oasysgui.selectFileFromDialog(self, self.SOURCE_FILE, "Open Source File", file_extension_filter="*.*"))

    def acceptExchangeData(self, exchangeData):

        self.input_spectrum = None
        self.input_script = None
        self.SOURCE = 0

        try:
            if not exchangeData is None:
                if exchangeData.get_program_name() == "XOPPY":
                    no_bandwidth = False
                    if exchangeData.get_widget_name() == "UNDULATOR_FLUX":
                        # self.SOURCE_FILE = "xoppy_undulator_flux"
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() == "BM":
                        if exchangeData.get_content("is_log_plot") == 1:
                            raise Exception("Logaritmic X scale of Xoppy Energy distribution not supported")
                        if exchangeData.get_content("calculation_type") == 0 and exchangeData.get_content("psi") in [0,
                                                                                                                     2]:
                            # self.SOURCE_FILE = "xoppy_bm_flux"
                            no_bandwidth = True
                            index_flux = 6
                        else:
                            raise Exception("Xoppy result is not a Flux vs Energy distribution integrated in Psi")
                    elif exchangeData.get_widget_name() == "XWIGGLER":
                        # self.SOURCE_FILE = "xoppy_xwiggler_flux"
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() == "WS":
                        # self.SOURCE_FILE = "xoppy_xwiggler_flux"
                        no_bandwidth = True
                        index_flux = 2
                    elif exchangeData.get_widget_name() == "XTUBES":
                        # self.SOURCE_FILE = "xoppy_xtubes_flux"
                        index_flux = 1
                        no_bandwidth = True
                    elif exchangeData.get_widget_name() == "XTUBE_W":
                        # self.SOURCE_FILE = "xoppy_xtube_w_flux"
                        index_flux = 1
                        no_bandwidth = True
                    elif exchangeData.get_widget_name() == "BLACK_BODY":
                        # self.SOURCE_FILE = "xoppy_black_body_flux"
                        no_bandwidth = True
                        index_flux = 2

                    elif exchangeData.get_widget_name() == "UNDULATOR_RADIATION":
                        # self.SOURCE_FILE = "xoppy_undulator_radiation"
                        no_bandwidth = True
                        index_flux = 1
                    elif exchangeData.get_widget_name() == "POWER":
                        # self.SOURCE_FILE = "xoppy_undulator_power"
                        no_bandwidth = True
                        index_flux = -1
                    elif exchangeData.get_widget_name() == "POWER3D":
                        # self.SOURCE_FILE = "xoppy_power3d"
                        no_bandwidth = True
                        index_flux = 1

                    else:
                        raise Exception("Xoppy Source not recognized")

                    # self.SOURCE_FILE += "_" + str(id(self)) + ".dat"

                    spectrum = exchangeData.get_content("xoppy_data")

                    if exchangeData.get_widget_name() == "UNDULATOR_RADIATION" or \
                            exchangeData.get_widget_name() == "POWER3D":
                        [p, e, h, v] = spectrum
                        tmp = p.sum(axis=2).sum(axis=1) * (h[1] - h[0]) * (v[1] - v[0]) * codata.e * 1e3
                        spectrum = numpy.vstack((e, p.sum(axis=2).sum(axis=1) * (h[1] - h[0]) * (v[1] - v[0]) *
                                                 codata.e * 1e3))
                        self.input_spectrum = spectrum
                    else:

                        if not no_bandwidth:
                            spectrum[:, index_flux] /= 0.001 * spectrum[:, 0]

                        self.input_spectrum = numpy.vstack((spectrum[:, 0], spectrum[:, index_flux]))

                    try:
                        self.input_script = exchangeData.get_content("xoppy_script")
                    except:
                        self.input_script = None

                    self.process_showers()
                    self.compute()

        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

    def check_fields(self):

        if self.SOURCE == 1:
            self.ENER_MIN = congruence.checkPositiveNumber(self.ENER_MIN, "Energy from")
            self.ENER_MAX = congruence.checkStrictlyPositiveNumber(self.ENER_MAX, "Energy to")
            congruence.checkLessThan(self.ENER_MIN, self.ENER_MAX, "Energy from", "Energy to")
            self.NPOINTS = congruence.checkStrictlyPositiveNumber(self.ENER_N, "Energy Points")
        elif self.SOURCE == 2:
            congruence.checkFile(self.SOURCE_FILE)

        self.check_att_pos()

    def check_att_pos(self):

        """ Here we check the use of filters that requieres a prefilter """

        if self.Att1 == 0 and self.Att2 >= 7:  # requires prefilter from Mo filter to the rest (W)
            QMessageBox.warning(self, "Warning", "Prefilter Required", QMessageBox.Ok)

        elif self.Att1 == 0 and self.Att2 == 0 and self.Att3 >= 4:  # requieres prefilter from Mo to the rest (Mo 0.44 mm)
            QMessageBox.warning(self, "Warning", "Prefilter Required", QMessageBox.Ok)

        else:
            pass

    ### Input for each axis of attenuators

    def att_pos(self):
        """ List of each attenuator position to be used in calcualtions """
        return [self.Att1, self.Att2, self.Att3, self.Att4, self.Att5]

    def att_substance(self):
        """ Substance (or material) for each axis """
        substance = []
        for i, att_axis in enumerate(self.att_dic.keys()):
            substance.append(self.att_dic[att_axis][f'filter{self.att_pos()[i] + 1}']['substance'])

        return substance

    def att_thick(self):
        """ Thickness of each attenuator at a given axis """
        thick = []
        for i, att_axis in enumerate(self.att_dic.keys()):
            thick.append(self.att_dic[att_axis][f'filter{self.att_pos()[i] + 1}']['thickness'])

        return thick

    def att_dens(self):
        """ Particular density of each attenuator at a given axis """
        dens = []
        for i, att_axis in enumerate(self.att_dic.keys()):
            dens.append(self.att_dic[att_axis][f'filter{self.att_pos()[i] + 1}']['density'])

        return dens

    def do_xoppy_calculation(self):

        if self.SOURCE == 0:
            if self.input_spectrum is None:
                raise Exception("No input beam")
            else:
                energies = self.input_spectrum[0, :].copy()
                source = self.input_spectrum[1, :].copy()
            if self.input_script is None:
                script_previous = '#\n# >> MISSING SCRIPT TO CREATE (energy, spectral_power) <<\n#\n'
            else:
                script_previous = self.input_script
        elif self.SOURCE == 1:
            energies = numpy.linspace(self.ENER_MIN, self.ENER_MAX, self.ENER_N)
            source = numpy.ones(energies.size)
            tmp = numpy.vstack((energies, source))
            self.input_spectrum = source
            script_previous = "import numpy\nenergy = numpy.linspace(%g,%g,%d)\nspectral_power = numpy.ones(%d)\n" % \
                              (self.ENER_MIN, self.ENER_MAX, self.ENER_N, self.ENER_N)
        elif self.SOURCE == 2:  # file contains energy_eV and spectral power (W/eV)
            source_file = self.SOURCE_FILE
            try:
                tmp = numpy.loadtxt(source_file)
                energies = tmp[:, 0]
                source = tmp[:, 1]
                self.input_spectrum = source
                script_previous = "import numpy\ntmp = numpy.loadtxt(%s)\nenergy = tmp[:,0]\nspectral_power = tmp[:,1]\n" % \
                                  (source_file)
            except:
                print("Error loading file %s " % (source_file))
                raise
        elif self.SOURCE == 3:  # file contains energy_eV and flux (ph/s/0.1%bw
            source_file = self.SOURCE_FILE
            try:
                tmp = numpy.loadtxt(source_file)
                energies = tmp[:, 0]
                source = tmp[:, 1] * (codata.e * 1e3)
                self.input_spectrum = source
                script_previous = "import numpy\nimport scipy.constants as codata\ntmp = numpy.loadtxt(%s)\nenergy = tmp[:,0]\nspectral_power = tmp[:,1] / (codata.e * 1e3)\n" % \
                                  (source_file)
            except:
                print("Error loading file %s " % (source_file))
                raise

        substance = self.att_substance()  # str list of substances
        thick = self.att_thick()  # float list of thickness
        angle = numpy.zeros_like(thick)  # float zeros it does not apply for filter type
        dens = self.att_dens()  # str list of subtance densities
        roughness = numpy.zeros_like(dens)  # float zeros it does not apply for filter type
        flags = numpy.zeros_like(dens)  # int

        NELEMENTS = len(self.att_substance())
        if NELEMENTS == 0: return

        # this is for creating script
        substance_str = "["
        thick_str = "["
        angle_str = "["
        dens_str = "["
        roughness_str = "["
        flags_str = "["
        for i in range(NELEMENTS):
            substance_str += "'%s'," % (substance[i])
            thick_str += "%g," % (thick[i])
            angle_str += "%g," % (angle[i])
            dens_str += "'%s'," % (dens[i])
            roughness_str += "%g," % (roughness[i])
            flags_str += "%d," % (flags[i])
        substance_str += "]"
        thick_str += "]"
        angle_str += "]"
        dens_str += "]"
        roughness_str += "]"
        flags_str += "]"

        if self.MATERIAL_CONSTANT_LIBRARY_FLAG == 0:
            material_constants_library = xraylib
            material_constants_library_str = "xraylib"
        else:
            material_constants_library = DabaxXraylib()
            material_constants_library_str = 'DabaxXraylib()'
            print(material_constants_library.info())

        out_dictionary = xoppy_calc_power(
            energies,
            source,
            substance=substance,
            thick=thick,
            angle=angle,
            dens=dens,
            roughness=roughness,
            flags=flags,
            nelements=NELEMENTS,
            FILE_DUMP=self.FILE_DUMP,
            material_constants_library=material_constants_library,
        )

        print(out_dictionary["info"])

        dict_parameters = {
            "substance": substance_str,
            "thick": thick_str,
            "angle": angle_str,
            "dens": dens_str,
            "roughness": roughness_str,
            "flags": flags_str,
            "nelements": NELEMENTS,
            "FILE_DUMP": self.FILE_DUMP,
            "material_constants_library": material_constants_library_str,
        }

        script_element = self.script_template().format_map(dict_parameters)

        script = script_previous + script_element

        self.xoppy_script.set_code(script)

        return out_dictionary, script

    def script_template(self):
        return """
#
# script to make the calculations (created by XOPPY:xpower)
#
import numpy
from xoppylib.power.xoppy_calc_power import xoppy_calc_power
import xraylib
from dabax.dabax_xraylib import DabaxXraylib
out_dictionary = xoppy_calc_power(
        energy,
        spectral_power,
        substance = {substance},
        thick     = {thick}, # in mm (for filters)
        angle     = {angle}, # in mrad (for mirrors)
        dens      = {dens},
        roughness = {roughness}, # in A (for mirrors)
        flags     = {flags}, # 0=Filter, 1=Mirror
        nelements = {nelements},
        FILE_DUMP = {FILE_DUMP},
        material_constants_library = {material_constants_library},
        )
# data to pass
energy = out_dictionary["data"][0,:]
spectral_power = out_dictionary["data"][-1,:]
#                       
# example plots
#
from srxraylib.plot.gol import plot
plot(out_dictionary["data"][0,:], out_dictionary["data"][1,:],
    out_dictionary["data"][0,:], out_dictionary["data"][-1,:],
    xtitle=out_dictionary["labels"][0],
    legend=[out_dictionary["labels"][1],out_dictionary["labels"][-1]],
    title='Spectral Power [W/eV]')

#
# end script
#
"""

    def extract_data_from_xoppy_output(self, calculation_output):

        """ Custom calculated data for this widget depending on which total WB power
        or power by WB attenuator axis is needed """

        out_dictionary, script = calculation_output

        cumulated_data = {}
        results = []
        shift = 6

        # First, we add the typical: energy axis and input beam

        results.append((out_dictionary['data'][0]).tolist())  # Pos: 0
        results.append((out_dictionary['data'][1]).tolist())  # Pos: 1

        # if just the total of the WB attenuators is needed

        if self.do_plot_total():
            # Total
            total_trans = numpy.ones_like(out_dictionary['data'][0])
            total_abs_spectra = numpy.zeros_like(out_dictionary['data'][0])
            for i in range(5):
                total_trans *= out_dictionary['data'][4 + i * shift]
                total_abs_spectra += out_dictionary['data'][6 + i * shift]

            results.append(total_trans.tolist())  # Pos: 2
            results.append(total_abs_spectra.tolist())  # Pos: 3
            results.append(((out_dictionary['data'][-1]) / codata.e / 1e3).tolist())  # Pos: 4
            results.append((out_dictionary['data'][-1]).tolist())  # Pos: 5

        # if what is needed is the absorption per attenuator axis

        if self.do_plot_per_axis():

            for i in range(len(self.att_substance())):
                results.append((out_dictionary['data'][4 + i * shift]).tolist())  # Trasmitivity
                results.append((out_dictionary['data'][6 + i * shift]).tolist())  # Spectral power absorbed
                results.append((out_dictionary['data'][7 + i * shift]).tolist())  # Spectral power after

        cumulated_data['data'] = numpy.array(results)

        # send exchange
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

    def do_plot_total(self):
        """ For WB attenuators total properties """
        out = False
        if self.PLOT_SETS == 0: out = True
        return out

    def do_plot_per_axis(self):
        """ For each WB attenuator axis """
        out = False
        if self.PLOT_SETS == 1: out = True
        return out

    def getTitles(self):
        titles = []
        titles.append("Input beam")  # input beam always

        if self.do_plot_total():
            titles.append("Total transmitivity of WB attenuators")
            titles.append("Total spectral power absorbed in WB attenuators")
            titles.append("Flux after WB attenuators")
            titles.append("Spectral power after WB attenuators")

        if self.do_plot_per_axis():
            for att_n in range(len(self.att_substance())):
                titles.append("Transmitivity of Axis " + str(att_n + 1))
                titles.append("Spectral power absorbed in Axis " + str(att_n + 1))
                titles.append("Spectral power after Axis " + str(att_n + 1))

        return titles

    def getXTitles(self):
        xtitles = []

        xtitles.append("Photon Energy [eV]")  # for ithe input beam

        if self.do_plot_total():
            for axis_n in range(len(self.att_substance()) + 1):
                xtitles.append("Photon Energy [eV]")
        if self.do_plot_per_axis():
            for axis_n in range(3 * len(self.att_substance()) + len(self.att_substance())):
                xtitles.append("Photon Energy [eV]")

        return xtitles

    def getYTitles(self):
        ytitles = []

        if self.SOURCE == 1:
            unit_str = '[a.u]'
        else:
            unit_str = '[W/eV]'

        ytitles.append("Spectral Power %s" % unit_str)  # input beam

        if self.do_plot_total():
            ytitles.append("Transmitivity")
            ytitles.append("Spectral power  %s" % unit_str)
            ytitles.append("Flux [photons/s/0.1%bw]")
            ytitles.append("Spectral power  %s" % unit_str)

        if self.do_plot_per_axis():
            for axis_n in range(3 * len(self.att_substance())):
                ytitles.append("Transmitivity")
                ytitles.append("Spectral power  %s" % unit_str)
                ytitles.append("Spectral power  %s" % unit_str)

        return ytitles

    def getVariablesToPlot(self):
        variables = []

        variables.append((0, 1))  # start plotting the source

        if self.do_plot_total():
            variables.append((0, 2))
            variables.append((0, 3))
            variables.append((0, 4))  # for this one it plots the Flux
            variables.append((0, 5))

        if self.do_plot_per_axis():
            for axis_n in range(len(self.att_substance())):
                variables.append((0, (2 + 3 * axis_n)))
                variables.append((0, (3 + 3 * axis_n)))
                variables.append((0, (4 + 3 * axis_n)))

        return variables

    def getLogPlot(self):
        logplot = []

        logplot.append((False, False))  # source

        if self.do_plot_total():
            for axis_n in range(len(self.att_substance())):
                logplot.append((False, False))

        if self.do_plot_per_axis:
            for axis_n in range(3 * len(self.att_substance())):
                logplot.append((False, False))

        return logplot


if __name__ == "__main__":

    import sys

    input_type = 0

    if input_type == 1:
        from oasys.widgets.exchange import DataExchangeObject

        input_data_type = "POWER"

        if input_data_type == "POWER":
            # create fake UNDULATOR_FLUX xoppy exchange data
            e = numpy.linspace(1000.0, 10000.0, 100)
            source = e / 10
            received_data = DataExchangeObject("XOPPY", "POWER")
            received_data.add_content("xoppy_data", numpy.vstack((e, e, source)).T)
            received_data.add_content("xoppy_code", "US")

        elif input_data_type == "POWER3D":
            # create unulator_radiation xoppy exchange data
            from xoppylib.sources.xoppy_undulators import xoppy_calc_undulator_radiation

            e, h, v, p, code = xoppy_calc_undulator_radiation(ELECTRONENERGY=6.04, ELECTRONENERGYSPREAD=0.001,
                                                              ELECTRONCURRENT=0.2, \
                                                              ELECTRONBEAMSIZEH=0.000395, ELECTRONBEAMSIZEV=9.9e-06, \
                                                              ELECTRONBEAMDIVERGENCEH=1.05e-05,
                                                              ELECTRONBEAMDIVERGENCEV=3.9e-06, \
                                                              PERIODID=0.018, NPERIODS=222, KV=1.68, DISTANCE=30.0,
                                                              SETRESONANCE=0, HARMONICNUMBER=1,
                                                              GAPH=0.001, GAPV=0.001, \
                                                              HSLITPOINTS=41, VSLITPOINTS=41, METHOD=0,
                                                              PHOTONENERGYMIN=7000, PHOTONENERGYMAX=8100,
                                                              PHOTONENERGYPOINTS=20,
                                                              USEEMITTANCES=1)
            received_data = DataExchangeObject("XOPPY", "POWER3D")
            received_data = DataExchangeObject("XOPPY", "UNDULATOR_RADIATION")
            received_data.add_content("xoppy_data", [p, e, h, v])
            received_data.add_content("xoppy_code", code)

        app = QApplication(sys.argv)
        w = OWAttenuatorsBox()
        w.acceptExchangeData(received_data)
        w.show()
        app.exec()
        w.saveSettings()

    else:
        app = QApplication(sys.argv)
        w = OWAttenuatorsBox()
        w.SOURCE = 1
        w.show()
        app.exec()
        w.saveSettings()
