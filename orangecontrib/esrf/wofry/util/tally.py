import numpy
from oasys.util.oasys_util import get_fwhm

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

    def save(self, filename="tmp.dat", add_header=True):
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

    def plot(self, title=""):
        from srxraylib.plot.gol import plot
        x = numpy.array(self.scan_variable_value)


        y = numpy.array(self.intensity_at_center)
        plot(x, y, yrange=[0,1.1*y.max()],
             title=title, ytitle="Intensity at center[a.u.]", xtitle=self.scan_variable_name,
             figsize=(15, 4), show=0)

        # y = numpy.array(self.intensity_total)
        # plot(x, y, yrange=[0,1.1*y.max()],
        #      title=title, ytitle="Beam intensity [a.u.]", xtitle=self.scan_variable_name,
        #      figsize=(15, 4), show=0)

        y = numpy.array(self.fwhm)
        plot(x, y, yrange=[0,1.1*y.max()],
             title=title, ytitle="FWHM [um]", xtitle=self.scan_variable_name,
             figsize=(15, 4), show=1)



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

    def plot_cross_spectral_density(self):
        from srxraylib.plot.gol import plot, plot_image
        csd = self.get_cross_pectral_density()
        plot_image(numpy.abs(csd), 1e6*self.abscissas, 1e6*self.abscissas,
                   title="Cross Spectral Density", xtitle="X1 [um]", ytitle="X2 [um]")
        print("matrix cross_spectral_density: ", csd.shape)

    def plot_spectral_density(self):
        #
        # plot intensity
        #
        abscissas = self.get_abscissas()
        eigenvalues = self.get_eigenvalues()
        eigenvectors = self.get_eigenvectors()
        csd = self.get_cross_pectral_density()

        from srxraylib.plot.gol import plot
        # abscissas = self.get_wavefronts()[-1].get_abscissas()
        nmodes = self.get_number_of_calls()
        y = numpy.zeros_like(abscissas)
        for i in range(nmodes):
            y += eigenvalues[i] * numpy.real(numpy.conjugate(eigenvectors[i, :]) * eigenvectors[i, :])

        spectral_density = self.get_spectral_density() # numpy.zeros_like(abscissas)
        # for i in range(abscissas.size):
        #     spectral_density[i] = csd[i, i]

        fwhm, quote, coordinates = get_fwhm(spectral_density, 1e6 * abscissas)
        plot(1e6 * abscissas, spectral_density,
             1e6 * abscissas, y, legend=["From Cross Spectral Density", "From modes"],
             xtitle="x [um]", ytitle="Spectral Density", title="FWHM = %g um" % fwhm)

    def plot_occupation(self):
        x, y = self.get_occupation()
        nmodes = self.get_number_of_calls()
        from srxraylib.plot.gol import plot
        plot(x[0:nmodes], y[0:nmodes],
             title="CF: %g" % (y[0]),
             xtitle="mode index", ytitle="occupation")


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

    sc.plot()
    sc.save("tmp.dat")

    from srxraylib.plot.gol import plot
    plot(sc.get_abscissas(), sc.get_spectral_density_from_intensities(), title="Spectral Density from intensities")

    sc.plot_cross_spectral_density()
    sc.plot_spectral_density()
    sc.plot_occupation()


    # cf, _, _, _ = sc.calculate_coherent_fraction(do_plot=1)