
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
        Lens.__init__(self, name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                      boundary_shape=boundary_shape, material=material, thickness=thickness)

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):

        print("\n\n\n>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        print("      MODIFY WAVEFRONT HERE......................")
        print(" element_index: ", element_index)
        print(" parameters: ", parameters)
        # print(" boundaries: ", boundaries)
        print(" info parameters: ", self.info())
        print("""
# def proj_thick_2D_crl(_foc_plane, _shape, _apert_h, _apert_v, _r_min, _n, _wall_thick=0, _xc=0, _yc=0, _nx=1001,
#                       _ny=1001,_ang_rot_ex=0, _ang_rot_ey=0, _ang_rot_ez=0, _offst_ffs_x=0, _offst_ffs_y=0,
#                       _tilt_ffs_x=0, _tilt_ffs_y=0, _ang_rot_ez_ffs=0, _wt_offst_ffs=0, _offst_bfs_x=0, _offst_bfs_y=0,
#                       _tilt_bfs_x=0, _tilt_bfs_y=0, _ang_rot_ez_bfs=0,_wt_offst_bfs=0, isdgr=False, project=True,
#                       _axis_x=None, _axis_y=None, _aperture=None):
#
# _foc_plane: plane of focusing: 1- horizontal, 2- vertical, 3- both
# _shape: 1- parabolic, 2- circular (spherical), 3- elliptical (not implemented), 4- Cartesian oval (not implemented)
# _apert_h: horizontal aperture size [m]
# _apert_v: vertical aperture size [m]
# _r_min: radius (on tip of parabola for parabolic shape) [m]
# _n: number of lenses (/"holes")
# _wall_thick:  min. wall thickness between "holes" [m]
# _xc: horizontal coordinate of center [m]
# _yc: vertical coordinate of center [m]
# _nx: number of points vs horizontal position to represent the transmission element
# _ny: number of points vs vertical position to represent the transmission element
# _ang_rot_ex: angle [rad] of full CRL rotation about horizontal axis
# _ang_rot_ey: angle [rad] of full CRL rotation about vertical axis
# _ang_rot_ez: angle [rad] of full CRL rotation about longitudinal axis
# _offst_ffs_x: lateral offset in the horizontal axis of the front focusing surface [m]
# _offst_ffs_y: lateral offset in the vertical axis of the front focusing surface [m]
# _tilt_ffs_x: angle [rad] of the parabolic front surface rotation about horizontal axis
# _tilt_ffs_y: angle [rad] of the parabolic front surface rotation about horizontal axis
# _ang_rot_ez_ffs: angle [rad] of the parabolic front surface rotation about the longitudinal axis
# _wt_offst_ffs: excess penetration [m] of the front parabola to be added to _wall_thick
# _offst_bfs_x: lateral offset in the horizontal axis of the back focusing surface [m]
# _offst_bfs_y: lateral offset in the back axis of the front focusing surface [m]
# _tilt_bfs_x: angle [rad] of the parabolic front back rotation about horizontal axis
# _tilt_bfs_y: angle [rad] of the parabolic front back rotation about horizontal axis
# _ang_rot_ez_bfs: angle [rad] of the parabolic back surface rotation about the longitudinal axis
# _wt_offst_bfs: excess penetration [m] of the back parabola to be added to _wall_thick (negative or positive values)
# isdgr: boolean for determining if angles are in degree or in radians (default)
# project: boolean. project=True necessary for using the profile as a transmission element
# _axis_x: forces the lens to be calculated on a given grid - avoids having to interpolate different calculations to the same grid
# _axis_y: forces the lens to be calculated on a given grid - avoids having to interpolate different calculations to the same grid
# _aperture: specifies the type of aperture: circular or square
#     :return: thickness profile    
""")
        print(">>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\n\n")

        print("\n\n\n ==========  parameters recovered for barc4ro.proj_thick_2D_crl : ")
        # _foc_plane, _shape, _apert_h, _apert_v, _r_min, _n, _wall_thick = 0, _xc = 0, _yc = 0, _nx = 1001,
        #                       _ny=1001,_ang_rot_ex=0, _ang_rot_ey=0, _ang_rot_ez=0, _offst_ffs_x=0, _offst_ffs_y=0,
        #                       _tilt_ffs_x=0, _tilt_ffs_y=0, _ang_rot_ez_ffs=0, _wt_offst_ffs=0, _offst_bfs_x=0, _offst_bfs_y=0,
        #                       _tilt_bfs_x=0, _tilt_bfs_y=0, _ang_rot_ez_bfs=0,_wt_offst_bfs=0, isdgr=False, project=True,
        #                       _axis_x=None, _axis_y=None, _aperture=None
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



        if isinstance(self.get_surface_shape(index=0), Paraboloid):
            _shape = 1
        elif isinstance(self.get_surface_shape(index=0), Plane): # for the moment treated as large parabola
            _shape = 1
        elif isinstance(self.get_surface_shape(index=0), Sphere):
            _shape = 2
        else:
            print(">>>>>", self.get_surface_shape(index=0))
            raise Exception("Wrong _shape value" )





        boundaries = self._boundary_shape.get_boundaries()

        #  So, in case of the 2D lens, the aperture can be rectangular with _apert_h and _apert_h,
        #  the case of a circular aperutre, both values must be given, but only _apert_h is considered.
        if isinstance(self._boundary_shape, Rectangle):
            _aperture = "r"
            _apert_h = boundaries[1] - boundaries[0]
            _apert_v = boundaries[3] - boundaries[2]
            # wavefront.clip_square(boundaries[0], boundaries[1], boundaries[2], boundaries[3])
        elif isinstance(self._boundary_shape, Circle):
            _aperture = "c"
            _apert_h = 2 * boundaries[0]
            _apert_v = 2 * boundaries[0]
            # wavefront.clip_circle(boundaries[0], boundaries[1], boundaries[2])
        elif isinstance(self._boundary_shape, Ellipse):
            _aperture = "c"
            _apert_h = 2 * (boundaries[1] - boundaries[0])
            _apert_v = 2 * (boundaries[3] - boundaries[2])  # not used by the library
            # wavefront.clip_circle(boundaries[0], boundaries[1], boundaries[2])
        else:
            raise NotImplementedError("to be implemented")


        #     :param _aperture: specifies the type of aperture: circular or square
        #     :param _apert_h: horizontal aperture size [m]
        #     :param _apert_v: vertical aperture size [m]
        #     :param _xc: horizontal coordinate of center [m]
        #     :param _yc: vertical coordinate of center [m]


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

        _axis_x = wavefront.get_coordinate_x()
        _axis_y = wavefront.get_coordinate_y()

        print("_aperture = ", _aperture)
        print("_apert_h = ", _apert_h)
        print("_apert_v = ", _apert_v)
        print("_axis_x : from, to, n = ", _axis_x.min(), _axis_x.max(), _axis_x.size)
        print("_axis_y : from, to, n = ", _axis_y.min(), _axis_y.max(), _axis_y.size)
        print("_wall_thick:  min. wall thickness between 'holes' [m]= ", _wall_thickness)
        print("_n: number of lenses (/holes) = ", _n)
        print("_r_min: radius (on tip of parabola for parabolic shape) [m] = ", _r_min)
        print("_shape: 1- parabolic, 2- circular (spherical) = ", _shape)
        print("_foc_plane: plane of focusing: 1- horizontal, 2- vertical, 3- both = ", _foc_plane)

        try:
            x, y, lens_thickness = proj_thick_2D_crl(_foc_plane, _shape, _apert_h, _apert_v, _r_min, _n,
                    _wall_thick=_wall_thickness, _xc=0, _yc=0, _nx=_axis_x.size, _ny=_axis_y.size,
                    _ang_rot_ex=0, _ang_rot_ey=0, _ang_rot_ez=0,
                    _offst_ffs_x=0, _offst_ffs_y=0,
                    _tilt_ffs_x=0, _tilt_ffs_y=0, _ang_rot_ez_ffs=0,
                    _wt_offst_ffs=0, _offst_bfs_x=0, _offst_bfs_y=0,
                    _tilt_bfs_x=0, _tilt_bfs_y=0, _ang_rot_ez_bfs=0, _wt_offst_bfs=0, isdgr=False, project=True,
                    _axis_x=_axis_x, _axis_y=_axis_y, _aperture=_aperture)

            print(x.shape, y.shape, lens_thickness.shape)
            from srxraylib.plot.gol import plot_image
            plot_image(1e6 * lens_thickness.T, 1e6 * x, 1e6 * y, title="Lens surface profile / um",
                       xtitle="X / um", ytitle="Y / um")

        except:
            print("\n\n\n\n\n>>>>>>>> ERROR IN proj_thick_2D_crl\n\n\n\n\n\n")
            return wavefront

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


        print("\n\n\n ==========  parameters recovered from xraylib : ")
        print("Element: %s" % element)
        print("        density = %g " % density)

        refraction_index = xraylib.Refractive_Index(element, photon_energy/1000, density)
        refraction_index_delta = 1 - refraction_index.real
        att_coefficient = 4*numpy.pi * (xraylib.Refractive_Index(element, photon_energy/1000, density)).imag / wave_length
        print("Photon energy = %g eV" % (photon_energy))
        print("Refracion index delta = %g " % (refraction_index_delta))
        print("Attenuation coeff mu = %g m^-1" % (att_coefficient))

        print()

        amp_factors = numpy.sqrt(numpy.exp(-1.0 * att_coefficient * lens_thickness))
        phase_shifts = -1.0 * wavefront.get_wavenumber() * refraction_index_delta * lens_thickness

        output_wavefront = wavefront.duplicate()
        output_wavefront.rescale_amplitudes(amp_factors.T)
        output_wavefront.add_phase_shifts(phase_shifts.T)

        return output_wavefront


    # def is_plano(self):
    #     if isinstance(self.get_surface_shape(index=1), Plane):
    #         return True
    #     else:
    #         return False
    #
    # @classmethod
    # def create_biconvex_2d_paraboloid_lens(cls, name="", radius=1.0, material="", thickness=0.0):
    #     surface_shape1 = Paraboloid(parabola_parameter=2 * radius, convexity = Convexity.UPWARD)
    #     surface_shape2 = Paraboloid(parabola_parameter=2 * radius, convexity=Convexity.DOWNWARD)
    #     return WOLens(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
    #                 thickness=thickness, material=material)
    #
    # @classmethod
    # def create_planoconvex_2d_paraboloid_lens(cls, name="", radius=1.0, material="", thickness=0.0):
    #     surface_shape1 = Paraboloid(parabola_parameter=2 * radius, convexity = Convexity.UPWARD)
    #     surface_shape2 = Plane()
    #     return WOLens(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
    #                 thickness=thickness, material=material)
    #
    # @classmethod
    # def create_biconvex_2d_parabolic_cylinder_lens(cls, name="", radius=1.0, material="", thickness=0.0):
    #     surface_shape1 = ParabolicCylinder(parabola_parameter=radius, cylinder_direction=Direction.TANGENTIAL, convexity = Convexity.UPWARD)
    #     surface_shape2 = ParabolicCylinder(parabola_parameter=radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.DOWNWARD)
    #     return WOLens(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
    #                 thickness=thickness, material=material)
    #
    # @classmethod
    # def create_planoconvex_2d_parabolic_cylinder_lens(cls, name="", radius=1.0, material="", thickness=0.0):
    #     surface_shape1 = ParabolicCylinder(parabola_parameter=radius, cylinder_direction=Direction.TANGENTIAL, convexity = Convexity.UPWARD)
    #     surface_shape2 = Plane()
    #     return WOLens(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
    #                 thickness=thickness, material=material)



if __name__ == "__main__":
    l = WOLens.create_biconvex_2d_parabolic_cylinder_lens(radius=10e-6)
    print(l.info())