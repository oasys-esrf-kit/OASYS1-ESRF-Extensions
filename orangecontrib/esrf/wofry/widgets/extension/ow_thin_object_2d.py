from orangewidget.settings import Setting
from orangewidget import gui

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import write_surface_file, read_surface_file
from oasys.util.oasys_objects import OasysSurfaceData

from syned.widget.widget_decorator import WidgetDecorator

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.wofry.widgets.gui.ow_optical_element import OWWOOpticalElement

from orangecontrib.esrf.wofry.util.thin_object import WOThinObject #TODO from wofryimpl....

class OWWOThinObject2D(OWWOOpticalElement):

    name = "ThinObject"
    description = "Wofry: Thin Object 2D"
    icon = "icons/thin_object.jpg"
    priority = 30

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


    write_profile_flag = Setting(0)
    write_profile = Setting("thin_object_profile_2D.h5")

    file_with_thickness_mesh = Setting("<none>")

    def __init__(self):

        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)

    def draw_specific_box(self):

        self.thinobject_box = oasysgui.widgetBox(self.tab_bas, "Thin Object Setting", addSpace=False, orientation="vertical",
                                           height=350)

        gui.comboBox(self.thinobject_box, self, "material", label="Lens material",
                     items=self.get_material_name(),
                     sendSelectedValue=False, orientation="horizontal")

        oasysgui.lineEdit(self.thinobject_box, self, "file_with_thickness_mesh", "File with thickness mesh",
                            labelWidth=200, valueType=str, orientation="horizontal")


        # files i/o tab
        self.tab_files = oasysgui.createTabPage(self.tabs_setting, "File I/O")
        files_box = oasysgui.widgetBox(self.tab_files, "Files", addSpace=True, orientation="vertical")

        gui.comboBox(files_box, self, "write_profile_flag", label="Dump profile to file",
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        self.box_file_out = gui.widgetBox(files_box, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.box_file_out, self, "write_profile", "File name",
                            labelWidth=200, valueType=str, orientation="horizontal")


        self.set_visible()


    # def set_input(self, input_data):
    #
    #     do_execute = False
    #     # if isinstance(input_data, OasysPreProcessorData):
    #     #     self.file_with_thickness_mesh = self.oasys_data.error_profile_data
    #     if isinstance(input_data, OasysSurfaceData):
    #         self.file_with_thickness_mesh = input_data.surface_data_file
    #     elif isinstance(input_data, WofryData):
    #         self.input_data = input_data
    #         do_execute = True
    #     elif isinstance(input_data, GenericWavefront2D):
    #         self.input_data = WofryData(wavefront=input_data)
    #         do_execute = True
    #
    #     if self.is_automatic_execution and do_execute:
    #         self.propagate_wavefront()

    def set_visible(self):
        self.box_file_out.setVisible(self.write_profile_flag == 1)

    def get_material_name(self, index=None):
        materials_list = ["", "Be", "Al", "Diamond"]
        if index is None:
            return materials_list
        else:
            return materials_list[index]

    def get_optical_element(self):

        return WOThinObject(name=self.name,
                 file_with_thickness_mesh=self.file_with_thickness_mesh,
                 material=self.get_material_name(self.material))

    # def get_optical_element_python_code(self):
    #     return self.get_optical_element().to_python_code()

    def check_data(self):
        super().check_data()
        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_x), "Horizontal Focal Length")
        # congruence.checkStrictlyPositiveNumber(numpy.abs(self.focal_y), "Vertical Focal Length")

    def receive_specific_syned_data(self, optical_element):
        pass
        # if not optical_element is None:
        #     if isinstance(optical_element, Lens):
        #         self.lens_radius = optical_element._radius
        #         self.wall_thickness = optical_element._thickness
        #         self.material = optical_element._material
        #     else:
        #         raise Exception("Syned Data not correct: Optical Element is not a Lens")
        # else:
        #     raise Exception("Syned Data not correct: Empty Optical Element")

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

    def propagate_wavefront(self):
        super().propagate_wavefront()

        if self.write_profile_flag == 1:
            xx, yy, s = self.get_optical_element().get_surface_thickness_mesh(self.input_data.get_wavefront())
            write_surface_file(s.T, xx, yy, self.write_profile, overwrite=True)
            print("\nFile for OASYS " + self.write_profile + " written to disk.")

    def do_plot_results(self, progressBarValue=80):
        super().do_plot_results(progressBarValue)
        if not self.view_type == 0:
            if not self.wavefront_to_plot is None:

                self.progressBarSet(progressBarValue)

                xx, yy, zz = read_surface_file(self.file_with_thickness_mesh)
                if zz.min() < 0: zz -= zz.min()

                self.plot_data2D(data2D=1e6*zz.T,
                                 dataX=1e6*xx,
                                 dataY=1e6*xx,
                                 progressBarValue=progressBarValue,
                                 tabs_canvas_index=2,
                                 plot_canvas_index=2,
                                 title="O.E. Thickness profile in $\mu$m",
                                 xtitle="Horizontal [$\mu$m] ( %d pixels)"%(xx.size),
                                 ytitle="Vertical [$\mu$m] ( %d pixels)"%(yy.size))

                self.progressBarFinished()

            

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    def get_example_wofry_data():
        from wofryimpl.propagator.light_source import WOLightSource
        from wofryimpl.beamline.beamline import WOBeamline
        from orangecontrib.wofry.util.wofry_objects import WofryData

        light_source = WOLightSource(dimension=2,
                                     initialize_from=0,
                                     range_from_h=-0.0003,
                                     range_to_h=0.0003,
                                     range_from_v=-0.0003,
                                     range_to_v=0.0003,
                                     number_of_points_h=400,
                                     number_of_points_v=200,
                                     energy=10000.0,
                                     )

        return WofryData(wavefront=light_source.get_wavefront(),
                           beamline=WOBeamline(light_source=light_source))



    a = QApplication(sys.argv)
    ow = OWWOThinObject2D()
    ow.file_with_thickness_mesh = "/home/srio/Downloads/SRW_M_thk_res_workflow_a_FC_CDn01.dat.h5"
    ow.set_input(get_example_wofry_data())


    ow.show()
    a.exec_()
    ow.saveSettings()
