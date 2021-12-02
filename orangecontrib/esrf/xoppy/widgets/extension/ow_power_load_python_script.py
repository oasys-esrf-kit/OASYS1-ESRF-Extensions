import sys
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QTextCursor

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets import widget
from oasys.util.oasys_util import TriggerIn, TriggerOut, EmittingStream
from oasys.widgets.gui import ConfirmDialog

from orangecontrib.xoppy.util.python_script import PythonScript

from syned.beamline.beamline import Beamline


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
                          orientation="horizontal")

        oasysgui.lineEdit(box3, self, "excel_file_name", "Excel File for results", labelWidth=150, valueType=str,
                          orientation="horizontal")


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

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        try:
            self.input_data.to_json(self.json_file_name)
        except:
            ConfirmDialog.confirmed(self,
                                          message="Cannot create %s from Oasys wire. Using external file." % (
                                          self.json_file_name),
                                          title="Cannot create file")

        # write python script
        dict_parameters = {
            "json_file_name": self.json_file_name,
            "excel_file_name": self.excel_file_name,
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
# Imports
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd
from xoppylib.xoppy_undulators import xoppy_calc_undulator_power_density
from xoppylib.fit_gaussian2d import fit_gaussian2d
from xoppylib.xoppy_undulators import xoppy_calc_undulator_spectrum
from xoppylib.xoppy_xraylib_util import xpower_calc
import scipy.constants as codata
#codata_mee = codata.codata.physical_constants["electron mass energy equivalent in MeV"][0]

from syned.util.json_tools import load_from_json_file
from syned.beamline.optical_elements.absorbers.filter import Filter
from syned.beamline.optical_elements.absorbers.slit import Slit
from syned.beamline.shape import Rectangle

def load_elements(file_name):

    # Brief function to load the excel file as pandas dataframe


    data_frame = pd.read_excel(file_name, header=1, skiprows=0)

    return data_frame

def load_elements_from_json_file(file_name=""):

    #
    beamline = load_from_json_file(file_name)

    # print(beamline.info())

    # print(tmp.get_light_source().info())
    element = ["CPMU18"]
    indices = [0]
    dist_to_source = [0.0]
    type1 = ['source']
    h = [0.0]
    v = [0.0]
    thickness = [None]
    formula = [None]
    density = [None]

    dist_cumulated = 0.0
    for i,element_i in enumerate(beamline.get_beamline_elements()):
        oe_i = element_i.get_optical_element()

        element.append(oe_i.get_name())
        indices.append(i)

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
            h.append(None)
            v.append(None)

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


    print("element: ",element)
    print("dist_to_source", dist_to_source)
    print("type: ", type1)
    print("h: ",h)
    print("v: ",v)
    print("thickness: ",thickness)
    print("formula: ", formula)
    print("density: ", density)

    titles = ["element", "dist_to_source", "type", "h", "v" "thickness", "formula", "density"]

    data_frame = [titles, element, dist_to_source, type1, h, v, thickness, formula, density]

    return data_frame
    
def ap_projections(df):

    # This function calculates all the projection on each element due the upstream elements,
    # it returns a new dataframe that includes two columns of the minimum projection on each element,
    # which is the beam projection at the given element

    h_proj = []
    v_proj = []

    # for the source

    h_proj.append(0)
    v_proj.append(0)

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
    new_df = pd.concat([df,df2], axis=1)

    return new_df

def get_full_aperture (id_dict, dataframe):

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
        DISTANCE =distance,
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
        h5_file= None,
        h5_entry_name= None,
        h5_initialize=False,
    )

    fit_parameters = fit_gaussian2d(p, h, v)
    s_x = np.around(fit_parameters[3], 2)
    s_y = np.around(fit_parameters[4], 2)

    full_h = np.around(6* s_x, 2)
    full_v = np.around(6 * s_y, 2)

    #srio print(f'At the dataframe.element[1] the beam has sigma x = s_x' f' mm and sigma y = s_y mm')

    #srio print(f'Therefore the full opening is defined as 6 x sigma: full_h mm and full_v mm')

    return distance, full_h , full_v


def calcul_spectrum(id_dict, dist, h_slit, v_slit, *args, window = False):

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

        thick = float(args[0])
        formula = str(args[1])
        density = float(args[2])

        out_dict = xpower_calc(energies=energy, source=spectral_power, substance=[formula], flags=[0],
                               dens=[density], thick=[thick], output_file=None)

        tot_power = np.trapz(out_dict['data'][6], x=energy, axis=-1)

        flux = out_dict['data'][6]/ 1.602176634e-19 / 1e3 #TODO: Intead of this number uses the corrrect way from codata

        flux_phot_sec = flux/(0.001 * energy)

        tot_phot_sec = np.trapz(flux_phot_sec, x=energy, axis=-1)

        return tot_power, tot_phot_sec

    else:

        tot_power = np.trapz(spectral_power, x=energy, axis = -1)
        tot_phot_sec = np.trapz(flux/(0.001*energy), x = energy, axis = -1)

        return tot_power, tot_phot_sec


def dif_totals(in_pow, in_phsec, out_pow, out_phsec):

    # Short function to calculates the absorbed power just by a subtraction

    if out_pow > in_pow:

        # If the element aperture is larger than the beam, depending on the energy steps and numerical 
        # calculations, sometimes the outcoming power is bigger than the incoming, which does not make sense!
        # so this is just to prevent that error and gives zero absortion in the element

        abs_pow = 0.0
        abs_phsec = 0.0

    elif out_pow <= in_pow:

         abs_pow = in_pow - out_pow
         abs_phsec = in_phsec - out_phsec
    else:
        raise RuntimeError('Error reading the total power')

    return abs_pow, abs_phsec


def run_calculations(df, id_dict):

    # Main function that depends on the above ones, it uses as an input the dataframe fo the elements and the id dictionary
    
    # Loads the data frame with the elements characteristics
    df1 = df # srio !!!  load_elements('id_components_test.xlsx')
      
    # calculates the projections on each element due upstream apertures
    new_df = ap_projections(df1)

    # get the distance and apertures of full aperture for the specific id
    distance, full_ap_h, full_ap_v = get_full_aperture(id_dict, new_df)
    
    # output lists
    abs_pow = []
    abs_phosec = []
    transm_power = []

    for i, type in enumerate(df.type):

        # this is to get the window index to compare is the element has a upstream window
        # TODO: consider the option of having two windows (which is normally not the case for ESRF-FE's )

        win_index = df.index[df['type'] == 'window'].tolist()

        if type == 'source':

            #srio print(f">>>>>>>>>> Calculating for element new_df.element[i]")
            # For the source, it gets te total power just by analytic equation
            codata_mee = codata.m_e * codata.c**2 / codata.e
            gamma = id_dict['ELECTRONENERGY'] * 1e9 / codata_mee

            p_tot = (id_dict['NPERIODS']/6) * codata.value('characteristic impedance of vacuum') * \
                    id_dict['ELECTRONCURRENT'] * codata.e * 2 * np.pi * codata.c * gamma**2 * \
                    (id_dict['KV']**2 + id_dict['KH']**2) / id_dict['PERIODID']

            abs_pow.append(0.0)
            abs_phosec.append(0.0)
            transm_power.append(p_tot)


        elif (type == 'slit' and i == 1):

            # This is for the first slit which is normally the mask

            #srio print(f">>>>>>>>>> Calculating for element new_df.element[i]")

            p_imp, phsec_imp = calcul_spectrum(id_dict, distance, full_ap_h, full_ap_v)
            p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h[i], new_df.v[i])

            abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
            abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
            transm_power.append(p_trans)


        elif (type == 'slit' and i > 1 and i < win_index[0]):

            # Slit that does not have an upstream window

            #srio print(f">>>>>>>>>> Calculating for element new_df.element[i]")

            p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i], new_df.v_proj[i])
            p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], np.min([new_df.h_proj[i],
                                                   new_df.h[i]]), np.min([new_df.v_proj[i], new_df.v[i]]))

            abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
            abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
            transm_power.append(p_trans)


        elif (type == 'slit' and i > 1 and i > win_index[0]):

            # Slit with an usptream window
            # TODO: It might be worty to have the optin of more than one window

            #srio print(f">>>>>>>>>> Calculating for element new_df.element[i]")

            p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i],
                                               new_df.v_proj[i], new_df.thickness[win_index[0]],
                                               new_df.formula[win_index[0]], new_df.density[win_index[0]],
                                               window=True)
            p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], np.min([new_df.h_proj[i],
                                                   new_df.h[i]]), np.min([new_df.v_proj[i], new_df.v[i]]),
                                                   new_df.thickness[win_index[0]], new_df.formula[win_index[0]],
                                                   new_df.density[win_index[0]], window=True)

            abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
            abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
            transm_power.append(p_trans)


        elif type == 'absorber':

            #srio print(f">>>>>>>>>> Calculating for element new_df.element[i]")

            p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i], new_df.v_proj[i])

            abs_pow.append(p_imp)
            abs_phosec.append(phsec_imp)
            transm_power.append(0.0)

        elif type == 'window':

            # directly for the window

            #srio print(f">>>>>>>>>> Calculating for element new_df.element[i]")

            p_imp, phsec_imp = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i], new_df.v_proj[i])

            p_trans, phsec_trans = calcul_spectrum(id_dict, new_df.dist_to_source[i], new_df.h_proj[i], new_df.v_proj[i],
                                               new_df.thickness[i], new_df.formula[i], new_df.density[i], window=True)

            abs_pow.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[0])
            abs_phosec.append(dif_totals(p_imp, phsec_imp, p_trans, phsec_trans)[1])
            transm_power.append(p_trans)

        else:

            # srio raise RuntimeError(F'Element must have type this element new_df.type[i] has not been reconized')
            raise RuntimeError()
            
    # Creates a data frame with the absorbed power and absorbed photons info
    tmp = dict()
    tmp['abs_pow'] = abs_pow
    tmp['abs_photonsec'] = abs_phosec
    tmp['transm_power'] = transm_power
    df2 = pd.DataFrame(tmp)

    #print(df2)

    # merges with the original dataframe
    full_df = pd.concat([new_df,df2], axis=1)

    return full_df


if True:

    # df1 = load_elements('/Users/srio/Oasys/id_components_test.xlsx')
    df1 = load_elements_from_json_file('{json_file_name}')
    
    # Defining the id parameters in a dictionary (from json?)#

    id_dict = dict()
    id_dict["ELECTRONENERGY"] = 6.0
    id_dict["ELECTRONENERGYSPREAD"] = 0.00093339
    id_dict["ELECTRONCURRENT"] = 0.2
    id_dict["ELECTRONBEAMSIZEH"] = 3.01836e-05
    id_dict["ELECTRONBEAMSIZEV"] = 3.63641e-06
    id_dict["ELECTRONBEAMDIVERGENCEH"] = 4.36821e-06
    id_dict["ELECTRONBEAMDIVERGENCEV"] = 1.37498e-06
    id_dict["PERIODID"] = 0.016
    id_dict["NPERIODS"] = 125.0
    id_dict["KV"] = 2.079
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
    id_dict["PHOTONENERGYMIN"] = 500
    id_dict["PHOTONENERGYMAX"] = 200000
    id_dict["PHOTONENERGYPOINTS"] = 1000

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
    ow.set_input(load_from_json_file("/Users/srio/Oasys/id03.json"))
    ow.show()
    a.exec_()
    ow.saveSettings()