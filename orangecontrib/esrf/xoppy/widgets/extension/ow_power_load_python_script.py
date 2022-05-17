import sys
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QTextCursor

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets import widget
from oasys.util.oasys_util import EmittingStream
from oasys.widgets.gui import ConfirmDialog

from orangecontrib.xoppy.util.python_script import PythonScript

from syned.beamline.beamline import Beamline
from oasys.widgets import congruence


class PowerLoadPythonScript(widget.OWWidget):

    name = "Power Load Python Script"
    description = "Power Load Python Script"
    icon = "icons/power_load_python_script.png"
    maintainer = "Manuel Sanchez del Rio & Juan Reyes-Herrera"
    maintainer_email = "srio(@at@)esrf.eu"
    priority = 100
    category = "Tools"
    keywords = ["script"]

    inputs = [("SynedData", Beamline, "set_input")]

    outputs = []

    json_file_name = Setting("beamline.json")
    excel_file_name = Setting("id_components_test_abs_pow.csv")    
    e_min = Setting(500)
    e_max = Setting(100000)
    e_points = Setting(200)

    #
    #
    #
    IMAGE_WIDTH = 890
    IMAGE_HEIGHT = 680

    # want_main_area=1

    is_automatic_run = Setting(True)


    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 560

    input_data = None


    def __init__(self, show_automatic_box=True, show_general_option_box=True):
        super().__init__() # show_automatic_box=show_automatic_box)


        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width()*0.05),
                               round(geom.height()*0.05),
                               round(min(geom.width()*0.98, self.MAX_WIDTH)),
                               round(min(geom.height()*0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        self.general_options_box = gui.widgetBox(self.controlArea, "General Options", addSpace=True, orientation="horizontal")
        self.general_options_box.setVisible(show_general_option_box)

        if show_automatic_box :
            gui.checkBox(self.general_options_box, self, 'is_automatic_run', 'Automatic Execution')
            
        #
        #
        #
        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Refresh Script", callback=self.refresh_script)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)        


        gui.separator(self.controlArea)


        gen_box = oasysgui.widgetBox(self.controlArea, "Output Files", addSpace=False, orientation="vertical", width=self.CONTROL_AREA_WIDTH-5)


        box3 = gui.widgetBox(gen_box, orientation="vertical")
        oasysgui.lineEdit(box3, self, "json_file_name", "Json File with beamline", labelWidth=150, valueType=str,
                          orientation="horizontal", callback=self.refresh_script)

        oasysgui.lineEdit(box3, self, "excel_file_name", "Excel File for results", labelWidth=150, valueType=str,
                          orientation="horizontal", callback=self.refresh_script)

        oasysgui.lineEdit(box3, self, "e_min", "Photon Energy Min [eV]", labelWidth=150, valueType=float,
                          orientation="horizontal", callback=self.refresh_script)

        oasysgui.lineEdit(box3, self, "e_max", "Photon Energy Max [eV]", labelWidth=150, valueType=float,
                          orientation="horizontal", callback=self.refresh_script)

        oasysgui.lineEdit(box3, self, "e_points", "Photon Energy Points", labelWidth=150, valueType=int,
                          orientation="horizontal", callback=self.refresh_script)

        #
        #
        #

        tabs_setting = oasysgui.tabWidget(self.mainArea)
        tabs_setting.setFixedHeight(self.IMAGE_HEIGHT)
        tabs_setting.setFixedWidth(self.IMAGE_WIDTH)

        tab_scr = oasysgui.createTabPage(tabs_setting, "Python Script")
        tab_out = oasysgui.createTabPage(tabs_setting, "System Output")


        self.xoppy_script = PythonScript()
        self.xoppy_script.code_area.setFixedHeight(400)

        script_box = gui.widgetBox(tab_scr, "Python script", addSpace=True, orientation="horizontal")
        script_box.layout().addWidget(self.xoppy_script)


        self.xoppy_output = oasysgui.textArea()

        out_box = oasysgui.widgetBox(tab_out, "System Output", addSpace=True, orientation="horizontal", height=self.IMAGE_WIDTH - 45)
        out_box.layout().addWidget(self.xoppy_output)

        #############################        

        gui.rubber(self.controlArea)

        self.process_showers()
    
    def check_fields(self):
            self.e_min = congruence.checkPositiveNumber(self.e_min, "Photon Energy Min [eV]")
            self.e_max = congruence.checkPositiveNumber(self.e_max, "Photon Energy Max [eV]")
            congruence.checkLessThan(self.e_min, self.e_max, "Photon Energy Min [eV]", "Photon Energy Max [eV]")
            self.e_points = congruence.checkPositiveNumber(self.e_points, "Photon Energy Points")

    def set_input(self, syned_data):

        if not syned_data is None:
            if isinstance(syned_data, Beamline):
                self.input_data = syned_data
                if self.is_automatic_run:
                    self.refresh_script()
            else:
                raise Exception("Bad input.")


    def callResetSettings(self):
        pass

    def execute_script(self):

        
        self._script = str(self.pythonScript.toPlainText())  
        self.console.write("\nRunning script:\n")
        self.console.push("exec(_script)")        
        self.console.new_prompt(sys.ps1)       
        

    def refresh_script(self):        

        self.xoppy_output.setText("")
        self.check_fields()

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        try:
            self.input_data.to_json(self.json_file_name)
        except:
            ConfirmDialog.confirmed(self,
                                          message="Cannot create %s from Oasys wire. Using external file." % (
                                          self.json_file_name),
                                          title="Cannot create file")

        # write Python script #
        dict_parameters = {
            "json_file_name": self.json_file_name,
            "excel_file_name": self.excel_file_name,            
            "e_min": self.e_min,
            "e_max": self.e_max,
            "e_points": self.e_points            
        }

        self.xoppy_script.set_code(self.script_template().format_map(dict_parameters))    


    def script_template(self):
        return """
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : juan
# Created Date: 12/2021
# version ='1.0'
# ---------------------------------------------------------------------------
# Script to get the power absorbed by each element in a FE for a given source and elements position
# ---------------------------------------------------------------------------
# Imports # # xoppylib could be used as well #
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd
import xraylib
from xoppylib.sources.xoppy_undulators import xoppy_calc_undulator_spectrum, xoppy_calc_undulator_power_density
from xoppylib.fit_gaussian2d import fit_gaussian2d
from xoppylib.power.xoppy_calc_power import xoppy_calc_power

import scipy.constants as codata

from syned.util.json_tools import load_from_json_file
from syned.beamline.optical_elements.absorbers.filter import Filter
from syned.beamline.optical_elements.absorbers.slit import Slit
from syned.beamline.shape import Rectangle

def load_elements_from_excel_file(file_name):
    # Brief function to load the excel file as pandas dataframe #
    # and a dictionary for the source #

    data_frame = pd.read_excel(file_name, header=1, skiprows=0)

    id_dict = dict()
    id_dict["ELECTRONENERGY"] = 6.0
    id_dict["ELECTRONENERGYSPREAD"] = 0.0009339
    id_dict["ELECTRONCURRENT"] = 0.2
    id_dict["ELECTRONBEAMSIZEH"] = 3.01836e-05
    id_dict["ELECTRONBEAMSIZEV"] = 3.63641e-06
    id_dict["ELECTRONBEAMDIVERGENCEH"] = 4.36821e-06
    id_dict["ELECTRONBEAMDIVERGENCEV"] = 1.37498e-06
    id_dict["PERIODID"] = 0.016
    id_dict["NPERIODS"] = 125
    id_dict["KV"] = 2.076
    id_dict["KH"] = 0.0
    id_dict["KPHASE"] = 0.0
    id_dict["GAPH"] = 0.010
    id_dict["GAPV"] = 0.010
    id_dict["HSLITPOINTS"] = 201
    id_dict["VSLITPOINTS"] = 201
    id_dict["METHOD"] = 2
    id_dict["USEEMITTANCES"] = 1
    id_dict["MASK_FLAG"] = 0
    id_dict["MASK_ROT_H_DEG"] = 0.0
    id_dict["MASK_ROT_V_DEG"] = 0.0
    id_dict["MASK_H_MIN"] = -1000.0
    id_dict["MASK_H_MAX"] = 1000.0
    id_dict["MASK_V_MIN"] = -1000.0
    id_dict["MASK_V_MAX"] = 1000.0
    id_dict["GAPH_CENTER"] = 0.0
    id_dict["GAPV_CENTER"] = 0.0
    id_dict["PHOTONENERGYMIN"] = {e_min}
    id_dict["PHOTONENERGYMAX"] = {e_max}
    id_dict["PHOTONENERGYPOINTS"] = {e_points}

    return data_frame, id_dict


def load_elements_from_json_file(file_name=""):
    # Loading data frame and dict from JSON #
    beamline = load_from_json_file(file_name)
    element = [beamline.get_light_source().get_name()]
    indices = [0]
    dist_to_source = [0.0]
    type1 = ['source']
    h = [0.0]
    v = [0.0]
    thickness = [None]
    formula = [None]
    density = [None]

    dist_cumulated = 0.0
    for i, element_i in enumerate(beamline.get_beamline_elements()):
        oe_i = element_i.get_optical_element()        

        element.append(oe_i.get_name())
        indices.append(i+1)

        coor = element_i.get_coordinates()
        dist_cumulated += coor.p()
        dist_to_source.append(dist_cumulated)

        if isinstance(oe_i, Filter):
            type1.append('window')
        elif isinstance(oe_i, Slit):
            type1.append('slit')
        else:
            type1.append('unknown')

        shape = oe_i.get_boundary_shape()
        if isinstance(shape, Rectangle):
            x_left, x_right, y_bottom, y_top = shape.get_boundaries()
            h.append(x_right - x_left)
            v.append(y_top - y_bottom)
        else:
            h.append(0.008)
            v.append(0.008)

        if isinstance(oe_i, Filter):
            thickness.append(oe_i.get_thickness() * 1e3)
        else:
            thickness.append(None)

        if isinstance(oe_i, Filter):
            formula.append(oe_i.get_material())
        else:
            formula.append(None)

        if isinstance(oe_i, Filter):
            if oe_i.get_material() == "C":
                density.append(3.52)
            else:
                density.append(None)
        else:
            density.append(None)

    titles = ["element", "dist_to_source", "type", "h", "v", "thickness", "formula", "density"]

    data_frame = pd.DataFrame(list(zip(element, dist_to_source, type1, h, v, thickness, formula, density)),
                              columns =titles)

    # Defining the id parameters in a dictionary (from JSON) #

    id_dict = dict()
    id_dict["ELECTRONENERGY"] = beamline.get_light_source().get_electron_beam().energy()
    id_dict["ELECTRONENERGYSPREAD"] = beamline.get_light_source().get_electron_beam()._energy_spread
    id_dict["ELECTRONCURRENT"] = beamline.get_light_source().get_electron_beam().current()
    x, xp, y, yp = beamline.get_light_source().get_electron_beam().get_sigmas_all()
    id_dict["ELECTRONBEAMSIZEH"] = x
    id_dict["ELECTRONBEAMSIZEV"] = y
    id_dict["ELECTRONBEAMDIVERGENCEH"] = xp
    id_dict["ELECTRONBEAMDIVERGENCEV"] = yp
    id_dict["PERIODID"] = beamline.get_light_source().get_magnetic_structure().period_length()
    id_dict["NPERIODS"] = int(beamline.get_light_source().get_magnetic_structure().number_of_periods())
    id_dict["KV"] = beamline.get_light_source().get_magnetic_structure().K_vertical()
    id_dict["KH"] = beamline.get_light_source().get_magnetic_structure().K_horizontal()
    id_dict["KPHASE"] = 0.0
    id_dict["GAPH"] = 0.010
    id_dict["GAPV"] = 0.010
    id_dict["HSLITPOINTS"] = 201
    id_dict["VSLITPOINTS"] = 201
    id_dict["METHOD"] = 2
    id_dict["USEEMITTANCES"] = 1
    id_dict["MASK_FLAG"] = 0
    id_dict["MASK_ROT_H_DEG"] = 0.0
    id_dict["MASK_ROT_V_DEG"] = 0.0
    id_dict["MASK_H_MIN"] = -1000.0
    id_dict["MASK_H_MAX"] = 1000.0
    id_dict["MASK_V_MIN"] = -1000.0
    id_dict["MASK_V_MAX"] = 1000.0
    id_dict["GAPH_CENTER"] = 0.0
    id_dict["GAPV_CENTER"] = 0.0
    id_dict["PHOTONENERGYMIN"] = {e_min}
    id_dict["PHOTONENERGYMAX"] = {e_max}
    id_dict["PHOTONENERGYPOINTS"] = {e_points}

    return data_frame, id_dict


def ap_projections(df):
    # This function calculates all the projection on each element due the upstream elements,
    # it returns a new dataframe that includes two columns of the minimum projection on each element,
    # which is the beam projection at the given element

    h_proj = []
    v_proj = []

    # for the source
    h_proj.append(0)
    v_proj.append(0)
    # this takes out the source row
    sub_df = df.iloc[1:]
    sub_df.reset_index(drop=True, inplace=True)

    for i, type in enumerate(sub_df.type):

        h_temp = []
        v_temp = []

        if i == 0:
            h_proj.append(sub_df.h[i])
            v_proj.append(sub_df.v[i])
        else:
            j = 1
            while j <= i:
                h_temp.append(sub_df.dist_to_source[i] / sub_df.dist_to_source[i - j] * sub_df.h[i - j])
                v_temp.append(sub_df.dist_to_source[i] / sub_df.dist_to_source[i - j] * sub_df.v[i - j])
                j += 1
            h_proj.append(np.around(np.min(h_temp), 4))
            v_proj.append(np.around(np.min(v_temp), 4))

    # Creates a data frame with the projections info
    tmp = dict()
    tmp['h_proj'] = h_proj
    tmp['v_proj'] = v_proj
    df2 = pd.DataFrame(tmp)

    # merges with the original dataframe
    new_df = pd.concat([df, df2], axis=1)

    return new_df


def get_full_aperture(id_dict, dataframe):
    # From the id dictionary, this function calculates the full power density at the first element position
    # in order to get the full aperture size (6*sigma)

    distance = dataframe.dist_to_source[1]

    h, v, p, code = xoppy_calc_undulator_power_density(
        ELECTRONENERGY=id_dict["ELECTRONENERGY"],
        ELECTRONENERGYSPREAD=id_dict["ELECTRONENERGYSPREAD"],
        ELECTRONCURRENT=id_dict["ELECTRONCURRENT"],
        ELECTRONBEAMSIZEH=id_dict["ELECTRONBEAMSIZEH"],
        ELECTRONBEAMSIZEV=id_dict["ELECTRONBEAMSIZEV"],
        ELECTRONBEAMDIVERGENCEH=id_dict["ELECTRONBEAMDIVERGENCEH"],
        ELECTRONBEAMDIVERGENCEV=id_dict["ELECTRONBEAMDIVERGENCEV"],
        PERIODID=id_dict["PERIODID"],
        NPERIODS=id_dict["NPERIODS"],
        KV=id_dict["KV"],
        KH=id_dict["KH"],
        KPHASE=id_dict["KPHASE"],
        DISTANCE=distance,
        GAPH=id_dict["GAPH"],
        GAPV=id_dict["GAPV"],
        HSLITPOINTS=id_dict["HSLITPOINTS"],
        VSLITPOINTS=id_dict["VSLITPOINTS"],
        METHOD=id_dict["METHOD"],
        USEEMITTANCES=id_dict["USEEMITTANCES"],
        MASK_FLAG=id_dict["MASK_FLAG"],
        MASK_ROT_H_DEG=id_dict["MASK_ROT_H_DEG"],
        MASK_ROT_V_DEG=id_dict["MASK_ROT_V_DEG"],
        MASK_H_MIN=id_dict["MASK_H_MIN"],
        MASK_H_MAX=id_dict["MASK_H_MAX"],
        MASK_V_MIN=id_dict["MASK_V_MIN"],
        MASK_V_MAX=id_dict["MASK_V_MAX"],
        h5_file=None,
        h5_entry_name=None,
        h5_initialize=False,
    )

    fit_parameters = fit_gaussian2d(p, h, v)
    s_x = np.around(fit_parameters[3], 2)
    s_y = np.around(fit_parameters[4], 2)

    # Here it takes the full aperture as 6x horizontal and vertical sigmas

    full_h = np.around(6 * s_x, 2)
    full_v = np.around(6 * s_y, 2)

    return distance, full_h, full_v


def calcul_spectrum(id_dict, dist, h_slit, v_slit, df, *up_win_list, window=False):
    # From 1D undulator spectrum this function uses the id dict and element characteristics to calculates the
    #    full power through the element

    energy, flux, spectral_power, cumulated_power = xoppy_calc_undulator_spectrum(
        ELECTRONENERGY=id_dict["ELECTRONENERGY"],
        ELECTRONENERGYSPREAD=id_dict["ELECTRONENERGYSPREAD"],
        ELECTRONCURRENT=id_dict["ELECTRONCURRENT"],
        ELECTRONBEAMSIZEH=id_dict["ELECTRONBEAMSIZEH"],
        ELECTRONBEAMSIZEV=id_dict["ELECTRONBEAMSIZEV"],
        ELECTRONBEAMDIVERGENCEH=id_dict["ELECTRONBEAMDIVERGENCEH"],
        ELECTRONBEAMDIVERGENCEV=id_dict["ELECTRONBEAMDIVERGENCEV"],
        PERIODID=id_dict["PERIODID"],
        NPERIODS=id_dict["NPERIODS"],
        KV=id_dict["KV"],
        KH=id_dict["KH"],
        KPHASE=id_dict["KPHASE"],
        DISTANCE=dist,
        GAPH=h_slit,
        GAPV=v_slit,
        GAPH_CENTER=id_dict["GAPH_CENTER"],
        GAPV_CENTER=id_dict["GAPV_CENTER"],
        PHOTONENERGYMIN=id_dict["PHOTONENERGYMIN"],
        PHOTONENERGYMAX=id_dict["PHOTONENERGYMAX"],
        PHOTONENERGYPOINTS=id_dict["PHOTONENERGYPOINTS"],
        METHOD=id_dict["METHOD"],
        USEEMITTANCES=id_dict["USEEMITTANCES"])

    if window:

        # from the list of windows elements read the parameters #
        thick = []
        formula = []
        density = []
        flags = []

        for element in up_win_list[0]:            
            thick.append(float(df.thickness[int(element)]))
            formula.append(str(df.formula[int(element)]))
            density.append(float(df.density[int(element)]))
            flags.append(0)

        out_dict = xoppy_calc_power(energies=energy, source=spectral_power, substance=formula, flags=flags,
                               dens=density, thick=thick, material_constants_library=xraylib)

        tot_power = np.trapz(out_dict['data'][-1], x=energy, axis=-1)
        flux = out_dict['data'][-1] / codata.e / 1e3
        flux_phot_sec = flux / (0.001 * energy)
        tot_phot_sec = np.trapz(flux_phot_sec, x=energy, axis=-1)

        return tot_power, tot_phot_sec

    else:

        tot_power = np.trapz(spectral_power, x=energy, axis=-1)
        tot_phot_sec = np.trapz(flux / (0.001 * energy), x=energy, axis=-1)

        return tot_power, tot_phot_sec


def dif_totals(in_pow, in_phsec, out_pow, out_phsec):
    # Short function to calculates the absorbed power just by a subtraction #

    if out_pow > in_pow:

        # If the element aperture is larger than the beam, depending on the energy steps and numerical #
        # calculations, sometimes the outcoming power is bigger than the incoming, which does not make sense! #
        # so this is just to prevent that error and gives zero absortion in the element #

        abs_pow = 0.0
        abs_phsec = 0.0

    elif out_pow <= in_pow:

        abs_pow = in_pow - out_pow
        abs_phsec = in_phsec - out_phsec
    else:
        raise RuntimeError('Error reading the total power')

    return abs_pow, abs_phsec


def run_calculations(df, id_dict):
    # Main function that depends on the above ones, it uses as an input the dataframe fo the elements and the id dictionary #

    # Loads the data frame with the elements characteristics #
    df1 = df  # srio !!!  load_elements('id_components_test.xlsx')

    # calculates the projections on each element from upstream apertures #
    new_df = ap_projections(df1)

    # get the distance and apertures of full aperture for the specific id #
    distance, full_ap_h, full_ap_v = get_full_aperture(id_dict, new_df)

    # output lists
    abs_pow = []
    abs_phosec = []
    transm_power = []

    for i, type in enumerate(df.type):

        # this is to get the window index to compare is the element has a upstream window #
        win_indexs = df.index[df['type'] == 'window'].tolist()

        if type == 'source':

            print(">>>>>>>>>> Calculating for element:", new_df.element[i])
            # For the source, it gets te total power just by analytic equation
            codata_mee = codata.m_e * codata.c ** 2 / codata.e
            gamma = id_dict['ELECTRONENERGY'] * 1e9 / codata_mee

            p_tot = (id_dict['NPERIODS'] / 6) * codata.value('characteristic impedance of vacuum') * id_dict[
                    'ELECTRONCURRENT'] * codata.e * 2 * np.pi * codata.c * gamma ** 2 * (
                    id_dict['KV'] ** 2 + id_dict['KH'] ** 2) / id_dict['PERIODID']

            abs_pow.append(0.0)
            abs_phosec.append(0.0)
            transm_power.append(p_tot)


        elif type == 'slit' and i == 1:

            # This is for the first slit which is normally the FE mask #

            print(">>>>>>>>>> Calculating for first element:", new_df.element[i])

            p_imp, phsec_imp = calcul_spectrum(id_dict, distance, full_ap_h, full_ap_v, new_df)
            p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h[i], new_df.v[i], new_df)

            abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
            abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
            transm_power.append(p_trans)


        elif type == 'slit' and i > 1 and all(j > i for j in win_indexs):

            # Slit that does not have an upstream window #

            print(">>>>>>>>>> Calculating for slit without any upstream slit:", new_df.element[i])

            p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i], new_df.v_proj[i],
                                               new_df)

            p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], np.min([new_df.h_proj[i],
                                                   new_df.h[i]]), np.min([new_df.v_proj[i], new_df.v[i]]), new_df)

            abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
            abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
            transm_power.append(p_trans)


        elif type == 'slit' and i > 1 and any(j < i for j in win_indexs):

            # Slit with an upstream window #

            print(">>>>>>>>>> Calculating for slit with at least one upstream window:", new_df.element[i])

            up_win_list = list(item for item in win_indexs if item < i)

            p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i],
                                               new_df.v_proj[i],new_df, up_win_list, window=True)

            p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], np.min([new_df.h_proj[i],
                                                   new_df.h[i]]), np.min([new_df.v_proj[i], new_df.v[i]]), new_df,
                                                   up_win_list, window=True)

            abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
            abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
            transm_power.append(p_trans)


        elif type == 'absorber':

            print(">>>>>>>>>> Calculating for element:", new_df.element[i])

            p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i],
                                               new_df.v_proj[i])

            abs_pow.append(p_imp)
            abs_phosec.append(phsec_imp)
            transm_power.append(0.0)

        elif type == 'window':

            # none upstream window

            if win_indexs and i == win_indexs[0]:

                # This gets the index for this only window
                up_win_list = list(item for item in win_indexs if item <= i)

                print(">>>>>>>>>> Calculating for (first) window, without any upstream window:", new_df.element[i])

                p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i], new_df.v_proj[i], new_df)

                p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i],
                                                       new_df.v_proj[i],new_df, up_win_list, window=True)

                abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
                abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
                transm_power.append(p_trans)

            elif win_indexs and any(j < i for j in win_indexs):
                # This gets the list of all upstream windows
                up_win_list = list(item for item in win_indexs if item < i)
                # This gets the list of all upstream windows including itself
                includ_win_list = list(item for item in win_indexs if item <= i)

                print(">>>>>>>>>> Calculating for window with at least one upstream window:", new_df.element[i])

                p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i],
                                                   new_df.v_proj[i], new_df, up_win_list, window=True)

                p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i],
                                                       new_df.v_proj[i], new_df, includ_win_list, window=True)

                abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
                abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
                transm_power.append(p_trans)

        else:
            raise RuntimeError('The following type sis not included', new_df.type[i])

    # Creates a data frame with the absorbed power and absorbed photons info
    tmp = dict()
    tmp['abs_pow [W]'] = abs_pow
    tmp['abs_photonsec'] = abs_phosec
    tmp['trans_power [W]'] = transm_power
    df2 = pd.DataFrame(tmp)
    # merges with the original dataframe
    full_df = pd.concat([new_df, df2], axis=1)

    return full_df


if True:

    df1, id_dict = load_elements_from_json_file('{json_file_name}')

    full_df = run_calculations(df1, id_dict)

    full_df.to_csv('{excel_file_name}')

    print(full_df) 

"""


    def writeStdOut(self, text):
        cursor = self.xoppy_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.xoppy_output.setTextCursor(cursor)
        self.xoppy_output.ensureCursorVisible()


if __name__ == "__main__":
    import sys
    from syned.util.json_tools import load_from_json_file

    a = QApplication(sys.argv)
    ow = PowerLoadPythonScript()
    ow.set_input(load_from_json_file("N:/OASYS/Tools_XOPPY/beamline.json"))
    ow.show()
    a.exec_()
    ow.saveSettings()