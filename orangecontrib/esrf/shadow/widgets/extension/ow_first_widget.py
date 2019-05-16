from orangecontrib.esrf.util.gui.ow_esrf_widget import ESRFWidget

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

import orangecanvas.resources as resources
import os
import numpy

class OWbm(ESRFWidget):
    name = "First Widget"
    id = "rafael"
    description = "First Widget"
    icon = "icons/first_widget.png"
    priority = 1
    category = ""
    keywords = ["esrf", "first"]

    #inputs = WidgetDecorator.syned_input_data()

    input_field = Setting(1.0)
    input_field_2 = Setting("Ciao Ciao")
    combo_input = Setting(1)

    file_path = os.path.join(resources.package_dirname("orangecontrib.esrf.shadow.widgets.extension"), "miscellanea", "test_first_widget.txt")

    def build_gui(self):
        general_box = oasysgui.widgetBox(self.controlArea, "General Settings", addSpace=False, orientation="vertical", height=250, width=390)

        oasysgui.lineEdit(general_box, self, "input_field", "Input Field [\u03bcm]", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(general_box, self, "input_field_2", "Input Field 2", labelWidth=100, valueType=str, orientation="horizontal")

        self.cb_combo_input = gui.comboBox(general_box, self, "combo_input", label="Combo Input", labelWidth=250,
                                     items=["Ciao Ciao", "Pippo", "Pluto", "Paperino"],
                                     sendSelectedValue=False, orientation="horizontal", callback=self.combo_value_changed)


    def combo_value_changed(self):
        self.input_field_2 = self.cb_combo_input.currentText()


    def check_fields(self):
        congruence.checkStrictlyPositiveNumber(self.input_field, "Input Field")

    def do_calculation(self):
        return numpy.loadtxt(self.file_path)


    def getDefaultPlotTabIndex(self):
        return -1

    def getTitles(self):
        return ["Plot 1", "Plot 2", "Plot 3"]

    def getXTitles(self):
        return ["Energy [eV]", "Energy [eV]", "Energy [eV]"]

    def getYTitles(self):
        return ["X [$\mu$m]", "Y [$\mu$m]", "Z [$\mu$m]"]

    def getVariablesToPlot(self):
        return [(0, 1), (0, 2), (0, 3)]

    def getLogPlot(self):
        return [(False, False), (False, False), (False, False)]

    def get_data_exchange_widget_name(self):
        return "ESRF_FIRST_WIDGET"
