import numpy
from orangewidget.settings import Setting
from orangewidget import gui
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

# from syned.beamline.optical_elements.ideal_elements.lens import IdealLens
from orangecontrib.esrf.syned.util.lens import Lens # TODO: from syned.beamline.optical_elements....

# from wofry.beamline.optical_elements.ideal_elements.lens import WOIdealLens
from orangecontrib.esrf.wofry.util.lens import WOLens

from orangecontrib.wofry.widgets.gui.ow_optical_element import OWWOOpticalElement, OWWOOpticalElementWithBoundaryShape

from syned.beamline.shape import SurfaceShape, Plane, Paraboloid, ParabolicCylinder, Sphere, SphericalCylinder
from syned.beamline.shape import Convexity, Direction


class OWWORealLens2D(OWWOOpticalElementWithBoundaryShape):

    name = "Lens"
    description = "Wofry: Real Lens 2D"
    icon = "icons/lens.png"
    priority = 20


    surface_shape = Setting(1)
    two_d_lens = Setting(0)
    wall_thickness = Setting(10e-6)
    lens_radius = Setting(200e-6)
    number_of_refractive_surfaces = Setting(1)
    material = Setting(1)


    # TODO: this is redundant...
    # width = Setting(1e-3)
    # height = Setting(1e-4)
    shape = Setting(1)
    radius = Setting(100e-6)



    def __init__(self):
        super().__init__()


    def set_visible(self):
        self.lens_radius_box_id.setVisible(self.surface_shape in [1,2])

    def get_material_name(self, index=None):
        materials_list = ["", "Be", "Al", "Diamond"]
        if index is None:
            return materials_list
        else:
            return materials_list[index]

    def draw_specific_box(self):

        super().draw_specific_box()

        self.lens_box = oasysgui.widgetBox(self.tab_bas, "Real Lens Setting", addSpace=True, orientation="vertical")

        gui.comboBox(self.lens_box, self, "surface_shape", label="Lens shape", labelWidth=350,
                     items=["Flat", "Parabolic", "Circular"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_visible)

        oasysgui.lineEdit(self.lens_box, self, "wall_thickness", "(t_wall) Wall thickness [m]", labelWidth=260, valueType=float, orientation="horizontal")

        self.lens_radius_box_id = oasysgui.widgetBox(self.lens_box, orientation="vertical")
        oasysgui.lineEdit(self.lens_radius_box_id, self, "lens_radius", "(R) radius of curvature [m]", labelWidth=260,
                          valueType=float, orientation="horizontal",)

        gui.comboBox(self.lens_box, self, "number_of_refractive_surfaces", label="Number of refractive surfaces", labelWidth=350,
                     items=["1", "2"], sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(self.lens_box, self, "two_d_lens", label="Focusing in", labelWidth=350,
                     items=["2D", "1D (tangential)", "1D (sagittal)"], sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(self.lens_box, self, "material", label="Lens material",
                     items=self.get_material_name(),
                     sendSelectedValue=False, orientation="horizontal")

    def get_optical_element(self):

        if self.surface_shape == 0:
            surface_shape1 = Plane()
        elif self.surface_shape == 1:
            if self.two_d_lens == 0:
                surface_shape1 = Paraboloid(parabola_parameter=self.lens_radius, convexity=Convexity.DOWNWARD)
            elif self.two_d_lens == 1:
                surface_shape1 = ParabolicCylinder(parabola_parameter=self.lens_radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.DOWNWARD)
            elif self.two_d_lens == 2:
                surface_shape1 = ParabolicCylinder(parabola_parameter=self.lens_radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.UPWARD)
        elif self.surface_shape == 2:
            if self.two_d_lens == 0:
                surface_shape1 = Sphere(radius=self.lens_radius, convexity=Convexity.DOWNWARD)
            elif self.two_d_lens == 1:
                surface_shape1 = SphericalCylinder(radius=self.lens_radius, cylinder_direction=Direction.TANGENTIAL, convexity=Convexity.DOWNWARD)
            elif self.two_d_lens == 3:
                surface_shape1 = SphericalCylinder(radius=self.lens_radius, cylinder_direction=Direction.SAGITTAL, convexity=Convexity.UPWARD)

        if self.number_of_refractive_surfaces == 0:
            surface_shape2 = Plane()
        else:
            surface_shape2 = surface_shape1   #   not used!


        bs = self.get_boundary_shape()
        return WOLens(name="Real Lens", surface_shape1=surface_shape1, surface_shape2=surface_shape2,
                    boundary_shape=bs, thickness=self.wall_thickness,
                      material=self.get_material_name(index=self.material) )

    def get_optical_element_python_code(self):
        txt  = ""
        # txt += "\nfrom wofry.beamline.optical_elements.ideal_elements.lens import WOIdealLens"
        # txt += "\n"
        # txt += "\noptical_element = WOIdealLens(name='%s',focal_x=%f,focal_y=%f)"%(self.oe_name,self.focal_x,self.focal_y)
        # txt += "\n"
        return txt

    def check_data(self):
        super().check_data()
        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_x), "Horizontal Focal Length")
        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_y), "Vertical Focal Length")

    def receive_specific_syned_data(self, optical_element):
        if not optical_element is None:
            if isinstance(optical_element, Lens):
                self.lens_radius = optical_element._radius
                self.wall_thickness = optical_element._thickness
                self.material = optical_element._material
            else:
                raise Exception("Syned Data not correct: Optical Element is not a Lens")
        else:
            raise Exception("Syned Data not correct: Empty Optical Element")

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D

    a = QApplication(sys.argv)
    ow = OWWORealLens2D()
    input_wavefront = GenericWavefront2D.initialize_wavefront_from_range(-0.002,0.002,-0.001,0.001,(400,200))
    ow.set_input(input_wavefront)

    ow.show()
    a.exec_()
    ow.saveSettings()
