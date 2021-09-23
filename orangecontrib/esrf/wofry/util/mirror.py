import numpy
from syned.beamline.optical_elements.mirrors.mirror import Mirror


#
from wofry.beamline.decorators import OpticalElementDecorator

from shadow4.optical_surfaces.s4_conic import S4Conic
from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D
from numba import jit, prange

@jit(nopython=True, parallel=True)
def goFromToSequential(field1, x1, y1, x2, y2, wavelength=1e-10, normalize_intensities=False):
    field2 = x2 * 0j
    wavenumber = numpy.pi * 2 / wavelength

    for i in prange(field2.size):
        r = numpy.sqrt(numpy.power(x1 - x2[i], 2) + numpy.power(y1 - y2[i], 2))
        field2[i] = (field1 * numpy.exp(1.j * wavenumber * r)).sum()

    if normalize_intensities:
        field2 *= numpy.sqrt((numpy.abs(field1) ** 2).sum() / (numpy.abs(field2) ** 2).sum())
    return field2

class WOMirror1D(Mirror, OpticalElementDecorator):
    def __init__(self,
                 name="Undefined",
                 surface_shape=None,
                 boundary_shape=None,
                 coating=None,
                 coating_thickness=None,
                 keywords_at_creation=None):

        Mirror.__init__(self, name=name,
                      surface_shape=surface_shape,
                      boundary_shape=boundary_shape,
                      coating=coating, coating_thickness=coating_thickness)

        self._keywords_at_creation = keywords_at_creation


    def get_height_profile(self, input_wavefront):


        shape                          = self._keywords_at_creation["shape"]
        p_focus                        = self._keywords_at_creation["p_focus"]
        q_focus                        = self._keywords_at_creation["q_focus"]
        grazing_angle_in               = self._keywords_at_creation["grazing_angle_in"]
        error_flag                     = self._keywords_at_creation["error_flag"]
        error_file                     = self._keywords_at_creation["error_file"]
        error_file_oversampling_factor = self._keywords_at_creation["error_file_oversampling_factor"]
        mirror_length                  = self._keywords_at_creation["mirror_length"]
        mirror_points                  = self._keywords_at_creation["mirror_points"]


        if error_flag == 0:  # no profile file
            x2_oe = numpy.linspace(-0.5 * mirror_length, 0.5 * mirror_length,
                                   mirror_points)  # x1 / numpy.sin(grazing_angle_in)
            y2_oe = numpy.zeros_like(x2_oe)
        else:
            a = numpy.loadtxt(error_file)
            x2_oe = a[:, 0]
            y2_oe = a[:, 1]

            if error_file_oversampling_factor != 1:
                xnew = numpy.linspace(x2_oe[0], x2_oe[-1], int(x2_oe.size * error_file_oversampling_factor))
                ynew = numpy.interp(xnew, x2_oe, y2_oe)
                x2_oe = xnew
                y2_oe = ynew


        if shape == 0:
            height = numpy.zeros_like(x2_oe)
        elif shape == 1:
            ccc = S4Conic.initialize_as_sphere_from_focal_distances(p_focus, q_focus, grazing_angle_in)
            height = ccc.height(x2_oe)

            print(ccc.info())
            y2_oe += height

        elif shape == 2:
            ccc = S4Conic.initialize_as_ellipsoid_from_focal_distances(p_focus, q_focus, grazing_angle_in)
            height = ccc.height(x2_oe)
            print(ccc.info())
            y2_oe += height
        elif shape == 3:
            ccc = S4Conic.initialize_as_paraboloid_from_focal_distances(p_focus, q_focus, grazing_angle_in)
            height = ccc.height(x2_oe)
            print(ccc.info())
            y2_oe += height
        else:
            raise Exception("Wrong shape")

        return x2_oe, y2_oe


    def get_footprint(self, input_wavefront):

        grazing_angle_in   = self._keywords_at_creation["grazing_angle_in"]
        p_distance         = self._keywords_at_creation["p_distance"]

        # TODO avoid recalculation??
        x2_oe, y2_oe = self.get_height_profile(input_wavefront)

        field2  = self.propagator1D_offaxis_up_to_mirror(input_wavefront, x2_oe, y2_oe,
                                                    p_distance, grazing_angle_in)

        return x2_oe, y2_oe, field2



    def applyOpticalElement(self, input_wavefront, parameters=None, element_index=None):


        grazing_angle_in   = self._keywords_at_creation["grazing_angle_in"]
        flip               = self._keywords_at_creation["flip"]
        p_distance         = self._keywords_at_creation["p_distance"]
        q_distance         = self._keywords_at_creation["q_distance"]
        zoom_factor        = self._keywords_at_creation["zoom_factor"]
        write_profile      = self._keywords_at_creation["write_profile"]

        x2_oe, y2_oe = self.get_height_profile(input_wavefront)

        output_wavefront, x2_oe, y2_oe, field2  = self.propagator1D_offaxis(input_wavefront, x2_oe, y2_oe,
                                                    p_distance, q_distance,
                                                    grazing_angle_in,
                                                    zoom_factor=zoom_factor,
                                                    normalize_intensities=True,
                                                    flip=flip)

        # output files
        if write_profile:
            f = open("reflector_profile1D.dat", "w")
            for i in range(x2_oe.size):
                f.write("%g %g\n" % (x2_oe[i], y2_oe[i]))
            f.close()
            print("File reflector_profile1D.dat written to disk.")

        return output_wavefront


    @classmethod
    def propagator1D_offaxis(cls, input_wavefront, x2_oe, y2_oe, p, q, theta_grazing_in, theta_grazing_out=None,
                             zoom_factor=1.0, normalize_intensities=False, flip=0):

        if theta_grazing_out is None:
            theta_grazing_out = theta_grazing_in

        x1 = input_wavefront.get_abscissas()
        field1 = input_wavefront.get_complex_amplitude()
        wavelength = input_wavefront.get_wavelength()

        if flip == 0:
            x1_oe = -p * numpy.cos(theta_grazing_in) + x1 * numpy.sin(theta_grazing_in)
            y1_oe =  p * numpy.sin(theta_grazing_in) + x1 * numpy.cos(theta_grazing_in)
        else:
            x1_oe =  p * numpy.cos(theta_grazing_in) + x1 * numpy.sin(theta_grazing_in)
            y1_oe =  p * numpy.sin(theta_grazing_in) - x1 * numpy.cos(theta_grazing_in)

        # field2 is the electric field in the mirror
        field2 = goFromToSequential(field1, x1_oe, y1_oe, x2_oe, y2_oe,
                                    wavelength=wavelength, normalize_intensities=normalize_intensities)

        x3 = x1 * zoom_factor

        if flip == 0:
            x3_oe = q * numpy.cos(theta_grazing_out) - x3 * numpy.sin(theta_grazing_out)
            y3_oe = q * numpy.sin(theta_grazing_out) + x3 * numpy.cos(theta_grazing_out)
        else:
            x3_oe = -q * numpy.cos(theta_grazing_out) - x3 * numpy.sin(theta_grazing_out)
            y3_oe =  q * numpy.sin(theta_grazing_out) - x3 * numpy.cos(theta_grazing_out)




        # field3 is the electric field in the image plane
        field3 = goFromToSequential(field2, x2_oe, y2_oe, x3_oe, y3_oe,
                                    wavelength=wavelength, normalize_intensities=normalize_intensities)


        output_wavefront = GenericWavefront1D.initialize_wavefront_from_arrays(x3, field3 / numpy.sqrt(zoom_factor),
                                                                                   wavelength=wavelength)

        return output_wavefront, x2_oe, y2_oe, field2

    @classmethod
    def propagator1D_offaxis_up_to_mirror(cls, input_wavefront, x2_oe, y2_oe, p, theta_grazing_in,
                                          normalize_intensities=False):


        x1 = input_wavefront.get_abscissas()
        field1 = input_wavefront.get_complex_amplitude()
        wavelength = input_wavefront.get_wavelength()

        x1_oe = -p * numpy.cos(theta_grazing_in) + x1 * numpy.sin(theta_grazing_in)
        y1_oe =  p * numpy.sin(theta_grazing_in) + x1 * numpy.cos(theta_grazing_in)

        # field2 is the electric field in the mirror
        field2 = goFromToSequential(field1, x1_oe, y1_oe, x2_oe, y2_oe,
                                    wavelength=wavelength, normalize_intensities=normalize_intensities)

        return field2


    @classmethod
    def create_from_keywords(cls,
                name="mirror 1D",
                shape=0,
                flip=0,
                p_focus=1.0,
                q_focus=1.0,
                grazing_angle_in=0.003,
                p_distance=1.0,
                q_distance=1.0,
                zoom_factor=1.0,
                error_flag=0,
                error_file="",
                error_file_oversampling_factor=1.0,
                mirror_length=1.0,
                mirror_points=100,
                write_profile=0,
                             ):

        keywords_at_creation = {}
        keywords_at_creation["name"]                           = name
        keywords_at_creation["shape"]                          = shape
        keywords_at_creation["flip"]                           = flip
        keywords_at_creation["p_focus"]                        = p_focus
        keywords_at_creation["q_focus"]                        = q_focus
        keywords_at_creation["grazing_angle_in"]               = grazing_angle_in
        keywords_at_creation["p_distance"]                     = p_distance
        keywords_at_creation["q_distance"]                     = q_distance
        keywords_at_creation["zoom_factor"]                    = zoom_factor
        keywords_at_creation["error_flag"]                     = error_flag
        keywords_at_creation["error_file"]                     = error_file
        keywords_at_creation["error_file_oversampling_factor"] = error_file_oversampling_factor
        keywords_at_creation["mirror_length"]                  = mirror_length
        keywords_at_creation["mirror_points"]                  = mirror_points
        keywords_at_creation["write_profile"]                  = write_profile

        out = WOMirror1D(name="Undefined",
                 surface_shape=None,
                 boundary_shape=None,
                 coating=None,
                 coating_thickness=None,
                 keywords_at_creation=keywords_at_creation)

        # out._keywords_at_creation = keywords_at_creation

        return out

    def to_python_code(self, do_plot=False):
        if self._keywords_at_creation is None:
            raise Exception("Python code autogenerated only if created with WOLens.create_from_keywords()")

        txt = "\n"
        txt += "\nfrom orangecontrib.esrf.wofry.util.mirror import WOMirror1D"
        txt += "\n"
        txt += "\noptical_element = WOMirror1D.create_from_keywords("
        txt += "\n    name='%s'," % self._keywords_at_creation["name"]
        txt += "\n    shape=%d," % self._keywords_at_creation["shape"]
        txt += "\n    flip=%d," % self._keywords_at_creation["flip"]
        txt += "\n    p_focus=%g," % self._keywords_at_creation["p_focus"]
        txt += "\n    q_focus=%g," % self._keywords_at_creation["q_focus"]
        txt += "\n    grazing_angle_in=%g," % self._keywords_at_creation["grazing_angle_in"]
        txt += "\n    p_distance=%g," % self._keywords_at_creation["p_distance"]
        txt += "\n    q_distance=%g," % self._keywords_at_creation["q_distance"]
        txt += "\n    zoom_factor=%g," % self._keywords_at_creation["zoom_factor"]
        txt += "\n    error_flag=%d," % self._keywords_at_creation["error_flag"]
        txt += "\n    error_file='%s'," % self._keywords_at_creation["error_file"]
        txt += "\n    error_file_oversampling_factor=%g," % self._keywords_at_creation["error_file_oversampling_factor"]
        txt += "\n    mirror_length=%g," % self._keywords_at_creation["mirror_length"]
        txt += "\n    mirror_points=%d," % self._keywords_at_creation["mirror_points"]
        txt += "\n    write_profile=%d)" % self._keywords_at_creation["write_profile"]
        txt += "\n"
        return txt

#
#
#


if __name__ == "__main__":

    womirror = WOMirror1D.create_from_keywords()
    print(womirror.info())

    print(womirror.to_python_code())
    for key in womirror._keywords_at_creation.keys():
        print(key, womirror._keywords_at_creation[key])


    from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D
    input_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=-0.0005, x_max=0.0005,
                                                                         number_of_points=1000)
    input_wavefront.set_photon_energy(10000)
    input_wavefront.set_spherical_wave(radius=13.73, center=0, complex_amplitude=complex(1, 0))

    output_wavefront = womirror.applyOpticalElement(input_wavefront=input_wavefront)

    from srxraylib.plot.gol import plot

    plot(input_wavefront.get_abscissas(), input_wavefront.get_intensity())
    plot(output_wavefront.get_abscissas(),output_wavefront.get_intensity())



