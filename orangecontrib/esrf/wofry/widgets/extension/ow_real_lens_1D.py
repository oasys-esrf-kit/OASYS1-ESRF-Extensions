import numpy
import os, sys
from scipy import interpolate

import orangecanvas.resources as resources

from PyQt5.QtGui import QPalette, QColor, QFont, QPixmap
from PyQt5.QtWidgets import QMessageBox, QLabel, QSizePolicy
from PyQt5.QtCore import Qt

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import TriggerIn, TriggerOut, EmittingStream

from syned.widget.widget_decorator import WidgetDecorator

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.esrf.wofry.widgets.gui.ow_wofry_widget import WofryWidget # TODO: from orangecontrib.wofry.widgets.gui.ow_wofry_widget import WofryWidget

from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D

from barc4ro.projected_thickness import proj_thick_1D_crl
import xraylib

class OWWORealLens1D(WofryWidget):

    name = "Lens 1D"
    id = "WofryLens1D"
    description = "Wofry: Real Lens 1D"
    icon = "icons/lens.png"
    priority = 4

    category = "Wofry Wavefront Propagation"
    keywords = ["data", "file", "load", "read"]

    outputs = [{"name":"WofryData",
                "type":WofryData,
                "doc":"WofryData",
                "id":"WofryData"},
               {"name":"Trigger",
                "type": TriggerIn,
                "doc":"Feedback signal to start a new beam simulation",
                "id":"Trigger"}]

    inputs = [("WofryData", WofryData, "set_input"),
              ("GenericWavefront1D", GenericWavefront1D, "set_input"),
              ("DABAM 1D Profile", numpy.ndarray, "receive_dabam_profile"),
              ("Trigger", TriggerOut, "receive_trigger_signal"),
              WidgetDecorator.syned_input_data()[0]]


    # Basic lens parameters____________________________________________________________________________________________#
    shape = Setting(1)
    radius = Setting(0.0005)
    wall_thickness = Setting(0.00005)
    lens_aperture = Setting(0.001)
    number_of_refractive_surfaces = Setting(1)
    n_lenses = Setting(1)
    material = Setting(0)
    refraction_index_delta = Setting(5.3e-7)
    att_coefficient = Setting(0.00357382)
    error_flag = Setting(0)
    error_file = Setting("<none>")
    error_edge_management = Setting(0)
    write_profile_flag = Setting(0)
    write_profile = Setting("profile1D.dat")
    write_input_wavefront = Setting(0)

    image1_path = os.path.join(resources.package_dirname("orangecontrib.esrf.wofry.widgets.gui"), "misc", "Refractor_parameters.png")

    # Lens misaligments for Barc4ro____________________________________________________________________________________#

    mis_flag = Setting(0)
    xc = Setting(0.0)
    ang_rot = Setting(0.0)
    wt_offset_ffs = Setting(0.0)
    offset_ffs = Setting(0.0)
    tilt_ffs = Setting(0.0)
    wt_offset_bfs = Setting(0.0)
    offset_bfs = Setting(0.0)
    tilt_bfs = Setting(0.0)

    image2_path = os.path.join(resources.package_dirname("orangecontrib.esrf.wofry.widgets.gui"), "misc", "Refractor_misalignments.png")

    input_data = None
    titles = ["Wavefront 1D Intensity", "Wavefront 1D Phase","Wavefront Real(Amplitude)","Wavefront Imag(Amplitude)","O.E. Profile"]

    def __init__(self):
        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)


        #
        # build control panel
        #

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Propagate Wavefront", callback=self.propagate_wavefront)
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

        self.tab_sou = oasysgui.createTabPage(tabs_setting, "Settings")
        self.tab_err = oasysgui.createTabPage(tabs_setting, "Errors")
        self.tab_mis = oasysgui.createTabPage(tabs_setting, "Misalignments")

        box_refractor = oasysgui.widgetBox(self.tab_sou, "1D Lens Settings", addSpace=False, orientation="vertical")
        box_errors = oasysgui.widgetBox(self.tab_err, "1D Lens error profile", addSpace=False, orientation="vertical")
        box_misaligments = oasysgui.widgetBox(self.tab_mis, "Typical lens misalignments (only for parabolic shape)", addSpace=False, orientation="vertical")

        # Tab refractor: basic lens properties _________________________________________________________________________

        gui.comboBox(box_refractor, self, "shape", label="Lens shape", labelWidth=350,
                     items=["Flat", "Parabolic", "Circular"],
                     sendSelectedValue=False, orientation="horizontal",callback=self.set_visible)

        self.box_radius_id = oasysgui.widgetBox(box_refractor, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_radius_id, self, "radius", "(R) Radius of curvature [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("radius")

        self.box_aperture_id = oasysgui.widgetBox(box_refractor, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_aperture_id, self, "lens_aperture", "(A) Lens aperture [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("lens_aperture")

        self.box_wall_thickness_id = oasysgui.widgetBox(box_refractor, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_wall_thickness_id, self, "wall_thickness", "(t_wall) Wall thickness [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("wall_thickness")

        gui.comboBox(box_refractor, self, "number_of_refractive_surfaces", label="Number of refractive surfaces", labelWidth=350,
                     items=["1", "2"],
                     sendSelectedValue=False, orientation="horizontal")

        self.box_n_lenses_id = oasysgui.widgetBox(box_refractor, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_n_lenses_id, self, "n_lenses", "Number of lenses",
                          labelWidth=300, valueType=int, orientation="horizontal")
        tmp.setToolTip("n_lenses")

        gui.comboBox(box_refractor, self, "material", label="Lens material",
                     items=["External", "Be", "Al", "Diamond"],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.box_refraction_index_id = oasysgui.widgetBox(box_refractor, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_refraction_index_id, self, "refraction_index_delta", "Refraction index delta",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("refraction_index_delta")

        self.box_att_coefficient_id = oasysgui.widgetBox(box_refractor, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_att_coefficient_id, self, "att_coefficient", "Attenuation coefficient [m-1]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("att_coefficient")



        gui.comboBox(box_refractor, self, "write_profile_flag", label="Dump profile to file",
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        self.box_file_out = gui.widgetBox(box_refractor, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.box_file_out, self, "write_profile", "File name",
                            labelWidth=200, valueType=str, orientation="horizontal")

        gui.comboBox(box_refractor, self, "write_input_wavefront", label="Input wf to file (for script)",
                     items=["No", "Yes [wavefront_input.h5]"], sendSelectedValue=False, orientation="horizontal")

        # Help figure
        self.figure_box1 = oasysgui.widgetBox(box_refractor, "Principal parabolic lens parameters", addSpace=False, orientation="horizontal")
        label1 = QLabel("")
        label1.setAlignment(Qt.AlignCenter)
        label1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label1.setPixmap(QPixmap(self.image1_path))
        self.figure_box1.layout().addWidget(label1)

        # Tab errors: error profile _________________________________________________________________________

        gui.comboBox(box_errors, self, "error_flag", label="Add profile deformation",
                     items=["No", "Yes (from file)"],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.error_profile = oasysgui.widgetBox(box_errors, "", addSpace=True, orientation="vertical")
        file_box_id = oasysgui.widgetBox(self.error_profile, "", addSpace=True, orientation="horizontal")

        self.error_file_id = oasysgui.lineEdit(file_box_id, self, "error_file", "Error file X[m] Y[m]",
                                                    labelWidth=100, valueType=str, orientation="horizontal")
        gui.button(file_box_id, self, "...", callback=self.set_error_file)
        self.error_file_id.setToolTip("error_file")

        gui.comboBox(self.error_profile, self, "error_edge_management", label="Manage edges",
                     items=["Extrapolate deformation profile", "Crop beam to deformation profile dimension"],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")


        # Tab Misalignments: Typical lens misalignments for Barc4ro_temporarily_only_for_parabolic______________________

        self.mis_flag_box = gui.comboBox(box_misaligments, self, "mis_flag", label="Add misalignments", labelWidth=350,
                     items=["No","Yes"], sendSelectedValue=False, orientation="horizontal", callback=self.set_visible)

        self.box_xc_id = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_xc_id, self, "xc", "(xc) Coordinate of center [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("lens_aperture")

        self.box_ang_rot_id = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_ang_rot_id, self, "ang_rot", "(ang_rot) Angle of full CRL rotation about horizontal [rad]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("ang_rot")

        self.box_wt_offset_ffs_id = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_wt_offset_ffs_id, self, "wt_offset_ffs", "(wt_offset_ffs) ffs offset respect wall thickness [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("wt_offset_ffs")

        self.box_offset_ffs_id = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_offset_ffs_id, self, "offset_ffs", "(offset_ffs) Lateral ffs offset respect horizontal [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("offset_ffs")

        self.box_tilt_ffs_id = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_tilt_ffs_id, self, "tilt_ffs", "(tilt_ffs) Angle of the parabolic ffs respect horizontal [rad]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("tilt_ffs")

        self.box_wt_offset_bfs_id = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_wt_offset_bfs_id, self, "wt_offset_bfs",
                                "(wt_offset_bfs) bfs offset respect wall thickness [m]",
                                labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("wt_offset_bfs")

        self.box_offset_bfs_id = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_offset_bfs_id, self, "offset_bfs",
                                "(offset_bfs) Lateral bfs offset respect horizontal [m]",
                                labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("offset_bfs")

        self.box_tilt_bfs_id = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_tilt_bfs_id, self, "tilt_bfs",
                                "(tilt_bfs) Angle of the parabolic bfs respect horizontal [rad]",
                                labelWidth=300, valueType=float, orientation="horizontal")
        tmp.setToolTip("tilt_bfs")

        self.figure_box2 = oasysgui.widgetBox(box_misaligments, "Front focusing surface (ffs), back focusing surface (bfs)", addSpace=False, orientation="horizontal")

        label2 = QLabel("")
        label2.setAlignment(Qt.AlignCenter)
        label2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label2.setPixmap(QPixmap(self.image2_path))
        self.figure_box2.layout().addWidget(label2)

        self.set_visible()

    def set_visible(self):
        self.error_profile.setVisible(self.error_flag)
        self.box_radius_id.setVisible(self.shape in [1,2])
        self.box_refraction_index_id.setVisible(self.material in [0])
        self.box_att_coefficient_id.setVisible(self.material in [0])
        self.box_file_out.setVisible(self.write_profile_flag == 1)

        # Variables misalignments #
        self.mis_flag_box.setVisible(self.shape in [1]) # Only for parabolic shape
        self.box_xc_id.setVisible(self.mis_flag in [1] and self.shape in [1])
        self.box_ang_rot_id.setVisible(self.mis_flag in [1] and self.shape in [1])
        self.box_wt_offset_ffs_id.setVisible(self.mis_flag in [1] and self.shape in [1])
        self.box_offset_ffs_id.setVisible(self.mis_flag in [1] and self.shape in [1])
        self.box_tilt_ffs_id.setVisible(self.mis_flag in [1] and self.shape in [1])
        self.box_wt_offset_bfs_id.setVisible(self.mis_flag in [1] and self.shape in [1])
        self.box_offset_bfs_id.setVisible(self.mis_flag in [1] and self.shape in [1])
        self.box_tilt_bfs_id.setVisible(self.mis_flag in [1] and self.shape in [1])
        self.figure_box2.setVisible(self.mis_flag in [1] and self.shape in [1])

    def set_error_file(self):
        self.error_file_id.setText(oasysgui.selectFileFromDialog(self, self.error_file, "Open file with profile error"))

    def initializeTabs(self):
        size = len(self.tab)
        indexes = range(0, size)

        for index in indexes:
            self.tabs.removeTab(size-1-index)

        self.tab = []
        self.plot_canvas = []

        for index in range(0, len(self.titles)):
            self.tab.append(gui.createTabPage(self.tabs, self.titles[index]))
            self.plot_canvas.append(None)

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

    def check_fields(self):

        self.radius = congruence.checkStrictlyPositiveNumber(self.radius, "Radius")
        self.wall_thickness = congruence.checkNumber(self.wall_thickness, "Wall thickness")
        self.lens_aperture = congruence.checkNumber(self.lens_aperture, "Lens aperture")
        self.n_lenses = congruence.checkStrictlyPositiveNumber(self.n_lenses, "Number of Lenses")
        self.refraction_index_delta = congruence.checkNumber(self.refraction_index_delta, "Refraction index delta")
        self.att_coefficient = congruence.checkNumber(self.att_coefficient, "Attenuation coefficient")
        self.error_file = congruence.checkFileName(self.error_file)
        self.n_lenses = congruence.checkNumber(self.n_lenses, "Number of lenses")

        self.xc = congruence.checkNumber(self.xc, "xc")
        self.ang_rot = congruence.checkNumber(self.ang_rot, "ang_rot")
        self.wt_offset_ffs = congruence.checkNumber(self.wt_offset_ffs, "wt_offset_ffs")
        self.offset_ffs = congruence.checkNumber(self.offset_ffs, "offset_ffs")
        self.tilt_ffs = congruence.checkNumber(self.tilt_ffs, "tilt_ffs")
        self.wt_offset_bfs = congruence.checkNumber(self.offset_bfs, "offset_ffs")
        self.offset_bfs = congruence.checkNumber(self.offset_bfs, "offset_bfs")
        self.tilt_bfs = congruence.checkNumber(self.tilt_bfs, "tilt_bfs")

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

                self.propagate_wavefront()

    def receive_syned_data(self):
        raise Exception(NotImplementedError)

    def set_input(self, wofry_data):

        if not wofry_data is None:
            if isinstance(wofry_data, WofryData):
                self.input_data = wofry_data
            else:
                self.input_data = WofryData(wavefront=wofry_data)

            if self.is_automatic_execution:
                self.propagate_wavefront()
        else:
            self.input_data = None



    def receive_dabam_profile(self, dabam_profile):
        if not dabam_profile is None:
            try:
                file_name = "dabam_profile_" + str(id(self)) + ".dat"

                file = open(file_name, "w")

                for element in dabam_profile:
                    file.write(str(element[0]) + " " + str(element[1]) + "\n")

                file.flush()
                file.close()

                self.error_flag = 1
                self.error_file = file_name
                self.set_visible()

            except Exception as exception:
                QMessageBox.critical(self, "Error", exception.args[0], QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

    def propagate_wavefront(self):
        self.progressBarInit()

        self.wofry_output.setText("")
        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        self.check_fields()

        if self.input_data is None: raise Exception("No Input Wavefront")

        if self.error_flag == 0:
            error_file = ""
        else:
            error_file = self.error_file

        if self.write_profile_flag == 0:
            write_profile = ""
        else:
            write_profile = self.write_profile

        if self.mis_flag == 0:
            xc            = self.xc
            ang_rot       = self.ang_rot
            wt_offset_ffs = self.wt_offset_ffs
            offset_ffs    = self.offset_ffs
            tilt_ffs      = self.tilt_ffs
            wt_offset_bfs = self.wt_offset_bfs
            offset_bfs    = self.offset_bfs
            tilt_bfs      = self.tilt_bfs
        elif self.mis_flag == 1:
            xc            = 0.0
            ang_rot       = 0.0
            wt_offset_ffs = 0.0
            offset_ffs    = 0.0
            tilt_ffs      = 0.0
            wt_offset_bfs = 0.0
            offset_bfs    = 0.0
            tilt_bfs      = 0.0

        #Lens material ____________________________________________________________________________________

        photon_energy = self.input_data.get_wavefront().get_photon_energy()
        wave_length = self.input_data.get_wavefront().get_wavelength()

        if self.material == 0: # external
            refraction_index_delta = self.refraction_index_delta
            att_coefficient = self.att_coefficient
        else:
            if self.material == 1: # Be
                element = "Be"
                density = xraylib.ElementDensity(4)
            elif self.material == 2: # Al
                element = "Al"
                density = xraylib.ElementDensity(13)
            elif self.material == 3: # Diamond
                element = "C"
                density = 3.51
            print("Element: %s" % element)
            print("        density = %g " % density)

            refraction_index = xraylib.Refractive_Index(element, photon_energy/1000, density)
            refraction_index_delta = 1 - refraction_index.real
            att_coefficient = 4*numpy.pi * (xraylib.Refractive_Index(element, photon_energy/1000, density)).imag / wave_length

        print("Refracion index delta = %g " % (refraction_index_delta))
        print("Attenuation coeff mu = %g m^-1" % (att_coefficient))


        output_wavefront, abscissas_on_lens, lens_thickness = self.calculate_output_wavefront_after_lens1D(
                    self.input_data.get_wavefront(),
                    shape=self.shape,
                    radius=self.radius,
                    lens_aperture = self.lens_aperture,
                    wall_thickness=self.wall_thickness,
                    refraction_index_delta=refraction_index_delta,
                    att_coefficient=att_coefficient,
                    number_of_refractive_surfaces=self.number_of_refractive_surfaces,
                    n_lenses=self.n_lenses,
                    error_flag=self.error_flag,
                    error_file=error_file,
                    error_edge_management=self.error_edge_management,
                    write_profile=write_profile,
                    xc=xc,
                    ang_rot=ang_rot,
                    wt_offset_ffs=wt_offset_ffs,
                    offset_ffs=offset_ffs,
                    tilt_ffs=tilt_ffs,
                    wt_offset_bfs=wt_offset_bfs,
                    offset_bfs=offset_bfs,
                    tilt_bfs=tilt_bfs)

        self.progressBarSet(50)
        if self.write_input_wavefront:
            self.input_data.get_wavefront().save_h5_file("wavefront_input.h5", subgroupname="wfr", intensity=True,
                                                         phase=True, overwrite=True, verbose=True)

        # script #TODO Add all the new variables to the dictionary

        dict_parameters = {"shape": self.shape,
                           "radius": self.radius,
                           "wall_thickness": self.wall_thickness,
                           "lens_aperture": self.lens_aperture,
                           "number_of_refractive_surfaces": self.number_of_refractive_surfaces,
                           "n_lenses": self.n_lenses,
                           "refraction_index_delta": refraction_index_delta,
                           "att_coefficient": att_coefficient,
                           "error_flag": self.error_flag,
                           "error_file": error_file,
                           "error_edge_management": self.error_edge_management,
                           "write_profile": '"' + write_profile + '"',
                           "xc": xc,
                           "ang_rot": ang_rot,
                           "wt_offset_ffs": wt_offset_ffs,
                           "offset_ffs": offset_ffs,
                           "tilt_ffs": tilt_ffs,
                           "wt_offset_bfs": wt_offset_bfs,
                           "offset_bfs": offset_bfs,
                           "tilt_bfs": tilt_bfs}

        script_template = self.script_template_output_wavefront_from_radius()
        self.wofry_script.set_code(script_template.format_map(dict_parameters))

        if self.view_type > 0:
            self.do_plot_wavefront(output_wavefront, abscissas_on_lens, lens_thickness)

        beamline = self.input_data.get_beamline().duplicate()

        self.progressBarFinished()

        self.send("WofryData", WofryData(beamline=beamline, wavefront=output_wavefront))
        self.send("Trigger", TriggerIn(new_object=True))

    @classmethod
    def calculate_output_wavefront_after_lens1D(cls,
                                                input_wavefront,
                                                shape=1,
                                                radius=0.0005,
                                                lens_aperture=0.001,
                                                wall_thickness=0.0002,
                                                refraction_index_delta=0.99999947,
                                                att_coefficient=0.00357382,
                                                number_of_refractive_surfaces=2,
                                                n_lenses=1,
                                                error_flag=0,
                                                error_file="",
                                                error_edge_management=0,
                                                write_profile="",
                                                xc=0,
                                                ang_rot=0,
                                                wt_offset_ffs=0,
                                                offset_ffs=0,
                                                tilt_ffs=0,
                                                wt_offset_bfs=0,
                                                offset_bfs=0,
                                                tilt_bfs=0):

        photon_energy = input_wavefront.get_photon_energy()
        abscissas = input_wavefront.get_abscissas().copy()
        output_wavefront = input_wavefront.duplicate()


        abscissas_on_lens = abscissas

        if number_of_refractive_surfaces == 0:
            n_ref_lens = 1
        elif number_of_refractive_surfaces == 1:
            n_ref_lens = 2
        else:
            raise Exception("Error while reading the number of refractive lenses")

        if shape == 0: # Flat
            lens_thickness = numpy.full_like(abscissas_on_lens, wall_thickness)

        elif shape == 1: # Parabolic

            focus_length = radius / (n_lenses * n_ref_lens * refraction_index_delta)

            print(f"Ideal focal length of {n_lenses} paraboloidal lenses: {round(focus_length, 2)} m for {photon_energy} eV photon energy")

            # Implementation of barc4ro
            x_2, lens_thickness = proj_thick_1D_crl(shape, lens_aperture, radius, _n=n_ref_lens,
                                                _wall_thick=wall_thickness, _xc=xc, _nx=100, _ang_rot_ex=ang_rot,
                                                _offst_ffs_x=offset_ffs, _tilt_ffs_x=tilt_ffs, _wt_offst_ffs=wt_offset_ffs,
                                                _offst_bfs_x=offset_bfs, _tilt_bfs_x=tilt_bfs, _wt_offst_bfs=wt_offset_bfs,
                                                isdgr=False, project=True, _axis=abscissas)

        elif shape == 2: # Circular
            lens_thickness = (numpy.abs(radius) - numpy.sqrt(radius ** 2 - abscissas_on_lens ** 2)) + wall_thickness
            bound = 0.5 * lens_aperture
            if radius < bound: bound = radius
            for i, x in enumerate(abscissas_on_lens):
                if (x < -bound) or (x > bound):
                    lens_thickness[i] = 0
            for i, x in enumerate(abscissas_on_lens):
                if (x < -bound) or (x > bound):
                    lens_thickness[i] = lens_thickness.max()


        if error_flag:
            a = numpy.loadtxt(error_file) # extrapolation
            if error_edge_management == 0:
                finterpolate = interpolate.interp1d(a[:, 0], a[:, 1], fill_value="extrapolate")  # fill_value=(0,0),bounds_error=False)
            elif error_edge_management == 1:
                finterpolate = interpolate.interp1d(a[:, 0], a[:, 1], fill_value=(0,0), bounds_error=False)
            else: # crop
                raise Exception("Bad value of error_edge_management")
            thickness_interpolated = finterpolate(abscissas_on_lens)
            lens_thickness += thickness_interpolated


        amp_factors = (numpy.exp(-1.0 * att_coefficient * lens_thickness)) ** n_lenses/2
        phase_shifts = -1.0 * output_wavefront.get_wavenumber() * refraction_index_delta * lens_thickness * n_lenses

        output_wavefront.rescale_amplitudes(amp_factors)
        output_wavefront.add_phase_shifts(phase_shifts)

        if error_flag:
            profile_limits_projected = a[-1,0] - a[0,0]
            wavefront_dimension = output_wavefront.get_abscissas()[-1] - output_wavefront.get_abscissas()[0]
            print("profile deformation dimension: %f um"%(1e6 * profile_limits_projected))
            print("wavefront window dimension: %f um" % (1e6 * wavefront_dimension))

            if wavefront_dimension <= profile_limits_projected:
                print("\nWavefront window inside error profile domain: no action needed")
            else:
                if error_edge_management == 0:
                    print("\nProfile deformation extrapolated to fit wavefront dimensions")
                else:
                    output_wavefront.clip(a[0,0] ,a[-1,0])
                    print("\nWavefront clipped to limits of deformation profile")

        # output files
        if write_profile != "":
            f = open(write_profile, "w")
            for i in range(lens_thickness.size):
                f.write("%g %g\n"%(abscissas_on_lens[i], lens_thickness[i]))
            f.close()
            print("File %s written to disk." % write_profile)

        return output_wavefront, abscissas_on_lens, lens_thickness

    # TODO Rewrite all the output Python script
    # warning: pay attention to the double backslash in \\n
    def script_template_output_wavefront_from_radius(self):
        return \
"""import numpy
from scipy import interpolate
from barc4ro.projected_thickness import proj_thick_1D_crl

def calculate_output_wavefront_after_lens1D(input_wavefront,
                                            shape=1,
                                            radius=0.0005,
                                            lens_aperture=0.001,
                                            wall_thickness=0.0002,
                                            refraction_index_delta=0.99999947,
                                            att_coefficient=0.00357382,
                                            number_of_refractive_surfaces=2,
                                            n_lenses=1,
                                            error_flag=0,
                                            error_file="",
                                            error_edge_management=0,
                                            write_profile="",
                                            xc=0,
                                            ang_rot=0,
                                            wt_offset_ffs=0,
                                            offset_ffs=0,
                                            tilt_ffs=0,
                                            wt_offset_bfs=0,
                                            offset_bfs=0,
                                            tilt_bfs=0):


    photon_energy = input_wavefront.get_photon_energy()
    abscissas = input_wavefront.get_abscissas().copy()
    output_wavefront = input_wavefront.duplicate()


    abscissas_on_lens = abscissas

    if number_of_refractive_surfaces == 0:
        n_ref_lens = 1
    elif number_of_refractive_surfaces == 1:
        n_ref_lens = 2
    else:
        raise Exception("Error while reading the number of refractive lenses")

    if shape == 0: # Flat
        lens_thickness = numpy.full_like(abscissas_on_lens, wall_thickness)

    elif shape == 1: # Parabolic

        focus_length = radius / (n_lenses * n_ref_lens * refraction_index_delta)


        # Implementation of barc4ro
        x_2, lens_thickness = proj_thick_1D_crl(shape, lens_aperture, radius,
                                            _n=n_ref_lens,
                                            _wall_thick=wall_thickness,
                                            _xc=xc,
                                            _nx=100,
                                            _ang_rot_ex=ang_rot,
                                            _offst_ffs_x=offset_ffs,
                                            _tilt_ffs_x=tilt_ffs,
                                            _wt_offst_ffs=wt_offset_ffs,
                                            _offst_bfs_x=offset_bfs,
                                            _tilt_bfs_x=tilt_bfs,
                                            _wt_offst_bfs=wt_offset_bfs,
                                            isdgr=False,
                                            project=True,
                                            _axis=abscissas)
        

    elif shape == 2: # Circular
        lens_thickness = n_ref_lens * (numpy.abs(radius) - numpy.sqrt(radius ** 2 - abscissas_on_lens ** 2)) + wall_thickness
        bound = 0.5 * lens_aperture
        if radius < bound: bound = radius
        for i, x in enumerate(abscissas_on_lens):
            if (x < -bound) or (x > bound):
                lens_thickness[i] = 0
        for i, x in enumerate(abscissas_on_lens):
            if (x < -bound) or (x > bound):
                lens_thickness[i] = lens_thickness.max()


    if error_flag:
        a = numpy.loadtxt(error_file) # extrapolation
        if error_edge_management == 0:
            finterpolate = interpolate.interp1d(a[:, 0], a[:, 1], fill_value="extrapolate")  # fill_value=(0,0),bounds_error=False)
        elif error_edge_management == 1:
            finterpolate = interpolate.interp1d(a[:, 0], a[:, 1], fill_value=(0,0), bounds_error=False)
        else: # crop
            raise Exception("Bad value of error_edge_management")
        thickness_interpolated = finterpolate(abscissas_on_lens)
        lens_thickness += thickness_interpolated


    amp_factors = (numpy.exp(-1.0 * att_coefficient * lens_thickness)) ** n_lenses/2
    phase_shifts = -1.0 * output_wavefront.get_wavenumber() * refraction_index_delta * lens_thickness * n_lenses

    output_wavefront.rescale_amplitudes(amp_factors)
    output_wavefront.add_phase_shifts(phase_shifts)

    if error_flag:
        # profile_limits = a[-1, 0] - a[0, 0]
        profile_limits_projected = a[-1,0] - a[0,0]
        wavefront_dimension = output_wavefront.get_abscissas()[-1] - output_wavefront.get_abscissas()[0]
        # print("profile deformation dimension: %f m"%(profile_limits))
        print("profile deformation dimension: %f um"%(1e6 * profile_limits_projected))
        print("wavefront window dimension: %f um" % (1e6 * wavefront_dimension))

        if wavefront_dimension <= profile_limits_projected:
            print("Wavefront window inside error profile domain: no action needed")
        else:
            if error_edge_management == 0:
                print("Profile deformation extrapolated to fit wavefront dimensions")
            else:
                output_wavefront.clip(a[0,0] ,a[-1,0])
                print("Wavefront clipped to limits of deformation profile")

    # output files
    if write_profile != "":
        f = open(write_profile, "w")
        for i in range(lens_thickness.size):
            f.write("%g %g\\n"%(abscissas_on_lens[i], lens_thickness[i]))
        f.close()
        print("File %s written to disk." % write_profile)

    return output_wavefront, abscissas_on_lens, lens_thickness
#
# main
#
from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D
input_wavefront = GenericWavefront1D.load_h5_file("wavefront_input.h5","wfr")
output_wavefront, abscissas_on_lens, lens_thickness = calculate_output_wavefront_after_lens1D(input_wavefront,
                        shape={shape},
                        radius={radius},
                        lens_aperture={lens_aperture},
                        wall_thickness={wall_thickness},
                        refraction_index_delta={refraction_index_delta},
                        att_coefficient={att_coefficient},
                        number_of_refractive_surfaces={number_of_refractive_surfaces},
                        n_lenses = {n_lenses},
                        error_flag= {error_flag},
                        error_file="{error_file}",
                        error_edge_management={error_edge_management},
                        write_profile={write_profile},
                        xc={xc},
                        ang_rot={ang_rot},
                        wt_offset_ffs={wt_offset_ffs},
                        offset_ffs={offset_ffs},
                        tilt_ffs={tilt_ffs},
                        wt_offset_bfs={wt_offset_bfs},
                        offset_bfs={offset_bfs},
                        tilt_bfs={tilt_bfs})

                    
from srxraylib.plot.gol import plot
plot(output_wavefront.get_abscissas(),output_wavefront.get_intensity())
"""
    def do_plot_results(self, progressBarValue): # required by parent
        pass

    def do_plot_wavefront(self, wavefront1D, abscissas_on_lens, lens_thickness, progressBarValue=80):

        if not self.input_data is None:

            self.plot_data1D(x=1e6*wavefront1D.get_abscissas(),
                             y=wavefront1D.get_intensity(),
                             progressBarValue=progressBarValue,
                             tabs_canvas_index=0,
                             plot_canvas_index=0,
                             calculate_fwhm=True,
                             title=self.titles[0],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Intensity")

            self.plot_data1D(x=1e6*wavefront1D.get_abscissas(),
                             y=wavefront1D.get_phase(from_minimum_intensity=0.1,unwrap=1),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=1,
                             plot_canvas_index=1,
                             calculate_fwhm=False,
                             title=self.titles[1],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Phase [unwrapped, for intensity > 10% of peak] (rad)")

            self.plot_data1D(x=1e6*wavefront1D.get_abscissas(),
                             y=numpy.real(wavefront1D.get_complex_amplitude()),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=2,
                             plot_canvas_index=2,
                             calculate_fwhm=False,
                             title=self.titles[2],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Real(Amplitude)")

            self.plot_data1D(x=1e6*wavefront1D.get_abscissas(),
                             y=numpy.imag(wavefront1D.get_complex_amplitude()),
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=3,
                             plot_canvas_index=3,
                             calculate_fwhm=False,
                             title=self.titles[3],
                             xtitle="Spatial Coordinate [$\mu$m]",
                             ytitle="Imag(Amplitude)")

            self.plot_data1D(x=abscissas_on_lens, #TODO check how is possible to plot both refractive surfaces
                             y=lens_thickness*1e6, # in microns
                             progressBarValue=progressBarValue + 10,
                             tabs_canvas_index=4,
                             plot_canvas_index=4,
                             calculate_fwhm=False,
                             title=self.titles[4],
                             xtitle="Spatial Coordinate along o.e. [m]",
                             ytitle="Total lens thickness [$\mu$m]")

            self.plot_canvas[0].resetZoom()



if __name__ == '__main__':

    from PyQt5.QtWidgets import QApplication


    def create_wavefront():
        #
        # create input_wavefront
        #
        from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D
        input_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=-0.0005, x_max=0.0005,
                                                                             number_of_points=1000)
        input_wavefront.set_photon_energy(10000)
        input_wavefront.set_spherical_wave(radius=13.73, center=0, complex_amplitude=complex(1, 0))
        return input_wavefront

    app = QApplication([])
    ow = OWWORealLens1D()
    ow.set_input(create_wavefront())

    # ow.receive_dabam_profile(numpy.array([[-1.50,0],[1.50,0]]))

    ow.propagate_wavefront()

    ow.show()
    app.exec_()
    ow.saveSettings()