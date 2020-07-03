from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPlot
from orangecontrib.shadow.widgets.gui import ow_automatic_element
from orangecontrib.esrf.shadow.widgets.gui.plots import plot_data1D, plot_data2D

import numpy

class ESRFCaustic(ow_automatic_element.AutomaticElement):

    name = "ESRF Caustic Generator"
    description = "Shadow: ESRF Caustic Generator"
    icon = "icons/caustic.png"
    maintainer = "APS team"
    maintainer_email = "srio@esrf.eu, srio@lbl.gov"
    priority = 5
    category = "Data Display Tools"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 675

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


    def __init__(self, show_automatic_box=True):
        super().__init__()

        gui.button(self.controlArea, self, "Calculate", callback=self.calculate, height=45)

        general_box = oasysgui.widgetBox(self.controlArea, "General Settings", addSpace=True, orientation="vertical",
                                         width=self.CONTROL_AREA_WIDTH-8, height=400)


        gui.comboBox(general_box, self, "no_lost", label="Rays",labelWidth=220,
                                     items=["All rays","Good only","Lost only"],
                                     sendSelectedValue=False, orientation="horizontal")


        gui.comboBox(general_box, self, "use_reflectivity", label="Include reflectivity",labelWidth=220,
                                     items=["No","Yes"],
                                     sendSelectedValue=False, orientation="horizontal")

        box_y = oasysgui.widgetBox(general_box, "Propagation along Y (col 2)", addSpace=True, orientation="vertical", height=200)
        oasysgui.lineEdit(box_y, self, "npositions", "Y Points", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(box_y, self, "y_min", "Y min", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(box_y, self, "y_max", "Y max", labelWidth=260, valueType=float, orientation="horizontal")


        gui.comboBox(general_box, self, "shadow_column", label="Scan direction",labelWidth=220,
                                     items=["X (col 1)","Z (col 3)"],
                                     sendSelectedValue=False, orientation="horizontal")

        box_x = oasysgui.widgetBox(general_box, "Scan direction", addSpace=True, orientation="vertical", height=200)
        oasysgui.lineEdit(box_x, self, "npoints_x", "Points", labelWidth=260, valueType=int,orientation="horizontal")
        oasysgui.lineEdit(box_x, self, "x_min", "min", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(box_x, self, "x_max", "max", labelWidth=260, valueType=float, orientation="horizontal")

        gui.separator(self.controlArea, height=200)

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

        tmp = oasysgui.createTabPage(tabs_setting, "Info")
        self.focnewInfo = oasysgui.textArea(height=self.IMAGE_HEIGHT-35)
        info_box = oasysgui.widgetBox(tmp, "", addSpace=True, orientation="horizontal", height = self.IMAGE_HEIGHT-20, width = self.IMAGE_WIDTH-20)
        info_box.layout().addWidget(self.focnewInfo)


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
        else:
            col = 3

        if self.use_reflectivity:
            ref = 23
        else:
            ref = 0

        for i in range(self.npositions):
            if numpy.mod(i,10) == 0:
                print("Calculating position %d of %d"%(i+1,self.npositions))
            beami = beam_to_analize.duplicate()
            beami.retrace(positions[i])
            tkt_x = beami.histo1(col, xrange=[self.x_min, self.x_max], nbins=self.npoints_x, nolost=self.no_lost, ref=ref)
            out_x[:, i] = tkt_x["histogram"]
            fwhm[i] = tkt_x["fwhm"]

            if ref == 23:
                center[i] = numpy.average(beami.getshonecol(col, nolost=self.no_lost),
                                          weights=beami.getshonecol(23, nolost=self.no_lost))
            else:
                center[i] = numpy.average(beami.getshonecol(col,nolost=self.no_lost),)


        print("\nResult arrays X,Y (shapes): ", out_x.shape, tkt_x["bin_center"].shape, positions.shape )
        x = tkt_x["bin_center"]
        y = positions

        if self.shadow_column == 0:
            col_title="X (col 1)"
        elif self.shadow_column == 1:
            col_title = "Z (col 3)"
        plot_canvas = plot_data2D(
                             out_x.T, y, x,
                             title="",ytitle="%s [m] (%d pixels)"%(col_title,x.size),xtitle="Y [m] (%d pixels)"%y.size,)
        self.image_box.layout().removeItem(self.image_box.layout().itemAt(0))
        self.image_box.layout().addWidget(plot_canvas)


        #FWHM
        fwhm[fwhm == 0] = 'nan'
        self.box_fwhm.layout().removeItem(self.box_fwhm.layout().itemAt(0))
        plot_widget_id = plot_data1D(y,fwhm,title="FWHM",xtitle="y [m]",ytitle="FHWH [m]",symbol='.')
        self.box_fwhm.layout().addWidget(plot_widget_id)

        #center
        self.box_center.layout().removeItem(self.box_center.layout().itemAt(0))
        plot_widget_id = plot_data1D(y,center,title="CENTER",xtitle="y [m]",ytitle="CENTER [m]",symbol='.',
                                     yrange=[self.x_min,self.x_max])
        self.box_center.layout().addWidget(plot_widget_id)


    def writeStdOut(self, text):
        cursor = self.shadow_output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.shadow_output.setTextCursor(cursor)
        self.shadow_output.ensureCursorVisible()

if __name__ == "__main__":
    import sys
    import Shadow

    class MyBeam():
        pass
    beam_to_analize = Shadow.Beam()
    beam_to_analize.load("/Users/srio/Oasys/screen.0101")
    my_beam = MyBeam()
    my_beam._beam = beam_to_analize

    a = QApplication(sys.argv)
    ow = ESRFCaustic()
    ow.show()
    ow.input_beam = my_beam
    a.exec_()
    ow.saveSettings()
