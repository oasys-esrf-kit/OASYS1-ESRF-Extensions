import numpy
import xraylib

from oasys.util.oasys_util import write_surface_file
from orangecontrib.esrf.wofry.util.thin_object import WOThinObject #TODO from wofryimpl....


class WOThinObjectCorrector(WOThinObject):

    def __init__(self, name="Undefined",
                 file_with_thickness_mesh="",
                 material="",
                 correction_method=1,
                 focus_at=10.0,
                 wall_thickness=0.0,
                 apply_correction_to_wavefront=0,
                 ):

        super().__init__(name=name,
                 file_with_thickness_mesh=file_with_thickness_mesh,
                 material=material,
                         )

        self._correction_method = correction_method
        self._focus_at = focus_at
        self._wall_thickness = wall_thickness
        self._apply_correction_to_wavefront = apply_correction_to_wavefront

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):

        photon_energy = wavefront.get_photon_energy()
        wave_length = wavefront.get_wavelength()
        x = wavefront.get_coordinate_x()
        y = wavefront.get_coordinate_y()

        if self._correction_method == 0: # write file with zero profile
            profile = numpy.zeros((x.size, y.size))
        elif self._correction_method == 1: # focus to waist

            print("\n\n\n ==========  parameters from optical element : ")
            print(self.info())


            if self.get_material() == "Be": # Be
                element = "Be"
                density = xraylib.ElementDensity(4)
            elif self.get_material() == "Al": # Al
                element = "Al"
                density = xraylib.ElementDensity(13)
            elif self.get_material() == "Diamond": # Diamond
                element = "C"
                density = 3.51
            else:
                raise Exception("Bad material: " + self.get_material())

            refraction_index = xraylib.Refractive_Index(element, photon_energy/1000, density)
            refraction_index_delta = 1 - refraction_index.real
            att_coefficient = 4*numpy.pi * (xraylib.Refractive_Index(element, photon_energy/1000, density)).imag / wave_length

            print("\n\n\n ==========  parameters recovered from xraylib : ")
            print("Element: %s" % element)
            print("        density = %g " % density)
            print("Photon energy = %g eV" % (photon_energy))
            print("Refracion index delta = %g " % (refraction_index_delta))
            print("Attenuation coeff mu = %g m^-1" % (att_coefficient))

            # auxiliar spherical wavefront
            wavefront_model = wavefront.duplicate()
            wavefront_model.set_spherical_wave(radius=-self._focus_at, complex_amplitude=1.0,)


            phase_correction = numpy.angle( wavefront_model.get_complex_amplitude() / wavefront.get_complex_amplitude())
            profile = -phase_correction / wavefront.get_wavenumber() / refraction_index_delta


        profile += self._wall_thickness
        write_surface_file(profile.T, x, y, self.get_file_with_thickness_mesh(), overwrite=True)
        print("\nFile for OASYS " + self.get_file_with_thickness_mesh() + " written to disk.")

        if self._apply_correction_to_wavefront > 0:
            output_wavefront = super().applyOpticalElement(wavefront, parameters=parameters, element_index=element_index)
        else:
            output_wavefront = wavefront

        return output_wavefront

    # def to_python_code(self, data=None):
    #     txt  = ""
    #     txt += "\nfrom orangecontrib.esrf.wofry.widgets.extension.ow_thin_object_corrector_2d import WOThinObjectCorrector"
    #     txt += "\n"
    #     txt += "\noptical_element = WOThinObjectCorrector(name='%s',file_with_thickness_mesh='%s',material='%s',\n" % \
    #            (self.get_name(), self.get_file_with_thickness_mesh(), self.get_material())
    #     txt += "    correction_method=%d, focus_at= %g, wall_thickness=%g, apply_correction_to_wavefront=%d)" % \
    #            (self._correction_method, self._focus_at, self._wall_thickness, self._apply_correction_to_wavefront)
    #     txt += "\n"
    #     return txt