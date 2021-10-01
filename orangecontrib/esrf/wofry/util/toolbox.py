import numpy
from scipy.interpolate import interp2d
import scipy.constants as codata
import xraylib

from oasys.util.oasys_util import write_surface_file, read_surface_file
from oasys.util.oasys_objects import OasysSurfaceData


from syned.beamline.optical_element import OpticalElement
from syned.widget.widget_decorator import WidgetDecorator

from wofry.beamline.decorators import OpticalElementDecorator
from wofry.propagator.polarization import Polarization

from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D
from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D


# mimics a syned element
# class Toolbox(OpticalElement):  # to be written the 2D version....


class WOToolbox1D(OpticalElement, OpticalElementDecorator):
    def __init__(self,
                 name="Undefined",
                 shift_center=0.0,
                 crop_factor=1.0,
                 abscissas_factor=1.0,  # abscissas_factor abscissas: 0=N0, 1=Yes
                 change_photon_energy=0,  # 0=No, 1=Yes
                 new_photon_energy=0.0,  # if change_photon_energy, the new photon energy in eV
                 ):

        super().__init__(
                      name=name)

        self._shift_center = shift_center
        self._crop_factor = crop_factor
        self._abscissas_factor = abscissas_factor
        self._change_photon_energy = change_photon_energy
        self._new_photon_energy = new_photon_energy

        # support text contaning name of variable, help text and unit. Will be stored in self._support_dictionary
        self._set_support_text([
                    ("name",                       "Name" ,                                "" ),
                    ("crop_factor",                "Crop factor",                          "" ),
                    ("abscissas_factor",           "Abscissas factor",                     ""),
                    ("change_photon_energy",       "Change photon energy",                 "(flag)" ),
                    ("new_photon_energy",          "New photon energy",                    "(if change_photon_energy>0)" ),
            ] )

    def get_shift_center(self):
        return self._shift_center

    def get_crop_factor(self):
        return self._crop_factor

    def get_abscissas_factor(self):
        return self._abscissas_factor

    def applyOpticalElement(self, input_wavefront, parameters=None, element_index=None):
        # return wavefront

        sigma = input_wavefront.get_complex_amplitude(polarization=Polarization.SIGMA)
        try:
            pi = input_wavefront.get_complex_amplitude(polarization=Polarization.PI)
        except:
            pi = None

        xnew = input_wavefront.get_abscissas().copy()

        xnew += self._shift_center

        if self._crop_factor > 1: # pad
            pad_width = int (input_wavefront.size() * self.get_crop_factor() ) -  input_wavefront.size()
            step = xnew[1] - xnew[0]


            if pad_width > 0:
                pad_halfwidth = pad_width // 2
                xnew = numpy.concatenate((
                    numpy.flip( (numpy.arange(pad_halfwidth) + 1) * step * (-1) ) + xnew[0],
                    xnew,
                    (numpy.arange(pad_halfwidth) + 1) * step + xnew[-1],
                ))
                sigma = numpy.pad(sigma, (pad_halfwidth, pad_halfwidth), 'constant', constant_values=(0, 0))
                if pi is not None:
                    pi = numpy.pad(pi, (pad_halfwidth, pad_halfwidth), 'constant', constant_values=(0, 0))

        elif self._crop_factor < 1: #crop
            crop_halfwidth = int(input_wavefront.size() * (1.0 - self.get_crop_factor())  / 2)

            if crop_halfwidth > 0:
                xnew = xnew[crop_halfwidth:-crop_halfwidth]
                sigma = sigma[crop_halfwidth:-crop_halfwidth]
                if pi is not None:
                    pi = pi[crop_halfwidth:-crop_halfwidth]
        else:
            pass

        if self.get_abscissas_factor() != 1.0:
            xnew *= self.get_abscissas_factor()

        output_wavefront = GenericWavefront1D.initialize_wavefront_from_arrays(
            xnew, sigma, y_array_pi=pi, wavelength=input_wavefront.get_wavelength())

        if self._change_photon_energy:
            output_wavefront.set_photon_energy(self._new_photon_energy)

        return output_wavefront

    def to_python_code(self, data=None):
        txt  = ""
        txt += "\nfrom orangecontrib.esrf.wofry.util.toolbox import WOToolbox1D #TODO update"
        txt += "\n"

        txt += "\noptical_element = WOToolbox1D(name='%s',crop_factor=%g,abscissas_factor=%d,shift_center=%g,change_photon_energy=%d,new_photon_energy=%g)" % \
               (self.get_name(), self.get_crop_factor(), self.get_abscissas_factor(), self.get_shift_center(), self._change_photon_energy, self._new_photon_energy)

        txt += "\n"
        return txt

if __name__ == "__main__":

    import numpy
    from srxraylib.plot.gol import plot, plot_image


    #
    # 2D
    #
    if False:
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


    #
    # 1D
    #

    if True:

        input_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=-0.004, x_max=0.004, number_of_points=1000)
        input_wavefront.set_wavelength(1e-10)
        input_wavefront.set_gaussian(sigma_x=0.001, amplitude=1, shift=0)

        optical_element = WOToolbox1D(name='test', shift_center=0.002, crop_factor=0.6, abscissas_factor=1,
                                      change_photon_energy=0, new_photon_energy=0.0)


        # no drift in this element
        output_wavefront = optical_element.applyOpticalElement(input_wavefront)
        #
        # ---- plots -----
        #
        plot(input_wavefront.get_abscissas(), input_wavefront.get_intensity(),
            output_wavefront.get_abscissas(), output_wavefront.get_intensity(),
                   title='OPTICAL ELEMENT NR 1', legend=['input',
                                                         'output'])