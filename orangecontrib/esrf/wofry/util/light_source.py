import numpy
from syned.storage_ring.light_source import LightSource
from syned.storage_ring.electron_beam import ElectronBeam
from syned.storage_ring.magnetic_structures.undulator import Undulator

from wofry.beamline.decorators import LightSourceDecorator
from wofryimpl.propagator.util.undulator_coherent_mode_decomposition_1d import UndulatorCoherentModeDecomposition1D



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
        if self.scan_direction == 0:
            txt += "\n    scan_direction='H',"
        else:
            txt += "\n    scan_direction='V',"
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