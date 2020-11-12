
import numpy
from orangecontrib.esrf.syned.util.lens import Lens # TODO: from syned.beamline.optical_elements.lenses.lens import Lens

from syned.beamline.shape import Convexity, Direction
from syned.beamline.shape import SurfaceShape, Plane, Paraboloid, ParabolicCylinder, Sphere, SphericalCylinder
from syned.beamline.shape import BoundaryShape, Rectangle, Circle, Ellipse, MultiplePatch

from wofry.beamline.decorators import OpticalElementDecorator

from barc4ro.projected_thickness import proj_thick_2D_crl
import xraylib

class WOLens(Lens, OpticalElementDecorator):
    def __init__(self,
                 name="Undefined",
                 surface_shape1=None,
                 surface_shape2=None,
                 boundary_shape=None,
                 material="",
                 thickness=0.0):
        Lens.__init__(self, name=name,
                      surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                      boundary_shape=boundary_shape, material=material, thickness=thickness)

        self._keywords_at_creation = None

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):

        x, y, lens_thickness = self.get_surface_thickness_mesh(wavefront)

        photon_energy = wavefront.get_photon_energy()
        wave_length = wavefront.get_wavelength()

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

        amp_factors = numpy.sqrt(numpy.exp(-1.0 * att_coefficient * lens_thickness))
        phase_shifts = -1.0 * wavefront.get_wavenumber() * refraction_index_delta * lens_thickness

        output_wavefront = wavefront.duplicate()
        output_wavefront.rescale_amplitudes(amp_factors)
        output_wavefront.add_phase_shifts(phase_shifts)

        return output_wavefront


    def get_surface_thickness_mesh(self, wavefront):

        _foc_plane, _shape, _apert_h, _apert_v, _r_min, _n, _wall_thickness, _aperture= self.__get_barc_inputs()
        _axis_x = wavefront.get_coordinate_x()
        _axis_y = wavefront.get_coordinate_y()

        print("\n\n\n ==========  parameters recovered for barc4ro.proj_thick_2D_crl : ")
        print(">>> _aperture = ", _aperture)
        print(">>> _apert_h = ", _apert_h)
        print(">>> _apert_v = ", _apert_v)
        print(">>> _wall_thick:  min. wall thickness between 'holes' [m]= ", _wall_thickness)
        print(">>> _n: number of lenses (/holes) = ", _n)
        print(">>> _r_min: radius (on tip of parabola for parabolic shape) [m] = ", _r_min)
        print(">>> _shape: 1- parabolic, 2- circular (spherical) = ", _shape)
        print(">>> _foc_plane: plane of focusing: 1- horizontal, 2- vertical, 3- both = ", _foc_plane)
        print(">>> _axis_x : from, to, n = ", _axis_x.min(), _axis_x.max(), _axis_x.size)
        print(">>> _axis_y : from, to, n = ", _axis_y.min(), _axis_y.max(), _axis_y.size)

        try:
            x, y, lens_thickness = proj_thick_2D_crl(_foc_plane, _shape, _apert_h, _apert_v, _r_min, _n,
                         _wall_thick=_wall_thickness, _aperture=_aperture,
                         _nx=_axis_x.size, _ny=_axis_y.size,
                         _axis_x=_axis_x, _axis_y=_axis_y,
                         _xc=0, _yc=0,
                         _ang_rot_ex=0, _ang_rot_ey=0, _ang_rot_ez=0,
                         _offst_ffs_x=0, _offst_ffs_y=0,
                         _tilt_ffs_x=0, _tilt_ffs_y=0, _ang_rot_ez_ffs=0,
                         _wt_offst_ffs=0, _offst_bfs_x=0, _offst_bfs_y=0,
                         _tilt_bfs_x=0, _tilt_bfs_y=0, _ang_rot_ez_bfs=0, _wt_offst_bfs=0,
                         isdgr=False, project=True,)

            # print(">>> ", x.shape, y.shape, lens_thickness.shape)
            #
            # from srxraylib.plot.gol import plot_image
            # plot_image(1e6 * lens_thickness.T, 1e6 * x, 1e6 * y, title="Lens surface profile / um",
            #            xtitle="X / um", ytitle="Y / um")

        except:
            raise Exception("Error running barc4ro.proj_thick_2D_crl")

        return x, y, lens_thickness.T

    def __get_barc_inputs(self):

        if isinstance(self.get_surface_shape(index=0), Paraboloid) or \
                isinstance(self.get_surface_shape(index=0), Sphere) or \
                isinstance(self.get_surface_shape(index=0), Plane):
            _foc_plane = 3
        elif isinstance(self.get_surface_shape(index=0), ParabolicCylinder) or \
                isinstance(self.get_surface_shape(index=0), SphericalCylinder):
            if self.get_surface_shape(index=0).get_cylinder_direction() == Direction.TANGENTIAL:
                _foc_plane = 2
            elif self.get_surface_shape(index=0).get_cylinder_direction() == Direction.SAGITTAL:
                _foc_plane = 1
            else:
                raise Exception("Wrong _foc_plane value.")
        else:
            raise Exception("Not implemented surface shape")

        if isinstance(self.get_surface_shape(index=0), Paraboloid):
            _shape = 1
        elif isinstance(self.get_surface_shape(index=0), Plane):  # for the moment treated as large parabola
            _shape = 1
        elif isinstance(self.get_surface_shape(index=0), Sphere):
            _shape = 2
        else:
            raise Exception("Wrong _shape value")

        boundaries = self._boundary_shape.get_boundaries()

        #  So, in case of the 2D lens, the aperture can be rectangular with _apert_h and _apert_h,
        #  the case of a circular aperutre, both values must be given, but only _apert_h is considered.

        #     :param _aperture: specifies the type of aperture: circular or square
        #     :param _apert_h: horizontal aperture size [m]
        #     :param _apert_v: vertical aperture size [m]
        if isinstance(self._boundary_shape, Rectangle):
            _aperture = "r"
            _apert_h = boundaries[1] - boundaries[0]
            _apert_v = boundaries[3] - boundaries[2]
        elif isinstance(self._boundary_shape, Circle):
            _aperture = "c"
            _apert_h = 2 * boundaries[0]
            _apert_v = 2 * boundaries[0]
        elif isinstance(self._boundary_shape, Ellipse):
            _aperture = "c"
            _apert_h = 2 * (boundaries[1] - boundaries[0])
            _apert_v = 2 * (boundaries[3] - boundaries[2])  # not used by the library
        else:
            raise NotImplementedError("to be implemented")


        if isinstance(self.get_surface_shape(index=0), Paraboloid):
            _r_min = self.get_surface_shape(index=0).get_parabola_parameter()
        elif isinstance(self.get_surface_shape(index=0), Plane):
            _r_min = 1e18
        elif isinstance(self.get_surface_shape(index=0), Sphere):
            _r_min = self.get_surface_shape(index=0).get_radius()
        else:
            raise NotImplementedError()

        if isinstance(self.get_surface_shape(index=1), Plane):
            _n = 1
        else:
            _n = 2

        _wall_thickness = self.get_thickness()

        return _foc_plane, _shape, _apert_h, _apert_v, _r_min, _n, _wall_thickness, _aperture

    @classmethod
    def create_from_keywords(cls,
                             name="Real Lens",
                             number_of_curved_surfaces=2,
                             two_d_lens=0,
                             surface_shape=0,
                             wall_thickness=10e-6,
                             material="Be",
                             lens_radius=100e-6,
                             aperture_shape=0,
                             aperture_dimension_h=500e-6,
                             aperture_dimension_v=1000e-6,
                             ):
        if number_of_curved_surfaces == 0:
            surface_shape1 = Plane()
        else:
            if surface_shape == 0:
                if two_d_lens == 0:
                    surface_shape1 = Paraboloid(parabola_parameter=lens_radius, convexity=Convexity.DOWNWARD)
                elif two_d_lens == 1:
                    surface_shape1 = ParabolicCylinder(parabola_parameter=lens_radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.DOWNWARD)
                elif two_d_lens == 2:
                    surface_shape1 = ParabolicCylinder(parabola_parameter=lens_radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.UPWARD)
            elif surface_shape == 1:
                if two_d_lens == 0:
                    surface_shape1 = Sphere(radius=lens_radius, convexity=Convexity.DOWNWARD)
                elif two_d_lens == 1:
                    surface_shape1 = SphericalCylinder(radius=lens_radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.DOWNWARD)
                elif two_d_lens == 3:
                    surface_shape1 = SphericalCylinder(radius=lens_radius, cylinder_direction=Direction.SAGITTAL, convexity=Convexity.UPWARD)


        if number_of_curved_surfaces == 0:
            surface_shape2 = Plane()
        elif number_of_curved_surfaces == 1:
            surface_shape2 = Plane()
        elif number_of_curved_surfaces == 2:
            surface_shape2 = surface_shape1   #   not used!

        if aperture_shape == 0:
            boundary_shape = Circle(radius=0.5*aperture_dimension_v)
        elif aperture_shape == 1:
            boundary_shape = Rectangle(x_left=-0.5*aperture_dimension_h, x_right=0.5*aperture_dimension_h,
                                       y_bottom=-0.5*aperture_dimension_v, y_top=0.5*aperture_dimension_v)



        keywords_at_creation = {}
        keywords_at_creation["name"]                          = name
        keywords_at_creation["number_of_curved_surfaces"]     = number_of_curved_surfaces
        keywords_at_creation["two_d_lens"]                    = two_d_lens
        keywords_at_creation["surface_shape"]                 = surface_shape
        keywords_at_creation["wall_thickness"]                = wall_thickness
        keywords_at_creation["material"]                      = material
        keywords_at_creation["lens_radius"]                   = lens_radius
        keywords_at_creation["aperture_shape"]                = aperture_shape
        keywords_at_creation["aperture_dimension_h"]          = aperture_dimension_h
        keywords_at_creation["aperture_dimension_v"]          = aperture_dimension_v

        out = WOLens(name=name,
                      surface_shape1=surface_shape1,
                      surface_shape2=surface_shape2,
                      boundary_shape=boundary_shape,
                      thickness=wall_thickness,
                      material=material )

        out._keywords_at_creation = keywords_at_creation

        return out

    def to_python_code(self, do_plot=False):
        if self._keywords_at_creation is None:
            raise Exception("Python code autogenerated only if created with WOLens.create_from_keywords()")

        txt = ""
        txt += "\nfrom orangecontrib.esrf.wofry.util.lens import WOLens"
        txt += "\n"
        txt += "\noptical_element = WOLens.create_from_keywords("
        txt += "\n    name='%s',"                    % self._keywords_at_creation["name"]
        txt += "\n    number_of_curved_surfaces=%d," % self._keywords_at_creation["number_of_curved_surfaces"]
        txt += "\n    two_d_lens=%d,"                % self._keywords_at_creation["two_d_lens"]
        txt += "\n    surface_shape=%d,"             % self._keywords_at_creation["surface_shape"]
        txt += "\n    wall_thickness=%g,"            % self._keywords_at_creation["wall_thickness"]
        txt += "\n    material='%s',"                % self._keywords_at_creation["material"]
        txt += "\n    lens_radius=%g,"               % self._keywords_at_creation["lens_radius"]
        txt += "\n    aperture_shape=%d,"            % self._keywords_at_creation["aperture_shape"]
        txt += "\n    aperture_dimension_h=%g,"      % self._keywords_at_creation["aperture_dimension_h"]
        txt += "\n    aperture_dimension_v=%g)"      % self._keywords_at_creation["aperture_dimension_v"]
        txt += "\n"
        return txt


if __name__ == "__main__":
    pass
