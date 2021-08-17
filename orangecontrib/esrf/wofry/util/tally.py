import numpy
from oasys.util.oasys_util import get_fwhm

from srxraylib.plot.gol import plot, plot_image
import matplotlib.pylab as plt
import os

# def get_fwhm(histogram, bins):
#     quote = numpy.max(histogram)*0.5
#     cursor = numpy.where(histogram >= quote)
#
#     if histogram[cursor].size > 1:
#         bin_size    = bins[1]-bins[0]
#         fwhm        = bin_size*(cursor[0][-1]-cursor[0][0])
#         coordinates = (bins[cursor[0][0]], bins[cursor[0][-1]])
#     else:
#         fwhm = 0.0
#         coordinates = None
#
#     return fwhm, quote, coordinates

#
#
#
class Tally():
    def __init__(self,
                 scan_variable_name='x',
                 additional_stored_variable_names=None,
                 do_store_wavefronts=False):
        self.reset()
        self.scan_variable_name = scan_variable_name
        self.additional_stored_variable_names = additional_stored_variable_names
        self.do_store_wavefronts = do_store_wavefronts

    def reset(self):
        self.scan_variable_index = -1
        self.scan_variable_value = []
        self.fwhm = []
        self.intensity_at_center = []
        self.intensity_total = []
        self.intensity_peak = []
        self.additional_stored_values = []
        self.stored_wavefronts = []


    def append(self, wf, scan_variable_value=None, additional_stored_values=None):
        fwhm, intensity_total, intensity_at_center, intensity_peak = self.process_wavefront(wf)
        self.fwhm.append(fwhm)
        self.intensity_at_center.append(intensity_at_center)
        self.intensity_total.append(intensity_total)
        self.intensity_peak.append(intensity_peak)
        self.scan_variable_index += 1
        if scan_variable_value is None:
            self.scan_variable_value.append(self.scan_variable_index)
        else:
            self.scan_variable_value.append(scan_variable_value)

        self.additional_stored_values.append(additional_stored_values)

        if self.do_store_wavefronts:
            self.stored_wavefronts.append(wf.duplicate())

    def get_wavefronts(self):
        return self.stored_wavefronts

    def get_number_of_calls(self):
        return self.scan_variable_index + 1

    def get_additional_stored_values(self):
        return self.additional_stored_values

    def get_scan_variable_value(self):
        return numpy.array(self.scan_variable_value)

    def get_intensity_at_center(self):
        return numpy.array(self.intensity_at_center)

    def get_fwhm(self):
        return numpy.array(self.fwhm)

    def get_wavefronts_intensity(self):
        if len(self.stored_wavefronts) == 0:
            raise Exception("No stored wavefronts found")

        for i, wf in enumerate(self.stored_wavefronts):
            x, y = wf.get_abscissas(), wf.get_intensity()
            if i == 0:
                INTENSITY = numpy.zeros((self.get_number_of_calls(), x.size))
            INTENSITY[i, :] = y
        return INTENSITY

    def get_wavefronts_abscissas(self):
        if len(self.stored_wavefronts) == 0:
            raise Exception("No stored wavefronts found")
        else:
            return self.stored_wavefronts[-1].get_abscissas()

    def save_scan(self, filename="tmp.dat", add_header=True):
        f = open(filename, 'w')
        if add_header:
            if self.additional_stored_variable_names is None:
                number_of_additional_parameters = 0
            else:
                number_of_additional_parameters = len(self.additional_stored_variable_names)
            header = "#S 1 scored data\n"
            header += "#N %d\n" % (number_of_additional_parameters + 5)
            header_titles = "#L  %s  %s  %s  %s  %s" % (self.scan_variable_name, "fwhm", "total_intensity", "on_axis_intensity", "peak_intensity")
            for i in range(number_of_additional_parameters):
                header_titles += "  %s" % self.additional_stored_variable_names[i]
            header_titles += "\n"
            header += header_titles
            f.write(header)
        for i in range(len(self.fwhm)):
            f.write("%g %g %g %g %g" % (self.scan_variable_value[i],
                                    1e6*self.fwhm[i],
                                    self.intensity_total[i],
                                    self.intensity_at_center[i],
                                    self.intensity_peak[i]))
            for j in range(number_of_additional_parameters):
                f.write(" %g" % self.additional_stored_values[i][j])
            f.write("\n")
        f.close()
        print("File written to disk: %s" % filename)

    def plot(self, title="", factor_abscissas=1.0, xtitle=None):
        self.plot_fwhm(title=title, factor_abscissas=factor_abscissas, xtitle=xtitle)
        self.plot_intensity_at_center(title=title, factor_abscissas=factor_abscissas, xtitle=xtitle)

    def plot_intensity_at_center(self, title="", factor_abscissas=1.0, xtitle=None):
        x = numpy.array(self.scan_variable_value)
        y = numpy.array(self.intensity_at_center)
        if xtitle is None:
            xtitle = self.scan_variable_name
        out = plot(factor_abscissas * x, y, yrange=[0,1.1*y.max()],
             title=title, ytitle="Intensity at center[a.u.]", xtitle=xtitle,
             figsize=(15, 4), show=0)
        return out

    def plot_fwhm(self, title="", factor_fwhm=1.0, xtitle=None, ytitle=None):
        x = numpy.array(self.scan_variable_value)
        y = numpy.array(self.fwhm)
        if xtitle is None:
            xtitle = self.scan_variable_name
        if ytitle is None:
            if factor_fwhm == 1.0:
                ytitle = "FWHM [m]"
            elif factor_fwhm == 1e6:
                ytitle = "FWHM [um]"
            else:
                ytitle = "FWHM"

        out = plot(x, factor_fwhm * y, yrange=[0,1.1*factor_fwhm*y.max()],
             title=title, ytitle=ytitle, xtitle=xtitle,
             figsize=(15, 4), show=1)
        return out

    def plot_wavefronts_intensity(self,
                                  xtitle="scan_variable_value",
                                  ytitle="wavefront abscissas",
                                  factor_abscissas=1.0,
                                  title=""):

        out = plot_image(self.get_wavefronts_intensity(),
                   self.get_scan_variable_value(),
                   factor_abscissas * self.get_wavefronts_abscissas(),
                   xtitle=xtitle, ytitle=ytitle, title=title, aspect='auto')
        return out

    @classmethod
    def process_wavefront(cls, wf):
        I = wf.get_intensity()
        x = wf.get_abscissas()

        fwhm, quote, coordinates = get_fwhm(I, x)
        intensity_at_center = I[I.size // 2]
        intensity_total = I.sum() * (x[1] - x[0])
        intensity_peak = I.max()

        return fwhm, intensity_total, intensity_at_center, intensity_peak



class TallyCoherentModes(Tally):
    def __init__(self,
                 additional_stored_variable_names=None):

        super().__init__(scan_variable_name='mode_index',
                 additional_stored_variable_names=additional_stored_variable_names,
                 do_store_wavefronts=True)

        self.abscissas = None
        self.cross_spectral_density = None
        self.spectral_density = None,
        self.eigenvalues = None
        self.eigenvectors = None

    def get_cross_pectral_density(self):
        if self.cross_spectral_density is None: self.calculate_cross_spectral_density()
        return self.cross_spectral_density

    def get_spectral_density_from_intensities(self):
        WF = self.get_wavefronts()
        print(WF)
        intensity = None
        for i,wf in enumerate(WF):
            if intensity is None:
                intensity = wf.get_intensity()
            else:
                intensity += wf.get_intensity()
        return intensity


    def get_spectral_density(self):
        csd = self.get_cross_pectral_density()
        nx = csd.shape[0]
        spectral_density = numpy.zeros(nx)
        for i in range(nx):
            spectral_density[i] = csd[i, i]
        return spectral_density

    def get_eigenvalues(self):
        if self.eigenvalues is None: self.diagonalize()
        return self.eigenvalues

    def get_eigenvectors(self):
        if self.eigenvectors is None: self.diagonalize()
        return self.eigenvectors

    def get_abscissas(self):
        if self.abscissas is None: self.abscissas = self.get_wavefronts()[-1].get_abscissas()
        return self.abscissas


    def calculate_cross_spectral_density(self, do_plot=False):
        # retrieve arrays
        WFs = self.get_wavefronts()
        nmodes = self.get_number_of_calls()
        abscissas = self.get_abscissas()
        #
        # calculate the CSD
        #

        input_array = numpy.zeros((nmodes, abscissas.size), dtype=complex)
        for i,wf in enumerate(WFs):
            input_array[i,:] = wf.get_complex_amplitude() # tmp[i][0]

        cross_spectral_density = numpy.zeros((abscissas.size, abscissas.size), dtype=complex)

        for i in range(nmodes):
            cross_spectral_density += numpy.outer(numpy.conjugate(input_array[i, :]), input_array[i, :])

        self.cross_spectral_density = cross_spectral_density


    def diagonalize(self, do_plot=False):
        csd = self.get_cross_pectral_density()

        #
        # diagonalize the CSD
        #

        w, v = numpy.linalg.eig(csd)
        print(w.shape, v.shape)
        idx = w.argsort()[::-1]  # large to small
        self.eigenvalues = numpy.real(w[idx])
        self.eigenvectors = v[:, idx].T


    def get_occupation(self):
        ev = self.get_eigenvalues()
        nmodes = self.get_number_of_calls()
        return  numpy.arange(ev.size), ev / ev.sum()



    def calculate_coherent_fraction(self, do_plot=False):
        if self.eigenvalues is None:
            self.diagonalize()
        # eigenvalues, eigenvectors, cross_spectral_density = self.diagonalize(do_plot=do_plot)
        cf = self.eigenvalues[0] / self.eigenvalues.sum()
        return cf, self.eigenvalues, self.eigenvectors, self.cross_spectral_density

    def plot_cross_spectral_density(self, show=True, filename=""):
        csd = self.get_cross_pectral_density()
        plot_image(numpy.abs(csd), 1e6*self.abscissas, 1e6*self.abscissas,
                   title="Cross Spectral Density", xtitle="X1 [um]", ytitle="X2 [um]",show=False)

        if filename != "":
            plt.savefig(filename)
            print("File written to disk: %s" % filename)

        if show:
            plt.show()
        else:
            plt.close()

        print("matrix cross_spectral_density: ", csd.shape)

    def plot_spectral_density(self, show=True, filename="", method=2, title=""):
        #
        # plot intensity
        #
        abscissas = self.get_abscissas()
        eigenvalues = self.get_eigenvalues()
        eigenvectors = self.get_eigenvectors()
        csd = self.get_cross_pectral_density()

        spectral_density = self.get_spectral_density() # numpy.zeros_like(abscissas)
        fwhm, quote, coordinates = get_fwhm(spectral_density, 1e6 * abscissas)

        if method > 0:
            nmodes = self.get_number_of_calls()
            y = numpy.zeros_like(abscissas)
            for i in range(nmodes):
                y += eigenvalues[i] * numpy.real(numpy.conjugate(eigenvectors[i, :]) * eigenvectors[i, :])

        if method == 0:
            plot(1e6 * abscissas, spectral_density,
                 xtitle="x [um]", ytitle="Spectral Density (From Cross Spectral Density)",
                 title="%s FWHM = %g um" % (title, fwhm), show=False)
        elif method == 1:
            plot(1e6 * abscissas, y,
                 xtitle="x [um]", ytitle="Spectral Density (From modes)", title="%s FWHM = %g um" % (title,fwhm), show=False)
        elif method == 2:
            plot(1e6 * abscissas, spectral_density,
                 1e6 * abscissas, y, legend=["From Cross Spectral Density", "From modes"],
                 xtitle="x [um]", ytitle="Spectral Density", title="%s FWHM = %g um" % (title, fwhm), show=False)


        if filename != "":
            plt.savefig(filename)
            print("File written to disk: %s" % filename)

        if show:
            plt.show()
        else:
            plt.close()

    def save_spectral_density(self, filename="", add_header=True):
        #
        # plot intensity
        #
        abscissas = self.get_abscissas()
        eigenvalues = self.get_eigenvalues()
        eigenvectors = self.get_eigenvectors()
        csd = self.get_cross_pectral_density()

        spectral_density = self.get_spectral_density()
        fwhm, quote, coordinates = get_fwhm(spectral_density, 1e6 * abscissas)


        f = open(filename, 'w')
        if add_header:
            header = "#S 1 spectral density\n#N 2\n#UFWHM %g\n" % fwhm
            header += "#L  %s  %s\n" % ("abscissas [um]","spectral density")
            f.write(header)

        for i in range(abscissas.size):
            f.write("%g  %g\n" % (1e6 * abscissas[i], spectral_density[i]))
        f.close()
        print("File written to disk: %s" % filename)


    def plot_occupation(self, show=True, filename=""):
        x, y = self.get_occupation()
        nmodes = self.get_number_of_calls()
        plot(x[0:nmodes], y[0:nmodes],
             title="CF: %g" % (y[0]),
             xtitle="mode index", ytitle="occupation", show=False)

        if filename != "":
            plt.savefig(filename)
            print("File written to disk: %s" % filename)

        if show:
            plt.show()
        else:
            plt.close()

    def save_occupation(self, filename="", add_header=True):
        x, y = self.get_occupation()
        nmodes = self.get_number_of_calls()


        f = open(filename, 'w')
        if add_header:
            header = "#S 1 occupation\n#N 2\n"
            header += "#L  %s  %s\n" % ("mode index","occupation")
            f.write(header)

        for i in range(nmodes):
            f.write("%g  %g\n" % (x[i], y[i]))
        f.close()
        print("File written to disk: %s" % filename)


if __name__ == "__main__":
    from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D

    # sc = Tally(scan_variable_name='mode index', additional_stored_variable_names=['a', 'b'])
    sc = TallyCoherentModes()
    for xmode in range(51):
        output_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=-0.00012, x_max=0.00012,
                                                                              number_of_points=1000)
        output_wavefront.set_photon_energy(10000)
        output_wavefront.set_gaussian_hermite_mode(sigma_x=3.03783e-05, amplitude=1, mode_x=xmode, shift=0, beta=0.0922395)


        sc.append(output_wavefront, scan_variable_value=xmode, additional_stored_values=[1,2.1])

    # sc.plot()
    sc.save_scan("tmp.dat")

    # plot(sc.get_abscissas(), sc.get_spectral_density_from_intensities(), title="Spectral Density from intensities")

    sc.plot_cross_spectral_density(show=1,filename="tmp_cs.png")
    sc.plot_spectral_density(show=1, filename="tmp_sd.png", method=2)
    sc.save_spectral_density(filename="tmp_sd.txt")
    sc.plot_occupation(show=1, filename="tmp_occ.png",)
    sc.save_occupation(filename="tmp_occ.txt")


    # cf, _, _, _ = sc.calculate_coherent_fraction(do_plot=1)