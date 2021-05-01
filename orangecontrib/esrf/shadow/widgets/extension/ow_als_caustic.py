from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.util.oasys_util import EmittingStream

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPlot
from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.esrf.shadow.widgets.gui.plots import plot_data1D, plot_data2D
from srxraylib.util.h5_simple_writer import H5SimpleWriter

import numpy
import sys


class ESRFCaustic(AutomaticElement):

    name = "Caustic Generator"
    description = "Shadow: Caustic Generator"
    icon = "icons/caustic.png"
    maintainer = "APS+ESRF team"
    maintainer_email = "srio@esrf.eu, srio@lbl.gov"
    priority = 5
    category = "Data Display Tools"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645
    #
    # CONTROL_AREA_WIDTH = 405
    # TABS_AREA_HEIGHT = 650



    want_main_area=1
    want_control_area = 1

    input_beam=None

    npoints_x = Setting(1000) # in X and Z
    npoints_z = Setting(101)  # in X and Z
    npositions = Setting(300) # in Y



    y_min=Setting(-5.0)
    y_max=Setting(5.0)

    no_lost  = Setting(1)
    use_reflectivity = Setting(1)
    shadow_column = Setting(0)

    x_min = Setting(-0.2)
    x_max = Setting( 0.2)

    save_h5_file_flag = Setting(0)
    save_h5_file_name = Setting("caustic.h5")

    def __init__(self, show_automatic_box=True):
        super().__init__()

        try:
            tmp = self.workspace_units_label
        except:
            self.workspace_units = 0
            self.workspace_units_label = "m"
            self.workspace_units_to_m = 1.0
            self.workspace_units_to_cm = 100.0
            self.workspace_units_to_mm = 1000.0

        gui.button(self.controlArea, self, "Calculate", callback=self.calculate, height=45)

        general_box = oasysgui.widgetBox(self.controlArea, "General Settings", addSpace=True, orientation="vertical",)
                                         # width=self.CONTROL_AREA_WIDTH-8, height=400)


        gui.comboBox(general_box, self, "no_lost", label="Rays",labelWidth=220,
                                     items=["All rays","Good only","Lost only"],
                                     sendSelectedValue=False, orientation="horizontal")


        gui.comboBox(general_box, self, "use_reflectivity", label="Include reflectivity",labelWidth=220,
                                     items=["No","Yes"],
                                     sendSelectedValue=False, orientation="horizontal")

        box_y = oasysgui.widgetBox(general_box, "Propagation along Y (col 2)", addSpace=True, orientation="vertical", height=100)
        oasysgui.lineEdit(box_y, self, "npositions", "Y Points", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(box_y, self, "y_min", "Y min"+ " [" + self.workspace_units_label + "]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(box_y, self, "y_max", "Y max"+ " [" + self.workspace_units_label + "]", labelWidth=260, valueType=float, orientation="horizontal")


        gui.comboBox(general_box, self, "shadow_column", label="Scan direction",labelWidth=220,
                                     items=["X (col 1)","Z (col 3)", "R (col 20)"],
                                     sendSelectedValue=False, orientation="horizontal")

        box_x = oasysgui.widgetBox(general_box, "Scan direction", addSpace=True, orientation="vertical", height=100)
        oasysgui.lineEdit(box_x, self, "npoints_x", "Points", labelWidth=260, valueType=int,orientation="horizontal")
        oasysgui.lineEdit(box_x, self, "x_min", "min"+ " [" + self.workspace_units_label + "]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(box_x, self, "x_max", "max"+ " [" + self.workspace_units_label + "]", labelWidth=260, valueType=float, orientation="horizontal")

        gui.separator(self.controlArea, height=200)

        box_file = oasysgui.widgetBox(general_box, "File", addSpace=True, orientation="vertical", height=100)
        gui.comboBox(box_file, self, "save_h5_file_flag", label="Save plots into h5 file", labelWidth=250,
                                         items=["No", "Yes"],
                                         sendSelectedValue=False, orientation="horizontal",callback=self.set_visible)

        self.box_file_1 = oasysgui.widgetBox(box_file, "", addSpace=False, orientation="horizontal", height=25)
        oasysgui.lineEdit(self.box_file_1, self, "save_h5_file_name", "File Name", labelWidth=100,  valueType=str, orientation="horizontal")



        #
        #
        #
        tabs_setting = oasysgui.tabWidget(self.mainArea)
        tabs_setting.setFixedHeight(self.IMAGE_HEIGHT+5)
        tabs_setting.setFixedWidth(self.IMAGE_WIDTH)


        tmp = oasysgui.createTabPage(tabs_setting, "Intensity vs y")
        self.image_box = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.image_box.setFixedHeight(self.IMAGE_HEIGHT-30)
        self.image_box.setFixedWidth(self.IMAGE_WIDTH-20)

        tmp = oasysgui.createTabPage(tabs_setting, "FWHM(y)")
        self.box_fwhm = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.box_fwhm.setFixedHeight(self.IMAGE_HEIGHT-30)
        self.box_fwhm.setFixedWidth(self.IMAGE_WIDTH-20)

        tmp = oasysgui.createTabPage(tabs_setting, "Center(y)")
        self.box_center = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.box_center.setFixedHeight(self.IMAGE_HEIGHT-30)
        self.box_center.setFixedWidth(self.IMAGE_WIDTH-20)

        tmp = oasysgui.createTabPage(tabs_setting, "I0(y)")
        self.box_I0 = gui.widgetBox(tmp, "", addSpace=True, orientation="vertical")
        self.box_I0.setFixedHeight(self.IMAGE_HEIGHT-30)
        self.box_I0.setFixedWidth(self.IMAGE_WIDTH-20)

        tmp = oasysgui.createTabPage(tabs_setting, "Info")
        self.focnewInfo = oasysgui.textArea(height=self.IMAGE_HEIGHT-35)
        info_box = oasysgui.widgetBox(tmp, "", addSpace=True, orientation="horizontal", height = self.IMAGE_HEIGHT-20, width = self.IMAGE_WIDTH-20)
        info_box.layout().addWidget(self.focnewInfo)


        self.set_visible()

    def set_visible(self):
        self.box_file_1.setVisible(self.save_h5_file_flag != 0)

    def writeStdOut(self, text="", initialize=False):
        cursor = self.focnewInfo.textCursor()
        if initialize:
            self.focnewInfo.setText(text)
        else:
            cursor.movePosition(QtGui.QTextCursor.End)
            cursor.insertText(text)

    def setBeam(self, beam):
        if ShadowCongruence.checkEmptyBeam(beam):
            if ShadowCongruence.checkGoodBeam(beam):
                self.input_beam = beam

                if self.is_automatic_run:
                    self.calculate()
            else:
                QtWidgets.QMessageBox.critical(self, "Error",
                                           "Data not displayable: No good rays or bad content",
                                           QtWidgets.QMessageBox.Ok)
    def get_shadow3_beam(self):
        if ShadowCongruence.checkEmptyBeam(self.input_beam):
            if ShadowCongruence.checkGoodBeam(self.input_beam):

                beam_to_analize = self.input_beam._beam

                return beam_to_analize


    def calculate(self):

        self.progressBarInit()

        # capture stout
        self.writeStdOut(initialize=True)
        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        beam_to_analize = self.get_shadow3_beam()

        if beam_to_analize is None:
            print("No SHADOW Beam")
            return

        if beam_to_analize is None:
            return

        positions = numpy.linspace(self.y_min, self.y_max, self.npositions)

        out_x = numpy.zeros((self.npoints_x, self.npositions))
        fwhm = numpy.zeros(self.npositions)
        center = numpy.zeros(self.npositions)

        if self.shadow_column == 0:
            col = 1
        elif self.shadow_column == 1:
            col = 3
        elif self.shadow_column == 2:
            col = 20

        if self.use_reflectivity:
            ref = 23
        else:
            ref = 0

        self.progressBarSet(10)
        self.setStatusMessage("Retracing...")
        for i in range(self.npositions):
            if numpy.mod(i,10) == 0:
                print("Calculating position %d of %d"%(i+1,self.npositions))
                self.progressBarSet(10 + 85 * i / self.npositions)
            beami = beam_to_analize.duplicate()
            beami.retrace(positions[i], resetY=True)
            tkt_x = beami.histo1(col, xrange=[self.x_min, self.x_max], nbins=self.npoints_x, nolost=self.no_lost, ref=ref)
            out_x[:, i] = tkt_x["histogram"]
            fwhm[i] = tkt_x["fwhm"]

            if ref == 23:
                center[i] = numpy.average(beami.getshonecol(col, nolost=self.no_lost),
                                          weights=beami.getshonecol(23, nolost=self.no_lost))
            else:
                center[i] = numpy.average(beami.getshonecol(col,nolost=self.no_lost),)


        #
        # plots
        #
        print("\nResult arrays X,Y (shapes): ", out_x.shape, tkt_x["bin_center"].shape, positions.shape )
        x = tkt_x["bin_center"]
        y = positions

        if self.shadow_column == 0:
            col_title="X (col 1)"
        elif self.shadow_column == 1:
            col_title = "Z (col 3)"
        elif self.shadow_column == 2:
            col_title = "R (col 20)"

        plot_canvas = plot_data2D(
                             out_x.T, y, 1e6 * self.workspace_units_to_m * x,
                             title="",ytitle="%s [um] (%d pixels)"%(col_title,x.size),xtitle="Y [%s] (%d pixels)"%(self.workspace_units_label,y.size),)
        self.image_box.layout().removeItem(self.image_box.layout().itemAt(0))
        self.image_box.layout().addWidget(plot_canvas)


        #FWHM
        fwhm[fwhm == 0] = 'nan'
        self.box_fwhm.layout().removeItem(self.box_fwhm.layout().itemAt(0))
        plot_widget_id = plot_data1D(y,1e6 * self.workspace_units_to_m * fwhm,title="FWHM",xtitle="y [%s]"%self.workspace_units_label,ytitle="FHWH [um]",symbol='.')
        self.box_fwhm.layout().addWidget(plot_widget_id)

        #I0
        nx, ny = out_x.shape
        I0 = out_x.T[:,nx//2]
        self.box_I0.layout().removeItem(self.box_I0.layout().itemAt(0))
        plot_widget_id = plot_data1D(y,I0,title="I at central profile",xtitle="y [%s]"%self.workspace_units_label,ytitle="I0",symbol='.')
        self.box_I0.layout().addWidget(plot_widget_id)

        #center
        self.box_center.layout().removeItem(self.box_center.layout().itemAt(0))
        plot_widget_id = plot_data1D(y, 1e6 * self.workspace_units_to_m * center,title="CENTER",xtitle="y [%s]"%self.workspace_units_label,ytitle="CENTER [um]",symbol='.',
                                     yrange=[1e6 * self.workspace_units_to_m * self.x_min, 1e6 * self.workspace_units_to_m * self.x_max])
        self.box_center.layout().addWidget(plot_widget_id)



        if self.save_h5_file_flag:

            h5w = H5SimpleWriter.initialize_file(self.save_h5_file_name, creator="h5_basic_writer.py")

            h5w.create_entry("caustic", nx_default="image")

            h5w.add_image(out_x.T, y, 1e6 * self.workspace_units_to_m * x,
                          entry_name="caustic", image_name="image",
                          title_y="%s [um] (%d pixels)"%(col_title,x.size),
                          title_x="Y [%s] (%d pixels)"%(self.workspace_units_label, y.size),)

            h5w.add_dataset(y, 1e6 * self.workspace_units_to_m * fwhm,
                            entry_name="caustic", dataset_name="fwhm",
                            title_x="Y [%s]" % self.workspace_units_label, title_y="FWHM [um]")

            h5w.add_dataset(y, 1e6 * self.workspace_units_to_m * center,
                            entry_name="caustic", dataset_name="center",
                            title_x="Y [%s]" % self.workspace_units_label, title_y="center [um]")

            h5w.add_dataset(y, I0,
                            entry_name="caustic", dataset_name="I0",
                            title_x="Y [%s]" % self.workspace_units_label, title_y="I at central profile")

        self.progressBarFinished()


if __name__ == "__main__":
    import sys
    import Shadow

    class MyBeam():
        pass
    beam_to_analize = Shadow.Beam()
    beam_to_analize.load("/Users/srio/Oasys/lens.01")
    my_beam = MyBeam()
    my_beam._beam = beam_to_analize

    a = QApplication(sys.argv)
    ow = ESRFCaustic()


    ow.show()

    ow.npoints_x = 30
    ow.npoints_z = 30
    ow.npositions = 50
    ow.y_min =0
    ow.y_max = 100
    ow.shadow_column = 1

    ow.x_min = -350e-6
    ow.x_max = 350e-6
    ow.save_h5_file_flag = 1


    ow.input_beam = my_beam
    a.exec_()
    ow.saveSettings()
