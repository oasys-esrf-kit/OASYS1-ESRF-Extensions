
from syned.beamline.beamline import Beamline
from syned.storage_ring.light_source import LightSource
from syned.storage_ring.empty_light_source import EmptyLightSource

class WOBeamline(Beamline):

    def __init__(self,
                 light_source=None,
                 beamline_elements_list=None):
        super().__init__(light_source=light_source, beamline_elements_list=beamline_elements_list)


    def to_python_code(self):

        text_code  =  "\n\n\n##########  SOURCE ##########\n\n\n"
        text_code += self.get_light_source().to_python_code()

        if self.get_beamline_elements_number() > 0:
            text_code += "\n\n\n##########  OPTICAL SYSTEM ##########\n\n\n"


            for index in range(self.get_beamline_elements_number()):
                text_code += "\n\n\n##########  OPTICAL ELEMENT INDEX %i ##########\n\n\n" % index
                oe_name = "oe_" + str(index)
                beamline_element = self.get_beamline_element_at(index)
                optical_element = beamline_element.get_optical_element()
                coordinates = beamline_element.get_coordinates()

                # DRIFT BEFORE ----------------

                if coordinates.p() != 0.0:
                    text_code += "\n    # drift_before %p " % coordinates.p()

                # OPTICAL ELEMENT ----------------


                # DRIFT AFTER ----------------

                if coordinates.q() != 0.0:
                    text_code += "\n    # drift_after %p " % coordinates.q()

        return text_code