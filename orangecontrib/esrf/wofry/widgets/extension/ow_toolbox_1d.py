from orangewidget.settings import Setting
from orangewidget import gui

from oasys.widgets import gui as oasysgui

from orangecontrib.esrf.wofry.widgets.gui.ow_optical_element_1d import OWWOOpticalElement1D
from orangecontrib.esrf.wofry.util.toolbox import WOToolbox1D #TODO from wofryimpl....

class OWWOToolbox1D(OWWOOpticalElement1D):

    name = "Toolbox Wavefront 1D"
    description = "Wofry: Toolbox Wavefront 1D"
    icon = "icons/util.png"
    priority = 150

    crop_factor = Setting(1.0)
    shift_center_in_microns = Setting(0.0)
    abscissas_factor = Setting(1.0)
    change_photon_energy = Setting(0)    # 0=No, 1=Yes
    new_photon_energy    = Setting(0.0)  # if change_photon_energy=1, the new photon energy in eV

    def __init__(self):

        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)

    def draw_specific_box(self):

        toolbox_box = oasysgui.widgetBox(self.tab_bas, "Toolbox 1D Setting", addSpace=False, orientation="vertical",
                                           height=350)

        tmp = oasysgui.lineEdit(toolbox_box, self, "shift_center_in_microns", "Shift center [microns]",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("shift_center_in_microns")


        tmp = oasysgui.lineEdit(toolbox_box, self, "abscissas_factor", "Multiply abscissas by",
                          labelWidth=250, valueType=float, orientation="horizontal")
        tmp.setToolTip("abscissas_factor")

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



    def get_optical_element(self):

        return WOToolbox1D(name=self.oe_name,
                           crop_factor=self.crop_factor,
                           shift_center=self.shift_center_in_microns*1e-6,
                           abscissas_factor=self.abscissas_factor,
                           change_photon_energy=self.change_photon_energy,
                           new_photon_energy=self.new_photon_energy)

    def check_data(self):
        super().check_data()
        # congruence.checkFileName(self.file_with_thickness_mesh)

    def receive_specific_syned_data(self, optical_element):
        pass

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    def get_example_wofry_data():
        from wofryimpl.propagator.light_source import WOLightSource
        from wofryimpl.beamline.beamline import WOBeamline
        from orangecontrib.wofry.util.wofry_objects import WofryData
        light_source = WOLightSource(dimension=1,
                                     initialize_from=2,
                                     sigma_h=.1e-6,
                                     sigma_v=.1e-6,
                                     )

        return WofryData(wavefront=light_source.get_wavefront(),
                           beamline=WOBeamline(light_source=light_source))



    a = QApplication(sys.argv)
    ow = OWWOToolbox1D()
    ow.set_input(get_example_wofry_data())

    ow.show()
    a.exec_()
    ow.saveSettings()
