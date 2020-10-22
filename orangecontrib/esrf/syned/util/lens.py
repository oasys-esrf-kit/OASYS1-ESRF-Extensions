#from syned.beamline.optical_element_with_two_surface_shapes import OpticalElementsWithTwoSurfaceShapes
from orangecontrib.esrf.syned.util.optical_element_with_two_surface_shapes import OpticalElementsWithTwoSurfaceShapes


class Lens(OpticalElementsWithTwoSurfaceShapes):
    def __init__(self,
                 name="Undefined",
                 surface_shape1=None,
                 surface_shape2=None,
                 boundary_shape=None,
                 material="",
                 thickness=0.0):

        if surface_shape1 is None: surface_shape1 = Plane()
        if surface_shape2 is None: surface_shape2 = Plane()

        super().__init__(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                         boundary_shape=boundary_shape)
        self._material = material
        self._thickness = thickness
        # support text contaning name of variable, help text and unit. Will be stored in self._support_dictionary
        self._set_support_text([
                    ("name",                "Name" ,                                "" ),
                    ("surface_shape1",      "Surface shape 1",                      "" ),
                    ("surface_shape2",      "Surface shape 2",                      ""),
                    ("boundary_shape",      "Boundary shape",                       "" ),
                    ("material",            "Material (element, compound or name)", "" ),
                    ("thickness",           "Thickness",                            "m"),
            ] )

    def get_thickness(self):
        return self._thickness

    def get_material(self):
        return self._material
