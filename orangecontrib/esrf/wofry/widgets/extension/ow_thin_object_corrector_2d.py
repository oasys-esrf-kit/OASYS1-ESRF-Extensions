from orangewidget.settings import Setting
from orangewidget import gui


from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from oasys.util.oasys_objects import OasysPreProcessorData, OasysSurfaceData

from syned.widget.widget_decorator import WidgetDecorator

from orangecontrib.esrf.wofry.util.thin_object_corrector import WOThinObjectCorrector #TODO from wofryimpl...

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.wofry.widgets.gui.ow_optical_element import OWWOOpticalElement



class OWWOThinObjectCorrector2D(OWWOOpticalElement):

    name = "ThinObjectCorrector2D"
    description = "Wofry: Thin Object Corrector 2D"
    icon = "icons/corrector2d.png"
    priority = 208


    material = Setting(1)
    refraction_index_delta = Setting(5.3e-7)
    att_coefficient = Setting(0.00357382)

    aperture_shape = Setting(0)
    aperture_dimension_v = Setting(100e-6)
    aperture_dimension_h = Setting(200e-6)

    refraction_index_delta = Setting(5.3e-7)
    att_coefficient = Setting(0.00357382)

    correction_method = Setting(1)
    focus_at = Setting(10.0)
    wall_thickness = Setting(0.0)
    apply_correction_to_wavefront = Setting(1)

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

        self.box_refraction_index_id = oasysgui.widgetBox(self.box_corrector_1, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_refraction_index_id, self, "refraction_index_delta", "Refraction index delta",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("refraction_index_delta")

        self.box_att_coefficient_id = oasysgui.widgetBox(self.box_corrector_1, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.box_att_coefficient_id, self, "att_coefficient", "Attenuation coefficient [m-1]",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("att_coefficient")


        self.box_wall_thickness_id = oasysgui.widgetBox(self.box_corrector_1, "", addSpace=False, orientation="horizontal")
        tmp = oasysgui.lineEdit(self.thinobject_box, self, "wall_thickness", "Wall thickness [m]",
                          labelWidth=300, valueType=float, orientation="horizontal", tooltip="wall_thickness")


        oasysgui.lineEdit(self.thinobject_box, self, "file_with_thickness_mesh", "Output file with thickness mesh",
                            labelWidth=200, valueType=str, orientation="horizontal")


        gui.comboBox(self.thinobject_box, self, "apply_correction_to_wavefront", label="Apply correction to wavefront", labelWidth=350,
                     items=["No","Yes"],
                     sendSelectedValue=False, orientation="horizontal")

        self.set_visible()

    def set_visible(self):
        self.box_corrector_1.setVisible(self.correction_method != 0)
        self.box_refraction_index_id.setVisible(self.material in [0])
        self.box_att_coefficient_id.setVisible(self.material in [0])

    def get_material_name(self, index=None):
        materials_list = ["External", "Be", "Al", "Diamond"]
        if index is None:
            return materials_list
        else:
            return materials_list[index]

    def get_optical_element(self):

        return WOThinObjectCorrector(name="Undefined",
                 file_with_thickness_mesh=self.file_with_thickness_mesh,
                 material=self.get_material_name(self.material),
                 refraction_index_delta=self.refraction_index_delta,
                 att_coefficient=self.att_coefficient,
                 correction_method=self.correction_method,
                 focus_at=self.focus_at,
                 wall_thickness=self.wall_thickness,
                 apply_correction_to_wavefront=self.apply_correction_to_wavefront,
                 file_with_thickness_mesh_flag=1,
                                     )

    def check_data(self):
        super().check_data()

    def receive_specific_syned_data(self, optical_element):
        pass

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

                zz, xx, yy = self.get_optical_element().calculate_correction_profile(self.input_data.get_wavefront())

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
            

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    def get_example_wofry_data():
        from wofryimpl.propagator.light_source import WOLightSource
        from wofryimpl.beamline.beamline import WOBeamline
        from orangecontrib.wofry.util.wofry_objects import WofryData

        light_source = WOLightSource(dimension=2,
                                     initialize_from=0,
                                     range_from_h=-0.0002,
                                     range_to_h=0.0002,
                                     range_from_v=-0.0002,
                                     range_to_v=0.0002,
                                     number_of_points_h=400,
                                     number_of_points_v=200,
                                     energy=10000.0,
                                     )

        return WofryData(wavefront=light_source.get_wavefront(),
                           beamline=WOBeamline(light_source=light_source))


    a = QApplication(sys.argv)
    ow = OWWOThinObjectCorrector2D()
    ow.set_input(get_example_wofry_data())


    ow.show()
    a.exec_()
    ow.saveSettings()
