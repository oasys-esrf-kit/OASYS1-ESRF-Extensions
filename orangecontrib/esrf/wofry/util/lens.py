
import numpy
from orangecontrib.esrf.syned.util.lens import Lens # TODO: from syned.beamline.optical_elements.lenses.lens import Lens

from syned.beamline.shape import Convexity, Direction
from syned.beamline.shape import SurfaceShape, Plane, Paraboloid, ParabolicCylinder, Sphere, SphericalCylinder
from syned.beamline.shape import BoundaryShape, Rectangle, Circle, Ellipse, MultiplePatch

from wofry.beamline.decorators import OpticalElementDecorator

from barc4ro.projected_thickness import proj_thick_2D_crl, proj_thick_1D_crl
from scipy import interpolate
import scipy.constants as codata
import xraylib

class WOLens(Lens, OpticalElementDecorator):
    def __init__(self,
                 name="Undefined",
                 surface_shape1=None,
                 surface_shape2=None,
                 boundary_shape=None,
                 material="",
                 thickness=0.0,
                 keywords_at_creation=None):
        Lens.__init__(self, name=name,
                      surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                      boundary_shape=boundary_shape, material=material, thickness=thickness)

        self._keywords_at_creation = keywords_at_creation

    def get_refraction_index(self, photon_energy=10000.0):

        wave_length = codata.h * codata.c / codata.e / photon_energy

        if self.get_material() == "External":
            refraction_index_delta = self._keywords_at_creation["refraction_index_delta"]
            att_coefficient = self._keywords_at_creation["att_coefficient"]
            print("\n\n\nRefracion index delta = %g " % (refraction_index_delta))
            print("Attenuation coeff mu = %g m^-1" % (att_coefficient))
            return refraction_index_delta, att_coefficient

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

        x, y, lens_thickness = self.get_surface_thickness_mesh(wavefront)

        photon_energy = wavefront.get_photon_energy()

        #
        print("\n\n\n ==========  parameters in use : ")

        refraction_index_delta, att_coefficient = \
            self.get_refraction_index(photon_energy=photon_energy)

        # this is for info...
        number_of_curved_surfaces = self._keywords_at_creation["number_of_curved_surfaces"]
        lens_radius = self._keywords_at_creation["lens_radius"]
        n_lenses = self._keywords_at_creation["n_lenses"]

        print("\n\nRadius of curvature R = %g um" % (1e6 * lens_radius))
        print("Number of lenses N: %d" % n_lenses)
        print("Number of curved refractive surfaces in a lens Nd = %d" % (number_of_curved_surfaces))
        if number_of_curved_surfaces != 0:
            F = lens_radius / (number_of_curved_surfaces * n_lenses * refraction_index_delta)
            print("Focal distance F = R / (Nd N delta) = %g m" % (F))
        # end info...


        amp_factors = numpy.exp(-1.0 * att_coefficient * lens_thickness / 2) # factor of 2 because it is amplitude
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

        lens_thickness *= self._keywords_at_creation["n_lenses"]

        return x, y, lens_thickness

    def __get_barc_inputs(self):

    #     :param _foc_plane: plane of focusing: 1- horizontal, 2- vertical, 3- both
        if isinstance(self.get_surface_shape(index=0), ParabolicCylinder) or \
                isinstance(self.get_surface_shape(index=0), SphericalCylinder):
            if self.get_surface_shape(index=0).get_cylinder_direction() == Direction.TANGENTIAL:
                _foc_plane = 2
            elif self.get_surface_shape(index=0).get_cylinder_direction() == Direction.SAGITTAL:
                _foc_plane = 1
            else:
                raise Exception("Wrong _foc_plane value.")
        elif isinstance(self.get_surface_shape(index=0), Paraboloid) or \
                isinstance(self.get_surface_shape(index=0), Sphere) or \
                isinstance(self.get_surface_shape(index=0), Plane):
            _foc_plane = 3
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
                             refraction_index_delta=5.3e-07,
                             att_coefficient=0.00357382,
                             lens_radius=100e-6,
                             n_lenses=1,
                             aperture_shape=0,
                             aperture_dimension_h=500e-6,
                             aperture_dimension_v=1000e-6,
                             ):
        if number_of_curved_surfaces == 0:
            surface_shape1 = Plane()
        else:
            #     :param _foc_plane: plane of focusing: 1- horizontal, 2- vertical, 3- both
            if surface_shape == 0:
                if two_d_lens == 0:
                    surface_shape1 = Paraboloid(parabola_parameter=lens_radius, convexity=Convexity.DOWNWARD)
                elif two_d_lens == 1:
                    surface_shape1 = ParabolicCylinder(parabola_parameter=lens_radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.DOWNWARD)
                elif two_d_lens == 2:
                    surface_shape1 = ParabolicCylinder(parabola_parameter=lens_radius, cylinder_direction=Direction.SAGITTAL, convexity=Convexity.UPWARD)
            elif surface_shape == 1:
                if two_d_lens == 0:
                    surface_shape1 = Sphere(radius=lens_radius, convexity=Convexity.DOWNWARD)
                elif two_d_lens == 1:
                    surface_shape1 = SphericalCylinder(radius=lens_radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.DOWNWARD)
                elif two_d_lens == 2:
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
        keywords_at_creation["refraction_index_delta"]        = refraction_index_delta
        keywords_at_creation["att_coefficient"]               = att_coefficient
        keywords_at_creation["lens_radius"]                   = lens_radius
        keywords_at_creation["n_lenses"]                      = n_lenses
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
        if self._keywords_at_creation["material"] == "External":
            txt += "\n    refraction_index_delta=%g, # used if material='External'" % self._keywords_at_creation["refraction_index_delta"]
            txt += "\n    att_coefficient=%g, # used if material='External'"        % self._keywords_at_creation["att_coefficient"]
        txt += "\n    lens_radius=%g,"               % self._keywords_at_creation["lens_radius"]
        txt += "\n    n_lenses=%g,"                  % self._keywords_at_creation["n_lenses"]
        txt += "\n    aperture_shape=%d,"            % self._keywords_at_creation["aperture_shape"]
        txt += "\n    aperture_dimension_h=%g,"      % self._keywords_at_creation["aperture_dimension_h"]
        txt += "\n    aperture_dimension_v=%g)"      % self._keywords_at_creation["aperture_dimension_v"]
        txt += "\n"
        return txt

#
#
#

class WOLens1D(Lens, OpticalElementDecorator):
    def __init__(self,
                 name="Undefined",
                 surface_shape1=None,
                 surface_shape2=None,
                 boundary_shape=None,
                 material="",
                 thickness=0.0,
                 keywords_at_creation=None):
        WOLens.__init__(self, name=name,
                      surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                      boundary_shape=boundary_shape, material=material, thickness=thickness)

        self._keywords_at_creation = keywords_at_creation


    def get_surface_thickness_mesh(self, input_wavefront):

        shape = self._keywords_at_creation["shape"                         ]
        radius = self._keywords_at_creation["radius"                        ]
        lens_aperture = self._keywords_at_creation["lens_aperture"                 ]
        wall_thickness = self._keywords_at_creation["wall_thickness"                ]
        number_of_curved_surfaces  = self._keywords_at_creation["number_of_curved_surfaces" ]
        n_lenses = self._keywords_at_creation["n_lenses"                      ]
        error_flag = self._keywords_at_creation["error_flag"                    ]
        error_file = self._keywords_at_creation["error_file"                    ]
        error_edge_management = self._keywords_at_creation["error_edge_management"         ]
        write_profile_flag = self._keywords_at_creation["write_profile_flag"]
        write_profile = self._keywords_at_creation["write_profile"                 ]
        if self._keywords_at_creation["mis_flag"]:
            xc = self._keywords_at_creation["xc"                            ]
            ang_rot = self._keywords_at_creation["ang_rot"                       ]
            wt_offset_ffs = self._keywords_at_creation["wt_offset_ffs"                 ]
            offset_ffs = self._keywords_at_creation["offset_ffs"                    ]
            tilt_ffs = self._keywords_at_creation["tilt_ffs"                      ]
            wt_offset_bfs = self._keywords_at_creation["wt_offset_bfs"                 ]
            offset_bfs = self._keywords_at_creation["offset_bfs"                    ]
            tilt_bfs = self._keywords_at_creation["tilt_bfs"                      ]
        else:
            xc            = 0
            ang_rot       = 0
            wt_offset_ffs = 0
            offset_ffs    = 0
            tilt_ffs      = 0
            wt_offset_bfs = 0
            offset_bfs    = 0
            tilt_bfs      = 0

        abscissas = input_wavefront.get_abscissas().copy()
        abscissas_on_lens = abscissas

        n_ref_lens = number_of_curved_surfaces

        if n_ref_lens == 0:
            lens_thickness = numpy.full_like(abscissas_on_lens, wall_thickness)
        else:
            if shape == 0:  # Flat
                lens_thickness = numpy.full_like(abscissas_on_lens, wall_thickness)

            elif shape == 1:  # Parabolic

                # focus_length = radius / (n_lenses * n_ref_lens * refraction_index_delta)

                # Implementation of barc4ro
                x_2, lens_thickness = proj_thick_1D_crl(shape, lens_aperture, radius,
                                                        _n=n_ref_lens,
                                                        _wall_thick=wall_thickness,
                                                        _xc=xc,
                                                        _nx=100,
                                                        _ang_rot_ex=ang_rot,
                                                        _offst_ffs_x=offset_ffs,
                                                        _tilt_ffs_x=tilt_ffs,
                                                        _wt_offst_ffs=wt_offset_ffs,
                                                        _offst_bfs_x=offset_bfs,
                                                        _tilt_bfs_x=tilt_bfs,
                                                        _wt_offst_bfs=wt_offset_bfs,
                                                        isdgr=False,
                                                        project=True,
                                                        _axis=abscissas)

            elif shape == 2:  # Circular
                lens_thickness = n_ref_lens * (
                            numpy.abs(radius) - numpy.sqrt(radius ** 2 - abscissas_on_lens ** 2)) + wall_thickness
                bound = 0.5 * lens_aperture
                if radius < bound: bound = radius
                for i, x in enumerate(abscissas_on_lens):
                    if (x < -bound) or (x > bound):
                        lens_thickness[i] = 0
                for i, x in enumerate(abscissas_on_lens):
                    if (x < -bound) or (x > bound):
                        lens_thickness[i] = lens_thickness.max()

        lens_thickness *= n_lenses

        if error_flag:
            a = numpy.loadtxt(error_file)  # extrapolation
            if error_edge_management == 0:
                finterpolate = interpolate.interp1d(a[:, 0], a[:, 1],
                                                    fill_value="extrapolate")  # fill_value=(0,0),bounds_error=False)
            elif error_edge_management == 1:
                finterpolate = interpolate.interp1d(a[:, 0], a[:, 1], fill_value=(0, 0), bounds_error=False)
            else:  # crop
                raise Exception("Bad value of error_edge_management")
            thickness_interpolated = finterpolate(abscissas_on_lens)
            lens_thickness += thickness_interpolated

        # output files
        if write_profile_flag:
            f = open(write_profile, "w")
            for i in range(lens_thickness.size):
                f.write("%g %g\n" % (abscissas_on_lens[i], lens_thickness[i]))
            f.close()
            print("File %s written to disk." % write_profile)

        return abscissas_on_lens, lens_thickness


    def get_refraction_index(self, photon_energy=10000.0):

        wave_length = codata.h * codata.c / codata.e / photon_energy

        if self.get_material() == "External":
            refraction_index_delta = self._keywords_at_creation["refraction_index_delta"]
            att_coefficient = self._keywords_at_creation["att_coefficient"]
            print("\n\n\nRefracion index delta = %g " % (refraction_index_delta))
            print("Attenuation coeff mu = %g m^-1" % (att_coefficient))
            return refraction_index_delta, att_coefficient

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


    def applyOpticalElement(self, input_wavefront, parameters=None, element_index=None):

        #
        print("\n\n\n ==========  parameters in use : ")

        refraction_index_delta, att_coefficient = \
            self.get_refraction_index(input_wavefront.get_photon_energy())

        # this is for info...
        radius = self._keywords_at_creation["radius"                        ]
        number_of_curved_surfaces  = self._keywords_at_creation["number_of_curved_surfaces" ]

        n_lenses = self._keywords_at_creation["n_lenses"                      ]
        F = radius / (number_of_curved_surfaces * n_lenses * refraction_index_delta)

        print("\n\nRadius of curvature R = %g um" % (1e6 * radius))
        print("Number of lenses N: %d" % n_lenses)
        print("Number of curved refractive surfaces in a lens Nd = %d" % (number_of_curved_surfaces))
        print("Focal distance F = R / (Nd N delta) = %g m" % (F))
        # end info.



        error_flag = self._keywords_at_creation["error_flag"                    ]
        error_file = self._keywords_at_creation["error_file"                    ]
        error_edge_management = self._keywords_at_creation["error_edge_management"         ]

        output_wavefront = input_wavefront.duplicate()
        abscissas_on_lens, lens_thickness = self.get_surface_thickness_mesh(input_wavefront=input_wavefront)

        amp_factors = numpy.exp(-1.0 * att_coefficient * lens_thickness / 2) # factor of 2 because it is amplitude
        phase_shifts = -1.0 * output_wavefront.get_wavenumber() * refraction_index_delta * lens_thickness

        output_wavefront.rescale_amplitudes(amp_factors)
        output_wavefront.add_phase_shifts(phase_shifts)

        if error_flag:
            a = numpy.loadtxt(error_file)  # extrapolation
            # profile_limits = a[-1, 0] - a[0, 0]
            profile_limits_projected = a[-1, 0] - a[0, 0]
            wavefront_dimension = output_wavefront.get_abscissas()[-1] - output_wavefront.get_abscissas()[0]
            # print("profile deformation dimension: %f m"%(profile_limits))
            print("profile deformation dimension: %f um" % (1e6 * profile_limits_projected))
            print("wavefront window dimension: %f um" % (1e6 * wavefront_dimension))

            if wavefront_dimension <= profile_limits_projected:
                print("Wavefront window inside error profile domain: no action needed")
            else:
                if error_edge_management == 0:
                    print("Profile deformation extrapolated to fit wavefront dimensions")
                else:
                    output_wavefront.clip(a[0, 0], a[-1, 0])
                    print("Wavefront clipped to limits of deformation profile")

        return output_wavefront

    @classmethod
    def create_from_keywords(cls,
                             name                           ="Real Lens 1D",
                             shape                          =1,
                             radius                         =0.0005,
                             lens_aperture                  =0.001,
                             wall_thickness                 =5e-5,
                             material                       ="Be",
                             refraction_index_delta         =5.3e-07,
                             att_coefficient                =0.00357382,
                             number_of_curved_surfaces      =2,
                             n_lenses                       =1,
                             error_flag                     =0,
                             error_file                     ="",
                             error_edge_management          =0,
                             write_profile_flag             =0,
                             write_profile                  ="",
                             mis_flag                       =0,
                             xc                             =0,
                             ang_rot                        =0,
                             wt_offset_ffs                  =0,
                             offset_ffs                     =0,
                             tilt_ffs                       =0,
                             wt_offset_bfs                  =0,
                             offset_bfs                     =0,
                             tilt_bfs                       =0,
                             ):


        keywords_at_creation = {}

        # keywords_at_creation["name"                          ] = name
        keywords_at_creation["shape"                         ] = shape
        keywords_at_creation["radius"                        ] = radius
        keywords_at_creation["lens_aperture"                 ] = lens_aperture
        keywords_at_creation["wall_thickness"                ] = wall_thickness
        # keywords_at_creation["material"                      ] = material
        keywords_at_creation["refraction_index_delta"        ] = refraction_index_delta
        keywords_at_creation["att_coefficient"               ] = att_coefficient
        keywords_at_creation["number_of_curved_surfaces" ]     = number_of_curved_surfaces
        keywords_at_creation["n_lenses"                      ] = n_lenses
        keywords_at_creation["error_flag"                    ] = error_flag
        keywords_at_creation["error_file"                    ] = error_file
        keywords_at_creation["error_edge_management"         ] = error_edge_management
        keywords_at_creation["write_profile_flag"            ] = write_profile_flag
        keywords_at_creation["write_profile"                 ] = write_profile
        keywords_at_creation["mis_flag"                      ] = mis_flag
        keywords_at_creation["xc"                            ] = xc
        keywords_at_creation["ang_rot"                       ] = ang_rot
        keywords_at_creation["wt_offset_ffs"                 ] = wt_offset_ffs
        keywords_at_creation["offset_ffs"                    ] = offset_ffs
        keywords_at_creation["tilt_ffs"                      ] = tilt_ffs
        keywords_at_creation["wt_offset_bfs"                 ] = wt_offset_bfs
        keywords_at_creation["offset_bfs"                    ] = offset_bfs
        keywords_at_creation["tilt_bfs"                      ] = tilt_bfs


        return WOLens1D(name=name, material=material, thickness=wall_thickness, keywords_at_creation=keywords_at_creation)

    def to_python_code(self):
        if self._keywords_at_creation is None:
            raise Exception("Python code autogenerated only if created with WOLens.create_from_keywords()")

        txt = ""
        txt += "\nfrom orangecontrib.esrf.wofry.util.lens import WOLens1D"
        txt += "\n"
        txt += "\noptical_element = WOLens1D.create_from_keywords("
        txt += "\n    name='%s'," % self.get_name()
        txt += "\n    shape=%d," % self._keywords_at_creation["shape"]
        txt += "\n    radius=%g," % self._keywords_at_creation["radius"]
        txt += "\n    lens_aperture=%g," % self._keywords_at_creation["lens_aperture"]
        txt += "\n    wall_thickness=%g," % self._keywords_at_creation["wall_thickness"]
        txt += "\n    material='%s'," % self.get_material()
        if self.get_material() == "External":
            txt += "\n    refraction_index_delta=%g, # used if material='External'" % self._keywords_at_creation["refraction_index_delta"]
            txt += "\n    att_coefficient=%g, # used if material='External'" % self._keywords_at_creation["att_coefficient"]
        txt += "\n    number_of_curved_surfaces=%d," % self._keywords_at_creation["number_of_curved_surfaces"]
        txt += "\n    n_lenses=%d," % self._keywords_at_creation["n_lenses"]
        txt += "\n    error_flag=%d," % self._keywords_at_creation["error_flag"]
        txt += "\n    error_file='%s'," % self._keywords_at_creation["error_file"]
        txt += "\n    error_edge_management=%d," % self._keywords_at_creation["error_edge_management"]
        txt += "\n    write_profile_flag=%d," % self._keywords_at_creation["write_profile_flag"]
        txt += "\n    write_profile='%s'," % self._keywords_at_creation["write_profile"]
        txt += "\n    mis_flag=%d," % self._keywords_at_creation["mis_flag"]
        txt += "\n    xc=%g," % self._keywords_at_creation["xc"]
        txt += "\n    ang_rot=%g," % self._keywords_at_creation["ang_rot"]
        txt += "\n    wt_offset_ffs=%g," % self._keywords_at_creation["wt_offset_ffs"]
        txt += "\n    offset_ffs=%g," % self._keywords_at_creation["offset_ffs"]
        txt += "\n    tilt_ffs=%g," % self._keywords_at_creation["tilt_ffs"]
        txt += "\n    wt_offset_bfs=%g," % self._keywords_at_creation["wt_offset_bfs"]
        txt += "\n    offset_bfs=%g," % self._keywords_at_creation["offset_bfs"]
        txt += "\n    tilt_bfs=%g)" % self._keywords_at_creation["tilt_bfs"]
        txt += "\n"
        return txt

if __name__ == "__main__":
    pass

    # wolens = WOLens1D.create_from_keywords()
    # print(wolens.info())
    # for key in wolens._keywords_at_creation.keys():
    #     print(key, wolens._keywords_at_creation[key])
    #
    #
    # from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D
    # input_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=-0.0005, x_max=0.0005,
    #                                                                      number_of_points=1000)
    # input_wavefront.set_photon_energy(10000)
    # input_wavefront.set_spherical_wave(radius=13.73, center=0, complex_amplitude=complex(1, 0))
    #
    # output_wavefront = wolens.applyOpticalElement(input_wavefront=input_wavefront)
    #
    # from srxraylib.plot.gol import plot
    #
    # plot(input_wavefront.get_abscissas(), input_wavefront.get_intensity())
    # plot(output_wavefront.get_abscissas(),output_wavefront.get_intensity())



    # wolens2d = WOLens.create_from_keywords(name='Real Lens 2D',
    # number_of_curved_surfaces=2,
    # two_d_lens=2,
    # surface_shape=0,
    # wall_thickness=5e-05,
    # material='Be',
    # lens_radius=0.0006419,
    # n_lenses=1,
    # aperture_shape=1,
    # aperture_dimension_h=0.0002,
    # aperture_dimension_v=0.001)
    #
    # _foc_plane, _shape, _apert_h, _apert_v, _r_min, _n, _wall_thickness, _aperture = wolens2d.get_barc_inputs()
    #
    # print("\n\n\n ==========  parameters recovered for barc4ro.proj_thick_2D_crl : ")
    # print(">>> _aperture = ", _aperture)
    # print(">>> _apert_h = ", _apert_h)
    # print(">>> _apert_v = ", _apert_v)
    # print(">>> _wall_thick:  min. wall thickness between 'holes' [m]= ", _wall_thickness)
    # print(">>> _n: number of lenses (/holes) = ", _n)
    # print(">>> _r_min: radius (on tip of parabola for parabolic shape) [m] = ", _r_min)
    # print(">>> _shape: 1- parabolic, 2- circular (spherical) = ", _shape)
    # print(">>> _foc_plane: (plane of focusing: 1- horizontal, 2- vertical, 3- both) = ", _foc_plane)
