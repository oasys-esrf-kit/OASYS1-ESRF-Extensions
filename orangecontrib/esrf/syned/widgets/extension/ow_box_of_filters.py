import os, sys
import json
import urllib.request
from PyQt5.QtWidgets import QMessageBox

# import orangecanvas.resources as resources

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from orangecontrib.syned.widgets.gui.ow_optical_element import OWOpticalElement
from orangecontrib.esrf.syned.util.syned_filter_with_density import FilterWithDensity
from orangecontrib.esrf.syned.util.syned_filter_packs import FilterBox, FilterBlock


from syned.util.json_tools import load_from_json_file, load_from_json_url

class OWBoxOfFilters(OWOpticalElement):

    name = "Box of Filters"
    description = "Syned: Box of Filters"
    icon = "icons/box_of_filters.png"
    priority = 3.1

    att1 = Setting(0)
    att2 = Setting(0)
    att3 = Setting(0)
    att4 = Setting(0)
    att5 = Setting(0)

    n_blocks = Setting(3)
    syned_file_name = Setting("Select *.json file")
    # syned_file_name = Setting("/users/srio/OASYS1.2/OASYS1-ESRF-EXTENSIONS/orangecontrib/esrf/syned/util/tmp.json")
    # syned_file_name = Setting(os.path.join(resources.package_dirname("orangecontrib.esrf.xoppy.data"), 'bm05_wb_attenuators.json'))
    syned_file_name = Setting("https://raw.githubusercontent.com/oasys-esrf-kit/OASYS1-ESRF-Extensions/master/orangecontrib/esrf/xoppy/data/bm05_wb_attenuators.json")

    syned_filterbox = FilterBox()
    # att_dic = Setting(None)

    def __init__(self):
        super().__init__(allow_angle_radial=False, allow_angle_azimuthal=False)

    def draw_specific_box(self):

        #################
        box_json = oasysgui.widgetBox(self.tab_bas, "json files i/o", addSpace=True, orientation="vertical")

        # box_json =  oasysgui.widgetBox(files_box, "Read/Write File", addSpace=False, orientation="vertical")

        file_box = oasysgui.widgetBox(box_json, "", addSpace=False, orientation="horizontal")

        self.le_syned_file_name = oasysgui.lineEdit(file_box, self, "syned_file_name", "File Name/URL",
                                                    labelWidth=150, valueType=str, orientation="horizontal")

        gui.button(file_box, self, "...", callback=self.select_syned_file, width=25)

        button_box = oasysgui.widgetBox(box_json, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Read Syned File", callback=self.read_syned_file)
        button.setFixedHeight(25)

        button = gui.button(button_box, self, "Read plane json File", callback=self.read_plane_json_file)
        button.setFixedHeight(25)

        button = gui.button(button_box, self, "Write Syned File...", callback=self.write_syned_file)
        button.setFixedHeight(25)



        ################
        filter_box = oasysgui.widgetBox(self.tab_bas, "Box of Filters Setting", addSpace=True, orientation="vertical")


        box1 = gui.widgetBox(filter_box)
        gui.comboBox(box1, self, "n_blocks",
                                       label="Number of blocks or axes", addSpace=False,
                                       items=['0','1','2','3','4','5'], callback=self.set_visibility,
                                       valueType=int, orientation="horizontal", labelWidth=250, editable=0)

        self.wid_att1 = gui.widgetBox(box1)
        self.wid_att1_combo = gui.comboBox(self.wid_att1, self, "att1",
                                       label="Att1", addSpace=False,
                                       items=['Empty'],
                                       valueType=int, orientation="horizontal", labelWidth=150, editable=1)
        self.wid_att2 = gui.widgetBox(box1)
        self.wid_att2_combo = gui.comboBox(self.wid_att2, self, "att2",
                                       label="Att2", addSpace=False,
                                       items=['Empty'],
                                       valueType=int, orientation="horizontal", labelWidth=150, editable=1)
        self.wid_att3 = gui.widgetBox(box1)
        self.wid_att3_combo = gui.comboBox(self.wid_att3, self, "att3",
                                       label="Att3", addSpace=False,
                                       items=['Empty'],
                                       valueType=int, orientation="horizontal", labelWidth=150, editable=1)
        self.wid_att4 = gui.widgetBox(box1)
        self.wid_att4_combo = gui.comboBox(self.wid_att4, self, "att4",
                                       label="Att4", addSpace=False,
                                       items=['Empty'],
                                       valueType=int, orientation="horizontal", labelWidth=150, editable=1)
        self.wid_att5 = gui.widgetBox(box1)
        self.wid_att5_combo = gui.comboBox(self.wid_att5, self, "att5",
                                       label="Att5", addSpace=False,
                                       items=['Empty'],
                                       valueType=int, orientation="horizontal", labelWidth=150, editable=1)

        self.set_visibility()

        # if self.att_dic is not None:
        #     self.configure_blocks_from_syned_json(self._att_dic_to_syned_filterbox(self.att_dic))

    def set_visibility(self):
        self.wid_att1.setVisible(False)
        self.wid_att2.setVisible(False)
        self.wid_att3.setVisible(False)
        self.wid_att4.setVisible(False)
        self.wid_att5.setVisible(False)

        if self.n_blocks >= 1: self.wid_att1.setVisible(True)
        if self.n_blocks >= 2: self.wid_att2.setVisible(True)
        if self.n_blocks >= 3: self.wid_att3.setVisible(True)
        if self.n_blocks >= 4: self.wid_att4.setVisible(True)
        if self.n_blocks >= 5: self.wid_att5.setVisible(True)

    def select_syned_file(self):
        self.le_syned_file_name.setText(oasysgui.selectFileFromDialog(self, self.syned_file_name, "Open json File"))

    def read_syned_file(self):
        try:
            congruence.checkEmptyString(self.syned_file_name, "Syned File Name/Url")

            if (len(self.syned_file_name) > 7 and self.syned_file_name[:7] == "http://") or \
                (len(self.syned_file_name) > 8 and self.syned_file_name[:8] == "https://"):
                congruence.checkUrl(self.syned_file_name)
                is_remote = True
            else:
                congruence.checkFile(self.syned_file_name)
                is_remote = False

            try:
                if is_remote:
                    content = load_from_json_url(self.syned_file_name,                                  exec_commands=[
                                      "from orangecontrib.esrf.syned.util.syned_filter_with_density import FilterWithDensity",
                                      "from orangecontrib.esrf.syned.util.syned_filter_packs import FilterBlock, FilterBox"])
                else:
                    content = load_from_json_file(self.syned_file_name,                                  exec_commands=[
                                      "from orangecontrib.esrf.syned.util.syned_filter_with_density import FilterWithDensity",
                                      "from orangecontrib.esrf.syned.util.syned_filter_packs import FilterBlock, FilterBox"])

                if isinstance(content, FilterBox):
                    self.configure_blocks_from_syned_json(content)
                    self.syned_filterbox = content
                else:
                    raise Exception("json file must contain a SYNED FilterBox")
            except Exception as e:
                raise Exception("Error reading SYNED FilterBox from file: " + str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)

    def _att_dic_to_syned_filterbox(self, att_dic):
        n_keys = 0
        keys = []
        for key in att_dic.keys():
            n_keys += 1
            keys.append(key)

        # update combo boxes
        block_list = []
        for i in range(n_keys):
            items = []
            for filter in att_dic[keys[i]].keys():
                if filter[0] != "_":
                    item = att_dic[keys[i]][filter]
                    f = FilterWithDensity(name=item['name'],
                                          material=item['substance'],
                                          thickness=item['thickness'],
                                          density=item['thickness'])
                    items.append(f)

            block_list.append(FilterBlock(filters_list=items))

        return FilterBox(filter_blocks_list=block_list)

    def read_plane_json_file(self):
        try:
            congruence.checkEmptyString(self.syned_file_name, "plane json File Name/Url")

            if (len(self.syned_file_name) > 7 and self.syned_file_name[:7] == "http://") or \
                (len(self.syned_file_name) > 8 and self.syned_file_name[:8] == "https://"):
                congruence.checkUrl(self.syned_file_name)
                is_remote = True
            else:
                congruence.checkFile(self.syned_file_name)
                is_remote = False

            try:
                if is_remote:
                    # raise Exception("URL not implemented for plane json files")
                    response = urllib.request.urlopen(self.syned_file_name)
                    att_dic = json.load(response)
                else:
                    with open(self.syned_file_name) as att_file:
                        att_dic = json.load(att_file)

                if isinstance(att_dic, dict):
                    self.configure_blocks_from_syned_json(self._att_dic_to_syned_filterbox(att_dic))
                    self.syned_filterbox = self._att_dic_to_syned_filterbox(att_dic)
                else:
                    raise Exception("json file must contain a FilterBox")
            except Exception as e:
                raise Exception("Error reading filter box from plane json file: " + str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)

    def write_syned_file(self):
        try:
            filename = oasysgui.selectSaveFileFromDialog(self, message="Save File", default_file_name="", file_extension_filter="*.*")
            if filename is not None:
                self.syned_filterbox.to_json(filename)
                QMessageBox.information(self, "File Save", "JSON file %s correctly written to disk" % filename, QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)

    def update_combo(self, id, new_input):
        n_old = id.count()
        n = len(new_input)
        for i in range(n):
            if i >= n_old:
                id.addItem(new_input[i])
            else:
                id.setItemText(i, new_input[i])

    def configure_blocks_from_syned_json(self, content):
        if content.get_n() > 5:
            raise Exception('Maximum of 5 blocks allowed.')
        else:
            self.n_blocks = content.get_n()

        self.set_visibility()

        # update combo boxes
        for i in range(content.get_n()):
            blc = content.get_item(i)
            items = []
            for j in range(blc.get_n()):
                filter = blc.get_item(j)
                items.append(filter.get_name())
            if i == 0: self.update_combo(self.wid_att1_combo, items)
            if i == 1: self.update_combo(self.wid_att2_combo, items)
            if i == 2: self.update_combo(self.wid_att3_combo, items)
            if i == 3: self.update_combo(self.wid_att4_combo, items)
            if i == 4: self.update_combo(self.wid_att5_combo, items)

    def get_optical_element(self):
        self.syned_filterbox.set_selection([self.att1, self.att2, self.att3s, self.att4, self.att5])
        return self.syned_filterbox


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = OWBoxOfFilters()
    w.show()
    app.exec()

