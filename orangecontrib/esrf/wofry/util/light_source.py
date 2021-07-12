import numpy
from syned.storage_ring.light_source import LightSource
from syned.storage_ring.electron_beam import ElectronBeam
from syned.storage_ring.magnetic_structures.undulator import Undulator

from wofry.beamline.decorators import LightSourceDecorator
from wofryimpl.propagator.util.undulator_coherent_mode_decomposition_1d import UndulatorCoherentModeDecomposition1D

from wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D

class WOLightSourceCMD(LightSource, LightSourceDecorator, UndulatorCoherentModeDecomposition1D):
    def __init__(self,
                 name                = "Undefined",
                 # electron_beam       = None,
                 # magnetic_structure  = None,
                 undulator_coherent_mode_decomposition_1d = None,
                 dimension           = 1,
                 ):

        electron_beam = ElectronBeam(energy_in_GeV=undulator_coherent_mode_decomposition_1d.electron_energy,
                                     current=undulator_coherent_mode_decomposition_1d.electron_current)
        magnetic_structure = Undulator(K_vertical=undulator_coherent_mode_decomposition_1d.K,
                                       period_length=undulator_coherent_mode_decomposition_1d.undulator_period,
                                       number_of_periods=undulator_coherent_mode_decomposition_1d.undulator_nperiods)

        LightSource.__init__(self, name=name, electron_beam=electron_beam, magnetic_structure=magnetic_structure)
        UndulatorCoherentModeDecomposition1D.__init__(self,
                 electron_energy      = undulator_coherent_mode_decomposition_1d.electron_energy     ,
                 electron_current     = undulator_coherent_mode_decomposition_1d.electron_current    ,
                 undulator_period     = undulator_coherent_mode_decomposition_1d.undulator_period    ,
                 undulator_nperiods   = undulator_coherent_mode_decomposition_1d.undulator_nperiods  ,
                 K                    = undulator_coherent_mode_decomposition_1d.K                   ,
                 photon_energy        = undulator_coherent_mode_decomposition_1d.photon_energy       ,
                 abscissas_interval   = undulator_coherent_mode_decomposition_1d.abscissas_interval  ,
                 number_of_points     = undulator_coherent_mode_decomposition_1d.number_of_points    ,
                 distance_to_screen   = undulator_coherent_mode_decomposition_1d.distance_to_screen  ,
                 scan_direction       = undulator_coherent_mode_decomposition_1d.scan_direction      ,
                 magnification_x      = undulator_coherent_mode_decomposition_1d.magnification_x     ,
                 sigmaxx              = 1.0 / numpy.sqrt(undulator_coherent_mode_decomposition_1d.mxx)  ,
                 sigmaxpxp            = 1.0 / numpy.sqrt(undulator_coherent_mode_decomposition_1d.mxpxp),
                 useGSMapproximation  = undulator_coherent_mode_decomposition_1d.useGSMapproximation ,
                )

        self._dimension =  dimension
        self.dimension = dimension
        self._set_support_text([
                    # ("name"      ,           "to define ", "" ),
                    ("dimension"      , "dimension ", "" ),
            ] )

    def get_dimension(self):
        return self._dimension

    # from Wofry Decorator
    def get_wavefront(self):
        self.get_eigenvector_wavefront(mode=0)

    def to_python_code(self, do_plot=True, add_import_section=False):

        txt = ""

        txt += "#"
        txt += "\n# create output_wavefront\n#"
        txt += "\n#"

        if self._dimension == 1:
            txt += "\nfrom wofryimpl.propagator.util.undulator_coherent_mode_decomposition_1d import UndulatorCoherentModeDecomposition1D"

        else:
            raise Exception("Not implemented")

        txt += "\ncoherent_mode_decomposition = UndulatorCoherentModeDecomposition1D("
        txt += "\n    electron_energy=%g," % self.electron_energy
        txt += "\n    electron_current=%g," % self.electron_current
        txt += "\n    undulator_period=%g," % self.undulator_period
        txt += "\n    undulator_nperiods=%g," % self.undulator_nperiods
        txt += "\n    K=%g," % self.K
        txt += "\n    photon_energy=%g," % self.photon_energy
        txt += "\n    abscissas_interval=%g," % self.abscissas_interval
        txt += "\n    number_of_points=%g," % self.number_of_points
        txt += "\n    distance_to_screen=%g," % self.distance_to_screen
        txt += "\n    scan_direction='%s'," % self.scan_direction
        txt += "\n    sigmaxx=%g,"   % (1.0 / numpy.sqrt(self.mxx))
        txt += "\n    sigmaxpxp=%g," % (1.0 / numpy.sqrt(self.mxpxp))
        if self.useGSMapproximation:
            txt += "\n    useGSMapproximation=True,)"
        else:
            txt += "\n    useGSMapproximation=False,)"
        txt += "\n# make calculation"
        txt += "\ncoherent_mode_decomposition_results = coherent_mode_decomposition.calculate()"

        txt += "\n\nmode_index = 0"
        txt += "\noutput_wavefront = coherent_mode_decomposition.get_eigenvector_wavefront(mode_index)"


        return txt


class WOPySRULightSource(LightSource, LightSourceDecorator):
    def __init__(self,
                 name                = "Undefined",
                 electron_beam       = None,
                 magnetic_structure  = None,
                 ):


        LightSource.__init__(self, name=name, electron_beam=electron_beam, magnetic_structure=magnetic_structure)

        self.__source_wavefront_parameters = {
            'distance'       : 30.0,
            'gapH'           : 0.003,
            'gapV'           : 0.003,
            'photon_energy'  : 7000.0,
            'h_slit_points'    : 51,
            'v_slit_points'    : 51,
            'flag_send_wavefront_dimension' : 0, # 0=2D wavefront, 1=H wawefront, 2=V wavefront (for python script)
            }


        self._dimension =  2

        self._set_support_text([
                    # ("name"      ,           "to define ", "" ),
                    ("dimension"      , "dimension ", "" ),
            ] )



    @classmethod
    def initialize_from_keywords(cls,
                                 name="Undefined",
                                 energy_in_GeV=6.04,
                                 current=0.2,
                                 K_vertical=1.68,
                                 period_length=0.018,
                                 number_of_periods=222,
                                 distance=10.0,
                                 gapH=0.003,
                                 gapV=0.003,
                                 photon_energy=7000.0,
                                 h_slit_points=51,
                                 v_slit_points=51,
                                 flag_send_wavefront_dimension=0,
                                 ):


        out = WOPySRULightSource(name=name,
                                 electron_beam=ElectronBeam(
                                     energy_in_GeV=energy_in_GeV,
                                     current=current),
                                 magnetic_structure=Undulator(
                                     K_vertical=K_vertical,
                                     period_length=period_length,
                                     number_of_periods=number_of_periods))

        out.set_source_wavefront_parameters(distance=distance,
                                            gapH=gapH,
                                            gapV=gapV,
                                            photon_energy=photon_energy,
                                            h_slit_points=h_slit_points,
                                            v_slit_points=v_slit_points,
                                            flag_send_wavefront_dimension=flag_send_wavefront_dimension)

        return out


    def set_source_wavefront_parameters(self, distance=None, gapH=None, gapV=None, photon_energy=None,
                                        h_slit_points=None, v_slit_points=None,
                                        flag_send_wavefront_dimension=None,):

        if distance is not None: self.__source_wavefront_parameters['distance'] = distance
        if gapH is not None: self.__source_wavefront_parameters['gapH'] = gapH
        if gapV is not None: self.__source_wavefront_parameters['gapV'] = gapV
        if photon_energy is not None: self.__source_wavefront_parameters['photon_energy'] = photon_energy
        if h_slit_points is not None: self.__source_wavefront_parameters['h_slit_points'] = h_slit_points
        if v_slit_points is not None: self.__source_wavefront_parameters['v_slit_points'] = v_slit_points
        if flag_send_wavefront_dimension is not None:
            self.__source_wavefront_parameters['flag_send_wavefront_dimension'] = flag_send_wavefront_dimension


    def get_source_wavefront_parameters(self):
        return self.__source_wavefront_parameters

    def get_dimension(self):  # overwrite this method to export 1D wavefronts if wanted

        if self.__source_wavefront_parameters['flag_send_wavefront_dimension'] == 0:
            return 2
        elif self.__source_wavefront_parameters['flag_send_wavefront_dimension'] == 1:
            return 1
        elif self.__source_wavefront_parameters['flag_send_wavefront_dimension'] == 2:
            return 1

    # from Wofry Decorator
    def get_wavefront(self):
        E, x, y, H, V, I, II = self.calculate_undulator_emission()

        # normalize E
        distance = self.__source_wavefront_parameters['distance']
        # pySRU results are ph/s/0.1bw/mrad^2/distance^2 so I multiply E by sqrt(distance**2)
        wf = GenericWavefront2D.initialize_wavefront_from_arrays(x, y,
                                                                 E[:,:,0].copy() * distance ,
                                                                 z_array_pi=E[:,:,1].copy() * distance,
                                                                 wavelength=1e-10)
        wf.set_photon_energy(self.__source_wavefront_parameters['photon_energy'])

        return wf #, I, x, y, II

    def to_python_code(self, do_plot=True, add_import_section=False):

        txt = ""

        txt += "#"
        txt += "\n# create output_wavefront\n#"
        txt += "\n#"

        txt += "\nfrom orangecontrib.esrf.wofry.util.light_source import WOPySRULightSource # TODO: from wofryimpl..."

        ebeam = self.get_electron_beam()
        und = self.get_magnetic_structure()

        txt += "\nlight_source = WOPySRULightSource.initialize_from_keywords("
        txt += "\n    energy_in_GeV=%g," % ebeam.energy()
        txt += "\n    current=%g," % ebeam.current()
        txt += "\n    K_vertical=%g," % und.K_vertical()
        txt += "\n    period_length=%g," % und.period_length()
        txt += "\n    number_of_periods=%g," % und.number_of_periods()
        txt += "\n    distance=%g," % self.__source_wavefront_parameters['distance']
        txt += "\n    gapH=%g," % self.__source_wavefront_parameters['gapH']
        txt += "\n    gapV=%g," % self.__source_wavefront_parameters['gapV']
        txt += "\n    photon_energy=%g," % self.__source_wavefront_parameters['photon_energy']
        txt += "\n    h_slit_points=%d," % self.__source_wavefront_parameters['h_slit_points']
        txt += "\n    v_slit_points=%d,)" % self.__source_wavefront_parameters['v_slit_points']

        if self.__source_wavefront_parameters['flag_send_wavefront_dimension'] == 0:
            txt += "\n\noutput_wavefront = light_source.get_wavefront()"
        elif self.__source_wavefront_parameters['flag_send_wavefront_dimension'] == 1:
            txt += "\n\noutput_wavefront = light_source.get_wavefront().get_Wavefront1D_from_profile(0, 0.0)"
        elif self.__source_wavefront_parameters['flag_send_wavefront_dimension'] == 2:
            txt += "\n\noutput_wavefront = light_source.get_wavefront().get_Wavefront1D_from_profile(1, 0.0)"

        return txt

    def calculate_undulator_emission(self):

        from pySRU.Simulation import create_simulation
        from pySRU.ElectronBeam import ElectronBeam as PySruElectronBeam
        from pySRU.MagneticStructureUndulatorPlane import MagneticStructureUndulatorPlane
        from pySRU.TrajectoryFactory import TrajectoryFactory
        from pySRU.RadiationFactory import TRAJECTORY_METHOD_ANALYTIC, TRAJECTORY_METHOD_ODE
        from pySRU.RadiationFactory import RadiationFactory
        from pySRU.RadiationFactory import RADIATION_METHOD_NEAR_FIELD, RADIATION_METHOD_APPROX_FARFIELD

        distance        = self.__source_wavefront_parameters['distance']
        gapH            = self.__source_wavefront_parameters['gapH']
        gapV            = self.__source_wavefront_parameters['gapV']
        photon_energy   = self.__source_wavefront_parameters['photon_energy']
        zero_emittance  = False
        h_slit_points   = self.__source_wavefront_parameters['h_slit_points']
        v_slit_points   = self.__source_wavefront_parameters['v_slit_points']

        print('Running pySRU', distance, gapV, gapH, photon_energy, v_slit_points, h_slit_points)

        hArray = numpy.linspace(-0.5 * gapH, 0.5 * gapH, h_slit_points)
        vArray = numpy.linspace(-0.5 * gapV, 0.5 * gapV, v_slit_points)
        H = numpy.outer(hArray, numpy.ones_like(vArray))
        V = numpy.outer(numpy.ones_like(hArray), vArray)

        myBeam = PySruElectronBeam(Electron_energy = self.get_electron_beam().energy(),
                                   I_current       = self.get_electron_beam().current())

        myUndulator = MagneticStructureUndulatorPlane(K             = self.get_magnetic_structure().K_vertical(),
                                                      period_length = self.get_magnetic_structure().period_length(),
                                                      length        = self.get_magnetic_structure().length())

        simulation_test = create_simulation(magnetic_structure=myUndulator, electron_beam=myBeam,
                                            magnetic_field=None, photon_energy=photon_energy,
                                            traj_method=TRAJECTORY_METHOD_ODE, Nb_pts_trajectory=None,
                                            rad_method=RADIATION_METHOD_NEAR_FIELD, Nb_pts_radiation=None,
                                            initial_condition=None, distance=distance, XY_are_list=False,
                                            X=hArray, Y=vArray)

        # simulation_test.radiation.plot("title=photon energy = %f"%eArray[ie])
        intensArray = simulation_test.radiation.intensity.copy()

        # TODO: this is not nice: I redo the calculations because I need the electric vectors to get wavefront.
        #       this should be avoided after refactoring pySRU to include electric field in simulations!!
        electric_field = simulation_test.radiation_fact.calculate_electrical_field(
            simulation_test.trajectory, simulation_test.source, H, V, distance)

        E = electric_field._electrical_field
        # pol_deg1 = (np.abs(E[:, 0]) / (np.abs(E[:, 0]) + np.abs(E[:, 1]))).flatten()  # SHADOW definition!!



        II = numpy.sum(numpy.abs(E) ** 2, axis=-1)

        # grid in m
        return (E, hArray, vArray, H, V, intensArray, II)



if __name__ == "__main__":


    pp = WOPySRULightSource.initialize_from_keywords(
        name="",
        energy_in_GeV=6.04,
        current=0.2,
        K_vertical=1.68,
        period_length=0.018,
        number_of_periods=222,
        distance=10.0,
        gapH=0.003,
        gapV=0.003,
        photon_energy=7000.0,
        h_slit_points=51,
        v_slit_points=51,
        flag_send_wavefront_dimension=1,
    )

    wf = pp.get_wavefront()

    print(">>>>> Dimension: ", pp.get_dimension())

    from srxraylib.plot.gol import plot_image
    plot_image(wf.get_intensity(), wf.get_coordinate_x(), wf.get_coordinate_y())
    # plot_image(iint, x, y, title="pySRU")
    # plot_image(II, x, y, title="Me")