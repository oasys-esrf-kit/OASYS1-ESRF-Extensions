import numpy

from oasys.util.oasys_util import write_surface_file
from orangecontrib.esrf.wofry.util.thin_object import WOThinObject, WOThinObject1D #TODO from wofryimpl....
from wofry.beamline.decorators import OpticalElementDecorator

class WOThinObjectCorrector(WOThinObject, OpticalElementDecorator):

    def __init__(self, name="Undefined",
                 file_with_thickness_mesh="",
                 material="",
                 refraction_index_delta=1e-07,
                 att_coefficient=0.0,
                 correction_method=1,
                 focus_at=10.0,
                 wall_thickness=0.0,
                 apply_correction_to_wavefront=0,
                 file_with_thickness_mesh_flag=0,
                 ):

        super().__init__(name=name,
                 file_with_thickness_mesh=file_with_thickness_mesh,
                 material=material,
                         )

        self._correction_method = correction_method
        self._focus_at = focus_at
        self._wall_thickness = wall_thickness
        self._apply_correction_to_wavefront = apply_correction_to_wavefront
        self._file_with_thickness_mesh_flag = file_with_thickness_mesh_flag

        self._refraction_index_delta = refraction_index_delta
        self._att_coefficient = att_coefficient

    def calculate_correction_profile(self, wavefront):

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
        if self._file_with_thickness_mesh_flag:
            write_surface_file(profile.T, x, y, self.get_file_with_thickness_mesh(), overwrite=True)
            print("\nFile for OASYS " + self.get_file_with_thickness_mesh() + " written to disk.")

        # for info


        # H profile
        n = profile.shape[0]
        one_over_fraction_in_length = 10
        w = n // (2 * one_over_fraction_in_length)

        profile_line = profile[:, w]
        xx = x[(n // 2 - w):(n // 2 + w)]
        yy = profile_line[(n // 2 - w):(n // 2 + w)]

        yder = numpy.gradient(yy, xx)
        coeff = numpy.polyfit(xx, yder, 1)
        print("\n\n\n ==========  fitted radius in the H profile center (over 1/%d of length): " % one_over_fraction_in_length)
        print("fitted lens (with two curved sides) of radius = %g m " % (2 / coeff[0]))
        print("which corresponds to a focal length of %g m " % (1 / coeff[0] / refraction_index_delta))

        # V profile
        n = profile.shape[1]
        one_over_fraction_in_length = 10
        w = n // (2 * one_over_fraction_in_length)

        profile_line = profile[w, :]
        xx = y[(n // 2 - w):(n // 2 + w)]
        yy = profile_line[(n // 2 - w):(n // 2 + w)]

        yder = numpy.gradient(yy, xx)
        coeff = numpy.polyfit(xx, yder, 1)
        print("\n\n\n ==========  fitted radius in the V profile center (over 1/%d of length): " % one_over_fraction_in_length)
        print("fitted lens (with two curved sides) of radius = %g m " % (2 / coeff[0]))
        print("which corresponds to a focal length of %g m " % (1 / coeff[0] / refraction_index_delta))

        return profile, x, y


    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):

        profile, x, y = self.calculate_correction_profile(wavefront)

        if self._apply_correction_to_wavefront > 0:
            #TODO change this....
            output_wavefront = super().applyOpticalElement(wavefront, parameters=parameters, element_index=element_index)
        else:
            output_wavefront = wavefront

        return output_wavefront


    def to_python_code(self, data=None):
        txt = ""
        txt += "\nfrom orangecontrib.esrf.wofry.util.thin_object_corrector import WOThinObjectCorrector #TODO update"
        txt += "\n"
        txt += "\noptical_element = WOThinObjectCorrector("
        txt += "\n    name='%s'," % self.get_name()
        txt += "\n    file_with_thickness_mesh_flag=%d," % self._file_with_thickness_mesh_flag
        txt += "\n    file_with_thickness_mesh='%s'," % self.get_file_with_thickness_mesh()
        txt += "\n    material='%s'," % self.get_material()
        if self.get_material() == "External":
            txt += "\n    refraction_index_delta=%g," % self._refraction_index_delta
            txt += "\n    att_coefficient=%g," % self._att_coefficient
        txt += "\n    focus_at=%g," % self._focus_at
        txt += "\n    wall_thickness=%g," % self._wall_thickness
        txt += "\n    apply_correction_to_wavefront=%d)" % self._apply_correction_to_wavefront

        txt += "\n"
        return txt

class WOThinObjectCorrector1D(WOThinObject1D, OpticalElementDecorator):
    def __init__(self, name="Undefined",
                 file_with_thickness_mesh="",
                 material="",
                 refraction_index_delta=1e-07,
                 att_coefficient=0.0,
                 correction_method=1,
                 focus_at=10.0,
                 wall_thickness=0.0,
                 apply_correction_to_wavefront=0,
                 file_with_thickness_mesh_flag=0,
                 fit_fraction_in_length=0.1,
                 fit_filename="",
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
        self._file_with_thickness_mesh_flag = file_with_thickness_mesh_flag

        self._fit_fraction_in_length = fit_fraction_in_length
        self._fit_filename = fit_filename

    def calculate_correction_profile(self, wavefront):
        photon_energy = wavefront.get_photon_energy()

        x = wavefront.get_abscissas()

        if self._correction_method == 0:  # write file with zero profile
            profile = numpy.zeros_like(x)
            profile += self._wall_thickness
        elif self._correction_method == 1:  # focus to waist

            print("\n\n\n ==========  parameters from optical element : ")
            print(self.info())

            refraction_index_delta, att_coefficient = self.get_refraction_index(photon_energy)
            # auxiliar spherical wavefront
            target_wavefront = wavefront.duplicate()
            target_wavefront.set_spherical_wave(radius=-self._focus_at, complex_amplitude=1.0, )

            phase_input = wavefront.get_phase(unwrap=True)
            phase_target = target_wavefront.get_phase(unwrap=True)
            phase_correction = phase_target - phase_input

            profile = - phase_correction / (wavefront.get_wavenumber() * refraction_index_delta)
            profile -= profile.min()
            profile += self._wall_thickness

        if self._file_with_thickness_mesh_flag:
            f = open(self.get_file_with_thickness_mesh(), 'w')
            for i in range(x.size):
                f.write("%g %g\n" % (x[i], profile[i]))
            f.close()
            print("\nFile 1D for OASYS " + self.get_file_with_thickness_mesh() + " written to disk.")

        # for info
        n = profile.size
        fraction_in_length = self._fit_fraction_in_length
        w = int((n * fraction_in_length) / 2)

        if w <= 1: w = 1


        xx = x[(n // 2 - w):(n // 2 + w)]
        yy = profile[(n // 2 - w):(n // 2 + w)]

        yder = numpy.gradient(yy, xx)
        coeff = numpy.polyfit(xx, yder, 1)
        print("\n\n\n ==========  fitted radius in the profile center (over %g of length): " % fraction_in_length)
        print("fitted lens (with two curved sides) of radius = %g m " % (2 / coeff[0]))
        print("which corresponds to a focal length of %g m " % (1 / coeff[0] / refraction_index_delta))

        if self._fit_filename != "":
            f = open(self._fit_filename, 'w')
            f.write("# ==========  fitted radius in the profile center (over %g of length): \n" % fraction_in_length)
            f.write("# fitted lens (with two curved sides) of radius = %g m \n" % (2 / coeff[0]))
            f.write("# which corresponds to a focal length of %g m \n" % (1 / coeff[0] / refraction_index_delta))

            f.write("%g\n" % (2 / coeff[0]))
            f.write("%g\n" % (1 / coeff[0] / refraction_index_delta))
            f.close()
            print("File %s written to disk." % self._fit_filename)
        return x, profile

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):

        x, profile = self.calculate_correction_profile(wavefront)

        refraction_index_delta, att_coefficient = self.get_refraction_index(wavefront.get_photon_energy())

        if self._apply_correction_to_wavefront > 0:

            amp_factors = numpy.exp(-1.0 * att_coefficient * profile / 2) # factor of 2 because it is amplitude
            phase_shifts = -1.0 * wavefront.get_wavenumber() * refraction_index_delta * profile

            output_wavefront = wavefront.duplicate()
            output_wavefront.rescale_amplitudes(amp_factors)
            output_wavefront.add_phase_shifts(phase_shifts)
        else:
            output_wavefront = wavefront

        return output_wavefront

    def to_python_code(self, data=None):
        txt = ""
        txt += "\nfrom orangecontrib.esrf.wofry.util.thin_object_corrector import WOThinObjectCorrector1D #TODO update"
        txt += "\n"
        txt += "\noptical_element = WOThinObjectCorrector1D("
        txt += "\n    name='%s'," % self.get_name()
        txt += "\n    file_with_thickness_mesh_flag=%d," % self._file_with_thickness_mesh_flag
        txt += "\n    file_with_thickness_mesh='%s'," % self.get_file_with_thickness_mesh()
        txt += "\n    material='%s'," % self.get_material()
        if self.get_material() == "External":
            txt += "\n    refraction_index_delta=%g," % self._refraction_index_delta
            txt += "\n    att_coefficient=%g," % self._att_coefficient
        txt += "\n    focus_at=%g," % self._focus_at
        txt += "\n    wall_thickness=%g," % self._wall_thickness
        txt += "\n    apply_correction_to_wavefront=%d," % self._apply_correction_to_wavefront
        txt += "\n    fit_fraction_in_length=%g," % self._fit_fraction_in_length
        txt += "\n    fit_filename='%s')" % self._fit_filename

        txt += "\n"
        return txt

