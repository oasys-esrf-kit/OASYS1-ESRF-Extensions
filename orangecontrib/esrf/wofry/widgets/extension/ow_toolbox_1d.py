from orangewidget.settings import Setting
from orangewidget import gui

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import write_surface_file, read_surface_file
from oasys.util.oasys_objects import OasysSurfaceData

from syned.widget.widget_decorator import WidgetDecorator

from orangecontrib.wofry.util.wofry_objects import WofryData

from orangecontrib.esrf.wofry.widgets.gui.ow_optical_element_1d import OWWOOpticalElement1D
from orangecontrib.esrf.wofry.util.toolbox import WOToolbox1D #TODO from wofryimpl....

class OWWOToolbox1D(OWWOOpticalElement1D):

    name = "Toolbox Wavefront 1D"
    description = "Wofry: Toolbox Wavefront 1D"
    icon = "icons/util.png"
    priority = 150

    crop_factor          = Setting(1.0)
    shift_center_in_microns = Setting(0.0)
    change_photon_energy = Setting(0)    # 0=No, 1=Yes
    new_photon_energy    = Setting(0.0)  # if change_photon_energy, the new photon energy in eV

    def __init__(self):

        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)

    def draw_specific_box(self):

        toolbox_box = oasysgui.widgetBox(self.tab_bas, "Toolbox 1D Setting", addSpace=False, orientation="vertical",
                                           height=350)

        tmp = oasysgui.lineEdit(toolbox_box, self, "shift_center_in_microns", "Shift center [microns]",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("shift_center_in_microns")


        tmp = oasysgui.lineEdit(toolbox_box, self, "crop_factor", "Crop/pad factor (<1:crop, >1:pad) ",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("crop_factor")


        gui.comboBox(toolbox_box, self, "change_photon_energy", label="Change photon energy",
                     items=['No','Yes'], #callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")


        new_energy_box = oasysgui.widgetBox(toolbox_box, "", addSpace=False,
                                        orientation="horizontal")  # width=550, height=50)
        tmp = oasysgui.lineEdit(new_energy_box, self, "new_photon_energy", "new photon energy",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("new_photon_energy")
        self.show_at("self.change_photon_energy == 1", new_energy_box)



        # self.set_visible()

    # def set_visible(self):
    #     self.box_refraction_index_id.setVisible(self.material in [0])
    #     self.box_att_coefficient_id.setVisible(self.material in [0])


    def get_optical_element(self):

        return WOToolbox1D(name=self.oe_name,
                           crop_factor=self.crop_factor,
                           shift_center=self.shift_center_in_microns*1e-6,
                           change_photon_energy=self.change_photon_energy,
                           new_photon_energy=self.new_photon_energy)

    def check_data(self):
        super().check_data()
        # congruence.checkFileName(self.file_with_thickness_mesh)

    def receive_specific_syned_data(self, optical_element):
        pass



    #
    # overwritten methods to append profile plot
    #

    # def get_titles(self):
    #     titles = super().get_titles()
    #     titles.append("O.E. Profile")
    #     return titles

    # def propagate_wavefront(self):
    #     super().propagate_wavefront()
    #
    #     if self.write_profile_flag == 1:
    #         xx, yy, s = self.get_optical_element().get_surface_thickness_mesh(self.input_data.get_wavefront())
    #         write_surface_file(s.T, xx, yy, self.write_profile, overwrite=True)
    #         print("\nFile for OASYS " + self.write_profile + " written to disk.")

    # def do_plot_results(self, progressBarValue=80): # OVERWRITTEN
    #
    #     super().do_plot_results(progressBarValue)
    #     if not self.view_type == 0:
    #         if not self.wavefront_to_plot is None:
    #
    #             self.progressBarSet(progressBarValue)
    #
    #             wo_lens = self.get_optical_element()
    #             abscissas_on_lens, lens_thickness = wo_lens.get_surface_thickness_mesh(self.input_data.get_wavefront())
    #
    #             self.plot_data1D(x=abscissas_on_lens*1e6, #TODO check how is possible to plot both refractive surfaces
    #                              y=lens_thickness*1e6, # in microns
    #                              progressBarValue=progressBarValue + 10,
    #                              tabs_canvas_index=4,
    #                              plot_canvas_index=4,
    #                              calculate_fwhm=False,
    #                              title=self.get_titles()[4],
    #                              xtitle="Spatial Coordinate along o.e. [$\mu$m]",
    #                              ytitle="Total lens thickness [$\mu$m]")
    #
    #             self.progressBarFinished()

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from srxraylib.plot.gol import plot

    def get_example_wofry_data():
        from wofryimpl.propagator.light_source import WOLightSource
        from wofryimpl.beamline.beamline import WOBeamline
        from orangecontrib.wofry.util.wofry_objects import WofryData
        from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D
        light_source = WOLightSource(dimension=1,
                                     initialize_from=2,
                                     # range_from_h=-0.)0003,
                                     # range_to_h=0.0003,
                                     # range_from_v=-0.0003,
                                     # range_to_v=0.0003,
                                     # number_of_points_h=400,
                                     # # number_of_points_v=200,
                                     # energy=10000.0,
                                     sigma_h=.1e-6,
                                     sigma_v=.1e-6,
                                     )

        # wfr = GenericWavefront1D.initialize_wavefront_from_range(x_min=-0.005,x_max=0.005,number_of_points=1000)
        # wfr.set_wavelength(1e-10)
        # wfr.set_gaussian(sigma_x=0.001, amplitude=1,shift=0)

        # plot(wfr.get_abscissas(), wfr.get_intensity())
        return WofryData(wavefront=light_source.get_wavefront(),
                           beamline=WOBeamline(light_source=light_source))



    a = QApplication(sys.argv)
    ow = OWWOToolbox1D()
    ow.set_input(get_example_wofry_data())

    ow.show()
    a.exec_()
    ow.saveSettings()
