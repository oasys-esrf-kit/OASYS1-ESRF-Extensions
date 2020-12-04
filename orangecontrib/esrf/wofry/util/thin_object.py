import numpy
from scipy.interpolate import interp2d
import scipy.constants as codata
import xraylib

from oasys.util.oasys_util import write_surface_file, read_surface_file
from oasys.util.oasys_objects import OasysSurfaceData


from syned.beamline.optical_element import OpticalElement
from syned.widget.widget_decorator import WidgetDecorator

from wofry.beamline.decorators import OpticalElementDecorator


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
                    ("name",                       "Name" ,                                "" ),
                    ("boundary_shape",             "Boundary shape",                       "" ),
                    ("material",                   "Material (element, compound or name)", "" ),
                    ("file_with_thickness_mesh",   "File with thickness mesh",             "" ),
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

    def get_refraction_index(self, photon_energy):

        wave_length = codata.h * codata.c / codata.e / photon_energy

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

        return refraction_index_delta, att_coefficient

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):
        # return wavefront

        print("\n\n\n ==========  parameters from optical element : ")
        print(self.info())

        photon_energy = wavefront.get_photon_energy()

        refraction_index_delta, att_coefficient = self.get_refraction_index(photon_energy)

        xx, yy, zz = read_surface_file(self.get_file_with_thickness_mesh())
        if zz.min() < 0: zz -= zz.min()

        f = interp2d(xx, yy, zz, kind='linear', bounds_error=False, fill_value=0)
        x = wavefront.get_coordinate_x()
        y = wavefront.get_coordinate_y()
        interpolated_profile = f(x, y)

        amp_factors = numpy.sqrt(numpy.exp(-1.0 * att_coefficient * interpolated_profile))
        phase_shifts = -1.0 * wavefront.get_wavenumber() * refraction_index_delta * interpolated_profile

        output_wavefront = wavefront.duplicate()
        output_wavefront.rescale_amplitudes(amp_factors.T)
        output_wavefront.add_phase_shifts(phase_shifts.T)

        return output_wavefront

    def to_python_code(self, data=None):
        txt  = ""
        txt += "\nfrom orangecontrib.esrf.wofry.widgets.extension.ow_thin_object_2d import WOThinObject"
        txt += "\n"
        txt += "\noptical_element = WOThinObject(name='%s',file_with_thickness_mesh='%s',material='%s')" % \
               (self.get_name(), self.get_file_with_thickness_mesh(), self.get_material())
        txt += "\n"
        return txt


class WOThinObject1D(WOThinObject):
    def __init__(self,
                 name="Undefined",
                 file_with_thickness_mesh="",
                 material=""):
        super().__init__(
                      name=name,
                      file_with_thickness_mesh=file_with_thickness_mesh,
                      material=material)

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):
        # return wavefront

        print("\n\n\n ==========  parameters from optical element : ")
        print(self.info())

        photon_energy = wavefront.get_photon_energy()

        refraction_index_delta, att_coefficient = self.get_refraction_index(photon_energy)

        a = numpy.loadtxt(self.get_file_with_thickness_mesh())
        xx = a[:,0].copy()
        zz = a[:,1].copy()
        # xx, yy, zz = read_surface_file(self.get_file_with_thickness_mesh())
        if zz.min() < 0: zz -= zz.min()
        #
        # f = interp2d(xx, yy, zz, kind='linear', bounds_error=False, fill_value=0)
        x = wavefront.get_abscissas()

        interpolated_profile = numpy.interp(x, xx, zz)
        
        #
        amp_factors = numpy.sqrt(numpy.exp(-1.0 * att_coefficient * interpolated_profile))
        phase_shifts = -1.0 * wavefront.get_wavenumber() * refraction_index_delta * interpolated_profile

        output_wavefront = wavefront.duplicate()
        output_wavefront.rescale_amplitudes(amp_factors)
        output_wavefront.add_phase_shifts(phase_shifts)

        return output_wavefront

if __name__ == "__main__":

    import numpy
    from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D
    from srxraylib.plot.gol import plot, plot_image


    input_wavefront = GenericWavefront2D.initialize_wavefront_from_range(x_min=-0.0003, x_max=0.0003, y_min=-0.0003,
                                                                          y_max=0.0003, number_of_points=(400, 200))
    input_wavefront.set_photon_energy(10000)
    input_wavefront.set_plane_wave_from_complex_amplitude(complex_amplitude=complex(1, 0))

    optical_element = WOThinObject(name='ThinObject',
                                   file_with_thickness_mesh='/home/srio/Downloads/SRW_M_thk_res_workflow_a_FC_CDn01.dat.h5',
                                   material='Be')

    # no drift in this element
    output_wavefront = optical_element.applyOpticalElement(input_wavefront)

    #
    # ---- plots -----
    #
    plot_image(output_wavefront.get_intensity(), output_wavefront.get_coordinate_x(),
               output_wavefront.get_coordinate_y(), aspect='auto', title='OPTICAL ELEMENT NR 1')


    o1d = WOThinObject1D()
    print(o1d.info())