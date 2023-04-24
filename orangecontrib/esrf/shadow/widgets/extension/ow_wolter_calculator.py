import os, sys
import numpy

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QLabel, QSizePolicy
from PyQt5.QtGui import QTextCursor, QPixmap

import orangecanvas.resources as resources

from orangewidget import gui, widget
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui


from orangecontrib.esrf.shadow.util.wolter1 import recipe1, recipe2, recipe3, recipe4, rotate_and_shift_quartic
from orangecontrib.esrf.shadow.util.shadow_objects import ConicCoefficientsPreProcessorData

from oasys.util.oasys_util import EmittingStream

class OWWolterCalculator(OWWidget):
    name = "Wolter Calculator"
    id = "WolterCalculator"
    description = "Calculation of coefficients for Wolter systems"
    icon = "icons/wolter2.png"
    author = "Manuel Sanchez del Rio"
    maintainer_email = "srio@esrf.eu"
    priority = 7
    category = ""
    keywords = ["oasys", "wolter", "telescope", "advanced KB"]

    outputs = [{"name":"ConicCoeff_1_PreProcessor_Data",
                "type":ConicCoefficientsPreProcessorData,
                "doc":"ConicCoeff #1 PreProcessor Data",
                "id":"ConicCoeff_1_PreProcessor_Data"},
               {"name": "ConicCoeff_2_PreProcessor_Data",
                "type": ConicCoefficientsPreProcessorData,
                "doc": "ConicCoeff #2 PreProcessor Data",
                "id": "ConicCoeff_2_PreProcessor_Data"},
               ]

    want_main_area = True
    want_control_area = True

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 650 #18

    #################

    setup_type = Setting(0)
    same_angle = Setting(1)

    p1 = Setting(2.1)
    q1 = Setting(1.05)
    p2 = Setting(1.904995)
    q2 = Setting(10.0)
    distance = Setting(0.1)

    theta1 = Setting(0.1134464014)
    theta2 = Setting(0.003)

    ratio_hyp = Setting(1.1)  # ratio_hyp = q_hyp / p_ell > 1.0
    m_hyp = Setting(1 / 3)

    # to send to shadow
    conic_coefficients1 = Setting([0] * 10)
    conic_coefficients2 = Setting([0] * 10)
    source_plane_distance1 = Setting(0.0)
    source_plane_distance2 = Setting(0.0)
    image_plane_distance1 = Setting(0.0)
    image_plane_distance2 = Setting(0.0)
    angles_respect_to1 = Setting(0)
    angles_respect_to2 = Setting(0)
    incidence_angle_deg1 = Setting(0.0)
    incidence_angle_deg2 = Setting(0.0)
    reflection_angle_deg1 = Setting(0.0)
    reflection_angle_deg2 = Setting(0.0)
    mirror_orientation_angle1 = Setting(0)
    mirror_orientation_angle2 = Setting(0)

    npoints = Setting(200)
    y_length = Setting(0.3)

    sagittal_flat = Setting(0)

    tab=[]

    usage_path = os.path.join(resources.package_dirname("orangecontrib.esrf.shadow.widgets.extension"), "icons", "use_wolter.png")

    def __init__(self):
        super().__init__()

        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width() * 0.05),
                               round(geom.height() * 0.05),
                               round(min(geom.width() * 0.98, self.MAX_WIDTH)),
                               round(min(geom.height() * 0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        tab_calc = oasysgui.createTabPage(tabs_setting, "Calculate")
        # tab_out = oasysgui.createTabPage(tabs_setting, "Plot")
        tab_usa = oasysgui.createTabPage(tabs_setting, "Use of the Widget")


        #
        #-------------------- calculate
        #

        button = gui.button(tab_calc, self, "Calculate", callback=self.calculate)

        tab_step_1 = oasysgui.widgetBox(tab_calc, "Calculation Parameters", addSpace=True, orientation="vertical", height=600)

        box = oasysgui.widgetBox(tab_step_1, "setup inputs", orientation="vertical")

        gui.comboBox(box, self, "setup_type", label="Setup type", labelWidth=260,
                     items=["Wolter-I variable throw",
                            "Wolter-I fixed throw",
                            ],
                     callback=self.update_panel, sendSelectedValue=False, orientation="horizontal")

        self.w_p1 = oasysgui.lineEdit(box, self, "p1", "Distance focus11-oe1 (p1) [m]", labelWidth=210, valueType=float, orientation="horizontal")
        self.w_q1 = oasysgui.lineEdit(box, self, "q1", "Distance oe1-focus12 (q1) [m]", labelWidth=210, valueType=float, orientation="horizontal")
        self.w_p2 = oasysgui.lineEdit(box, self, "p2", "Distance focus21-oe2 (p2) [m]", labelWidth=210, valueType=float, orientation="horizontal")
        self.w_q2 = oasysgui.lineEdit(box, self, "q2", "Distance oe2-focus22 (q2) [m]", labelWidth=210, valueType=float, orientation="horizontal")
        self.w_distance = oasysgui.lineEdit(box, self, "distance", "Distance oe1-oe2 [m]", labelWidth=210, valueType=float, orientation="horizontal")

        self.w_ratio_hyp = oasysgui.lineEdit(box, self, "ratio_hyp", "Ratio hyperbola=q2/p2>1", labelWidth=210, valueType=float, orientation="horizontal")
        self.w_m_hyp = oasysgui.lineEdit(box, self, "m_hyp", "Magnification hyperbola=p2/q2", labelWidth=220,
                                             valueType=float, orientation="horizontal")

        gui.comboBox(box, self, "sagittal_flat", label="2D/1D focusing", labelWidth=260,
                     items=["2D (revolution symmetry)",
                            "1D (flat in sagittal)",
                            ], sendSelectedValue=False, orientation="horizontal")

        gui.separator(box)

        box_2 = oasysgui.widgetBox(tab_step_1, "angles", orientation="vertical")

        gui.comboBox(box_2, self, "same_angle", label="Same grazing angles", labelWidth=260,
                     items=["No",
                            "Yes",
                            ],
                     callback=self.update_panel, sendSelectedValue=False, orientation="horizontal")

        self.w_theta1 = oasysgui.lineEdit(box_2, self, "theta1", "Grazing angle oe1 [rad]", labelWidth=210, valueType=float, orientation="horizontal", callback=self.update_panel)
        self.w_theta2 = oasysgui.lineEdit(box_2, self, "theta2", "Grazing angle oe2 [rad]", labelWidth=210, valueType=float, orientation="horizontal")



        box_3 = oasysgui.widgetBox(tab_step_1, "For plotting mirror profiles", orientation="vertical")
        oasysgui.lineEdit(box_3, self, "npoints", "Points", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(box_3, self, "y_length", "Mirror length [m]", labelWidth=260, valueType=int, orientation="horizontal")

        #
        #-------------------- Use
        #

        tab_usa.setStyleSheet("background-color: white;")

        usage_box = oasysgui.widgetBox(tab_usa, "", addSpace=True, orientation="horizontal")

        label = QLabel("")
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setPixmap(QPixmap(self.usage_path))

        usage_box.layout().addWidget(label)

        #
        #
        #

        gui.rubber(self.controlArea)

        self.initializeTabs()

        self.update_panel()

        gui.rubber(self.mainArea)

    def update_panel(self):
        self.w_p1.setVisible(True)
        self.w_q1.setVisible(True)
        self.w_p2.setVisible(True)
        self.w_q2.setVisible(True)
        self.w_theta1.setVisible  (True)
        self.w_theta2.setVisible  (True)
        self.w_distance.setVisible(True)

        self.w_ratio_hyp.setEnabled(False)
        self.w_m_hyp.setEnabled(False)

        if self.setup_type == 0:
            self.w_p1.setEnabled(True)
            self.w_q1.setEnabled(True)
            self.w_p2.setEnabled(False)
            self.w_q2.setEnabled(False)
            self.w_theta1.setEnabled(True)
            self.w_theta2.setEnabled(True)
            self.w_distance.setEnabled(True)
        elif self.setup_type == 1:
            self.w_p1.setEnabled(True)
            self.w_q1.setEnabled(False)
            self.w_p2.setEnabled(True)
            self.w_q2.setEnabled(False)
            self.w_theta1.setEnabled(True)
            self.w_theta2.setEnabled(True)
            self.w_distance.setEnabled(True)
        elif self.setup_type == 2:
            self.w_p1.setEnabled(True)
            self.w_p2.setEnabled(True)
            self.w_p2.setEnabled(True)
            self.w_q2.setEnabled(False)
            self.w_theta1.setEnabled(True)
            self.same_angle = True
            self.w_distance.setEnabled(False)
        elif self.setup_type == 3:
            self.w_p1.setEnabled(True)
            self.w_q1.setEnabled(False)
            self.w_p2.setEnabled(True)
            self.w_q2.setEnabled(False)
            self.w_theta1.setEnabled(True)
            self.same_angle = True
            self.w_distance.setEnabled(False)
        else:
            raise Exception(NotImplementedError)


        if self.same_angle:
            self.theta2 = self.theta1
            self.w_theta1.setEnabled(True)
            self.w_theta2.setEnabled(False)
        else:
            self.w_theta1.setEnabled(True)
            self.w_theta2.setEnabled(True)

        if self.setup_type == 0:
            self.w_ratio_hyp.setEnabled(True)
            self.w_m_hyp.setEnabled(False)
        elif self.setup_type == 1:
            self.w_ratio_hyp.setEnabled(False)
            self.w_m_hyp.setEnabled(True)
        elif self.setup_type == 2:
            self.w_ratio_hyp.setEnabled(False)
            self.w_m_hyp.setEnabled(False)
            self.q2 = self.q1
            self.distance = 0.0
        elif self.setup_type == 3:
            self.w_ratio_hyp.setEnabled(False)
            self.w_m_hyp.setEnabled(False)
            self.q1 = 0
            self.q2 = 0
            self.distance = 0.0
        else:
            raise Exception(NotImplementedError)


    def calculate(self):
        try:
            self.shadow_output.setText("")
            self.design_output.setText("")

            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            self.check_fields()

            results_txt = ""
            print("####################################################")
            print("# DESIGN PHASE")
            print("####################################################\n")

            if self.same_angle:
                theta_hyp = self.theta1
            else:
                theta_hyp = self.theta2

            if self.setup_type == 0:

                print("||||||||||||||||| theta_hyp: ", theta_hyp)
                tkt_ell, tkt_hyp = recipe1(
                    p_ell=self.p1,
                    q_ell=self.q1,
                    distance=self.distance,
                    theta=self.theta1,
                    theta_hyp=theta_hyp,
                    ratio_hyp=self.ratio_hyp,
                )
                print("||||||||||||||||| tkt_hyp: ", tkt_hyp)
                print("\n\n>>>>>\n\n")

                # correct for incidence in the negative Y
                print(">>> corrected hyperbola for incidence in the negative Y ")
                ccc1 = tkt_hyp['ccc']
                ccc2 = rotate_and_shift_quartic(ccc1, omega=0.0, theta=0.0, phi=numpy.pi, )
                tkt_hyp['ccc'] = ccc2
                print(ccc2)

                # 1D focusing (flat in sagittal)
                # xx  yy  zz  xy  yz  xz  x   y   z   0
                #  0   1   2   3   4   5  6   7   8   9
                if self.sagittal_flat:
                    print(">>> corrected: flat in sagittal (1D focusing)")
                    tkt_ell['ccc'][0] = 0
                    tkt_ell['ccc'][3] = 0
                    tkt_ell['ccc'][5] = 0
                    tkt_ell['ccc'][6] = 0

                    tkt_hyp['ccc'][0] = 0
                    tkt_hyp['ccc'][3] = 0
                    tkt_hyp['ccc'][5] = 0
                    tkt_hyp['ccc'][6] = 0

                # round
                for i in range(10):
                    if numpy.abs(tkt_ell['ccc'][i]) < 1e-14: tkt_ell['ccc'][i] = 0
                    if numpy.abs(tkt_hyp['ccc'][i]) < 1e-14: tkt_hyp['ccc'][i] = 0

                self.p2     = tkt_hyp['p']
                self.q2     = tkt_hyp['q']
                self.theta2 = tkt_hyp['theta_grazing']
                self.m_hyp  = 1/self.ratio_hyp

                print(tkt_ell)
                print(tkt_hyp)

                source_plane_distance_1 = self.p1
                image_plane_distance_1 = self.distance / 2
                angles_respect_to_1 = 0
                incidence_angle_deg_1 = 90 - numpy.degrees(self.theta1)
                reflection_angle_deg_1 = 90 - numpy.degrees(self.theta1)
                mirror_orientation_angle_1 = None

                source_plane_distance_2 = self.distance / 2
                image_plane_distance_2 = self.p2
                angles_respect_to_2 = 0
                incidence_angle_deg_2 = 90 - numpy.degrees(theta_hyp)
                reflection_angle_deg_2 =  90 - numpy.degrees(theta_hyp)
                mirror_orientation_angle_2 = None

                # round (cosmetics)
                self.p2     = numpy.round(self.p2    , 5)
                self.q2     = numpy.round(self.q2    , 5)
                # self.theta2 = numpy.round(self.theta2, 5)
                self.m_hyp  = numpy.round(self.m_hyp , 5)


            elif self.setup_type == 1:

                tkt_ell, tkt_hyp = recipe2(
                    p_ell=self.p1,
                    distance=self.distance,
                    p_hyp=self.p2,
                    theta=self.theta1,
                    theta_hyp=theta_hyp,
                    m_hyp=self.m_hyp,
                    verbose=1,
                )

                print("\n\n>>>>>\n\n")

                # correct for incidence in the negative Y
                print(">>> corrected hyperbola for incidence in the negative Y ")
                ccc1 = tkt_hyp['ccc']
                ccc2 = rotate_and_shift_quartic(ccc1, omega=0.0, theta=0.0, phi=numpy.pi, )
                tkt_hyp['ccc'] = ccc2
                print(ccc2)

                # 1D focusing (flat in sagittal)
                if self.sagittal_flat:
                    print(">>> corrected: flat in sagittal (1D focusing)")

                    tkt_ell['ccc'][0] = 0
                    tkt_ell['ccc'][3] = 0
                    tkt_ell['ccc'][5] = 0
                    tkt_ell['ccc'][6] = 0

                    tkt_hyp['ccc'][0] = 0
                    tkt_hyp['ccc'][3] = 0
                    tkt_hyp['ccc'][5] = 0
                    tkt_hyp['ccc'][6] = 0

                # round
                for i in range(10):
                    if numpy.abs(tkt_ell['ccc'][i]) < 1e-14: tkt_ell['ccc'][i] = 0
                    if numpy.abs(tkt_hyp['ccc'][i]) < 1e-14: tkt_hyp['ccc'][i] = 0

                self.q1 = tkt_ell['p']
                self.q2 = tkt_hyp['q']
                self.theta2 = tkt_hyp['theta_grazing']
                self.rat_hyp = 1/self.m_hyp

                print(tkt_ell)
                print(tkt_hyp)


                source_plane_distance_1 = self.p1
                image_plane_distance_1 = self.distance / 2
                angles_respect_to_1 = 0
                incidence_angle_deg_1 = 90 - numpy.degrees(self.theta1)
                reflection_angle_deg_1 = 90 - numpy.degrees(self.theta1)
                mirror_orientation_angle_1 = None

                if self.same_angle:
                    theta_hyp = self.theta1
                else:
                    theta_hyp = self.theta2

                source_plane_distance_2 = self.distance / 2
                image_plane_distance_2 = self.p2
                angles_respect_to_2 = 0
                incidence_angle_deg_2 = 90 - numpy.degrees(theta_hyp)
                reflection_angle_deg_2 =  90 - numpy.degrees(theta_hyp)
                mirror_orientation_angle_2 = None

                # round (cosmetics)
                self.p2     = numpy.round(self.p2    , 5)
                self.q2     = numpy.round(self.q2    , 5)
                # self.theta2 = numpy.round(self.theta2, 5)
                self.m_hyp  = numpy.round(self.m_hyp , 5)

            else:
                raise Exception(NotImplementedError)

            try:
                results_txt += "\nellipse a=%f" % tkt_ell['a']
                results_txt += "\nellipse b=%f" % tkt_ell['b']
                results_txt += "\nellipse c=%f" % tkt_ell['c']
                results_txt += "\nhyperbola a=%f" % tkt_hyp['a']
                results_txt += "\nhyperbola b=%f" % tkt_hyp['b']
                results_txt += "\nhyperbola c=%f" % tkt_hyp['c']
            except:
                pass

            ccc_ell = tkt_ell['ccc']
            ccc_hyp = tkt_hyp['ccc']

            self.conic_coefficients1 = ccc_ell
            self.conic_coefficients2 = ccc_hyp

            # ccc_hyp = rotate_and_shift_quartic(ccc_hyp, omega=0.0, theta=0.0, phi=numpy.pi, )
            if self.sagittal_flat:
                ccc_ell_nor = ccc_ell[1]
                ccc_hyp_nor = ccc_hyp[1]
            else:
                ccc_ell_nor = ccc_ell[0]
                ccc_hyp_nor = ccc_hyp[0]

            results_txt += "\n\n\n    oe1(normalized)      oe2(normalized)"
            for i in range(10):
                results_txt += "\nccc[%d]       %10.4g       %10.4g  " % (i,
                                                                    ccc_ell[i]/ccc_ell_nor, ccc_hyp[i]/ccc_hyp_nor)

            results_txt += "\n\n\n    oe1           oe2 "
            for i in range(10):
                results_txt += "\nccc[%d]       %10.4g       %10.4g  " % (i, ccc_ell[i], ccc_hyp[i])

            #results_txt += "\nthrow=%f m" % (self.p1+self.distance+self.p2)
            self.design_output.setText(results_txt)

            #
            # plot data
            #

            self.progressBarInit()

            # plot oe 1
            y, z1a, z1b = self.height(oe=1)
            y, z2a, z2b = self.height(oe=2)
            self.plot_multi_data1D([y,y,y,y], [z1a,z1b,z2a,z2b],
                                  10, 2, 0,
                                  title="mirror 1", xtitle="y [m]", ytitle="z [m]",
                                  ytitles=["Mirror 1 solution 1","Mirror 1 solution 2","Mirror 2 solution 1","Mirror 2 solution 2"],
                                  colors=['blue','red','green','k'],
                                  replace=True,
                                  control=False,
                                  xrange=None,
                                  yrange=None,
                                  symbol=['','','',''],
                                )

            self.progressBarFinished()
            #
            # send data
            #
            print("\n\n\n\n")
            print("####################################################")
            print("# RAY-TRACING PHASE")
            print("####################################################\n")

            print("---------------------- first mirror:")
            print("sending ccc ell: ", self.conic_coefficients1)
            if source_plane_distance_1    is not None: print("sending source_plane_distance=", source_plane_distance_1)
            if image_plane_distance_1     is not None: print("sending image_plane_distance=", image_plane_distance_1)
            if angles_respect_to_1        is not None: print("sending angles_respect_to=", angles_respect_to_1)
            if incidence_angle_deg_1      is not None: print("sending incidence_angle_deg=", incidence_angle_deg_1)
            if reflection_angle_deg_1     is not None: print("sending reflection_angle_deg=", reflection_angle_deg_1)
            if mirror_orientation_angle_1 is not None: print("sending mirror_orientation_angle=", mirror_orientation_angle_1)

            print("---------------------- second mirror:")
            print("sending ccc hyp: ", self.conic_coefficients2)
            if source_plane_distance_2    is not None: print("sending source_plane_distance=", source_plane_distance_2)
            if image_plane_distance_2     is not None: print("sending image_plane_distance=", image_plane_distance_2)
            if angles_respect_to_2        is not None: print("sending angles_respect_to=", angles_respect_to_2)
            if incidence_angle_deg_2      is not None: print("sending incidence_angle_deg=", incidence_angle_deg_2)
            if reflection_angle_deg_2     is not None: print("sending reflection_angle_deg=", reflection_angle_deg_2)
            if mirror_orientation_angle_2 is not None: print("sending mirror_orientation_angle=", mirror_orientation_angle_2)

            self.send("ConicCoeff_1_PreProcessor_Data", ConicCoefficientsPreProcessorData(
                conic_coefficient_0 = self.conic_coefficients1[0],
                conic_coefficient_1 = self.conic_coefficients1[1],
                conic_coefficient_2 = self.conic_coefficients1[2],
                conic_coefficient_3 = self.conic_coefficients1[3],
                conic_coefficient_4 = self.conic_coefficients1[4],
                conic_coefficient_5 = self.conic_coefficients1[5],
                conic_coefficient_6 = self.conic_coefficients1[6],
                conic_coefficient_7 = self.conic_coefficients1[7],
                conic_coefficient_8 = self.conic_coefficients1[8],
                conic_coefficient_9 = self.conic_coefficients1[9],
                source_plane_distance = source_plane_distance_1,
                image_plane_distance = image_plane_distance_1,
                angles_respect_to = angles_respect_to_1,
                incidence_angle_deg = incidence_angle_deg_1,
                reflection_angle_deg = reflection_angle_deg_1,
                mirror_orientation_angle = mirror_orientation_angle_1,
                ))
            self.send("ConicCoeff_2_PreProcessor_Data", ConicCoefficientsPreProcessorData(
                conic_coefficient_0=self.conic_coefficients2[0],
                conic_coefficient_1=self.conic_coefficients2[1],
                conic_coefficient_2=self.conic_coefficients2[2],
                conic_coefficient_3=self.conic_coefficients2[3],
                conic_coefficient_4=self.conic_coefficients2[4],
                conic_coefficient_5=self.conic_coefficients2[5],
                conic_coefficient_6=self.conic_coefficients2[6],
                conic_coefficient_7=self.conic_coefficients2[7],
                conic_coefficient_8=self.conic_coefficients2[8],
                conic_coefficient_9=self.conic_coefficients2[9],
                source_plane_distance = source_plane_distance_2,
                image_plane_distance = image_plane_distance_2,
                angles_respect_to = angles_respect_to_2,
                incidence_angle_deg = incidence_angle_deg_2,
                reflection_angle_deg = reflection_angle_deg_2,
                mirror_orientation_angle = mirror_orientation_angle_2,
                ))

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 str(exception),
                                 QMessageBox.Ok)


    def initializeTabs(self):
        self.tabs = oasysgui.tabWidget(self.mainArea)

        self.tab = [oasysgui.createTabPage(self.tabs, "Design parameters"),
                    oasysgui.createTabPage(self.tabs, "Output"),
                    oasysgui.createTabPage(self.tabs, "Mirror Profiles"),
        ]

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)


        self.design_output = oasysgui.textArea()
        tmp2 = oasysgui.widgetBox(self.tab[0], "Design output", addSpace=True, orientation="horizontal", height = self.IMAGE_HEIGHT-4) #, width=410)
        tmp2.layout().addWidget(self.design_output)

        self.shadow_output = oasysgui.textArea() #height=self.IMAGE_HEIGHT-5, width=400)
        tmp1 = oasysgui.widgetBox(self.tab[1], "System output", addSpace=True, orientation="horizontal", height = self.IMAGE_HEIGHT-4) #, width=410)
        tmp1.layout().addWidget(self.shadow_output)

        #
        self.plot_canvas = [None]

        self.plot_canvas[0] = oasysgui.plotWindow(roi=False, control=False, position=True)
        self.plot_canvas[0].setDefaultPlotLines(True)
        self.plot_canvas[0].setActiveCurveColor(color='blue')
        self.plot_canvas[0].setGraphYLabel("Z [nm]")
        self.plot_canvas[0].setGraphTitle("oe Profiles")
        self.plot_canvas[0].setInteractiveMode(mode='zoom')

        # self.plot_canvas[1] = oasysgui.plotWindow(roi=False, control=False, position=True)
        # self.plot_canvas[1].setDefaultPlotLines(True)
        # self.plot_canvas[1].setActiveCurveColor(color='blue')
        # self.plot_canvas[1].setGraphYLabel("Z [nm]")
        # self.plot_canvas[1].setGraphTitle("oe2 Profile")
        # self.plot_canvas[1].setInteractiveMode(mode='zoom')


        self.tab[2].layout().addWidget(self.plot_canvas[0])
        # self.tab[3].layout().addWidget(self.plot_canvas[1])

        self.tabs.setCurrentIndex(0)

    def check_fields(self):
        pass

    def writeStdOut(self, text):
        cursor = self.shadow_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.shadow_output.setTextCursor(cursor)
        self.shadow_output.ensureCursorVisible()

    def height(self, oe=1):

        if oe == 1:
            ccc = self.conic_coefficients1
        elif oe == 2:
            ccc = self.conic_coefficients2

        y = numpy.linspace(-self.y_length / 2, self.y_length / 2, self.npoints)
        x = 0

        aa = ccc[2]
        bb = ccc[4] * y + ccc[5] * x + ccc[8]
        cc = ccc[0] * x**2 + ccc[1] * y**2 + ccc[3] * x * y + \
            ccc[6] * x + ccc[7] * y + ccc[9]

        if aa != 0:
            discr = bb**2 - 4 * aa * cc + 0j
            s1 = (-bb + numpy.sqrt(discr)) / 2 / aa
            s2 = (-bb - numpy.sqrt(discr)) / 2 / aa
        else:
            s1 = -cc / bb
            s2 = s1

        return y, numpy.real(s1), numpy.real(s2)


    def plot_multi_data1D(self, x_list, y_list,
                    progressBarValue, tabs_canvas_index, plot_canvas_index,
                    title="", xtitle="",
                    ytitle="",
                    ytitles= [""],
                    colors = ['green'],
                    replace=True,
                    control=False,
                    xrange=None,
                    yrange=None,
                    symbol=['']):

        if len(y_list) != len(ytitles):
            ytitles = ytitles * len(y_list)

        if len(y_list) != len(colors):
            colors = colors * len(y_list)
        if len(y_list) != len(symbol):
            symbols = symbol * len(y_list)
        else:
            symbols = symbol

        if tabs_canvas_index is None: tabs_canvas_index = 0 #back compatibility?

        self.tab[tabs_canvas_index].layout().removeItem(self.tab[tabs_canvas_index].layout().itemAt(0))

        self.plot_canvas[plot_canvas_index] = oasysgui.plotWindow(parent=None,
                                                                  backend=None,
                                                                  resetzoom=True,
                                                                  autoScale=False,
                                                                  logScale=True,
                                                                  grid=True,
                                                                  curveStyle=True,
                                                                  colormap=False,
                                                                  aspectRatio=False,
                                                                  yInverted=False,
                                                                  copy=True,
                                                                  save=True,
                                                                  print_=True,
                                                                  control=control,
                                                                  position=True,
                                                                  roi=False,
                                                                  mask=False,
                                                                  fit=False)


        self.plot_canvas[plot_canvas_index].setDefaultPlotLines(True)
        self.plot_canvas[plot_canvas_index].setActiveCurveColor(color=colors[0])
        self.plot_canvas[plot_canvas_index].setGraphXLabel(xtitle)
        self.plot_canvas[plot_canvas_index].setGraphYLabel(ytitle)

        self.tab[tabs_canvas_index].layout().addWidget(self.plot_canvas[plot_canvas_index])


        for i in range(len(y_list)):
            # print(">>>>>>>>>>>>>>>>>>>> ADDING PLOT INDEX", i, x_list[i].shape, y_list[i].shape,ytitles[i],symbols[i],colors[i])
            self.plot_canvas[plot_canvas_index].addCurve(x_list[i], y_list[i],
                                         ytitles[i],
                                         xlabel=xtitle,
                                         ylabel=ytitle,
                                         symbol=symbols[i],
                                         color=colors[i])
        #
        self.plot_canvas[plot_canvas_index].getLegendsDockWidget().setFixedHeight(150)
        self.plot_canvas[plot_canvas_index].getLegendsDockWidget().setVisible(True)
        self.plot_canvas[plot_canvas_index].setActiveCurve(ytitles[0])
        self.plot_canvas[plot_canvas_index].replot()


        if xrange is not None:
            self.plot_canvas[plot_canvas_index].setGraphXLimits(xrange[0],xrange[1])
        if yrange is not None:
            self.plot_canvas[plot_canvas_index].setGraphYLimits(yrange[0],yrange[1])

        self.progressBarSet(progressBarValue)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OWWolterCalculator()
    w.show()
    app.exec()
    w.saveSettings()
