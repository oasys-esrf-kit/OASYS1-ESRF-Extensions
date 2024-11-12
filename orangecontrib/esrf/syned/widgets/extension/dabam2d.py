import os, sys

import numpy, h5py
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from orangecontrib.esrf.util.dabam2d_util import scan_root_directory
from silx.gui.plot import Plot2D
from scipy.interpolate import  RectBivariateSpline
from srxraylib.metrology.profiles_simulation import slopes
import oasys.util.oasys_util as OU
from oasys.util.oasys_objects import OasysSurfaceData

class OWdabam2d(OWWidget):
    name = "DABAM2D File Access and Processing"
    id = "dabam2d_file_access_and_processing"
    description = "DABAM2D File Access and Processing"
    icon = "icons/dabam2d.png"
    author = "M Sanchez del Rio"
    maintainer_email = "srio@esrf.eu"
    priority = 100
    category = ""
    keywords = ["dabam2d_file_access_and_processing"]

    outputs = [{"name": "Surface Data",
                "type": OasysSurfaceData,
                "doc": "Surface Data",
                "id": "Surface Data"},
               {"name": "DABAM 1D Profile",
                "type": numpy.ndarray,
                "doc": "numpy.ndarray",
                "id": "numpy.ndarray"},
               ]

    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 800
    IMAGE_HEIGHT = 610

    CONTROL_AREA_WIDTH = 405

    #
    # variables stored in the widget
    #
    conversion_to_m_z = Setting(1.0)
    root = Setting("<None>")
    file_out = Setting("dabam2d_tmp.h5")
    rebase = Setting(0)
    extract_profile1D = Setting(0)
    coordinate_profile1D = Setting(0.0)
    #
    # local variables
    #
    data=None
    scanned_files_with_path = []
    scanned_files_without_path = []
    selected_files_with_path = []
    selected_files_without_path = []

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

        # main buttons
        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")
        button = gui.button(button_box, self, "Write and Send (sum of) Selection", callback=self.write_and_send)
        button.setFixedHeight(45)

        #
        # input file list
        #
        input_box_l = oasysgui.widgetBox(self.controlArea, "Input Dabax2d files", addSpace=True, orientation="vertical", height=460, width=self.CONTROL_AREA_WIDTH)

        root_file_box = oasysgui.widgetBox(input_box_l, "", addSpace=True, orientation="vertical",)
        figure_box = oasysgui.widgetBox(root_file_box, "", addSpace=True, orientation="horizontal")
        oasysgui.lineEdit(figure_box, self, "root", "root dir:",
                                                    labelWidth=80, valueType=str, orientation="horizontal")
        gui.button(figure_box, self, "...", callback=self.select_root)

        gui.button(input_box_l, self, "Scan root directory", callback=self.scan_directory)

        self.files_area = oasysgui.textArea(height=250)
        self.refresh_files_text_area()
        input_box_l.layout().addWidget(self.files_area)

        # operations
        operations_box = oasysgui.widgetBox(input_box_l, "Operations", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(operations_box, self, "conversion_to_m_z", label="Scaling factor", labelWidth=300, orientation="horizontal", valueType=float)
        gui.comboBox(operations_box, self, "rebase", label="Set min to zero", labelWidth=220,
                     items=["No",
                            "Yes",],
                     sendSelectedValue=False, orientation="horizontal")

        # buttons
        button_box_2 = oasysgui.widgetBox(input_box_l, "", addSpace=False, orientation="horizontal")
        gui.button(button_box_2, self, "View Selection", callback=self.view_selection)
        gui.button(button_box_2, self, "View Sum of Selection", callback=self.view_sum)
        gui.button(button_box_2, self, "Clear Views", callback=self.clear_views)

        # write and send
        write_and_send_box = oasysgui.widgetBox(self.controlArea, "Write and Send", addSpace=True,
                                         orientation="vertical",)

        oasysgui.lineEdit(write_and_send_box, self, "file_out", "output file:",
                                                    labelWidth=80, valueType=str, orientation="horizontal")

        gui.comboBox(write_and_send_box, self, "extract_profile1D", label="Extract and send 1D profile", labelWidth=220,
                     items=["axis 0 (horizontal)", "axis 1 (vertical)"],
                     sendSelectedValue=False, orientation="horizontal")

        oasysgui.lineEdit(write_and_send_box, self, "coordinate_profile1D", "At coordinate [m]:", labelWidth=260, valueType=float,
                          orientation="horizontal")

        # gui.separator(tab_out, height=20)

        # results
        main_tabs = oasysgui.tabWidget(self.mainArea)

        plot_tab = oasysgui.createTabPage(main_tabs, "Surfaces")


        self.tab = []
        self.tabs = oasysgui.tabWidget(plot_tab)

        self.clear_views()
        self.append_tabs_surfaces()

        gui.rubber(self.controlArea)
        gui.rubber(self.mainArea)

    def delete_tab(self):
        """
        main_tabs.setTabsClosable(True)
        main_tabs.tabCloseRequested.connect(self.delete_tab)
        """
        print(">>>> Delete tab")

    def select_root(self):
        root = QFileDialog.getExistingDirectory(self, "Select root/url directory to scan for h5 files", "")
        if root != "":
            self.root = root

    def write_and_send(self):
        self.get_selection()
        self.read_selected_data_files_sum()

        # self.zernike()

        # self.write_thickness_file()

        zz = numpy.round(self.data[-1][2], 12)
        xx = numpy.round(self.data[-1][0], 12)
        yy = numpy.round(self.data[-1][1], 12)
        filename = self.file_out
        try:
            OU.write_surface_file(zz.T, xx, yy, file_name=filename)
            print("File %s written to disk." % filename)
        except:
                print("*** Error writing hdf5 file **")

        # send 2D profile
        xx = self.data[-1][0]
        yy = self.data[-1][1]
        zz = self.data[-1][2]
        self.send("Surface Data",
                  OasysSurfaceData(xx=xx,
                                   yy=yy,
                                   zz=zz.T,
                                   surface_data_file=self.file_out))
        # send 1D profile
        # self.extract_profile1D = 0
        if self.extract_profile1D == 0:
            abscissas = xx
            perp_abscissas = yy
            index0 = numpy.argwhere(perp_abscissas >= 0.0)
            try:
                index0 = index0[0][0]
            except:
                index0 = -1
            profile1D = zz[:, index0]
            # slope1D = numpy.gradient(profile1D, abscissas)
            # profile1D_std = profile1D.std()
            # slope1D_std = slope1D.std()
            # if self.invert_axes_names:
            #     title = "profile at X[%d] = %g; StDev = %g um" % (index0, perp_abscissas[index0], 1e6*profile1D_std)
            #     titleS = "slopes at X[%d] = %g; StDev = %g urad" % (index0, perp_abscissas[index0], 1e6*slope1D_std)
            #     xtitle = "Y [m] "
            # else:
            #     title = "profile at Y[%d] = %g; StDev = %g um" % (index0, perp_abscissas[index0], 1e6*profile1D_std)
            #     titleS = "slopes at Y[%d] = %g; StDev = %g urad" % (index0, perp_abscissas[index0], 1e6*slope1D_std)
            #     xtitle = "X [m] "
            # self.plot_data1D(abscissas, 1e6*profile1D, self.profile1D_id, title=title, xtitle=xtitle, ytitle="Z [um] ")
            # self.plot_data1D(abscissas, 1e6*slope1D, self.slope1D_id, title=titleS, xtitle=xtitle, ytitle="Z' [urad]")
        else:
            abscissas = yy
            perp_abscissas = xx
            index0 = numpy.argwhere(perp_abscissas >= self.coordinate_profile1D)
            try:
                index0 = index0[0][0]
            except:
                index0 = -1
            profile1D = zz[index0, :]
            # slope1D = numpy.gradient(profile1D,abscissas)
            # profile1D_std = profile1D.std()
            # slope1D_std = slope1D.std()
            # if self.invert_axes_names:
            #     title = "profile at Y[%d] = %g; StDev = %g um" % (index0, perp_abscissas[index0], 1e6*profile1D_std)
            #     titleS = "slopes at Y[%d] = %g; StDev = %g urad" % (index0, perp_abscissas[index0], 1e6*slope1D_std)
            #     xtitle = "X [m] "
            # else:
            #     title = "profile at X[%d] = %g; StDev = %g um" % (index0, perp_abscissas[index0], 1e6*profile1D_std)
            #     titleS = "slopes at X[%d] = %g; StDev = %g urad" % (index0, perp_abscissas[index0], 1e6*slope1D_std)
            #     xtitle = "Y [m] "
            # self.plot_data1D(abscissas, 1e6*profile1D, self.profile1D_id, title=title, xtitle=xtitle, ytitle="Z [um] ")
            # self.plot_data1D(abscissas, 1e6*slope1D, self.slope1D_id, title=titleS, xtitle=xtitle, ytitle="Z' [urad]")

        dabam_profile = numpy.zeros((profile1D.size, 2))
        dabam_profile[:, 0] = abscissas
        dabam_profile[:, 1] = profile1D
        # from srxraylib.plot.gol import plot
        # plot(abscissas, profile1D)
        self.send("DABAM 1D Profile", dabam_profile)

    def scan_directory(self):
        scanned_files_without_path, scanned_files_with_path  = scan_root_directory(self.root)
        self.scanned_files_with_path = scanned_files_with_path
        self.scanned_files_without_path = scanned_files_without_path
        self.refresh_files_text_area(scanned_files_without_path)

    def refresh_files_text_area(self, files=None):
        text = ""
        if files is not None:
            for file in files:
                text += file + "\n"
        self.files_area.setText(text)

    # def write_thickness_file(self):
    #     zz = numpy.round(self.data[-1][2], 12)
    #     xx = numpy.round(self.data[-1][0], 12)
    #     yy = numpy.round(self.data[-1][1], 12)
    #     filename = self.file_out
    #     try:
    #         OU.write_surface_file(zz, xx, yy, file_name=filename)
    #         print("File %s written to disk." % filename)
    #     except:
    #         print("*** Error writing hdf5 file **")

    def clear_views(self):
        size = len(self.tab)
        for index in range(size):
            self.tabs.removeTab(size-1-index)
        self.tab = []

    def append_tabs_surfaces(self):
        current_tab = self.tabs.currentIndex()

        files = []
        for surface_file_name in self.selected_files_with_path:
            files.append(os.path.basename(surface_file_name))

        #
        if not len(files) == 0:
            for title in files:
                self.tab.append(oasysgui.createTabPage(self.tabs, title))

            for tab in self.tab:
                tab.setFixedHeight(self.IMAGE_HEIGHT)
                tab.setFixedWidth(self.IMAGE_WIDTH)

            self.tabs.setCurrentIndex(current_tab)
        else:
            pass

    def get_selection(self):
        cursor = self.files_area.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        print('Selected Count: ' + str(end - start))
        txt = self.files_area.textCursor().selectedText()
        selected_files = txt.split("\u2029")
        print('Selected files:\n ', selected_files)

        IDX = []
        for file in selected_files:
            if file in self.scanned_files_without_path:
                idx = self.scanned_files_without_path.index(file)
                IDX.append(idx)
                print("** found: ", file, idx)

        print("IDX: ", IDX)

        SELECTED_FILES_WITH_PATH = []
        SELECTED_FILES_WITHOUT_PATH = []
        for idx in IDX:
            SELECTED_FILES_WITH_PATH.append(self.scanned_files_with_path[idx])
            SELECTED_FILES_WITHOUT_PATH.append(self.scanned_files_without_path[idx])

        if len(IDX) > 0: print("SELECTED_PATH", idx, SELECTED_FILES_WITH_PATH)

        self.selected_files_with_path = SELECTED_FILES_WITH_PATH
        self.selected_files_without_path = SELECTED_FILES_WITHOUT_PATH

    def view_selection(self):
        self.get_selection()

        try:
            self.read_selected_data_files()
            self.append_tabs_surfaces()
            self.plot_selection()
        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def view_sum(self):
        self.get_selection()

        try:
            self.read_selected_data_files_sum()
            # self.append_tabs_surfaces()
            current_tab = self.tabs.currentIndex()
            self.tab.append(oasysgui.createTabPage(self.tabs, "sum"))
            for tab in self.tab:
                tab.setFixedHeight(self.IMAGE_HEIGHT)
                tab.setFixedWidth(self.IMAGE_WIDTH)

            self.tabs.setCurrentIndex(current_tab)
            self.plot_selection(title="sum")

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def read_selected_data_files(self):
        self.data = []
        for surface_file_name in self.selected_files_with_path:
            surface_file_name = congruence.checkDir(surface_file_name)

            try: # OASYS surface data format
                file = h5py.File(surface_file_name, 'r')
                zz = file["surface_file" + "/Z"][()].T
                xx = file["surface_file" + "/X"][()]
                yy = file["surface_file" + "/Y"][()]
                print("Data read from file: ", surface_file_name, zz.shape, xx.shape, yy.shape)
            except Exception as ee:
                raise IOError("Error loading HDF5 file" + str(ee))

            zz = zz * self.conversion_to_m_z # if self.negate == 0 else -1.0 * zz * self.conversion_to_m_z
            if self.rebase: zz -= zz.min()

            self.data.append([xx, yy, zz])

    def read_selected_data_files_sum(self):

        for i, surface_file_name in enumerate(self.selected_files_with_path):
            surface_file_name = congruence.checkDir(surface_file_name)

            try: # OASYS surface data format
                file = h5py.File(surface_file_name, 'r')
                zz = file["surface_file" + "/Z"][()].T
                xx = file["surface_file" + "/X"][()]
                yy = file["surface_file" + "/Y"][()]
                print("Data read from file: ", surface_file_name, zz.shape, xx.shape, yy.shape)
            except Exception as ee:
                raise IOError("Error loading HDF5 file" + str(ee))

            zz = zz * self.conversion_to_m_z # if self.negate == 0 else -1.0 * zz * self.conversion_to_m_z
            if self.rebase: zz -= zz.min()

            if i == 0:
                XX = xx.copy()
                YY = yy.copy()
                ZZ = zz.copy()
            else:
                interpolator = RectBivariateSpline(xx, yy, zz, kx=3, ky=3, s=0)
                zz_interpolated = interpolator(XX, YY)
                print(">>>> adding index orig interpolated ", i, zz.shape, zz_interpolated.shape, surface_file_name)
                print(">>>> adding to ", ZZ.shape)
                ZZ += zz_interpolated

        self.data = []
        try:
            self.data.append([XX, YY, ZZ])
        except:
            pass

    def plot_data2D(self, data2D, dataX, dataY, tabs_canvas_index, title="title", xtitle="X",ytitle="Y"):

        print(">>>>>> plotting ", data2D.shape, dataX.shape, dataY.shape)
        tabs_canvas_index.layout().removeItem(tabs_canvas_index.layout().itemAt(0))

        origin = (dataX[0], dataY[0])
        scale = (dataX[1] - dataX[0], dataY[1] - dataY[0])

        colormap = {"name": "temperature", "normalization": "linear",
                    "autoscale": True, "vmin": 0, "vmax": 0, "colors": 256}

        tmp = Plot2D()
        tmp.resetZoom()
        tmp.setXAxisAutoScale(True)
        tmp.setYAxisAutoScale(True)
        tmp.setGraphGrid(False)
        tmp.setKeepDataAspectRatio(True)
        tmp.yAxisInvertedAction.setVisible(False)
        tmp.setXAxisLogarithmic(False)
        tmp.setYAxisLogarithmic(False)
        tmp.getMaskAction().setVisible(False)
        tmp.getRoiAction().setVisible(False)
        tmp.getColormapAction().setVisible(True)
        tmp.setKeepDataAspectRatio(False)
        tmp.addImage(data2D.T,legend="1",scale=scale,origin=origin,colormap=colormap,replace=True)
        tmp.setActiveImage("1")
        tmp.setGraphXLabel(xtitle)
        tmp.setGraphYLabel(ytitle)
        tmp.setGraphTitle(title)
        tabs_canvas_index.layout().addWidget(tmp)

    def plot_selection(self, title=None):
        #
        # result
        #
        print(">>>>>>> in plot selection len: ", len(self.data))
        for index in range(len(self.data)):
            tab_index = -len(self.data) + index
            print("plotting fig index ", index, "in tab_index", tab_index)

            xx, yy, zz = self.data[index]
            title_top = "file: %s" % self.selected_files_without_path[index]
            if len(self.selected_files_without_path) > 1 and title is not None: title_top=title
            print("title, title_top: ", title, title_top, len(self.selected_files_without_path))

            self.plot_data2D(zz, xx, yy,
                       self.tab[tab_index],
                       title=title_top,
                       xtitle="X [m] (%d pixels, max:%f)"%(xx.size, xx.max()),
                       ytitle="Y [m] (%d pixels, max:%f)"%(yy.size, yy.max()) )


    def zernike(self):
        ################################### ZERNIKE #################################################################
        import barc4ro.barc4ro as b4RO
        N = 37
        heightProfData = self.data[-1][2].T
        Zcoeffs, fit, residues = b4RO.fit_zernike_circ(heightProfData, nmodes=N, startmode=1, rec_zern=False)
        print('Zernike coefficients (um): \n' + str(Zcoeffs * 1e6))

        from barc4plots.refactored_barc4plots import Data4Plot
        p = Data4Plot(image = Zcoeffs * 1e6, axis_x = None, axis_y = None, sort_ax = False, sort_ax_lim = False)
        p.label = "ZZZ"
        p.AxLegends[0] = "top title"
        p.AxLegends[1] = "coefficients"
        p.AxLegends[2] = r"$\mu$m"
        p.MinMax[0] = -2.5
        p.MinMax[1] = 2.5
        p.plot_wft_coeffs(noll=True)
        ################################### END ZERNIKE #############################################################
    def print_statistics(self):
        for data_i in self.data:

            slopeErrorRMS_X, slopeErrorRMS_Y = slopes(data_i[2],
                         data_i[0],
                         data_i[1],
                         silent=1, return_only_rms=1)


            print("\n*****************")
            print("Heigh error StDev: %g um" % (1e6 * data_i[2].std()))
            print("Slope error StDev in axis0: %g urad" % (1e6 * slopeErrorRMS_X))
            print("Slope error StDev in axis1: %g urad" % (1e6 * slopeErrorRMS_Y))
            print("*****************")

            import barc4ro.barc4ro as b4RO
            Zcoeffs, fit, residues = b4RO.fit_zernike_circ(data_i[2], nmodes=37, startmode=1, rec_zern=False)
            print('Zernike coefficients (um): \n' + str(Zcoeffs * 1e6))
if __name__ == "__main__":
    if 1:
        app = QApplication(sys.argv)
        w = OWdabam2d()
        w.root = "/nobackup/gurb1/srio/DABAM2D/ESRF/C_2D_R320um"
        w.show()
        app.exec()
        w.saveSettings()
    else:
        # import re
        # import urllib
        #
        # # def ls_ows(target_url="https://github.com/oasys-esrf-kit/dabam2d/tree/main/data/"):
        # def ls_ows(target_url="https://github.com/PaNOSC-ViNYL/Oasys-PaNOSC-Workspaces"):
        #     data = urllib.request.urlopen(target_url)
        #     list_files = []
        #     for line in data:
        #         line1 = str(line)
        #
        #         if ".dat" in line1:
        #             try:
        #                 found = re.search('dat">(.+?)</a>', line1).group(1)
        #                 list_files.append(found)
        #             except:
        #                 pass
        #
        # print(ls_ows("https://github.com/oasys-kit/dabaxFiles"))
        import github

        g = github.Github("USERNAME", "PASSWORD")
        repo = g.get_user().get_repo("REPO_NAME")
        print
        repo.get_dir_contents("")
