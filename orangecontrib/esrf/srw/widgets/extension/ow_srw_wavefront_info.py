from oasys.widgets import widget
from oasys.widgets import gui as oasysgui

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QRect

from orangecontrib.srw.util.srw_objects import SRWData

from wofrysrw.storage_ring.light_sources.srw_bending_magnet_light_source import SRWBendingMagnetLightSource
from wofrysrw.storage_ring.light_sources.srw_gaussian_light_source import SRWGaussianLightSource
from wofrysrw.storage_ring.light_sources.srw_undulator_light_source import SRWUndulatorLightSource
from wofrysrw.storage_ring.light_sources.srw_wiggler_light_source import SRWWigglerLightSource

from wofrysrw.beamline.srw_beamline import SRWBeamline

from oasys_srw.srwlib import *
import numpy as np
from skimage.restoration import unwrap_phase
import matplotlib.pyplot as plt


class OWSRWWavefrontInfo(widget.OWWidget):
    name = "Wavefront Info"
    id = "OWSRWWavefrontInfo"
    description = "Info"
    icon = "icons/info.png"
    priority = 35
    category = ""
    keywords = ["SRW", "info"]

    inputs = [("SRWData", SRWData, "set_input")]


    inputs = [("SRWData # 1", SRWData, "set_input_1"),
              ("SRWData # 2", SRWData, "set_input_2")]


    CONTROL_AREA_WIDTH = 600
    CONTROL_AREA_HEIGHT = 650

    srw_data = None

    want_main_area = 0

    def __init__(self):
        super().__init__()

        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width()*0.05),
                               round(geom.height()*0.05),
                               round(min(geom.width()*0.98, self.CONTROL_AREA_WIDTH+10)),
                               round(min(geom.height()*0.95, self.CONTROL_AREA_HEIGHT+10))))

        self.setFixedHeight(self.geometry().height())
        self.setFixedWidth(self.geometry().width())

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        self.text_area = oasysgui.textArea(height=self.CONTROL_AREA_HEIGHT-10, width=self.CONTROL_AREA_WIDTH-5, readOnly=True)
        self.text_area.setText("")
        self.text_area.setStyleSheet("background-color: white; font-family: Courier, monospace;")

        self.controlArea.layout().addWidget(self.text_area)


    # def set_input(self, input_data):
    #     self.setStatusMessage("")
    #
    #     if not input_data is None:
    #         self.srw_data = input_data
    #
    #         self.build_info()

    def set_input_1(self, input_data):
        self.setStatusMessage("")

        if not input_data is None:
            self.srw_data_1 = input_data

            self.build_info()

    def set_input_2(self, input_data):
        self.setStatusMessage("")

        if not input_data is None:
            self.srw_data_2 = input_data

            self.build_info()

    def extract_info(self, wfr, plots=False):

        # self.srw_data.get_srw_beamline()
        # parameters

        stvt_x = 8  # half window size in pixel for fit
        stvt_y = 8  # half window size in pixel for fit
        plots = False

        k = 2 * np.pi / srwl_uti_ph_en_conv(wfr.mesh.eStart, _in_u='eV', _out_u='m')

        # 2D intensity extraction

        arI1 = array('f', [0] * wfr.mesh.nx * wfr.mesh.ny)  # "flat" 2D array to take intensity data
        srwl.CalcIntFromElecField(arI1, wfr, 6, 0, 3, wfr.mesh.eStart, 0, 0)
        wp_intensity = np.reshape(arI1, (wfr.mesh.ny, wfr.mesh.nx))

        # 2D phase extraction

        arP1 = array('d', [0] * wfr.mesh.nx * wfr.mesh.ny)
        srwl.CalcIntFromElecField(arP1, wfr, 0, 4, 3, wfr.mesh.eStart, 0, 0)

        wp_phase = np.reshape(arP1, (wfr.mesh.ny, wfr.mesh.nx))
        wp_phase_x = wp_phase[int(wfr.mesh.ny / 2), int(wfr.mesh.nx / 2) - stvt_x:int(wfr.mesh.nx / 2) + stvt_x]
        wp_phase_y = wp_phase[int(wfr.mesh.ny / 2) - stvt_y:int(wfr.mesh.ny / 2) + stvt_y, int(wfr.mesh.nx / 2)]

        # Unwrapped phase
        uwp_phase = unwrap_phase(wp_phase)
        uwp_phase_x = unwrap_phase(wp_phase_x)
        uwp_phase_y = unwrap_phase(wp_phase_y)

        dx = (wfr.mesh.xFin - wfr.mesh.xStart) / wfr.mesh.nx
        dy = (wfr.mesh.yFin - wfr.mesh.yStart) / wfr.mesh.ny

        nx = wp_phase_x.shape[0]
        ny = wp_phase_y.shape[0]

        xStart = - (dx * (nx - 1)) / 2.0
        xFin = xStart + dx * (nx - 1)

        yStart = - (dy * (ny - 1)) / 2.0
        yFin = yStart + dy * (ny - 1)

        x = np.linspace(xStart, xFin, nx)
        y = np.linspace(yStart, yFin, ny)

        px = np.polynomial.polynomial.polyfit(x, uwp_phase_x, 5)
        Rx = k / (2 * px[2])

        py = np.polynomial.polynomial.polyfit(y, uwp_phase_y, 5)
        Ry = k / (2 * py[2])

        txt = '\n'
        txt += '- Propagated wavefront:\n'
        txt += 'Nx = %d, Ny = %d\n' % (wfr.mesh.nx, wfr.mesh.ny)
        txt += 'dx = %.4f um, dy = %.4f um\n' % (
        (wfr.mesh.xFin - wfr.mesh.xStart) * 1E6 / wfr.mesh.nx, (wfr.mesh.yFin - wfr.mesh.yStart) * 1E6 / wfr.mesh.ny)
        txt += 'range x = %.4f um, range y = %.4f um\n' % (
        (wfr.mesh.xFin - wfr.mesh.xStart) * 1E6, (wfr.mesh.yFin - wfr.mesh.yStart) * 1E6)
        txt += ' \n'
        txt += '- Wavefront curvature:\n'
        txt += 'SRW native: Rx = %.10f, Ry = %.10f\n' % (wfr.Rx, wfr.Ry)
        txt += 'Phase fit: Rx = %.10f, Ry = %.10f\n' % (Rx, Ry)
        txt += 'dRx = %.3f %%, dRy = %.3f %%\n' % ((Rx - wfr.Rx) * 100 / Rx, (Ry - wfr.Ry) * 100 / Ry)
        txt += ' \n'
        txt += '- Intensity:\n'
        txt += 'Total counts: %g\n' % (wp_intensity.sum())
        flux = wp_intensity.sum() * dx * dy * 1e6
        txt += 'Photon flux = %g\n' % (flux)

        if plots:
            # plots for visual inspection

            fig, axs = plt.subplots(3, 2)

            # arI1 = array('f', [0] * wfr.mesh.nx * wfr.mesh.ny)
            # srwl.CalcIntFromElecField(arI1, wfr, 6, 0, 3, wfr.mesh.eStart, 0, 0)
            # intensity = np.reshape(arP1, (wfr.mesh.ny, wfr.mesh.nx))

            axs[0, 0].set_title("wrapped phase")
            im = axs[0, 0].imshow(wp_phase,
                                  extent=[wfr.mesh.xStart * 1e6, wfr.mesh.xFin * 1e6, wfr.mesh.yStart * 1e6,
                                          wfr.mesh.yFin * 1e6], cmap=plt.cm.binary_r)
            plt.colorbar(im, ax=axs[0, 0])

            axs[0, 1].set_title("unwrapped phase")
            im = axs[0, 1].imshow(uwp_phase,
                                  extent=[wfr.mesh.xStart * 1e6, wfr.mesh.xFin * 1e6, wfr.mesh.yStart * 1e6,
                                          wfr.mesh.yFin * 1e6], cmap=plt.cm.jet)
            plt.colorbar(im, ax=axs[0, 1])

            axs[1, 0].set_title("wrapped phase - fit")
            im = axs[1, 0].plot(x * 1e6, wp_phase_x, label='h')
            im = axs[1, 0].plot(y * 1e6, wp_phase_y, label='v')
            axs[1, 0].legend(loc=1)

            axs[1, 1].set_title("unwrapped phase")
            im = axs[1, 1].plot(x * 1e6, uwp_phase_x, label='h')
            im = axs[1, 1].plot(y * 1e6, uwp_phase_y, label='v')
            axs[1, 1].legend(loc=1)

            # Reconstructed phase
            ph_x = px[0] + px[1] * x + px[2] * x ** 2
            ph_y = py[0] + py[1] * x + py[2] * x ** 2

            axs[2, 0].set_title("reconstructed phase")
            im = axs[2, 0].plot(x * 1e6, ph_x, label='h')
            im = axs[2, 0].plot(y * 1e6, ph_y, label='v')
            axs[2, 0].legend(loc=1)

            axs[2, 1].set_title("residues")
            im = axs[2, 1].plot(x * 1e6, uwp_phase_x - ph_x, label='h')
            im = axs[2, 1].plot(y * 1e6, uwp_phase_y - ph_y, label='v')
            axs[2, 1].legend(loc=1)

            fig.tight_layout()

            plt.subplot_tool()
            plt.show()

        return txt, flux


    def build_info(self):
        self.text_area.clear()
        txt1 = ""
        txt2 = ""
        txt3 = ""
        nwavefronts = 0
        try:
            txt1, flux1 =  self.extract_info(self.srw_data_1._SRWData__srw_wavefront)
            nwavefronts += 1
        except Exception as exception:
            pass
            # QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)
            # if self.IS_DEVELOP: raise exception

        try:
            txt2, flux2 = self.extract_info(self.srw_data_2._SRWData__srw_wavefront)
            nwavefronts += 1
        except Exception as exception:
            pass
            # QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)
            # if self.IS_DEVELOP: raise exception

        if nwavefronts == 2:
            txt3 = "\n************* Wavefronts intensity ratio\n"
            txt3 += "transmission (intensity # 2 / intensity # 1): %f\n" % (flux2 / flux1)
            txt3 += "absorption (1 - transmission): %f\n" % (1 - flux2 / flux1)

        self.text_area.setText("************* Wavefront # 1:\n" + txt1 +
                               "\n************* Wavefront # 2:\n" + txt2 +
                               txt3)