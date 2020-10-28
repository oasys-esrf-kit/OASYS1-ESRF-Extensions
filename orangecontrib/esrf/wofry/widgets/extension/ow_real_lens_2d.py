import numpy
from orangewidget.settings import Setting
from orangewidget import gui
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

# from syned.beamline.optical_elements.ideal_elements.lens import IdealLens
from orangecontrib.esrf.syned.util.lens import Lens # TODO: from syned.beamline.optical_elements....

# from wofry.beamline.optical_elements.ideal_elements.lens import WOIdealLens
from orangecontrib.esrf.wofry.util.lens import WOLens

from orangecontrib.wofry.widgets.gui.ow_optical_element import OWWOOpticalElement, OWWOOpticalElementWithBoundaryShape

from syned.beamline.shape import SurfaceShape, Plane, Paraboloid, ParabolicCylinder, Sphere, SphericalCylinder
from syned.beamline.shape import Convexity, Direction

from oasys.util.oasys_util import write_surface_file


class OWWORealLens2D(OWWOOpticalElement):

    name = "Lens"
    description = "Wofry: Real Lens 2D"
    icon = "icons/lens.png"
    priority = 20

    number_of_curved_surfaces = Setting(2)
    lens_radius = Setting(200e-6)

    surface_shape = Setting(0)
    two_d_lens = Setting(0)
    wall_thickness = Setting(10e-6)

    material = Setting(1)

    aperture_shape = Setting(0)
    aperture_dimension_v = Setting(100e-6)
    aperture_dimension_h = Setting(200e-6)
    # TODO: this is redundant...
    # width = Setting(1e-3)
    # height = Setting(1e-4)
    shape = Setting(1)
    radius = Setting(100e-6)

    write_input_wavefront = Setting(0)
    write_profile_flag = Setting(0)
    write_profile = Setting("lens_profile_2D.h5")

    def __init__(self):
        super().__init__()


    def set_visible(self):
        self.lens_radius_box_id.setVisible(self.number_of_curved_surfaces != 0)
        self.lens_width_id.setVisible(self.aperture_shape == 1)
        self.box_file_out.setVisible(self.write_profile_flag == 1)

    def get_material_name(self, index=None):
        materials_list = ["", "Be", "Al", "Diamond"]
        if index is None:
            return materials_list
        else:
            return materials_list[index]

    def draw_specific_box(self):

        self.lens_box = oasysgui.widgetBox(self.tab_bas, "Real Lens Setting", addSpace=False, orientation="vertical",
                                           height=350)

        oasysgui.lineEdit(self.lens_box, self, "wall_thickness", "(t_wall) Wall thickness [m]", labelWidth=260, valueType=float, orientation="horizontal")

        gui.comboBox(self.lens_box, self, "material", label="Lens material",
                     items=self.get_material_name(),
                     sendSelectedValue=False, orientation="horizontal")


        gui.comboBox(self.lens_box, self, "number_of_curved_surfaces", label="Number of curved surfaces", labelWidth=350,
                     items=["0 (parallel plate)", "1 (plano-concave)", "2 (bi-concave)"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_visible)


        self.lens_radius_box_id = oasysgui.widgetBox(self.lens_box, orientation="vertical", height=None)
        oasysgui.lineEdit(self.lens_radius_box_id, self, "lens_radius", "(R) radius of curvature [m]", labelWidth=260,
                          valueType=float, orientation="horizontal",)

        gui.comboBox(self.lens_radius_box_id, self, "surface_shape", label="Lens shape", labelWidth=350,
                     items=["Parabolic", "Circular"],
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(self.lens_radius_box_id, self, "two_d_lens", label="Focusing in", labelWidth=350,
                     items=["2D", "1D (tangential)", "1D (sagittal)"], sendSelectedValue=False, orientation="horizontal")


        # super().draw_specific_box() # adds boundary box
        gui.comboBox(self.lens_box, self, "aperture_shape", label="Aperture shape", labelWidth=350,
                     items=["Circular", "Rectangular"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_visible)
        oasysgui.lineEdit(self.lens_box, self, "aperture_dimension_v", "Aperture V (height/diameter) [m]", labelWidth=260,
                          valueType=float, orientation="horizontal",)

        self.lens_width_id = oasysgui.widgetBox(self.lens_box, orientation="vertical", height=None)
        oasysgui.lineEdit(self.lens_width_id, self, "aperture_dimension_h", "Aperture H (width) [m]", labelWidth=260,
                          valueType=float, orientation="horizontal",)



        # files i/o tab
        self.tab_files = oasysgui.createTabPage(self.tabs_setting, "File I/O")
        files_box = oasysgui.widgetBox(self.tab_files, "Files", addSpace=True, orientation="vertical")

        gui.comboBox(files_box, self, "write_input_wavefront", label="Input wf to file (for script)",
                     items=["No", "Yes [wavefront2D_input.h5]"], sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(files_box, self, "write_profile_flag", label="Dump profile to file",
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        self.box_file_out = gui.widgetBox(files_box, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.box_file_out, self, "write_profile", "File name",
                            labelWidth=200, valueType=str, orientation="horizontal")


        self.set_visible()

    def get_optical_element(self):

        return WOLens.create_from_keywords(
            name=self.name,
            number_of_curved_surfaces=self.number_of_curved_surfaces,
            two_d_lens=self.two_d_lens,
            surface_shape=self.surface_shape,
            wall_thickness=self.wall_thickness,
            lens_radius=self.lens_radius,
            material=self.get_material_name(index=self.material),
            aperture_shape=self.aperture_shape,
            aperture_dimension_h=self.aperture_dimension_h,
            aperture_dimension_v=self.aperture_dimension_v,
        )

    def get_optical_element_python_code(self):
        txt  = ""
        txt += "\nfrom orangecontrib.esrf.wofry.util.lens import WOLens"
        txt += "\n"
        txt += "\noptical_element = WOLens.create_from_keywords(name=%s,number_of_curved_surfaces=%d,two_d_lens=%d,surface_shape=%d,wall_thickness=%g,lens_radius=%g,material='%s',aperture_shape=%d,aperture_dimension_h=%g,aperture_dimension_v=%g)" \
               % (self.name,\
                  self.number_of_curved_surfaces,\
                  self.two_d_lens,\
                  self.surface_shape,\
                  self.wall_thickness,\
                  self.lens_radius,\
                  self.get_material_name(index=self.material),\
                  self.aperture_shape,\
                  self.aperture_dimension_h,\
                  self.aperture_dimension_v,)
        txt += "\n"
        return txt

    def check_data(self):
        super().check_data()
        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_x), "Horizontal Focal Length")
        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_y), "Vertical Focal Length")

    def receive_specific_syned_data(self, optical_element):
        if not optical_element is None:
            if isinstance(optical_element, Lens):
                self.lens_radius = optical_element._radius
                self.wall_thickness = optical_element._thickness
                self.material = optical_element._material
            else:
                raise Exception("Syned Data not correct: Optical Element is not a Lens")
        else:
            raise Exception("Syned Data not correct: Empty Optical Element")

    def propagate_wavefront(self):
        super().propagate_wavefront()

        if self.write_input_wavefront == 1:
            self.input_data.get_wavefront().save_h5_file("wavefront2D_input.h5",subgroupname="wfr",
                                         intensity=True,phase=False,overwrite=True,verbose=False)
            print("\nFile with input wavefront wavefront2D_input.h5 written to disk.")

        if self.write_profile_flag == 1:
            xx, yy, s = self.get_optical_element().get_surface_thickness_mesh(self.input_data.get_wavefront())
            write_surface_file(s.T, xx, yy, self.write_profile, overwrite=True)
            print("\nFile for OASYS " + self.write_profile + " written to disk.")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D

    a = QApplication(sys.argv)
    ow = OWWORealLens2D()
    input_wavefront = GenericWavefront2D.initialize_wavefront_from_range(-0.002,0.002,-0.001,0.001,(400,200))
    ow.set_input(input_wavefront)

    ow.show()
    a.exec_()
    ow.saveSettings()