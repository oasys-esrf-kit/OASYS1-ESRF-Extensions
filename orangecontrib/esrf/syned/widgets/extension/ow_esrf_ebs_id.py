from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui

from orangecontrib.syned.widgets.gui.ow_insertion_device import OWInsertionDevice
from orangecontrib.syned.widgets.light_sources.ow_undulator_light_source import OWUndulatorLightSource

from urllib.request import urlopen

class OWEBS(OWInsertionDevice):

    name = "EBS"
    description = "EBS"
    icon = "icons/ebs.png"
    priority = 10


    id_number = Setting(0)

    id_selected = Setting(0)



    def __init__(self):
        super().__init__()

        self.tab_ebs = oasysgui.createTabPage(self.tabs_setting, "EBS")
        box_ebs = oasysgui.widgetBox(self.tab_ebs, "EBS ID", addSpace=False,
                                        orientation="vertical", height=450)

        gui.comboBox(box_ebs, self, "id_selected", label="ID installed", labelWidth=220,
                     items=self.get_ebs_ids_list(),
                     sendSelectedValue=False, orientation="horizontal",
                     callback=self.select_ebs_id)

    def select_ebs_id(self):
        url1 = 'http://ftp.esrf.eu/pub/scisoft/syned/lightsources/'
        self.syned_file_name = url1 + self.get_ebs_ids_list()[self.id_selected]
        print(">>>>>>>>", self.syned_file_name)
        self.read_syned_file()

    def get_ebs_ids_list(self, id=0):

        url = 'ftp://ftp.esrf.eu/pub/scisoft/syned/lightsources/'
        urlpath = urlopen(url)
        string0 = urlpath.read().decode('utf-8')
        string = string0.split("\n")

        if id == 0:
            id_tex = ""
        else:
            id_tex = "ID%02d" % id

        mylist = []
        for line in string:
            list1 = line.strip().split(" ")
            filename = list1[-1]
            if ("EBS" in filename) and (id_tex in filename):
                mylist.append(filename)

        return mylist

from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":

    from orangecontrib.esrf.syned.widgets.extension.ow_esrf_ebs_id import OWEBS
    from PyQt5.QtWidgets import QApplication
    import sys
    a = QApplication(sys.argv)
    ow = OWEBS()
    ow.show()
    a.exec_()
