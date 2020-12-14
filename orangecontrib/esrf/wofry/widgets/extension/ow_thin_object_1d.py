from orangewidget.settings import Setting
from orangewidget import gui

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import write_surface_file, read_surface_file
from oasys.util.oasys_objects import OasysSurfaceData

from syned.widget.widget_decorator import WidgetDecorator

from orangecontrib.wofry.util.wofry_objects import WofryData

from orangecontrib.esrf.wofry.widgets.gui.ow_optical_element_1d import OWWOOpticalElement1D
from orangecontrib.esrf.wofry.util.thin_object import WOThinObject1D #TODO from wofryimpl....

class OWWOThinObject1D(OWWOOpticalElement1D):

    name = "ThinObject1D"
    description = "Wofry: Thin Object 1D"
    icon = "icons/thinb1d.png"
    priority = 6


    material = Setting(1)
    refraction_index_delta = Setting(5.3e-7)
    att_coefficient = Setting(0.00357382)

    aperture_shape = Setting(0)
    aperture_dimension_v = Setting(100e-6)
    aperture_dimension_h = Setting(200e-6)


    write_profile_flag = Setting(0)
    write_profile = Setting("thin_object_profile_2D.h5")

    file_with_thickness_mesh = Setting("<none>")

    def __init__(self):

        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)

    def draw_specific_box(self):

        self.thinobject_box = oasysgui.widgetBox(self.tab_bas, "Thin Object 1D Setting", addSpace=False, orientation="vertical",
                                           height=350)

        gui.comboBox(self.thinobject_box, self, "material", label="Lens material",
                     items=self.get_material_name(),callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.box_refraction_index_id = oasysgui.widgetBox(self.thinobject_box, "", addSpace=False, orientation="vertical")
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

        return WOThinObject1D(name=self.oe_name,
                    file_with_thickness_mesh=self.file_with_thickness_mesh,
                    material=self.get_material_name(self.material),
                    refraction_index_delta=self.refraction_index_delta,
                    att_coefficient=self.att_coefficient)

    def check_data(self):
        super().check_data()
        congruence.checkFileName(self.file_with_thickness_mesh)

    def receive_specific_syned_data(self, optical_element):
        pass



    #
    # overwritten methods to append profile plot
    #

    def get_titles(self):
        titles = super().get_titles()
        titles.append("O.E. Profile")
        return titles

    # def propagate_wavefront(self):
    #     super().propagate_wavefront()
    #
    #     if self.write_profile_flag == 1:
    #         xx, yy, s = self.get_optical_element().get_surface_thickness_mesh(self.input_data.get_wavefront())
    #         write_surface_file(s.T, xx, yy, self.write_profile, overwrite=True)
    #         print("\nFile for OASYS " + self.write_profile + " written to disk.")

    def do_plot_results(self, progressBarValue=80): # OVERWRITTEN

        super().do_plot_results(progressBarValue)
        if not self.view_type == 0:
            if not self.wavefront_to_plot is None:

                self.progressBarSet(progressBarValue)

                wo_lens = self.get_optical_element()
                abscissas_on_lens, lens_thickness = wo_lens.get_surface_thickness_mesh(self.input_data.get_wavefront())

                self.plot_data1D(x=abscissas_on_lens*1e6, #TODO check how is possible to plot both refractive surfaces
                                 y=lens_thickness*1e6, # in microns
                                 progressBarValue=progressBarValue + 10,
                                 tabs_canvas_index=4,
                                 plot_canvas_index=4,
                                 calculate_fwhm=False,
                                 title=self.get_titles()[4],
                                 xtitle="Spatial Coordinate along o.e. [$\mu$m]",
                                 ytitle="Total lens thickness [$\mu$m]")

                self.progressBarFinished()

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    def get_example_wofry_data():
        from wofryimpl.propagator.light_source import WOLightSource
        from wofryimpl.beamline.beamline import WOBeamline
        from orangecontrib.wofry.util.wofry_objects import WofryData

        light_source = WOLightSource(dimension=1,
                                     initialize_from=0,
                                     range_from_h=-0.0003,
                                     range_to_h=0.0003,
                                     # range_from_v=-0.0003,
                                     # range_to_v=0.0003,
                                     number_of_points_h=400,
                                     # number_of_points_v=200,
                                     energy=10000.0,
                                     )

        return WofryData(wavefront=light_source.get_wavefront(),
                           beamline=WOBeamline(light_source=light_source))



    a = QApplication(sys.argv)
    ow = OWWOThinObject1D()
    ow.file_with_thickness_mesh = "/home/srio/Downloads/SRW_M_thk_res_workflow_a_FC_CDn01.txt"
    ow.set_input(get_example_wofry_data())


    ow.show()
    a.exec_()
    ow.saveSettings()
