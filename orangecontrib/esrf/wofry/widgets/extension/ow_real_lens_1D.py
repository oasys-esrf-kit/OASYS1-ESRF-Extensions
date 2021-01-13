import numpy
import os, sys

import orangecanvas.resources as resources

from PyQt5.QtGui import QPalette, QColor, QFont, QPixmap
from PyQt5.QtWidgets import QMessageBox, QLabel, QSizePolicy
from PyQt5.QtCore import Qt

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import TriggerIn, TriggerOut, EmittingStream

from orangecontrib.esrf.syned.util.lens import Lens # TODO: from syned.beamline.optical_elements....

from syned.widget.widget_decorator import WidgetDecorator

from orangecontrib.wofry.util.wofry_objects import WofryData

from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D

from orangecontrib.esrf.wofry.widgets.gui.ow_optical_element_1d import OWWOOpticalElement1D # TODO rom orangecontrib.wofry.widgets.gui.ow_optical_element_1d

from orangecontrib.esrf.wofry.util.lens import WOLens1D


class OWWORealLens1D(OWWOOpticalElement1D):

    name = "Real Lens 1D"
    id = "WofryLens1D"
    description = "Wofry: Real Lens 1D"
    icon = "icons/lens1d.png"
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
              ("DABAM 1D Profile", numpy.ndarray, "receive_dabam_profile"),
              ("Trigger", TriggerOut, "receive_trigger_signal"),
              WidgetDecorator.syned_input_data()[0]]


    # Basic lens parameters____________________________________________________________________________________________#
    shape = Setting(1)
    radius = Setting(0.0005)
    wall_thickness = Setting(0.00005)
    lens_aperture = Setting(0.001)
    # number_of_refractive_surfaces = Setting(1)
    number_of_curved_surfaces = Setting(2)
    n_lenses = Setting(1)
    material = Setting(0)
    refraction_index_delta = Setting(5.3e-7)
    att_coefficient = Setting(0.00357382)
    error_flag = Setting(0)
    error_file = Setting("<none>")
    error_edge_management = Setting(0)
    write_profile_flag = Setting(0)
    write_profile = Setting("profile1D.dat")

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

    def __init__(self):
        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)

    def draw_specific_box(self):

        box_refractor = oasysgui.widgetBox(self.tab_bas, "1D Lens Geometry", addSpace=False, orientation="vertical",
                                           height=350)


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

        # Help figure
        self.figure_box1 = oasysgui.widgetBox(box_refractor, "Principal parabolic lens parameters", addSpace=False, orientation="horizontal")
        label1 = QLabel("")
        label1.setAlignment(Qt.AlignCenter)
        label1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label1.setPixmap(QPixmap(self.image1_path))
        self.figure_box1.layout().addWidget(label1)

        #
        # Tab Lens pars
        #
        self.tab_err = oasysgui.createTabPage(self.tabs_setting, "Parms")

        # Box refractor:_________________________________________________________________________

        box_refractor2 = oasysgui.widgetBox(self.tab_err, "1D Lens parameters", addSpace=False, orientation="vertical")


        # gui.comboBox(box_refractor2, self, "number_of_refractive_surfaces", label="Number of refractive surfaces", labelWidth=350,
        #              items=["1", "2"],
        #              sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(box_refractor2, self, "number_of_curved_surfaces", label="Number of curved surfaces", labelWidth=350,
                     items=["0 (parallel plate)", "1 (plano-concave)", "2 (bi-concave)"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_visible)


        self.box_n_lenses_id = oasysgui.widgetBox(box_refractor2, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_n_lenses_id, self, "n_lenses", "Number of lenses",
                          labelWidth=300, valueType=int, orientation="horizontal")
        tmp.setToolTip("n_lenses")

        gui.comboBox(box_refractor2, self, "material", label="Lens material",
                     items=self.get_material_name(),
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.box_refraction_index_id = oasysgui.widgetBox(box_refractor2, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_refraction_index_id, self, "refraction_index_delta", "Refraction index delta",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("refraction_index_delta")

        self.box_att_coefficient_id = oasysgui.widgetBox(box_refractor2, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_att_coefficient_id, self, "att_coefficient", "Attenuation coefficient [m-1]",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("att_coefficient")


        gui.comboBox(box_refractor2, self, "write_profile_flag", label="Dump profile to file",
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        self.box_file_out = gui.widgetBox(box_refractor2, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.box_file_out, self, "write_profile", "File name",
                            labelWidth=200, valueType=str, orientation="horizontal")
        # error box _________________________________________________________________________

        box_errors = oasysgui.widgetBox(self.tab_err, "1D Lens error profile", addSpace=False, orientation="vertical")


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

        #
        #
        #
        self.tab_mis = oasysgui.createTabPage(self.tabs_setting, "Misalignments")

        box_misaligments = oasysgui.widgetBox(self.tab_mis, "Typical lens misalignments (only for parabolic shape)",
                                              addSpace=False, orientation="vertical")

        # Tab Misalignments: Typical lens misalignments for Barc4ro_temporarily_only_for_parabolic______________________

        self.mis_flag_box = oasysgui.widgetBox(box_misaligments, "", addSpace=False, orientation="vertical")

        gui.comboBox(self.mis_flag_box, self, "mis_flag", label="Add misalignments", labelWidth=350,
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

    def get_material_name(self, index=None):
        materials_list = ["External", "Be", "Al", "Diamond"]
        if index is None:
            return materials_list
        else:
            return materials_list[index]

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

    def get_optical_element(self):
        return WOLens1D.create_from_keywords(
                    name                         =self.oe_name,
                    shape                        = self.shape,
                    radius                       = self.radius,
                    lens_aperture                = self.lens_aperture,
                    wall_thickness               = self.wall_thickness,
                    material                     = self.get_material_name(self.material),
                    refraction_index_delta       = self.refraction_index_delta,
                    att_coefficient              = self.att_coefficient,
                    number_of_curved_surfaces    = self.number_of_curved_surfaces,
                    n_lenses                     = self.n_lenses,
                    error_flag                   = self.error_flag,
                    error_file                   = self.error_file,
                    error_edge_management        = self.error_edge_management,
                    write_profile_flag           = self.write_profile_flag,
                    write_profile                = self.write_profile,
                    mis_flag                     = self.mis_flag,
                    xc                           = self.xc,
                    ang_rot                      = self.ang_rot,
                    wt_offset_ffs                = self.wt_offset_ffs,
                    offset_ffs                   = self.offset_ffs,
                    tilt_ffs                     = self.tilt_ffs,
                    wt_offset_bfs                = self.wt_offset_bfs,
                    offset_bfs                   = self.offset_bfs,
                    tilt_bfs                     = self.tilt_bfs,
                    )

    #
    # overwritten methods to append profile plot
    #

    def get_titles(self):
        titles = super().get_titles()
        titles.append("O.E. Profile")
        return titles

    def do_plot_results(self, progressBarValue=80): # OVERWRITTEN

        super().do_plot_results(progressBarValue)
        if not self.view_type == 0:
            if not self.wavefront_to_plot is None:

                self.progressBarSet(progressBarValue)

                wo_lens = self.get_optical_element()
                abscissas_on_lens, lens_thickness = wo_lens.get_surface_thickness_mesh(self.input_data.get_wavefront())

                self.plot_data1D(x=abscissas_on_lens*1e6, #TODO check how is possible to plot both refractive surfaces
                                 y=lens_thickness*1e6, # in microns
                                 progressBarValue=progressBarValue + 10,
                                 tabs_canvas_index=4,
                                 plot_canvas_index=4,
                                 calculate_fwhm=False,
                                 title=self.get_titles()[4],
                                 xtitle="Spatial Coordinate along o.e. [$\mu$m]",
                                 ytitle="Total lens thickness [$\mu$m]")

                self.progressBarFinished()


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

    def get_example_wofry_data():
        from wofryimpl.propagator.light_source import WOLightSource
        from wofryimpl.beamline.beamline import WOBeamline
        from orangecontrib.wofry.util.wofry_objects import WofryData

        light_source = WOLightSource(dimension=1,
                                     kind_of_wave=1,
                                     initialize_from=0,
                                     range_from_h=-0.0005,
                                     range_to_h=0.0005,
                                     range_from_v=-0.0005,
                                     range_to_v=0.0005,
                                     number_of_points_h=1000,
                                     number_of_points_v=1,
                                     energy=10000.0,
                                     radius=13.73,
                                     )
        return WofryData(wavefront=light_source.get_wavefront(),
                           beamline=WOBeamline(light_source=light_source))

    app = QApplication([])
    ow = OWWORealLens1D()
    # ow.set_input(create_wavefront())
    ow.set_input(get_example_wofry_data())
    # ow.receive_dabam_profile(numpy.array([[-1.50,0],[1.50,0]]))

    ow.propagate_wavefront()

    ow.show()
    app.exec_()
    ow.saveSettings()