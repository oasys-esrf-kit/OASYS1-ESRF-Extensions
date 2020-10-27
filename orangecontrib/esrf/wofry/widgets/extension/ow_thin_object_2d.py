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
from wofry.beamline.decorators import OpticalElementDecorator
from syned.beamline.optical_element import OpticalElement
# mimics a syned element



class ThinObject(OpticalElement):
    def __init__(self,
                 name="Undefined",
                 file_with_thickness_mesh="",
                 material=""):

        super().__init__(name=name,
                         boundary_shape=None)
        self._material = material
        self._file_with_thickness_mesh = file_with_thickness_mesh

        # support text contaning name of variable, help text and unit. Will be stored in self._support_dictionary
        self._set_support_text([
                    ("name",                "Name" ,                                "" ),
                    ("boundary_shape",      "Boundary shape",                       "" ),
                    ("material",            "Material (element, compound or name)", "" ),
            ] )


    def get_material(self):
        return self._material

    def get_file_with_thickness_mesh(self):
        return self._file_with_thickness_mesh

# mimics a wofry element
class WOThinObject(ThinObject, OpticalElementDecorator):
    def __init__(self,
                 name="Undefined",
                 file_with_thickness_mesh="",
                 material=""):
        ThinObject.__init__(self,
                      name=name,
                      file_with_thickness_mesh=file_with_thickness_mesh,
                      material=material)

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):
        return wavefront
        #
        #
        # photon_energy = wavefront.get_photon_energy()
        # wave_length = wavefront.get_wavelength()
        #
        # if self.get_material() == "Be": # Be
        #     element = "Be"
        #     density = xraylib.ElementDensity(4)
        # elif self.get_material() == "Al": # Al
        #     element = "Al"
        #     density = xraylib.ElementDensity(13)
        # elif self.get_material() == "Diamond": # Diamond
        #     element = "C"
        #     density = 3.51
        # else:
        #     raise Exception("Bad material: " + self.get_material())
        #
        # refraction_index = xraylib.Refractive_Index(element, photon_energy/1000, density)
        # refraction_index_delta = 1 - refraction_index.real
        # att_coefficient = 4*numpy.pi * (xraylib.Refractive_Index(element, photon_energy/1000, density)).imag / wave_length
        #
        # print("\n\n\n ==========  parameters recovered from xraylib : ")
        # print("Element: %s" % element)
        # print("        density = %g " % density)
        # print("Photon energy = %g eV" % (photon_energy))
        # print("Refracion index delta = %g " % (refraction_index_delta))
        # print("Attenuation coeff mu = %g m^-1" % (att_coefficient))
        #
        # amp_factors = numpy.sqrt(numpy.exp(-1.0 * att_coefficient * lens_thickness))
        # phase_shifts = -1.0 * wavefront.get_wavenumber() * refraction_index_delta * lens_thickness
        #
        # output_wavefront = wavefront.duplicate()
        # output_wavefront.rescale_amplitudes(amp_factors)
        # output_wavefront.add_phase_shifts(phase_shifts)
        #
        # return output_wavefront



class OWWOThinObject2D(OWWOOpticalElement):

    name = "ThinObject"
    description = "Wofry: Thin Object 2D"
    icon = "icons/thin_object.png"
    priority = 30


    material = Setting(1)

    aperture_shape = Setting(0)
    aperture_dimension_v = Setting(100e-6)
    aperture_dimension_h = Setting(200e-6)


    write_input_wavefront = Setting(0)
    write_profile_flag = Setting(0)
    write_profile = Setting("thin_object_profile_2D.h5")

    file_with_thickness_mesh = Setting("<none>")

    def __init__(self):
        super().__init__()


    def set_visible(self):
        self.box_file_out.setVisible(self.write_profile_flag == 1)

    def get_material_name(self, index=None):
        materials_list = ["", "Be", "Al", "Diamond"]
        if index is None:
            return materials_list
        else:
            return materials_list[index]

    def draw_specific_box(self):

        self.thinobject_box = oasysgui.widgetBox(self.tab_bas, "Thin Object Setting", addSpace=False, orientation="vertical",
                                           height=350)

        gui.comboBox(self.thinobject_box, self, "material", label="Lens material",
                     items=self.get_material_name(),
                     sendSelectedValue=False, orientation="horizontal")

        oasysgui.lineEdit(self.thinobject_box, self, "file_with_thickness_mesh", "File with thickness mesh",
                            labelWidth=200, valueType=str, orientation="horizontal")


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

        return WOThinObject(name="Undefined",
                 file_with_thickness_mesh=self.file_with_thickness_mesh,
                 material=self.get_material_name(self.material))

    def get_optical_element_python_code(self):
        txt  = ""
        # txt += "\nfrom orangecontrib.esrf.wofry.util.lens import WOLens"
        # txt += "\n"
        # txt += "\noptical_element = WOLens.create_from_keywords(name=%s,number_of_curved_surfaces=%d,two_d_lens=%d,surface_shape=%d,wall_thickness=%g,lens_radius=%g,material='%s',aperture_shape=%d,aperture_dimension_h=%g,aperture_dimension_v=%g)" \
        #        % (self.name,\
        #           self.number_of_curved_surfaces,\
        #           self.two_d_lens,\
        #           self.surface_shape,\
        #           self.wall_thickness,\
        #           self.lens_radius,\
        #           self.get_material_name(index=self.material),\
        #           self.aperture_shape,\
        #           self.aperture_dimension_h,\
        #           self.aperture_dimension_v,)
        txt += "\n"
        return txt

    def check_data(self):
        super().check_data()
        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_x), "Horizontal Focal Length")
        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_y), "Vertical Focal Length")

    def receive_specific_syned_data(self, optical_element):
        pass
        # if not optical_element is None:
        #     if isinstance(optical_element, Lens):
        #         self.lens_radius = optical_element._radius
        #         self.wall_thickness = optical_element._thickness
        #         self.material = optical_element._material
        #     else:
        #         raise Exception("Syned Data not correct: Optical Element is not a Lens")
        # else:
        #     raise Exception("Syned Data not correct: Empty Optical Element")

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
    ow = OWWOThinObject2D()
    input_wavefront = GenericWavefront2D.initialize_wavefront_from_range(-0.002,0.002,-0.001,0.001,(400,200))
    ow.set_input(input_wavefront)

    ow.show()
    a.exec_()
    ow.saveSettings()
