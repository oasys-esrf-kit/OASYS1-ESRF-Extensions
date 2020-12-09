from orangecontrib.esrf.wofry.util.lens import WOLens
from orangecontrib.esrf.wofry.util.thin_object import WOThinObject

class WOLensWithError(WOLens):

    def __init__(self,
                 name="Undefined",
                 surface_shape1=None,
                 surface_shape2=None,
                 boundary_shape=None,
                 material="",
                 thickness=0.0,
                 thin_object_with_error=None):

        super().__init__(
                 name=name,
                 surface_shape1=surface_shape1,
                 surface_shape2=surface_shape2,
                 boundary_shape=boundary_shape,
                 material=material,
                 thickness=thickness,)

        if thin_object_with_error is None:
            thin_object_with_error = WOLensWithError()
        self._thin_object_with_error = thin_object_with_error

    def get_thin_object_with_error(self):
        return self._thin_object_with_error

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):

        output_wavefront = super().applyOpticalElement(wavefront, parameters=parameters, element_index=element_index)

        thin_object_with_error = self.get_thin_object_with_error()

        output_wavefront = thin_object_with_error.applyOpticalElement(wavefront=output_wavefront, parameters=parameters, element_index=element_index)

        return output_wavefront

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
                             file_with_thickness_mesh="",
                             ):

        obj = super().create_from_keywords(
            name=name,
            number_of_curved_surfaces=number_of_curved_surfaces,
            two_d_lens=two_d_lens,
            surface_shape=surface_shape,
            wall_thickness=wall_thickness,
            material=material,
            lens_radius=lens_radius,
            aperture_shape=aperture_shape,
            aperture_dimension_h=aperture_dimension_h,
            aperture_dimension_v=aperture_dimension_v
            )

        out2 = WOLensWithError(
            name = obj.get_name(),
            surface_shape1 = obj.get_surface_shape1(),
            surface_shape2 = obj.get_surface_shape2(),
            boundary_shape = obj.get_boundary_shape(),
            material = obj.get_material(),
            thickness = obj.get_thickness(),
            thin_object_with_error = WOThinObject(name=name,
                                                  file_with_thickness_mesh=file_with_thickness_mesh,
                                                  material=obj.get_material()))


        out2._keywords_at_creation["file_with_thickness_mesh"] = file_with_thickness_mesh

        return out2


    def to_python_code(self, do_plot=False):

        return super().to_python_code() + self.get_thin_object_with_error().to_python_code()
