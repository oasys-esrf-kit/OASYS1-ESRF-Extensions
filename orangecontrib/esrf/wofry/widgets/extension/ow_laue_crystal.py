import numpy
import sys
from orangewidget.settings import Setting
from orangewidget import gui

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog

from syned.beamline.optical_elements.ideal_elements.ideal_lens import IdealLens
from syned.beamline.optical_elements.crystals.crystal import Crystal, DiffractionGeometry
from wofry.beamline.decorators import OpticalElementDecorator

from wofryimpl.beamline.optical_elements.ideal_elements.ideal_lens import WOIdealLens1D

from orangecontrib.wofry.widgets.gui.ow_optical_element_1d import OWWOOpticalElement1D
from orangecontrib.esrf.util.laue_crystal_focusing import LaueCrystalFocusing
from wofryimpl.beamline.beamline import WOBeamline
#
from oasys.util.oasys_util import EmittingStream, TriggerIn
#
from syned.beamline.element_coordinates import ElementCoordinates
from syned.beamline.beamline_element import BeamlineElement

from orangecontrib.wofry.util.wofry_objects import WofryData

class WOLaueCrystal1D(Crystal, OpticalElementDecorator):
    def __init__(self, name="",
                 crystal_descriptor="Si",
                 hkl=[1, 1, 1],
                 R=2.0, # m
                 poisson_ratio=0.2201,
                 photon_energy=20000.0,
                 thickness=250e-6,  # m
                 p=2.0,  # m
                 q=0.0,  # m
                 alfa_deg=2.0,  # CAN BE POSITIVE OR NEGATIVE)
                 integration_points=500,
                 npoints_x=100,
                 a_factor=1.0,
                 use_fast_hyp1f1=0,
                 source_flag=1,
                 verbose=1,
                 ):
        Crystal.__init__(self,
                         name,
                         material=crystal_descriptor,
                         diffraction_geometry=DiffractionGeometry.LAUE,
                         miller_index_h=int(hkl[0]),
                         miller_index_k=int(hkl[1]),
                         miller_index_l=int(hkl[2]),
                         asymmetry_angle=numpy.radians(90 - alfa_deg),
                         thickness=thickness,
                         )
        self._LaueCrystalFocusing = LaueCrystalFocusing(
            crystal_descriptor=crystal_descriptor,
            hkl=hkl,
            R=R*1e3, # mm
            poisson_ratio=poisson_ratio,
            photon_energy_in_keV=photon_energy*1e-3,
            thickness=thickness*1e3,  # mm
            p=p*1e3,  # mm
            alfa_deg=alfa_deg,  # CAN BE POSITIVE OR NEGATIVE)
            integration_points=integration_points,
            use_fast_hyp1f1=use_fast_hyp1f1,
            verbose=1,
        )
        if verbose: print(self._LaueCrystalFocusing.info())

        self._q = q*1e3 # mm
        self._npoints_x = npoints_x
        self._a_factor  = a_factor
        self._source_flag  = source_flag

    def applyOpticalElement(self, wavefront_in, parameters=None, element_index=None):
        if self._source_flag == 0: # external wavefront
            xx, yy_amplitude, wavefront = self._LaueCrystalFocusing.xscan_for_external_wavefront(
                                                                            Phi=wavefront_in.get_complex_amplitude(),
                                                                            Phi_tau=wavefront_in.get_abscissas() * 1e3,
                                                                            npoints_x=self._npoints_x,
                                                                            a_factor=self._a_factor,
                                                                            a_center=0.0,
                                                                            filename="")
        elif self._source_flag == 1: # point source
            xx, yy_amplitude, wavefront = self._LaueCrystalFocusing.xscan(self._q,
                                                                          npoints_x=self._npoints_x,
                                                                          a_factor=self._a_factor,
                                                                          a_center=0.0,
                                                                          filename="")
        return wavefront

    def qscan(self, qmin=0.0, qmax=10.0, qpoints=100):
        qq, amplitude = self._LaueCrystalFocusing.qscan(qmin=qmin*1e3, qmax=qmax*1e3, npoints=qpoints)
        return qq * 1e-3, amplitude

    def diffraction_profile_angle_scan(self, angle_min=0.0, angle_max=10.0, angle_points=100):
        THETA = numpy.linspace(angle_min, angle_max, angle_points)
        AMPLITUDE = self._LaueCrystalFocusing.diffraction_profile_angle_scan(THETA)
        return THETA, AMPLITUDE

    def to_python_code(self, do_plot=False, add_import_section=False):
        txt  = ""
        txt += "\nfrom orangecontrib.esrf.wofry.widgets.extension.ow_laue_crystal import WOLaueCrystal1D"
        txt += "\n"
        txt += "\noptical_element = WOLaueCrystal1D(name='%s',"         % self.get_name()
        txt += "\n    crystal_descriptor = '%s',"                     % self._LaueCrystalFocusing._crystal_descriptor
        txt += "\n    hkl = %s,"                                      % self._LaueCrystalFocusing._hkl
        txt += "\n    R = %f, # m"                                    % (self._LaueCrystalFocusing._R * 1e-3)
        txt += "\n    poisson_ratio = %f,"                            % self._LaueCrystalFocusing._poisson_ratio
        txt += "\n    photon_energy = %f,"                            % (self._LaueCrystalFocusing._photon_energy_in_keV * 1e3)
        txt += "\n    thickness = %g,  # m,"                          % (self._LaueCrystalFocusing._thickness * 1e-3)
        txt += "\n    p = %f,  # m"                                   % (self._LaueCrystalFocusing._p * 1e-3)
        txt += "\n    q = %f,  # m"                                   % (self._q * 1e-3)
        txt += "\n    alfa_deg = %f,  # CAN BE POSITIVE OR NEGATIVE)" % self._LaueCrystalFocusing._alfa_deg
        txt += "\n    integration_points = %d,"                       % self._LaueCrystalFocusing._integration_points
        txt += "\n    npoints_x = %d,"                                % self._npoints_x
        txt += "\n    a_factor = %f,"                                 % self._a_factor
        txt += "\n    use_fast_hyp1f1 = %d,"                          % self._LaueCrystalFocusing._use_fast_hyp1f1
        txt += "\n    source_flag = %d,"                              % self._source_flag
        txt += "\n    verbose = %d)"                                  % self._LaueCrystalFocusing._verbose

        txt += "\n"
        if self._source_flag == 1:
            txt += "\ninput_wavefront = None"
            txt += "\noutput_wavefront = optical_element.applyOpticalElement(input_wavefront)"

        txt += "\n\n# qq, amplitude = optical_element.qscan(qmin=0.01, qmax=5, qpoints=500)"
        txt += "\n# plot(qq, numpy.abs(amplitude) ** 2, title='q [m]')"

        txt += "\n\n# angle, angle_amplitude = optical_element.diffraction_profile_angle_scan(angle_min=-50e-6, angle_max=50e-6, angle_points=1000)"
        txt += "\n# plot(angle, numpy.abs(angle_amplitude) ** 2, title='Diffraction Profile', xtitle='angle [rad]', ytitle='Intensity [a.u.]')"

        txt += "\n"
        return txt

    #
    # added
    #
    def get_dimension(self):
        return 1

class OWWOLaueCrystal1D(OWWOOpticalElement1D):

    name = "Laue Crystal 1D"
    description = "Wofry: Laue Crystal 1D"
    icon = "icons/laue_crystal.png"
    priority = 301

    source_flag = Setting(1)

    # crystal
    crystal_descriptor = Setting("Si")
    hkl = Setting("[1, 1, 1]")
    thickness_um = Setting(250)
    alfa_deg = Setting(2.0)
    R = Setting(2.0)

    # positioning
    photon_energy = Setting(20000.0)
    npoints_x = Setting(100)
    a_factor = Setting(3.0)


    # advanced
    poisson_ratio = Setting(0.2201)
    integration_points = Setting(500)
    use_fast_hyp1f1 = Setting(0)

    # q-scan
    qscan_flag = Setting(0)
    qmin = Setting(0.0)
    qmax = Setting(10.0)
    qpoints = Setting(100)
    # to save q-scan
    qq = None
    qq_amplitude = None

    # angle-scan (rocking curve)
    angle_scan_flag = Setting(0)
    angle_min = Setting(-50)
    angle_max = Setting(50)
    angle_points = Setting(100)
    # to save q-scan
    angle = None
    angle_amplitude = None

    def __init__(self):
        super().__init__()

    def draw_specific_box(self):

        #
        # source
        #
        self.source_box = oasysgui.widgetBox(self.tab_bas, "Source", addSpace=False, orientation="vertical")

        gui.comboBox(self.source_box, self, "source_flag", label="Input wavefront to crystal", labelWidth=350,
                     items=["Oasys wire",
                            "point source (at p = distance from previous Continuation Plane)",
                            ],
                     sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible)

        self.source_items = oasysgui.widgetBox(self.source_box, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.source_items, self, "photon_energy", "Photon energy [eV]",
                          tooltip="photon_energy", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.source_items, self, "npoints_x", "Points in spatial coordinate",
                          tooltip="npoints_x", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(self.source_box, self, "a_factor", "Window width factor (in units of 'a', default=1)",
                          tooltip="a_factor", labelWidth=330, valueType=float, orientation="horizontal")

        #
        # crystal
        #
        self.crystal_box = oasysgui.widgetBox(self.tab_bas, "Laue Crystal Setting", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.crystal_box, self, "crystal_descriptor", "Crystal descriptor",
                          tooltip="crystal_descriptor", labelWidth=260, valueType=str, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "hkl", "Miller indices [h,k,l]",
                          tooltip="hkl", labelWidth=260, valueType=str, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "thickness_um", "Crystal thickness [um]",
                          tooltip="thickness_um", labelWidth=260, valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "alfa_deg", "Asymmetry angle (symmetric=0) [deg]",
                          tooltip="alfa_deg", labelWidth=260, valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "R", "Curved crystal radius [m]",
                          tooltip="R", labelWidth=260, valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.crystal_box, self, "poisson_ratio", "Poisson ratio for crystal material",
                          tooltip="poisson_ratio", labelWidth=260, valueType=float, orientation="horizontal")


        # self.set_visible()


    # overwrite this method to be used for advanced settings
    def create_propagation_setting_tab(self):

        self.tab_adv = oasysgui.createTabPage(self.tabs_setting, "Additional Setting")

        self.adv_box = oasysgui.widgetBox(self.tab_adv, "Calculation parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.adv_box, self, "integration_points", "Number of points for calculating integrals",
                          tooltip="integration_points", labelWidth=300, valueType=int, orientation="horizontal")

        gui.comboBox(self.adv_box, self, "use_fast_hyp1f1", label="Use asymptotic values for hyp1f1", labelWidth=380,
                     items=["No (exact)","Yes (approx)",],
                     sendSelectedValue=False, orientation="horizontal",
                     )

        ## q-scan
        q_box0 = oasysgui.widgetBox(self.tab_adv, "q-scan", addSpace=False, orientation="vertical")
        gui.comboBox(q_box0, self, "qscan_flag", label="Plot q-scan (slow)", labelWidth=350,
                     items=["No","Yes",],
                     sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible,
                     )

        self.q_box = oasysgui.widgetBox(q_box0, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.q_box, self, "qmin", "q minimum [m] (recommended > 0)",
                          tooltip="qmin", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.q_box, self, "qmax", "q maximum [m]",
                          tooltip="qmax", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.q_box, self, "qpoints", "Number of points for q",
                          tooltip="qpoints", labelWidth=260, valueType=int, orientation="horizontal")

        ## angle-scan
        angle_box0 = oasysgui.widgetBox(self.tab_adv, "angle-scan (diffraction profile)", addSpace=False, orientation="vertical")
        gui.comboBox(angle_box0, self, "angle_scan_flag", label="Plot angle-scan", labelWidth=350,
                     items=["No","Yes",],
                     sendSelectedValue=False, orientation="horizontal",
                     callback=self.set_visible,
                     )

        self.angle_box = oasysgui.widgetBox(angle_box0, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.angle_box, self, "angle_min", "angle min [urad]",
                          tooltip="angle_min", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.angle_box, self, "angle_max", "angle max [urad]",
                          tooltip="angle_max", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.angle_box, self, "angle_points", "Number of points for angle",
                          tooltip="angle_points", labelWidth=260, valueType=int, orientation="horizontal")


        self.set_visible()

    def set_visible(self):
        self.source_items.setVisible(False)
        self.q_box.setVisible(False)
        self.angle_box.setVisible(False)
        #
        self.source_items.setVisible(self.source_flag == 1)
        self.q_box.setVisible(self.qscan_flag == 1)
        self.angle_box.setVisible(self.angle_scan_flag == 1)

    def get_optical_element(self):
        cleaned = self.hkl.strip('[]')
        actual_list_hkl = [int(item.strip()) for item in cleaned.split(',')]

        if self.source_flag == 0:
            wf = self.input_data.get_wavefront()
            photon_energy = wf.get_photon_energy()
            npoints_x = wf.size()
        else:
            photon_energy = self.photon_energy
            npoints_x = self.npoints_x

        oe = WOLaueCrystal1D(name=self.oe_name,
                               crystal_descriptor=self.crystal_descriptor,
                               hkl=actual_list_hkl,
                               R=self.R,  # m
                               poisson_ratio=self.poisson_ratio,
                               photon_energy=photon_energy,
                               thickness=self.thickness_um*1e-6,  # m
                               p=self.p,  # m
                               alfa_deg=self.alfa_deg,  # CAN BE POSITIVE OR NEGATIVE)
                               integration_points=self.integration_points,
                               npoints_x=npoints_x,
                               a_factor=self.a_factor,
                               q=self.q,
                               use_fast_hyp1f1=self.use_fast_hyp1f1,
                               source_flag=self.source_flag,
                               verbose=1,
                               )
        print(oe.info())
        return oe

    def check_data(self):
        super().check_data()

        congruence.checkStrictlyPositiveNumber(self.thickness_um, "Crystal thickness [um]")
        congruence.checkNumber(self.p, "p [m]")
        congruence.checkNumber(self.q, "q [m]")

        if self.source_flag == 0:
            if (self.p != 0) or (self.q != 0):
                if ConfirmDialog.confirmed(parent=self,
                                           message="Wavefront from Oasys wire cannot be propagated externally to the crystal. Set p=q=0.",
                                           title="Confirm Modification",
                                           width=600):
                    self.p = 0.0
                    self.q = 0.0
                else:
                    print(">> **NOT CHANGED** p,q: ", self.p, self.q)


    def receive_specific_syned_data(self, optical_element):
        if not optical_element is None:
            if isinstance(optical_element, Crystal): # TODO
                pass
                # self.focal_x = optical_element._focal_x
            else:
                raise Exception("Syned Data not correct: Optical Element is not a Crystal")
        else:
            raise Exception("Syned Data not correct: Empty Optical Element")

    #
    # overwritten methods
    #

    # overwritten methods to append profile plot
    def get_titles(self):
        titles = super().get_titles()
        titles.append("q-scan")
        titles.append("angle-scan")
        return titles

    def do_plot_results(self, progressBarValue=80): # OVERWRITTEN
        super().do_plot_results(progressBarValue, closeProgressBar=False)

        if self.qscan_flag:
            if (self.qq is not None) and (self.qq_amplitude is not None):
                self.progressBarSet(progressBarValue + 5)
                self.plot_data1D(x=self.qq,
                                 y=numpy.abs(self.qq_amplitude) ** 2,
                                 progressBarValue=progressBarValue + 10,
                                 tabs_canvas_index=4,
                                 plot_canvas_index=4,
                                 calculate_fwhm=False,
                                 title=self.get_titles()[4],
                                 xtitle="q (distance from crystal) [m]",
                                 ytitle="Intensity [a.u.]")

        if self.angle_scan_flag:
            if (self.angle is not None) and (self.angle_amplitude is not None):
                self.progressBarSet(progressBarValue + 5)
                self.plot_data1D(x=self.angle * 1e6,
                                 y=numpy.abs(self.angle_amplitude) ** 2,
                                 progressBarValue=progressBarValue + 10,
                                 tabs_canvas_index=5,
                                 plot_canvas_index=5,
                                 calculate_fwhm=True,
                                 title=self.get_titles()[5],
                                 xtitle="angle [urad]",
                                 ytitle="Intensity [a.u.]")

        self.progressBarFinished()

    def propagate_wavefront(self):

        self.progressBarInit()

        self.wofry_output.setText("")

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        current_index = self.tabs.currentIndex()

        try:
            self.check_data()

            optical_element = self.get_optical_element()
            optical_element.name = self.oe_name if not self.oe_name is None else self.windowTitle()

            beamline_element = BeamlineElement(optical_element=optical_element,
                                               coordinates=ElementCoordinates(p=self.p,
                                                                              q=self.q,
                                                                              angle_radial=numpy.radians(self.angle_radial),
                                                                              angle_azimuthal=numpy.radians(self.angle_azimuthal)))

            if self.source_flag == 0:
                beamline = self.input_data.get_beamline().duplicate()
                beamline.append_beamline_element(beamline_element, {})
            elif self.source_flag == 1:
                beamline = WOBeamline(light_source=optical_element)

            self.wofry_python_script.set_code(beamline.to_python_code())

            self.setStatusMessage("Begin Propagation")

            if self.source_flag == 0:
                input_wavefront  = self.input_data.get_wavefront()
                output_wavefront = optical_element.applyOpticalElement(input_wavefront)
            else:
                output_wavefront = optical_element.applyOpticalElement(None)

            self.setStatusMessage("Propagation Completed")

            self.wavefront_to_plot = output_wavefront

            #
            # qscan
            #
            if self.qscan_flag:
                print("\n########################################################")
                print("\n                        Q-scan                          ")
                print("\n########################################################")
                # self.progressBarSet(progressBarValue + 5)

                optical_element = self.get_optical_element()
                qq, amplitude = optical_element.qscan(qmin=self.qmin, qmax=self.qmax, qpoints=self.qpoints)
                self.qq = qq
                self.qq_amplitude = amplitude
            else:
                pass

            #
            # qscan
            #
            if self.angle_scan_flag:
                print("\n########################################################")
                print("\n                    angle-scan                          ")
                print("\n########################################################")
                # self.progressBarSet(progressBarValue + 5)

                optical_element = self.get_optical_element()
                angle, amplitude = optical_element.diffraction_profile_angle_scan(angle_min=self.angle_min * 1e-6,
                                                                                  angle_max=self.angle_max * 1e-6,
                                                                                  angle_points=self.angle_points)
                self.angle = angle
                self.angle_amplitude = amplitude
            else:
                pass
            #
            # plots
            #
            if self.view_type > 0:
                self.initializeTabs()
                self.do_plot_results()
            else:
                self.progressBarFinished()

            self.send("WofryData", WofryData(beamline=beamline, wavefront=output_wavefront))
            self.send("Trigger", TriggerIn(new_object=True))

            self.setStatusMessage("")

            try:    self.print_intensities()
            except: pass


        except: # except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

        self.tabs.setCurrentIndex(current_index)

    def set_input(self, wofry_data): # OVERWRITTEN
        self.source_flag = 0
        super().set_input(wofry_data=wofry_data)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    def get_example_wofry_data():
        from wofryimpl.propagator.light_source import WOLightSource
        from wofryimpl.beamline.beamline import WOBeamline
        from orangecontrib.wofry.util.wofry_objects import WofryData

        light_source = WOLightSource(dimension=1,
                                     initialize_from=0,
                                     range_from_h=-0.001,
                                     range_to_h=0.001,
                                     number_of_points_h=500,
                                     energy=10000.0,
                                     )

        return WofryData(wavefront=light_source.get_wavefront(),
                           beamline=WOBeamline(light_source=light_source))

    a = QApplication(sys.argv)
    ow = OWWOLaueCrystal1D()
    # ow.set_input(get_example_wofry_data())
    # ow.p = 29.0

    ow.show()
    a.exec_()
    ow.saveSettings()
