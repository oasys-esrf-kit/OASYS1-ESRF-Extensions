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
class Score():
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



if __name__ == "__main__":
    from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D

    sc = Score(scan_variable_name='mode index',additional_stored_variable_names=['a','b'])


    for xmode in range(51):
        output_wavefront = GenericWavefront1D.initialize_wavefront_from_range(x_min=-0.00012, x_max=0.00012,
                                                                              number_of_points=1000)
        output_wavefront.set_photon_energy(10000)
        output_wavefront.set_gaussian_hermite_mode(sigma_x=3.03783e-05, amplitude=1, mode_x=xmode, shift=0, beta=0.0922395)

        if xmode == 0:
            WF = output_wavefront.duplicate()
        else:
            intens = WF.get_intensity()
            intens += output_wavefront.get_intensity()
            WF.set_complex_amplitude(numpy.sqrt(intens))

        sc.append(WF, scan_variable_value=xmode, additional_stored_values=[1,2.1])

    sc.plot()
    sc.save("tmp.dat")
