import numpy

from oasys.util.oasys_util import write_surface_file
from orangecontrib.esrf.wofry.util.thin_object import WOThinObject, WOThinObject1D #TODO from wofryimpl....


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

        x = wavefront.get_coordinate_x()
        y = wavefront.get_coordinate_y()

        if self._correction_method == 0: # write file with zero profile
            profile = numpy.zeros((x.size, y.size))
        elif self._correction_method == 1: # focus to waist

            print("\n\n\n ==========  parameters from optical element : ")
            print(self.info())


            refraction_index_delta, att_coefficient = self.get_refraction_index(photon_energy)
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

class WOThinObjectCorrector1D(WOThinObject1D):
    def __init__(self, name="Undefined",
                 file_with_thickness_mesh="",
                 material="",
                 refraction_index_delta=1e-07,
                 att_coefficient=0.0,
                 correction_method=1,
                 focus_at=10.0,
                 wall_thickness=0.0,
                 apply_correction_to_wavefront=0,
                 ):

        super().__init__(name=name,
                         file_with_thickness_mesh=file_with_thickness_mesh,
                         material=material,
                         refraction_index_delta=refraction_index_delta,
                         att_coefficient=att_coefficient,
                         )

        self._correction_method = correction_method
        self._focus_at = focus_at
        self._wall_thickness = wall_thickness
        self._apply_correction_to_wavefront = apply_correction_to_wavefront

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):

        photon_energy = wavefront.get_photon_energy()

        x = wavefront.get_abscissas()

        if self._correction_method == 0:  # write file with zero profile
            profile = numpy.zeros_like(x)
        elif self._correction_method == 1:  # focus to waist

            print("\n\n\n ==========  parameters from optical element : ")
            print(self.info())

            refraction_index_delta, att_coefficient = self.get_refraction_index(photon_energy)
            # auxiliar spherical wavefront
            wavefront_model = wavefront.duplicate()
            wavefront_model.set_spherical_wave(radius=-self._focus_at, complex_amplitude=1.0, )

            phase_correction = numpy.angle(
                wavefront_model.get_complex_amplitude() / wavefront.get_complex_amplitude())
            profile = -phase_correction / wavefront.get_wavenumber() / refraction_index_delta

        profile += self._wall_thickness
        f = open(self.get_file_with_thickness_mesh(), 'w')
        for i in range(x.size):
            f.write("%g %g\n" % (x[i], profile[i]))
        f.close()
        print("\nFile 1D for OASYS " + self.get_file_with_thickness_mesh() + " written to disk.")

        if self._apply_correction_to_wavefront > 0:
            output_wavefront = super().applyOpticalElement(wavefront, parameters=parameters,
                                                           element_index=element_index)
        else:
            output_wavefront = wavefront

        return output_wavefront

