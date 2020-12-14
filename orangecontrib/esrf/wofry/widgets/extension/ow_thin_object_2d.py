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
    icon = "icons/thinb2d.png"
    priority = 206

    inputs = [("WofryData", WofryData, "set_input"),
              WidgetDecorator.syned_input_data()[0],
              ("Surface Data", OasysSurfaceData, "set_input_surface_data")
              ]


    material = Setting(1)
    refraction_index_delta = Setting(5.3e-7)
    att_coefficient = Setting(0.00357382)

    aperture_shape = Setting(0)
    aperture_dimension_v = Setting(100e-6)
    aperture_dimension_h = Setting(200e-6)


    file_with_thickness_mesh = Setting("<none>")

    def __init__(self):

        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)

    def draw_specific_box(self):

        self.thinobject_box = oasysgui.widgetBox(self.tab_bas, "Thin Object Setting", addSpace=False, orientation="vertical",
                                           height=350)

        gui.comboBox(self.thinobject_box, self, "material", label="Lens material",
                     items=self.get_material_name(), callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.box_refraction_index_id = oasysgui.widgetBox(self.thinobject_box, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_refraction_index_id, self, "refraction_index_delta", "Refraction index delta",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("refraction_index_delta")

        self.box_att_coefficient_id = oasysgui.widgetBox(self.thinobject_box, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_att_coefficient_id, self, "att_coefficient", "Attenuation coefficient [m-1]",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("att_coefficient")



        filein_box = oasysgui.widgetBox(self.thinobject_box, "", addSpace=True,
                                        orientation="horizontal")  # width=550, height=50)
        self.le_beam_file_name = oasysgui.lineEdit(filein_box, self, "file_with_thickness_mesh",
                                                   "File with thickness mesh",
                                                   labelWidth=90, valueType=str, orientation="horizontal")
        gui.button(filein_box, self, "...", callback=self.selectFile)

        self.set_visible()


    def set_visible(self):
        self.box_refraction_index_id.setVisible(self.material in [0])
        self.box_att_coefficient_id.setVisible(self.material in [0])

    def selectFile(self):
        filename = oasysgui.selectFileFromDialog(self,
                previous_file_path=self.file_with_thickness_mesh, message="HDF5 Files (*.hdf5 *.h5 *.hdf)",
                start_directory=".", file_extension_filter="*.*")

        self.le_beam_file_name.setText(filename)


    def get_material_name(self, index=None):
        materials_list = ["External", "Be", "Al", "Diamond"]
        if index is None:
            return materials_list
        else:
            return materials_list[index]

    def get_optical_element(self):

        return WOThinObject(name=self.name,
                    file_with_thickness_mesh=self.file_with_thickness_mesh,
                    material=self.get_material_name(self.material),
                    refraction_index_delta=self.refraction_index_delta,
                    att_coefficient=self.att_coefficient,
                    )

    def check_data(self):
        super().check_data()
        congruence.checkFileName(self.file_with_thickness_mesh)

    def receive_specific_syned_data(self, optical_element):
        pass

    def set_input_surface_data(self, surface_data):
        if isinstance(surface_data, OasysSurfaceData):
           self.file_with_thickness_mesh = surface_data.surface_data_file
        else:
            raise Exception("Wrong surface_data")

    #
    # overwrite this method to add tab with thickness profile
    #

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

                xx, yy, zz = self.get_optical_element().get_surface_thickness_mesh(self.input_data.get_wavefront())

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
