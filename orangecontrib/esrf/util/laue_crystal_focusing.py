#
# **Focusing with Laue crystal** Theory and equations from:
# Guigay and Ferrero "Dynamical focusing by bent Laue crystals" Acta Cryst. (2016). A72, 489–499
#

import numpy
import mpmath
import scipy
import time

from scipy.special import jv as BesselJ
import scipy.constants as codata

from srxraylib.plot.gol import plot, set_qt, plot_show
from wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D



def hyp1f1_series_small(a, b, z, terms=20):
    """Series expansion for small |z|"""
    result = 1.0
    term = 1.0
    for k in range(1, terms):
        term *= (a + k - 1) * z / ((b + k - 1) * k)
        result += term
        if abs(term) < 1e-15:
            break
    return result

def fast_hyp1f1(kap, yprime):
    """
    Fast replacement for mpmath.hyp1f1(1j*kap, 1, 1j*yprime)
    """
    yp_abs = abs(yprime)

    if yp_abs < 1e-8:
        return 1.0 + 1j * (kap * yprime)

    elif yp_abs < 5:
        # Series expansion for small arguments
        return hyp1f1_series_small(1j * kap, 1, 1j * yprime)

    elif yp_abs > 100:
        # Asymptotic expansion for large arguments
        z = 1j * yprime
        return mpmath.exp(z) * z ** (-1j * kap) * mpmath.gamma(1 - 1j * kap) / mpmath.gamma(1)

    else:
        # Original for medium range
        return mpmath.hyp1f1(1j * kap, 1, 1j * yprime)

class LaueCrystalFocusing():
    def __init__(self,
                 crystal_descriptor="Si",
                 hkl=[1, 1, 1],
                 R=2000,
                 poisson_ratio=0.2201,
                 photon_energy_in_keV=20.0,
                 thickness=0.250,  # mm
                 p=29000.0,  # mm
                 alfa_deg=2.0,  # CAN BE POSITIVE OR NEGATIVE)
                 integration_points=500,
                 use_fast_hyp1f1=0,
                 verbose=1,
                 ):
            self._crystal_descriptor = crystal_descriptor
            self._hkl = hkl
            self._R = R # mm
            self._poisson_ratio = poisson_ratio
            self._photon_energy_in_keV = photon_energy_in_keV
            self._thickness = thickness # mm
            self._p = p # mm
            self._alfa_deg = alfa_deg  # CAN BE POSITIVE OR NEGATIVE
            self._integration_points = integration_points
            self._use_fast_hyp1f1 = use_fast_hyp1f1
            self._verbose = verbose

    def get_crystal_data(self):
        import xraylib
        #
        # get crystal data for silicon crystal
        #
        cryst = xraylib.Crystal_GetCrystal(self._crystal_descriptor)

        # print some info
        if self._verbose:
            print("  Unit cell dimensions [A] are %f %f %f" % (cryst['a'], cryst['b'], cryst['c']))
            print("  Unit cell angles are %f %f %f" % (cryst['alpha'], cryst['beta'], cryst['gamma']))
            print("  Unit cell volume [A] is %f" % (cryst['volume']))

        #
        # define miller indices and compute dSpacing
        #

        hh = self._hkl[0]
        kk = self._hkl[1]
        ll = self._hkl[2]
        debyeWaller = 1.0
        rel_angle = 1.0  # ratio of (incident angle)/(bragg angle) -> we work at Bragg angle

        dspacing = xraylib.Crystal_dSpacing(cryst, hh, kk, ll)
        if self._verbose: print("dspacing: %f A" % dspacing)
        #
        # define energy and get Bragg angle
        #
        ener = self._photon_energy_in_keV  # 12.398 # keV
        braggAngle = xraylib.Bragg_angle(cryst, ener, hh, kk, ll)
        if self._verbose: print("Bragg angle: %f degrees" % (braggAngle * 180 / numpy.pi))

        #
        # get the structure factor (at a given energy)
        #
        f0 = xraylib.Crystal_F_H_StructureFactor(cryst, ener, 0, 0, 0, debyeWaller, 1.0)
        fH = xraylib.Crystal_F_H_StructureFactor(cryst, ener, hh, kk, ll, debyeWaller, 1.0)
        if self._verbose: print("f0: (%f , %f)" % (f0.real, f0.imag))
        if self._verbose: print("fH: (%f , %f)" % (fH.real, fH.imag))

        #
        # convert structure factor in chi (or psi) = - classical_e_radius wavelength^2 fH /(pi volume)
        #
        codata = scipy.constants.physical_constants
        codata_c,  _, _ = codata["speed of light in vacuum"]
        codata_h,  _, _ = codata["Planck constant"]
        codata_ec, _, _ = codata["elementary charge"]
        codata_r,  _, _ = codata["classical electron radius"]

        ev2meter = codata_h * codata_c / codata_ec
        wavelength = ev2meter / (ener * 1e3)
        if self._verbose: print("Photon energy: %f keV" % ener)
        if self._verbose: print("Photon wavelength: %f A" % (1e10 * wavelength))

        volume = cryst['volume'] * 1e-10 * 1e-10 * 1e-10  # volume of silicon unit cell in m^3
        cte = - codata_r * wavelength * wavelength / (numpy.pi * volume)

        chi0 = cte * f0
        chiH = cte * fH

        if self._verbose: print("chi0: (%e , %e)" % (chi0.real, chi0.imag))
        if self._verbose: print("chiH: (%e , %e)" % (chiH.real, chiH.imag))

        return braggAngle, numpy.conjugate(chi0), numpy.conjugate(chiH)

    #
    # interface for q=0 or finite q
    #
    def xscan(self, q=1000.0, npoints_x=10, a_factor=1, a_center=0.0, filename=""):

        if self._p == 0:
            if q == 0:
                txt = "xscan_at_q0_and_p0() (Guigay & Ferrero 2016 eq 23 http://dx.doi.org/10.1107/S2053273316006549)"
            else:
                txt = "xscan_at_finite_q_and_p0() (Guigay & Ferrero 2016 eq 24 http://dx.doi.org/10.1107/S2053273316006549)"
        else:
            if q == 0:
                txt = "xscan_at_q0() (Guigay & Ferrero 2016 eq 30 http://dx.doi.org/10.1107/S2053273316006549)"
            else:
                txt = "xscan_at_finite_q() (Guigay & Ferrero 2016 eq 31 http://dx.doi.org/10.1107/S2053273316006549)"

        print("Calculating x-scan")
        print("    at p=%.3f mm, q=%.3f..." % (self._p, q))
        print("    using %s" % (txt))
        t0 = time.time()

        if self._p == 0:
            if q == 0:
                out = self.xscan_at_q0_and_p0(npoints_x=npoints_x, a_factor=a_factor, a_center=a_center, filename=filename)
            else:
                out = self.xscan_at_finite_q_and_p0(q, npoints_x=npoints_x, a_factor=a_factor, a_center=a_center, filename=filename)
        else:
            if q == 0:
                out = self.xscan_at_q0(npoints_x=npoints_x, a_factor=a_factor, a_center=a_center, filename=filename)
            else:
                out = self.xscan_at_finite_q(q, npoints_x=npoints_x, a_factor=a_factor, a_center=a_center, filename=filename)

        print("Calculation time: ", time.time() - t0)
        return out

    # x-scan at p=q=0 using Guigay % Ferrero 2016 eq 23
    def xscan_at_q0_and_p0(self, npoints_x=10, a_factor=1, a_center=0.0, filename=""):

        kwds = self._calculate_constats_for_equation23_2016()
        a = kwds['a']

        # x-scan at q=0
        print("a=%.3f mm..." % (a))

        xx = numpy.linspace(-a * a_factor, a * a_factor, npoints_x) - a_center
        yy_amplitude = numpy.zeros_like(xx, dtype=complex)

        print(f"Progress: 0%")
        for j in range(xx.size):
            progress = (j + 1) / xx.size * 100
            if progress % 10 == 0:  print(f"Progress: {progress:.0f}%")
            amplitude = self._equation23_2016(xx[j], **kwds)
            yy_amplitude[j] = amplitude
        print(f"Progress: 100%")

        # create and write wofry wavefront
        output_wavefront = GenericWavefront1D.initialize_wavefront_from_arrays(
            1e-3 * xx, yy_amplitude, y_array_pi=None, wavelength=1e-10)
        output_wavefront.set_photon_energy(1e3 * self._photon_energy_in_keV)
        if filename != "":
            output_wavefront.save_h5_file(filename,
                                          subgroupname="wfr", intensity=True, phase=False, overwrite=True,
                                          verbose=False)
            print("File %s written to disk" % filename)

        return xx, yy_amplitude, output_wavefront

    # x-scan at p=0, finite q, using Guigay % Ferrero 2016 eq 24
    def xscan_at_finite_q_and_p0(self, q=1000.0, npoints_x=10, a_factor=1, a_center=0.0, filename=""):

        kwds = self._calculate_constats_for_equation23_2016() #?????????????
        a = kwds['a']

        print("a=%.3f mm..." % (a))

        xx = numpy.linspace(-a * a_factor, a * a_factor, npoints_x) - a_center
        yy_amplitude = numpy.zeros_like(xx, dtype=complex)

        print(f"Progress: 0%")
        for j in range(xx.size):
            progress = (j + 1) / xx.size * 100
            if progress % 10 == 0:  print(f"Progress: {progress:.0f}%")
            amplitude = self._equation24_2016(xx[j], q, **kwds)
            yy_amplitude[j] = amplitude
        print(f"Progress: 100%")

        # create and write wofry wavefront
        output_wavefront = GenericWavefront1D.initialize_wavefront_from_arrays(
            1e-3 * xx, yy_amplitude, y_array_pi=None, wavelength=1e-10)
        output_wavefront.set_photon_energy(1e3 * self._photon_energy_in_keV)
        if filename != "":
            output_wavefront.save_h5_file(filename,
                                          subgroupname="wfr", intensity=True, phase=False, overwrite=True,
                                          verbose=False)
            print("File %s written to disk" % filename)

        return xx, yy_amplitude, output_wavefront


    # x-scan at q=0 using Guigay % Ferrero 2016 eq 30
    def xscan_at_q0(self, npoints_x=10, a_factor=1, a_center=0.0, filename=""):

        if self._p == 0:
            raise Exception("For p=0 please use xscan_at_q0_and_p0()")

        kwds = self._calculate_constats_for_equation30_2016()
        a = kwds['a']

        # x-scan at q=0
        print("a=%.3f mm..." % (a))

        xx = numpy.linspace(-a * a_factor, a * a_factor, npoints_x) - a_center
        yy_amplitude = numpy.zeros_like(xx, dtype=complex)

        print(f"Progress: 0%")
        for j in range(xx.size):
            progress = (j + 1) / xx.size * 100
            if progress % 10 == 0:  print(f"Progress: {progress:.0f}%")
            amplitude = self._equation30_2016(xx[j], **kwds)
            yy_amplitude[j] = amplitude
        print(f"Progress: 100%")

        # create and write wofry wavefront
        output_wavefront = GenericWavefront1D.initialize_wavefront_from_arrays(
            1e-3 * xx, yy_amplitude, y_array_pi=None, wavelength=1e-10)
        output_wavefront.set_photon_energy(1e3 * self._photon_energy_in_keV)
        if filename != "":
            output_wavefront.save_h5_file(filename,
                                          subgroupname="wfr", intensity=True, phase=False, overwrite=True,
                                          verbose=False)
            print("File %s written to disk" % filename)

        return xx, yy_amplitude, output_wavefront

    # x-scan at finite q using Guigay % Ferrero 2016 eq 31
    def xscan_at_finite_q(self, q=1000.0, npoints_x=10, a_factor=1, a_center=0.0, filename=""):

        if self._p == 0:
            raise Exception("For p=0 please use xscan_at_finite_q_and_p0()")

        kwds = self._calculate_constats_for_equation31_2016()
        a = kwds['a']

        # x-scan at q=0
        print("a=%.3f mm..." % (a))

        xx = numpy.linspace(-a * a_factor, a * a_factor, npoints_x) - a_center
        yy_amplitude = numpy.zeros_like(xx, dtype=complex)

        print(f"Progress: 0%")
        for j in range(xx.size):
            progress = (j + 1) / xx.size * 100
            if progress % 10 == 0:  print(f"Progress: {progress:.0f}%")
            amplitude = self._equation31_2016(xx[j], q, **kwds)
            yy_amplitude[j] = amplitude
        print(f"Progress: 100%")

        # create and write wofry wavefront
        output_wavefront = GenericWavefront1D.initialize_wavefront_from_arrays(
            1e-3 * xx, yy_amplitude, y_array_pi=None, wavelength=1e-10)
        output_wavefront.set_photon_energy(1e3 * self._photon_energy_in_keV)
        if filename != "":
            output_wavefront.save_h5_file(filename,
                                          subgroupname="wfr", intensity=True, phase=False, overwrite=True,
                                          verbose=False)
            print("File %s written to disk" % filename)

        return xx, yy_amplitude, output_wavefront

####################################
    # x-scan at p=q=0 using Guigay % Ferrero 2016 eq 23
    def xscan_for_external_wavefront(self, Phi=None, Phi_tau=None, npoints_x=10, a_factor=1, a_center=0.0, filename=""):

        kwds = self._calculate_constats_for_equation31_2016()
        a = kwds['a']

        # x-scan at q=0
        print("a=%.3f mm..." % (a))

        xx = numpy.linspace(-a * a_factor, a * a_factor, npoints_x) - a_center
        yy_amplitude = numpy.zeros_like(xx, dtype=complex)

        ##
        if Phi is None: Phi = numpy.ones_like(xx, dtype=complex)
        if Phi_tau is None: Phi_tau = xx
        ##
        print(f"Progress: 0%")
        for j in range(xx.size):
            progress = (j + 1) / xx.size * 100
            if progress % 10 == 0:  print(f"Progress: {progress:.0f}%")
            amplitude = self._equation28_2016(xx[j], Phi, Phi_tau, **kwds)
            yy_amplitude[j] = amplitude
        print(f"Progress: 100%")

        # create and write wofry wavefront
        output_wavefront = GenericWavefront1D.initialize_wavefront_from_arrays(
            1e-3 * xx, yy_amplitude, y_array_pi=None, wavelength=1e-10)
        output_wavefront.set_photon_energy(1e3 * self._photon_energy_in_keV)
        if filename != "":
            output_wavefront.save_h5_file(filename,
                                          subgroupname="wfr", intensity=True, phase=False, overwrite=True,
                                          verbose=False)
            print("File %s written to disk" % filename)

        return xx, yy_amplitude, output_wavefront
####################################
    #
    # private methods
    #

    # Guigay&Ferrero 2016: calculate equation 23, p=q=0
    def _equation23_2016(self, x,
                         a=None,
                         mu1=None,
                         mu2=None,
                         teta=None,
                         teta1=None,
                         teta2=None,
                         alfa=None,
                         acrist=None,
                         gamma=None,
                         lambda1=None,
                         omega=None,
                         t1=None,
                         a2=None,
                         g=None,
                         kap=None,
                         k=None,
                         pe=None,
                         acmax=None,
                         kiny=None,
                         att=None,
                         chizero=None,
                         t2=None,
                         chih2=None,
                         ):

        if numpy.abs(x) > a: return 0

        if alfa == 0:
            Z = k * numpy.sqrt(chih2) / numpy.sin(2 * teta)
            kum = BesselJ(0, Z * numpy.sqrt(a ** 2 - x ** 2))
        else:
            if self._use_fast_hyp1f1:
                kum = fast_hyp1f1(kap, acmax * (1 - (x / a) ** 2))
            else:
                kum = mpmath.hyp1f1(1j * kap, 1, 1j * acmax * (1 - (x / a) ** 2))

        return numpy.exp((1j * k * chizero.real - k * chizero.imag) * 0.25 * (t1 + t2)) * \
               kum * \
               numpy.exp(-1j * x ** 2 * k * mu1 / 2 / self._R) * \
               numpy.exp(1j * x * k * (omega.real - t1 * numpy.sin(teta1) / 2 / self._R)) * \
               numpy.exp(- x * k * omega.imag)



    # Guigay&Ferrero 2016: calculate equation 24, p=0, finite q
    def _equation24_2016(self, x, q,
                         a=None,
                         mu1=None,
                         mu2=None,
                         teta=None,
                         teta1=None,
                         teta2=None,
                         alfa=None,
                         acrist=None,
                         gamma=None,
                         lambda1=None,
                         omega=None,
                         t1=None,
                         a2=None,
                         g=None,
                         kap=None,
                         k=None,
                         pe=None,
                         acmax=None,
                         kiny=None,
                         att=None,
                         chizero=None,
                         t2=None,
                         chih2=None,
                         ):

        #if numpy.abs(x) > a: return 0
        v = numpy.linspace(0, a, self._integration_points)
        y = numpy.zeros_like(v, dtype=complex)
        invle = 1 / q - mu1 / self._R



        for i in range(v.size):

            if alfa == 0:
                Z = k * numpy.sqrt(chih2) / numpy.sin(2 * teta)
                kum = BesselJ(0, Z * numpy.sqrt(a ** 2 - v[i] ** 2))
            else:
                if self._use_fast_hyp1f1:
                    kum = fast_hyp1f1(kap, acmax * (1 - (v[i] / a) ** 2))
                else:
                    kum = mpmath.hyp1f1(1j * kap, 1, 1j * acmax * (1 - (v[i] / a) ** 2))

            Q1 = 1j * k * 0.5 * v[i] ** 2 * invle
            Q2 = k * v[i] * (x / q - 1j * kiny)

            y[i] = kum * \
                   numpy.exp(Q1) * \
                   numpy.cos(Q2)

        return 2 * numpy.trapz(y, x=v) * numpy.sqrt(att / numpy.abs(lambda1 * q))

########################################
    # Guigay&Ferrero 2016: calculate integral in equation 28 for q=0 with a given wavefront amplitude defined at p=0
    # note that the integral limits are gamma (u+-a) and the integrand is Phi(tau) P(u,tau) with Phi() the complex amplitude
    def _equation28_2016(self, x, Phi, Phi_tau,
                        a       = None,
                        mu1     = None,
                        mu2     = None,
                        teta    = None,
                        teta1   = None,
                        teta2   = None,
                        alfa    = None,
                        acrist  = None,
                        gamma   = None,
                        lambda1 = None,
                        omega   = None,
                        t1      = None,
                        a2      = None,
                        g       = None,
                        kap     = None,
                        k       = None,
                        pe      = None,
                        acmax   = None,
                        kiny    = None,
                        att     = None,
                        chizero = None,
                        t2      = None,
                        chih2   = None,
                      ):

        tau = numpy.linspace(gamma * (x - a), gamma * (x + a), self._integration_points)
        y = numpy.zeros_like(tau, dtype=complex)

        for i in range(tau.size):
            nu = x - tau[i] / gamma
            yprime = acmax * (1 - (nu / a) ** 2)


            if alfa == 0:
                Z = k * numpy.sqrt(chih2) / numpy.sin(2 * teta)
                kum = BesselJ(0, Z * numpy.sqrt(a ** 2 - v[i] ** 2))
            else:
                if self._use_fast_hyp1f1:
                    kum = fast_hyp1f1(kap, yprime)
                else:
                    kum = mpmath.hyp1f1(1j * kap, 1, 1j * yprime)

            Q1 = 1j * k * nu * omega
            Q2 = -1j * k * (mu1 * x**2 + x * t1 * numpy.sin(teta1)) / (2 * self._R)
            Q3 = -1j * k * (mu2 * (nu - x)**2 - a2 * gamma * (nu - x)) / (2 * self._R)
            Q4 = 1j * k * (g / self._R) * (a + x) * (nu - x)
            y[i] = kum * numpy.exp(Q1 + Q2 + Q3 + Q4)

        amplitude = numpy.trapz(y, x=tau)
        return amplitude

########################################
    # Guigay&Ferrero 2016: calculate integral with limits -a,a in equation 30, finite p, q=0
    def _equation30_2016(self, x,
                        a       = None,
                        mu1     = None,
                        mu2     = None,
                        teta    = None,
                        teta1   = None,
                        teta2   = None,
                        alfa    = None,
                        acrist  = None,
                        gamma   = None,
                        lambda1 = None,
                        omega   = None,
                        t1      = None,
                        a2      = None,
                        g       = None,
                        kap     = None,
                        k       = None,
                        chih2   = None,
                      ):

        v = numpy.linspace(-a, a, self._integration_points)
        y = numpy.zeros_like(v, dtype=complex)

        for i in range(v.size):
            s = 0
            mu2prime = mu2 * gamma**2
            rho = self._poisson_ratio / (1 - self._poisson_ratio)
            a_2 = self._thickness / numpy.cos(teta) * \
                  (numpy.cos(alfa) * numpy.sin(teta2) + rho * numpy.sin(alfa) * numpy.cos(teta2))

            arg1 = a ** 2 - v[i] ** 2
            if arg1 < 0: arg1 = 0
            yprime = acrist * gamma * (arg1) / (numpy.sin(2 * teta)) ** 2  # defined before eq 29

            mfac = gamma / numpy.sqrt(lambda1 * self._p)
            pe = 1 / (1 / self._p - mu2 / self._R)
            Q1 = gamma**2 * (x - v[i])**2 / (2 * pe)  # quadratic
            Q2 = -(mu1 * x**2) / (2 * self._R)
            Q3 = -(x * t1 * numpy.sin(teta1) - a2 * gamma * (v[i] - x)) / (2 * self._R)
            Q4 = v[i] * omega + g * (a + x) * (v[i] - x) / self._R


            Q = Q1 + Q2 + Q3 + Q4
            if alfa == 0:
                Z = k * numpy.sqrt(chih2) / numpy.sin(2 * teta)
                kum = BesselJ(0, Z * numpy.sqrt(a ** 2 - v[i] ** 2))
            else:
                if self._use_fast_hyp1f1:
                    kum = fast_hyp1f1(kap, yprime)
                else:
                    kum = mpmath.hyp1f1(1j * kap, 1, 1j * yprime)

            y[i] = mfac * kum * numpy.exp(1j * k * Q)

        return numpy.trapz(y, x=v)

    # Guigay&Ferrero 2016: calculate integral in equation 31 and add the corresponding phases, finite p, finite q
    # note that the x argument here is in fact (x - xc) in eq. 31
    def _equation31_2016(self, x, q,
                        a       = None,
                        mu1     = None,
                        mu2     = None,
                        teta    = None,
                        teta1   = None,
                        teta2   = None,
                        alfa    = None,
                        acrist  = None,
                        gamma   = None,
                        lambda1 = None,
                        omega   = None,
                        t1      = None,
                        a2      = None,
                        g       = None,
                        kap     = None,
                        k       = None,
                        pe      = None,
                        acmax   = None,
                        kiny    = None,
                        att     = None,
                        chizero = None,
                        t2      = None,
                        chih2   = None,
                      ):

        v = numpy.linspace(-a, a, self._integration_points)
        y = numpy.zeros_like(v, dtype=complex)
        qe = q * self._R / (self._R - q * mu1 - g * q)
        be = 1 / qe + 1 / pe
        invle = 1 / (pe + qe) + g / self._R
        s = 0
        for i in range(v.size):
            yprime = acmax * (1 - (v[i] / a) ** 2)

            if alfa == 0:
                Z = k * numpy.sqrt(chih2) / numpy.sin(2 * teta)
                kum = BesselJ(0, Z * numpy.sqrt(a ** 2 - v[i] ** 2))
            else:
                if self._use_fast_hyp1f1:
                    kum = fast_hyp1f1(kap, yprime)
                else:
                    kum = mpmath.hyp1f1(1j * kap, 1, 1j * yprime)

            Q1 = 1j * k * 0.5 * v[i] ** 2 * invle
            Q2 = - k * v[i] * kiny
            Q3 = k * v[i] * x / (q * pe * be)
            y[i] = kum * numpy.exp(Q1 + Q2) * numpy.cos(Q3)

        amplitude = numpy.trapz(y, x=v)

        amplitude *= numpy.sqrt(att / (lambda1 * q * self._p * be))
        # omitted phase (see just after equation 30)
        amplitude *= numpy.exp(1j * k * x ** 2 / 2 / q) * \
                     numpy.exp(1j * k * s ** 2 / 2 / self._p) * \
                     numpy.exp(1j * k * chizero.real * (t1 + t2) / 4)
        # omitted phase (see just before equation 31)
        m = g * a / self._R + gamma * (s / self._p + a ** 2 / 2 / self._R)  ## CHECK, shown after eq 30
        amplitude *= numpy.exp(- 1j * (k / 2 / be) * \
                               (x / q + t1 * numpy.sin(teta1) / 2 / self._R + m) ** 2)
        return amplitude

    #
    # pack constants
    #

    def _calculate_constats_for_equation23_2016(self):
        photon_energy_in_keV = self._photon_energy_in_keV
        p = self._p
        alfa = self._alfa_deg * numpy.pi / 180
        R = self._R
        poisson_ratio = self._poisson_ratio
        thickness = self._thickness

        teta, chizero, chih = self.get_crystal_data()

        lambda1 = codata.h * codata.c / codata.e / (photon_energy_in_keV * 1e3) * 1e3  # in mm
        chimh = -1j * chih
        chih2 = chih * chimh

        if self._verbose:
            print("photon_energy_in_keV:", photon_energy_in_keV)
            print("lambda1 in mm:", lambda1)
            print("lambda1 in m, A:", lambda1 * 1e-3, lambda1 * 1e-3 * 1e10)
            print("CrystalSi 111")
            print("teta_deg:", teta * 180 / numpy.pi)
            print("p:", p)
            print("R:", R)
            print("chizero:", chizero)
            print("chih:", chih)
            print("chimh:", chimh)
            print("chih*chihbar:", chih2)



        k = 2 * numpy.pi / lambda1
        h = 2 * k * numpy.sin(teta)


        u2 = 0.25 * chih2 * k ** 2
        raygam = R * numpy.cos(teta)
        kp = k * numpy.sin(2 * teta)
        kp2 = kp * numpy.sin(2 * teta)

        #
        # TODO: Not working for alfa_deg=0
        #


        teta1 = alfa + teta
        teta2 = alfa - teta
        SG = None
        fam1 = numpy.sin(teta1)
        fam2 = numpy.sin(teta2)
        gam1 = numpy.cos(teta1)
        gam2 = numpy.cos(teta2)


        t1 = thickness / gam1
        t2 = thickness / gam2
        qpoly = p * R * gam2 / (2 * p + R * gam1)
        att = numpy.exp(-k * 0.5 * (t1 + t2) * numpy.imag(chizero))
        s2max = 0.25 * t1 * t2
        u2max = u2 * s2max  # Omega = k**2 chi_h chi_hbar / 4 ? (end of pag 490)
        gamma = t2 / t1
        a = numpy.sin(2 * teta) * t1 * 0.5
        kin = 0.25 * (t1 - t2) * chizero / a
        kinx = numpy.real(kin)
        kiny = numpy.imag(kin)
        com = numpy.sin(alfa) * (1 + gam1 * gam2 * (1 + poisson_ratio))
        kp3 = 0.5 * k * (gamma * a) ** 2
        mu1 = (numpy.cos(alfa) * 2 * fam1 * gam1 + numpy.sin(alfa) * (fam1 ** 2 + poisson_ratio * gam1 ** 2)) / (
                    numpy.sin(2 * teta) * numpy.cos(teta))
        mu2 = (numpy.cos(alfa) * 2 * fam2 * gam2 + numpy.sin(alfa) * (fam2 ** 2 + poisson_ratio * gam2 ** 2)) / (
                    numpy.sin(2 * teta) * numpy.cos(teta))
        a1 = (thickness / numpy.cos(teta)) * (
                    numpy.cos(alfa) * numpy.sin(teta1) + poisson_ratio * numpy.sin(alfa) * numpy.cos(teta1))
        a2 = (thickness / numpy.cos(teta)) * (
                    numpy.cos(alfa) * numpy.sin(teta2) + poisson_ratio * numpy.sin(alfa) * numpy.cos(teta2))
        acrist = -h * com / R  # A in Eq 17


        acmax = acrist * s2max
        g = gamma * acrist * R / kp2
        kap = u2max / acmax  # beta = Omega / A TODO acmax is zero when alfa is zero!!!!!!!!!!!!!!!!!!

        pe = p * R / (gamma ** 2 * (R - p * mu2) - g * p)

        # WARNING DIFFERNT FROM Fig 2 (+p)

        # pe = p * R / (gamma**2 * (R + p * mu2) - g * p)
        if self._verbose:
            print("alfa:", alfa)
            print("teta1, teta2, teta:", teta1, teta2, teta)
            print("t1, t2, t/cos(teta):", t1, t2, thickness / numpy.cos(teta))
            print("a1, a2:", a1, a2, +thickness * numpy.tan(teta), -thickness * numpy.tan(teta))
            print("mu1, mu2:", mu1, mu2, +1 / numpy.cos(teta), -1 / numpy.cos(teta))
            print("acrist, com:", acrist, 0)
            print("pe:", pe)
            print("a: ", a, thickness * numpy.sin(teta))
            print("pe:", pe)

        omega = 0.25 * (t1 - t2) * chizero / a  # omega following the definition found after eq 22
        omega_real = numpy.real(omega)
        omega_imag = numpy.imag(omega)
        xc_over_q = omega_real - t1 * numpy.sin(alfa + teta) / (2 * R)

        return {
            "a"       : a,
            "mu1"     : mu1,
            "mu2"     : mu2,
            "teta"    : teta,
            "teta1"   : teta1,
            "teta2"   : teta2,
            "alfa"    : alfa,
            "acrist"  : acrist,
            "gamma"   : gamma,
            "lambda1" : lambda1,
            "omega"   : omega,
            "t1"      : t1,
            "a2"      : a2,
            "g"       : g,
            "kap"     : kap,
            "k"       : k,
            "pe"      : pe,
            "acmax"   : acmax,
            "kiny"    : kiny,
            "att"     : att,
            "chizero" : chizero,
            "t2"      : t2,
            "chih2"   : chih2,
            }


    def _calculate_constats_for_equation30_2016(self):
        photon_energy_in_keV = self._photon_energy_in_keV
        p = self._p
        alfa = self._alfa_deg * numpy.pi / 180
        R = self._R
        poisson_ratio = self._poisson_ratio
        thickness = self._thickness

        teta, chizero, chih = self.get_crystal_data()

        lambda1 = codata.h * codata.c / codata.e / (photon_energy_in_keV * 1e3) * 1e3  # in mm
        chimh = -1j * chih
        chih2 = chih * chimh

        if self._verbose:
            print("photon_energy_in_keV:", photon_energy_in_keV)
            print("lambda1 in mm:", lambda1)
            print("lambda1 in m, A:", lambda1 * 1e-3, lambda1 * 1e-3 * 1e10)
            print("CrystalSi 111")
            print("teta_deg:", teta * 180 / numpy.pi)
            print("p:", p)
            print("R:", R)
            print("chizero:", chizero)
            print("chih:", chih)
            print("chimh:", chimh)
            print("chih*chihbar:", chih2)



        k = 2 * numpy.pi / lambda1
        h = 2 * k * numpy.sin(teta)


        u2 = 0.25 * chih2 * k ** 2
        raygam = R * numpy.cos(teta)
        kp = k * numpy.sin(2 * teta)
        kp2 = kp * numpy.sin(2 * teta)

        #
        # TODO: Not working for alfa_deg=0
        #


        teta1 = alfa + teta
        teta2 = alfa - teta
        SG = None
        fam1 = numpy.sin(teta1)
        fam2 = numpy.sin(teta2)
        gam1 = numpy.cos(teta1)
        gam2 = numpy.cos(teta2)


        t1 = thickness / gam1
        t2 = thickness / gam2
        qpoly = p * R * gam2 / (2 * p + R * gam1)
        att = numpy.exp(-k * 0.5 * (t1 + t2) * numpy.imag(chizero))
        s2max = 0.25 * t1 * t2
        u2max = u2 * s2max  # Omega = k**2 chi_h chi_hbar / 4 ? (end of pag 490)
        gamma = t2 / t1
        a = numpy.sin(2 * teta) * t1 * 0.5
        kin = 0.25 * (t1 - t2) * chizero / a
        kinx = numpy.real(kin)
        kiny = numpy.imag(kin)
        com = numpy.sin(alfa) * (1 + gam1 * gam2 * (1 + poisson_ratio))
        kp3 = 0.5 * k * (gamma * a) ** 2
        mu1 = (numpy.cos(alfa) * 2 * fam1 * gam1 + numpy.sin(alfa) * (fam1 ** 2 + poisson_ratio * gam1 ** 2)) / (
                    numpy.sin(2 * teta) * numpy.cos(teta))
        mu2 = (numpy.cos(alfa) * 2 * fam2 * gam2 + numpy.sin(alfa) * (fam2 ** 2 + poisson_ratio * gam2 ** 2)) / (
                    numpy.sin(2 * teta) * numpy.cos(teta))
        a1 = (thickness / numpy.cos(teta)) * (
                    numpy.cos(alfa) * numpy.sin(teta1) + poisson_ratio * numpy.sin(alfa) * numpy.cos(teta1))
        a2 = (thickness / numpy.cos(teta)) * (
                    numpy.cos(alfa) * numpy.sin(teta2) + poisson_ratio * numpy.sin(alfa) * numpy.cos(teta2))
        acrist = -h * com / R  # A in Eq 17


        acmax = acrist * s2max
        g = gamma * acrist * R / kp2
        kap = u2max / acmax  # beta = Omega / A TODO acmax is zero when alfa is zero!!!!!!!!!!!!!!!!!!

        pe = p * R / (gamma ** 2 * (R - p * mu2) - g * p)

        # WARNING DIFFERNT FROM Fig 2 (+p)

        # pe = p * R / (gamma**2 * (R + p * mu2) - g * p)
        if self._verbose:
            print("alfa:", alfa)
            print("teta1, teta2, teta:", teta1, teta2, teta)
            print("t1, t2, t/cos(teta):", t1, t2, thickness / numpy.cos(teta))
            print("a1, a2:", a1, a2, +thickness * numpy.tan(teta), -thickness * numpy.tan(teta))
            print("mu1, mu2:", mu1, mu2, +1 / numpy.cos(teta), -1 / numpy.cos(teta))
            print("acrist, com:", acrist, 0)
            print("pe:", pe)
            print("a: ", a, thickness * numpy.sin(teta))

        omega = 0.25 * (t1 - t2) * chizero / a  # omega following the definition found after eq 22
        omega_real = numpy.real(omega)
        omega_imag = numpy.imag(omega)
        xc_over_q = omega_real - t1 * numpy.sin(alfa + teta) / (2 * R)

        return {
            "a"       : a,
            "mu1"     : mu1,
            "mu2"     : mu2,
            "teta"    : teta,
            "teta1"   : teta1,
            "teta2"   : teta2,
            "alfa"    : alfa,
            "acrist"  : acrist,
            "gamma"   : gamma,
            "lambda1" : lambda1,
            "omega"   : omega,
            "t1"      : t1,
            "a2"      : a2,
            "g"       : g,
            "kap"     : kap,
            "k"       : k,
            "chih2"   : chih2,
            }


    def _calculate_constats_for_equation31_2016(self):
        photon_energy_in_keV = self._photon_energy_in_keV
        p = self._p
        alfa = self._alfa_deg * numpy.pi / 180
        R = self._R
        poisson_ratio = self._poisson_ratio
        thickness = self._thickness

        teta, chizero, chih = self.get_crystal_data()

        lambda1 = codata.h * codata.c / codata.e / (photon_energy_in_keV * 1e3) * 1e3  # in mm
        chimh = -1j * chih
        chih2 = chih * chimh

        if self._verbose:
            print("photon_energy_in_keV:", photon_energy_in_keV)
            print("lambda1 in mm:", lambda1)
            print("lambda1 in m, A:", lambda1 * 1e-3, lambda1 * 1e-3 * 1e10)
            print("CrystalSi 111")
            print("teta_deg:", teta * 180 / numpy.pi)
            print("p:", p)
            print("R:", R)
            print("chizero:", chizero)
            print("chih:", chih)
            print("chimh:", chimh)
            print("chih*chihbar:", chih2)



        k = 2 * numpy.pi / lambda1
        h = 2 * k * numpy.sin(teta)


        u2 = 0.25 * chih2 * k ** 2
        raygam = R * numpy.cos(teta)
        kp = k * numpy.sin(2 * teta)
        kp2 = kp * numpy.sin(2 * teta)

        #
        # TODO: Not working for alfa_deg=0
        #


        teta1 = alfa + teta
        teta2 = alfa - teta
        SG = None
        fam1 = numpy.sin(teta1)
        fam2 = numpy.sin(teta2)
        gam1 = numpy.cos(teta1)
        gam2 = numpy.cos(teta2)


        t1 = thickness / gam1
        t2 = thickness / gam2
        qpoly = p * R * gam2 / (2 * p + R * gam1)
        att = numpy.exp(-k * 0.5 * (t1 + t2) * numpy.imag(chizero))
        s2max = 0.25 * t1 * t2
        u2max = u2 * s2max  # Omega = k**2 chi_h chi_hbar / 4 ? (end of pag 490)
        gamma = t2 / t1
        a = numpy.sin(2 * teta) * t1 * 0.5
        kin = 0.25 * (t1 - t2) * chizero / a
        kinx = numpy.real(kin)
        kiny = numpy.imag(kin)
        com = numpy.sin(alfa) * (1 + gam1 * gam2 * (1 + poisson_ratio))
        kp3 = 0.5 * k * (gamma * a) ** 2
        mu1 = (numpy.cos(alfa) * 2 * fam1 * gam1 + numpy.sin(alfa) * (fam1 ** 2 + poisson_ratio * gam1 ** 2)) / (
                    numpy.sin(2 * teta) * numpy.cos(teta))
        mu2 = (numpy.cos(alfa) * 2 * fam2 * gam2 + numpy.sin(alfa) * (fam2 ** 2 + poisson_ratio * gam2 ** 2)) / (
                    numpy.sin(2 * teta) * numpy.cos(teta))
        a1 = (thickness / numpy.cos(teta)) * (
                    numpy.cos(alfa) * numpy.sin(teta1) + poisson_ratio * numpy.sin(alfa) * numpy.cos(teta1))
        a2 = (thickness / numpy.cos(teta)) * (
                    numpy.cos(alfa) * numpy.sin(teta2) + poisson_ratio * numpy.sin(alfa) * numpy.cos(teta2))
        acrist = -h * com / R  # A in Eq 17


        acmax = acrist * s2max
        g = gamma * acrist * R / kp2
        kap = u2max / acmax  # beta = Omega / A TODO acmax is zero when alfa is zero!!!!!!!!!!!!!!!!!!

        pe = p * R / (gamma ** 2 * (R - p * mu2) - g * p)

        # WARNING DIFFERNT FROM Fig 2 (+p)

        # pe = p * R / (gamma**2 * (R + p * mu2) - g * p)
        if self._verbose:
            print("alfa:", alfa)
            print("teta1, teta2, teta:", teta1, teta2, teta)
            print("t1, t2, t/cos(teta):", t1, t2, thickness / numpy.cos(teta))
            print("a1, a2:", a1, a2, +thickness * numpy.tan(teta), -thickness * numpy.tan(teta))
            print("mu1, mu2:", mu1, mu2, +1 / numpy.cos(teta), -1 / numpy.cos(teta))
            print("acrist, com:", acrist, 0)
            print("pe:", pe)
            print("a: ", a, thickness * numpy.sin(teta))
            print("pe:", pe)

        omega = 0.25 * (t1 - t2) * chizero / a  # omega following the definition found after eq 22
        omega_real = numpy.real(omega)
        omega_imag = numpy.imag(omega)
        xc_over_q = omega_real - t1 * numpy.sin(alfa + teta) / (2 * R)

        return {
            "a"       : a,
            "mu1"     : mu1,
            "mu2"     : mu2,
            "teta"    : teta,
            "teta1"   : teta1,
            "teta2"   : teta2,
            "alfa"    : alfa,
            "acrist"  : acrist,
            "gamma"   : gamma,
            "lambda1" : lambda1,
            "omega"   : omega,
            "t1"      : t1,
            "a2"      : a2,
            "g"       : g,
            "kap"     : kap,
            "k"       : k,
            "pe"      : pe,           # used in eq 31
            "acmax"   : acmax,        # used in eq 31
            "kiny"    : kiny,         # used in eq 31
            "att"     : att,          # used in eq 31
            "chizero" : chizero,      # used in eq 31
            "t2"      : t2,           # used in eq 31
            "chih2"   : chih2,        # used in eq 31
            }

    #
    # q-scan % Guigay&Ferrero 2016 eq 31
    #
    def qscan(self, qmin=0.0, qmax=10000.0, npoints=10):
        qq = numpy.linspace(qmin, qmax, npoints)
        yy_amplitude = numpy.zeros_like(qq, dtype=complex)

        kwds_eq30 = self._calculate_constats_for_equation30_2016()
        kwds_eq31 = self._calculate_constats_for_equation31_2016()
        a = kwds_eq31['a']

        print("Calculating q-scan at p=%.3f mm..." % self._p)
        t0 = time.time()
        print(f"Progress: 0%")
        for j in range(qq.size):
            progress = (j + 1) / qq.size * 100
            if progress % 10 < (1 / qq.size * 100):  print(f"Progress: {progress:.0f}%")

            if qq[j] == 0:
                xcenter = 0.0 # TODO calculate the x value that corresponds to the symmetry center
                amplitude = self._equation30_2016(xcenter, **kwds_eq30)
                yy_amplitude[j] = amplitude
            else:
                amplitude = self._equation31_2016(0, qq[j], **kwds_eq31)
                yy_amplitude[j] = amplitude
        print(f"Progress: 100%")
        print("Calculation time: ", time.time() - t0)

        return qq, yy_amplitude

    def info(self):
        txt = ""
        txt += "\nself._crystal_descriptor    = %s" % (self._crystal_descriptor)
        txt += "\nself._hkl                   = " + repr(self._hkl)
        txt += "\nself._R                     = %f mm" % (self._R                   )
        txt += "\nself._poisson_ratio         = %f" % (self._poisson_ratio       )
        txt += "\nself._photon_energy_in_keV  = %f keV" % (self._photon_energy_in_keV)
        txt += "\nself._thickness             = %f mm" % (self._thickness           )
        txt += "\nself._p                     = %f mm" % (self._p                   )
        txt += "\nself._alfa_deg              = %f deg" % (self._alfa_deg            )
        txt += "\nself._integration_points    = %s " % (self._integration_points  )
        txt += "\nself._verbose               = %s " % (self._verbose             )
        txt += "\n"
        return txt


if __name__ == "__main__":

    # Fig 5
    if 0:
        a = LaueCrystalFocusing(
            R = 2000,
            poisson_ratio = 0.2201,
            photon_energy_in_keV = 20.0,
            thickness = 0.250,  # mm
            p = 29000.0,  # mm
            alfa_deg = 2.0,  # CAN BE POSITIVE OR NEGATIVE)
            use_fast_hyp1f1=0,
            verbose=0,
            )

        # xx, yy_amplitude, _ = a.xscan_at_q0(npoints_x=200, a_factor=2, a_center=0.01511, filename="tmp2016_q0.h5")
        # xx, yy_amplitude, _ = a.xscan(q=0, npoints_x=200, a_factor=2, a_center=0.01511, filename="tmp2016_q0.h5") # same as before

        # xx, yy_amplitude, _ = a.xscan_at_q0(npoints_x=1000, a_factor=3, a_center=0.0, filename="tmp2016_q0.h5")

        # print(a.info())
        # xx, yy_amplitude, _ = a.xscan_at_finite_q(q=437.275, npoints_x=200, a_factor=3, a_center=0.0, filename="tmp2016.h5")
        #
        # plot(xx, numpy.abs(yy_amplitude) ** 2, xtitle='x [mm]', ytitle="Intensity", title="", grid=1, show=1)


        qq, yy_amplitude = a.qscan(qmin=0.0, qmax=10000.0, npoints=200)
        plot(qq, numpy.abs(yy_amplitude) ** 2, xtitle='q [mm]', ytitle="Intensity", title="", grid=1, show=1)


    #
    # fig 2
    #
    if 0:
        a = LaueCrystalFocusing(
            R = 2000,
            poisson_ratio = 0.2201,
            photon_energy_in_keV = 80.0,
            thickness = 1.0,  # mm
            p = 0.0,  # mm
            alfa_deg = -0.05,  # CAN BE POSITIVE OR NEGATIVE)
            use_fast_hyp1f1=0,
            verbose=0,
            )

        # xx, yy_amplitude, _ = a.xscan_at_q0(npoints_x=500, a_factor=2, a_center=0.01511, filename="tmp2016_q0.h5")
        xx, yy_amplitude, _ = a.xscan(q=1671.1, npoints_x=500, a_factor=1.0, a_center=0.0, filename="tmp2016_q0.h5")  # same as before

        # xx, yy_amplitude, _ = a.xscan_at_q0(npoints_x=1000, a_factor=3, a_center=0.0, filename="tmp2016_q0.h5")

        print(a.info())
        # xx, yy_amplitude, _ = a.xscan_at_finite_q(q=437.275, npoints_x=200, a_factor=3, a_center=0.0, filename="tmp2016.h5")
        #
        plot(xx, numpy.abs(yy_amplitude) ** 2, xtitle='x [mm]', ytitle="Intensity", title="", grid=1, show=1)


    # external wavefront
    #
    # fig 2
    #
    if 1:
        a = LaueCrystalFocusing(
            R = 2000,
            poisson_ratio = 0.2201,
            photon_energy_in_keV = 80.0,
            thickness = 1.0,  # mm
            p = 0.0,  # mm
            alfa_deg = -0.05,  # CAN BE POSITIVE OR NEGATIVE)
            use_fast_hyp1f1=0,
            verbose=0,
            )

        print(a.info())

        xx, yy_amplitude, _ = a.xscan_for_external_wavefront(npoints_x=500, a_factor=1.0, a_center=0.0, filename="")  # same as before

        plot(xx, numpy.abs(yy_amplitude) ** 2, xtitle='x [mm]', ytitle="Intensity", title="", grid=1, show=1)