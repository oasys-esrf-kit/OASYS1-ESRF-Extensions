import numpy
import sys

from PyQt5.QtWidgets import QMessageBox

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import TriggerIn, EmittingStream



from syned.beamline.element_coordinates import ElementCoordinates
from syned.beamline.beamline_element import BeamlineElement
from syned.widget.widget_decorator import WidgetDecorator

from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.esrf.wofry.widgets.gui.ow_optical_element_1d import OWWOOpticalElement1D # to be moved
from orangecontrib.esrf.wofry.util.mirror import WOMirror1D # to be moved to wofryimpl



class OWMirror1D(OWWOOpticalElement1D):

    name = "Mirror 1D"
    id = "WofryMirror1D"
    description = "Mirror 1D"
    icon = "icons/reflector_grazing1D.png"
    priority = 10

    category = "Wofry Wavefront Propagation"
    keywords = ["data", "file", "load", "read", "grazing"]

    outputs = [{"name":"WofryData",
                "type":WofryData,
                "doc":"WofryData",
                "id":"WofryData"},
               {"name":"Trigger",
                "type": TriggerIn,
                "doc":"Feedback signal to start a new beam simulation",
                "id":"Trigger"}]

    inputs = [("WofryData", WofryData, "set_input"),
              ("GenericWavefront1D", GenericWavefront1D, "set_input"),
              ("DABAM 1D Profile", numpy.ndarray, "receive_dabam_profile"),
              WidgetDecorator.syned_input_data()[0]]

    grazing_angle_in = Setting(1.5e-3)

    shape = Setting(1)
    flip = Setting(0)
    p_focus = Setting(1.0)
    q_focus = Setting(1.0)
    error_flag = Setting(0)
    error_file = Setting("<none>")
    error_file_oversampling_factor = Setting(1.0)
    mirror_length = Setting(0.2)
    mirror_points = Setting(500)
    write_profile = Setting(0)
    write_input_wavefront = Setting(0)


    input_data = None
    titles = ["Wavefront 1D Intensity", "Wavefront 1D Phase","Wavefront Real(Amplitude)","Wavefront Imag(Amplitude)","O.E. Profile"]


    def __init__(self):
        super().__init__(is_automatic=True, show_view_options=True, show_script_tab=True)

    def draw_specific_box(self):

        box_reflector = oasysgui.widgetBox(self.tab_bas, "Reflector", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(box_reflector, self, "grazing_angle_in", "Grazing incidence angle [rad]",
                          labelWidth=300, valueType=float, orientation="horizontal")

        gui.comboBox(box_reflector, self, "shape", label="Reflector shape",
                     items=["Flat","Circle","Ellipse","Parabola"], sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        gui.comboBox(box_reflector, self, "flip", label="Flip mirror (up-down,left-right)",
                     items=["No","Yes"], sendSelectedValue=False, orientation="horizontal")

        self.box_focal_id = oasysgui.widgetBox(box_reflector, "", addSpace=True, orientation="vertical")
        oasysgui.lineEdit(self.box_focal_id, self, "p_focus", "Focal entrance arm [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.box_focal_id, self, "q_focus", "Focal exit arm [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")

        gui.comboBox(box_reflector, self, "error_flag", label="Add profile deformation",
                     items=["No","Yes (from file)"],
                     callback=self.set_visible,
                     sendSelectedValue=False, orientation="horizontal")

        self.file_box_id = oasysgui.widgetBox(box_reflector, "", addSpace=True, orientation="vertical")
        file_box_id2 = oasysgui.widgetBox(self.file_box_id, "", addSpace=True, orientation="horizontal")
        self.error_file_id = oasysgui.lineEdit(file_box_id2, self, "error_file", "Error file X[m] Y[m]",
                                                    labelWidth=120, valueType=str, orientation="horizontal")
        gui.button(file_box_id2, self, "...", callback=self.set_error_file)

        oasysgui.lineEdit(self.file_box_id, self, "error_file_oversampling_factor", "Oversampling factor (>=1)",
                          labelWidth=300, valueType=float, orientation="horizontal")


        self.mirror_box_id = oasysgui.widgetBox(box_reflector, "", addSpace=True, orientation="vertical")
        oasysgui.lineEdit(self.mirror_box_id, self, "mirror_length", "Mirror length [m]",
                          labelWidth=300, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.mirror_box_id, self, "mirror_points", "Points on mirror",
                          labelWidth=300, valueType=int, orientation="horizontal")

        gui.comboBox(box_reflector, self, "write_profile", label="Dump profile to file",
                     items=["No","Yes [reflector_profile1D.dat]"], sendSelectedValue=False, orientation="horizontal")

        self.set_visible()



    def set_visible(self):
        self.file_box_id.setVisible(self.error_flag)
        self.box_focal_id.setVisible(self.shape)
        self.mirror_box_id.setVisible(self.error_flag == 0)

    def set_error_file(self):
        self.error_file_id.setText(oasysgui.selectFileFromDialog(self, self.error_file, "Open file with profile error"))

    def check_fields(self):
        self.grazing_angle_in = congruence.checkStrictlyPositiveNumber(self.grazing_angle_in, "Grazing incidence angle")
        self.p_focus = congruence.checkNumber(self.p_focus, "p focus")
        self.q_focus = congruence.checkNumber(self.q_focus, "q focus")
        self.error_file = congruence.checkFileName(self.error_file)
        self.error_file_oversampling_factor = congruence.checkStrictlyPositiveNumber(self.error_file_oversampling_factor)

    def receive_syned_data(self):
        raise Exception(NotImplementedError)

    def set_input(self, wofry_data):
        if not wofry_data is None:
            if isinstance(wofry_data, WofryData):
                self.input_data = wofry_data
            else:
                self.input_data = WofryData(wavefront=wofry_data)

            if self.is_automatic_execution:
                self.propagate_wavefront()

    def receive_dabam_profile(self, dabam_profile):
        if not dabam_profile is None:
            try:
                file_name = "dabam_profile_" + str(id(self)) + ".dat"

                file = open(file_name, "w")

                for element in dabam_profile:
                    file.write(str(element[0]) + " " + str(element[1]) + "\n")

                file.flush()
                file.close()

                self.error_flag = 1
                self.error_file = file_name
                self.set_visible()

            except Exception as exception:
                QMessageBox.critical(self, "Error", exception.args[0], QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

    def get_optical_element(self):
        if self.error_flag == 0:
            error_file = ""
            mirror_length = self.mirror_length
            mirror_points = self.mirror_points
        else:
            error_file = self.error_file
            mirror_length = 0
            mirror_points = 0

        return WOMirror1D.create_from_keywords(
                    name                         =self.oe_name,
                    shape=self.shape,
                    flip=self.flip,
                    p_focus=self.p_focus,
                    q_focus=self.q_focus,
                    grazing_angle_in=self.grazing_angle_in,
                    p_distance=self.p,
                    q_distance=self.q,
                    zoom_factor=self.magnification_x,
                    error_flag=self.error_flag,
                    error_file=error_file,
                    error_file_oversampling_factor=self.error_file_oversampling_factor,
                    mirror_length=mirror_length,
                    mirror_points=mirror_points,
                    write_profile=self.write_profile)


    def propagate_wavefront(self):
        self.progressBarInit()

        self.wofry_output.setText("")

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        if self.input_data is None: raise Exception("No Input Data")

        self.check_data()

        # propagation to o.e.

        input_wavefront  = self.input_data.get_wavefront()
        beamline         = self.input_data.get_beamline().duplicate()

        optical_element = self.get_optical_element()
        optical_element.name = self.oe_name if not self.oe_name is None else self.windowTitle()

        beamline_element = BeamlineElement(optical_element=optical_element,
                                           coordinates=ElementCoordinates(p=0.0, # to avoid using standard propagators
                                                                          q=0.0, # to avoid using standard propagators
                                                                          angle_radial=numpy.radians(self.angle_radial),
                                                                          angle_azimuthal=numpy.radians(self.angle_azimuthal)))

        beamline.append_beamline_element(beamline_element)

        self.setStatusMessage("Begin Propagation")

        output_wavefront = optical_element.applyOpticalElement(input_wavefront.duplicate())
        self.setStatusMessage("Propagation Completed")

        self.wavefront_to_plot = output_wavefront

        if self.view_type > 0:
            self.initializeTabs()
            self.do_plot_results(80.0)
        else:
            self.progressBarFinished()

        self.send("WofryData", WofryData(beamline=beamline, wavefront=output_wavefront))
        self.send("Trigger", TriggerIn(new_object=True))


        self.wofry_python_script.set_code(beamline.to_python_code())

        self.setStatusMessage("")
        try:
            self.print_intensities()
        except:
            pass

    #
    # overwritten methods
    #

    # overwritten method for specific built-in propagator
    def create_propagation_setting_tab(self):
        self.tab_pro = oasysgui.createTabPage(self.tabs_setting, "Propagation Setting")
        self.zoom_box = oasysgui.widgetBox(self.tab_pro, "", addSpace=False, orientation="vertical", height=90)
        oasysgui.lineEdit(self.zoom_box, self, "magnification_x", "Magnification Factor for interval",
                          labelWidth=260, valueType=float, orientation="horizontal")

    # overwritten methods to append profile plot
    def get_titles(self):
        titles = super().get_titles()
        titles.append("O.E. Profile")
        titles.append("Footprint")
        return titles

    def do_plot_results(self, progressBarValue=80): # OVERWRITTEN

        super().do_plot_results(progressBarValue, closeProgressBar=False)
        if not self.view_type == 0:
            if not self.wavefront_to_plot is None:

                self.progressBarSet(progressBarValue)

                x, y = self.get_optical_element().get_height_profile(self.input_data.get_wavefront())
                self.plot_data1D(x=x,
                                 y=1e6*y,
                                 progressBarValue=progressBarValue + 10,
                                 tabs_canvas_index=4,
                                 plot_canvas_index=4,
                                 calculate_fwhm=False,
                                 title=self.get_titles()[4],
                                 xtitle="Spatial Coordinate along o.e. [m]",
                                 ytitle="Profile Height [$\mu$m]")


                x, y, amplitude = self.get_optical_element().get_footprint(self.input_data.get_wavefront())
                self.plot_data1D(x=x,
                                 y=numpy.abs(amplitude)**2,
                                 progressBarValue=progressBarValue + 10,
                                 tabs_canvas_index=5,
                                 plot_canvas_index=5,
                                 calculate_fwhm=False,
                                 title=self.get_titles()[5],
                                 xtitle="Spatial Coordinate along o.e. [m]",
                                 ytitle="Intensity")



                self.plot_canvas[0].resetZoom()


                self.progressBarFinished()


if __name__ == '__main__':

    from PyQt5.QtWidgets import QApplication


    def create_wavefront():
        #
        # create input_wavefront
        #
        from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D
        input_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=-0.00147, x_max=0.00147,
                                                                             number_of_points=1000)
        input_wavefront.set_photon_energy(250)
        input_wavefront.set_spherical_wave(radius=13.73, center=0, complex_amplitude=complex(1, 0))
        return input_wavefront

    app = QApplication([])
    ow = OWMirror1D()
    ow.set_input(create_wavefront())

    # ow.receive_dabam_profile(numpy.array([[1,2],[3,4]]))
    ow.propagate_wavefront()

    ow.show()
    app.exec_()
    ow.saveSettings()
