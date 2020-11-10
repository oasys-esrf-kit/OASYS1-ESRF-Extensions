import numpy
import xraylib


from orangewidget.settings import Setting
from orangewidget import gui


from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from oasys.util.oasys_util import write_surface_file, read_surface_file
from oasys.util.oasys_util import write_surface_file
from oasys.util.oasys_objects import OasysPreProcessorData, OasysSurfaceData

from syned.widget.widget_decorator import WidgetDecorator
from orangecontrib.esrf.syned.util.lens import Lens # TODO: from syned.beamline.optical_elements....

from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D

from orangecontrib.esrf.wofry.widgets.extension.ow_thin_object_2d import WOThinObject # TODO: change import
from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.esrf.wofry.widgets.gui.ow_optical_element import OWWOOpticalElement # TODO: from orangecontrib.wofry.widgets.gui.ow_optical_element import OWWOOpticalElement


# mimics a wofry element
class WOThinObjectCorrector(WOThinObject):

    def __init__(self, name="Undefined",
                 file_with_thickness_mesh="",
                 material="",
                 correction_method=1,
                 focus_at=10.0,
                 wall_thickness=0.0,
                 apply_correction_to_wavefront=0,
                 ):

        super().__init__(name=name,
                 file_with_thickness_mesh=file_with_thickness_mesh,
                 material=material,
                         )

        self._correction_method = correction_method
        self._focus_at = focus_at
        self._wall_thickness = wall_thickness
        self._apply_correction_to_wavefront = apply_correction_to_wavefront

    def applyOpticalElement(self, wavefront, parameters=None, element_index=None):

        photon_energy = wavefront.get_photon_energy()
        wave_length = wavefront.get_wavelength()
        x = wavefront.get_coordinate_x()
        y = wavefront.get_coordinate_y()

        if self._correction_method == 0: # write file with zero profile
            profile = numpy.zeros((x.size, y.size))
        elif self._correction_method == 1:

            print("\n\n\n ==========  parameters from optical element : ")
            print(self.info())


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

            # auxiliar spherical wavefront
            wavefront_model = wavefront.duplicate()
            wavefront_model.set_spherical_wave(radius=-self._focus_at, complex_amplitude=1.0,)


            phase_correction = numpy.angle( wavefront_model.get_complex_amplitude() / wavefront.get_complex_amplitude())
            profile = -phase_correction / wavefront.get_wavenumber() / refraction_index_delta


        profile += self._wall_thickness
        write_surface_file(profile.T, x, y, self.get_file_with_thickness_mesh(), overwrite=True)
        print("\nFile for OASYS " + self.get_file_with_thickness_mesh() + " written to disk.")

        if self._apply_correction_to_wavefront > 0:
            output_wavefront = super().applyOpticalElement(wavefront, parameters=parameters, element_index=element_index)
        else:
            output_wavefront = wavefront

        return output_wavefront

    def to_python_code(self, data=None):
        txt  = ""
        txt += "\nfrom orangecontrib.esrf.wofry.widgets.extension.ow_thin_object_corrector_2d import WOThinObjectCorrector"
        txt += "\n"
        txt += "\noptical_element = WOThinObjectCorrector(name='%s',file_with_thickness_mesh='%s',material='%s',\n" % \
               (self.get_name(), self.get_file_with_thickness_mesh(), self.get_material())
        txt += "    correction_method=%d, focus_at= %g, wall_thickness=%g, apply_correction_to_wavefront=%d)" % \
               (self._correction_method, self._focus_at, self._wall_thickness, self._apply_correction_to_wavefront)
        txt += "\n"
        return txt



class OWWOThinObjectCorrector2D(OWWOOpticalElement):

    name = "ThinObjectCorrector"
    description = "Wofry: Thin Object Corrector 2D"
    icon = "icons/lenscorrector2d.png"
    priority = 35

    inputs = [("WofryData", WofryData, "set_input"),
              # ("GenericWavefront2D", GenericWavefront2D, "set_input"),
              WidgetDecorator.syned_input_data()[0],
              # ("Oasys PreProcessorData", OasysPreProcessorData, "set_input"),
              ("Surface Data", OasysSurfaceData, "set_input")
              ]


    material = Setting(1)

    aperture_shape = Setting(0)
    aperture_dimension_v = Setting(100e-6)
    aperture_dimension_h = Setting(200e-6)

    refraction_index_delta = Setting(5.3e-7)
    att_coefficient = Setting(0.00357382)

    correction_method = Setting(1)
    focus_at = Setting(10.0)
    wall_thickness = Setting(0.0)
    apply_correction_to_wavefront = Setting(1)


    write_input_wavefront = Setting(0)
    write_profile_flag = Setting(0)
    write_profile = Setting("thin_object_profile_2D.h5")

    file_with_thickness_mesh = Setting("profile2D.h5")

    def __init__(self):

        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)

    def draw_specific_box(self):

        self.thinobject_box = oasysgui.widgetBox(self.tab_bas, "Thin Object Corrector Setting", addSpace=False, orientation="vertical",
                                           height=350)


        gui.comboBox(self.thinobject_box, self, "correction_method", label="Correction type", labelWidth=350,
                     items=["None","Focus to waist"],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.box_corrector_1 = oasysgui.widgetBox(self.thinobject_box, "", addSpace=False, orientation="vertical")

        oasysgui.widgetBox(self.box_corrector_1, "", addSpace=False, orientation="horizontal")
        oasysgui.lineEdit(self.box_corrector_1, self, "focus_at", "Distance to waist [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")


        gui.comboBox(self.box_corrector_1, self, "material", label="Lens material",
                     items=self.get_material_name(),
                     sendSelectedValue=False, orientation="horizontal")


        self.box_wall_thickness_id = oasysgui.widgetBox(self.box_corrector_1, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.thinobject_box, self, "wall_thickness", "Wall thickness [m]",
                          labelWidth=300, valueType=float, orientation="horizontal", tooltip="wall_thickness")


        oasysgui.lineEdit(self.thinobject_box, self, "file_with_thickness_mesh", "Output file with thickness mesh",
                            labelWidth=200, valueType=str, orientation="horizontal")


        gui.comboBox(self.thinobject_box, self, "apply_correction_to_wavefront", label="Apply correction to wavefront", labelWidth=350,
                     items=["No","Yes"],
                     sendSelectedValue=False, orientation="horizontal")

        # files i/o tab
        self.tab_files = oasysgui.createTabPage(self.tabs_setting, "File I/O")
        files_box = oasysgui.widgetBox(self.tab_files, "Files", addSpace=True, orientation="vertical")

        gui.comboBox(files_box, self, "write_input_wavefront", label="Input wf to file (for script)",
                     items=["No", "Yes [wavefront2D_input.h5]"], sendSelectedValue=False, orientation="horizontal")

        self.set_visible()


    def set_input(self, input_data):

        do_execute = False

        if isinstance(input_data, WofryData):
            self.input_data = input_data
            do_execute = True
        elif isinstance(input_data, GenericWavefront2D):
            self.input_data = WofryData(wavefront=input_data)
            do_execute = True

        if self.is_automatic_execution and do_execute:
            self.propagate_wavefront()

    # overwrite this method to add tab with thickness profile
    def initializeTabs(self):
        size = len(self.tab)
        indexes = range(0, size)

        for index in indexes:
            self.tabs.removeTab(size-1-index)

        titles = ["Intensity","Phase","Thickness Profile"]
        self.tab = []
        self.plot_canvas = []

        for index in range(0, len(titles)):
            self.tab.append(gui.createTabPage(self.tabs, titles[index]))
            self.plot_canvas.append(None)

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

    def do_plot_results(self, progressBarValue=80):
        super().do_plot_results(progressBarValue)
        if not self.view_type == 0:
            if not self.wavefront_to_plot is None:

                self.progressBarSet(progressBarValue)

                xx, yy, zz = read_surface_file(self.file_with_thickness_mesh)
                if zz.min() < 0: zz -= zz.min()

                self.plot_data2D(data2D=zz.T,
                                 dataX=1e6*xx,
                                 dataY=1e6*xx,
                                 progressBarValue=progressBarValue,
                                 tabs_canvas_index=2,
                                 plot_canvas_index=2,
                                 title="thickness profile",
                                 xtitle="Horizontal [$\mu$m] ( %d pixels)"%(xx.size),
                                 ytitle="Vertical [$\mu$m] ( %d pixels)"%(yy.size))

                self.progressBarFinished()

    def set_visible(self):
        self.box_corrector_1.setVisible(self.correction_method != 0)

    def get_material_name(self, index=None):
        materials_list = ["", "Be", "Al", "Diamond"]
        if index is None:
            return materials_list
        else:
            return materials_list[index]


    def get_optical_element(self):

        return WOThinObjectCorrector(name="Undefined",
                 file_with_thickness_mesh=self.file_with_thickness_mesh,
                 material=self.get_material_name(self.material),
                 correction_method=self.correction_method,
                 focus_at=self.focus_at,
                 wall_thickness=self.wall_thickness,
                 apply_correction_to_wavefront=self.apply_correction_to_wavefront,
                                     )

    def get_optical_element_python_code(self):
        return self.get_optical_element().to_python_code()

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

    def propagate_wavefront(self):
        super().propagate_wavefront()

        if self.write_input_wavefront == 1:
            self.input_data.get_wavefront().save_h5_file("wavefront2D_input.h5",subgroupname="wfr",
                                         intensity=True,phase=False,overwrite=True,verbose=False)
            print("\nFile with input wavefront wavefront2D_input.h5 written to disk.")

        if self.write_profile_flag == 1:
            xx, yy, s = self.get_optical_element().get_surface_thickness_mesh(self.input_data.get_wavefront())
            write_surface_file(s.T, xx, yy, self.write_profile, overwrite=True)
            print("\nFile for OASYS " + self.write_profile + " written to disk.")
            

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D

    a = QApplication(sys.argv)
    ow = OWWOThinObjectCorrector2D()
    # ow.file_with_thickness_mesh = "/home/srio/Downloads/SRW_M_thk_res_workflow_a_FC_CDn01.dat.h5"
    input_wavefront = GenericWavefront2D.initialize_wavefront_from_range(-0.0002,0.0002,-0.0002,0.0002,(400,200))
    ow.set_input(input_wavefront)


    ow.show()
    a.exec_()
    ow.saveSettings()
