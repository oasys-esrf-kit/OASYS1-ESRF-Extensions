
import numpy
from orangecontrib.esrf.syned.util.lens import Lens # TODO: from syned.beamline.optical_elements.lenses.lens import Lens

from syned.beamline.shape import Convexity, Direction
from syned.beamline.shape import SurfaceShape, Plane, Paraboloid, ParabolicCylinder
from syned.beamline.shape import BoundaryShape, Rectangle, Circle, Ellipse, MultiplePatch

from wofry.beamline.decorators import OpticalElementDecorator

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
        boundaries = self._boundary_shape.get_boundaries()

        if isinstance(self._boundary_shape, Rectangle):
            wavefront.clip_square(boundaries[0], boundaries[1], boundaries[2], boundaries[3])
        elif isinstance(self._boundary_shape, Circle):
            wavefront.clip_circle(boundaries[0], boundaries[1], boundaries[2])
        else:
            raise NotImplementedError("to be implemented")


        #
        # to do: apply lens...
        #


        return wavefront

    def get_radius(self):
        if isinstance(self.get_surface_shape(index=0), Paraboloid):
            return self.get_surface_shape(index=0).get_parabola_parameter()
        else:
            raise NotImplementedError()


    def is_plano(self):
        if isinstance(self.get_surface_shape(index=1), Plane):
            return True
        else:
            return False

    @classmethod
    def create_biconvex_2d_paraboloid_lens(cls, name="", radius=1.0, material="", thickness=0.0):
        surface_shape1 = Paraboloid(parabola_parameter=2 * radius, convexity = Convexity.UPWARD)
        surface_shape2 = Paraboloid(parabola_parameter=2 * radius, convexity=Convexity.DOWNWARD)
        return WOLens(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                    thickness=thickness, material=material)

    @classmethod
    def create_planoconvex_2d_paraboloid_lens(cls, name="", radius=1.0, material="", thickness=0.0):
        surface_shape1 = Paraboloid(parabola_parameter=2 * radius, convexity = Convexity.UPWARD)
        surface_shape2 = Plane()
        return WOLens(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                    thickness=thickness, material=material)

    @classmethod
    def create_biconvex_2d_parabolic_cylinder_lens(cls, name="", radius=1.0, material="", thickness=0.0):
        surface_shape1 = ParabolicCylinder(parabola_parameter=radius, cylinder_direction=Direction.TANGENTIAL, convexity = Convexity.UPWARD)
        surface_shape2 = ParabolicCylinder(parabola_parameter=radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.DOWNWARD)
        return WOLens(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                    thickness=thickness, material=material)

    @classmethod
    def create_planoconvex_2d_parabolic_cylinder_lens(cls, name="", radius=1.0, material="", thickness=0.0):
        surface_shape1 = ParabolicCylinder(parabola_parameter=radius, cylinder_direction=Direction.TANGENTIAL, convexity = Convexity.UPWARD)
        surface_shape2 = Plane()
        return WOLens(name=name, surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                    thickness=thickness, material=material)



if __name__ == "__main__":
    l = WOLens.create_biconvex_2d_parabolic_cylinder_lens(radius=10e-6)
    print(l.info(), l.get_radius())