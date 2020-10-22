from syned.beamline.optical_element import OpticalElement
from syned.beamline.shape import SurfaceShape



class OpticalElementsWithTwoSurfaceShapes(OpticalElement):

    def __init__(self, name="",
                 surface_shape1=None,
                 surface_shape2=None,
                 boundary_shape=None):
        super().__init__(name, boundary_shape)
        if surface_shape1 is None: surface_shape1 = SurfaceShape()
        if surface_shape2 is None: surface_shape1 = SurfaceShape()
        self._surface_shape1 = surface_shape1
        self._surface_shape2 = surface_shape2

    def get_surface_shape(self, index):
        if index == 0:
            return self._surface_shape1
        elif index == 1:
            return self._surface_shape2
        else:
            raise Exception("only two shapes in OpticalElementsWithTwoSurfaceShapes")

    def set_surface_shape(self, index, surface_shape=None):
        if surface_shape is None: surface_shape = SurfaceShape()
        if index == 0:
            self._surface_shape2 = surface_shape
        elif index == 1:
            self._surface_shape2 = surface_shape
        else:
            raise Exception("only two shapes in OpticalElementsWithTwoSurfaceShapes")
