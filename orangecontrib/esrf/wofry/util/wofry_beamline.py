
from syned.beamline.beamline import Beamline
from syned.storage_ring.light_source import LightSource
from syned.storage_ring.empty_light_source import EmptyLightSource

class WOBeamline(Beamline):

    def __init__(self,
                 light_source=None,
                 beamline_elements_list=None):
        super().__init__(light_source=light_source, beamline_elements_list=beamline_elements_list)

        self._propagation_info_list = [{}] * super().get_beamline_elements_number()


    def duplicate(self):
        beamline_elements_list = []
        for beamline_element in self._beamline_elements_list:
            beamline_elements_list.append(beamline_element)

        return WOBeamline(light_source=self._light_source,
                        beamline_elements_list=beamline_elements_list)

    def append_beamline_element(self, beamline_element, propagation_info={}):
        super().append_beamline_element(beamline_element)
        self._propagation_info_list.append(propagation_info)

    def get_propagation_info_list(self):
        return self._propagation_info_list

    def get_propagation_info_at(self, i):
        return self.get_propagation_info_list()[i]

    def to_python_code(self,do_plot=True):

        text_code = "\nimport numpy"
        text_code += "\n\n"

        text_code += "\n#"
        text_code += "\n# Import section (propagators)"
        text_code += "\n#"
        text_code += "\nfrom wofry.propagator.propagator import PropagationManager, PropagationElements, PropagationParameters"
        text_code += "\nfrom syned.beamline.beamline_element import BeamlineElement"
        text_code += "\nfrom syned.beamline.element_coordinates import ElementCoordinates"
        text_code += "\nfrom wofry.propagator.propagators2D.fresnel_zoom_xy import FresnelZoomXY2D"
        text_code += "\nfrom wofry.propagator.propagators2D.fresnel import Fresnel2D"
        text_code += "\nfrom wofry.propagator.propagators2D.fresnel_convolution import FresnelConvolution2D"
        text_code += "\nfrom wofry.propagator.propagators2D.fraunhofer import Fraunhofer2D"
        text_code += "\nfrom wofry.propagator.propagators2D.integral import Integral2D"
        text_code += "\nfrom wofry.propagator.propagators2D.fresnel_zoom_xy import FresnelZoomXY2D"


        text_code  +=  "\n\n\n##########  SOURCE ##########\n\n\n"
        text_code += self.get_light_source().to_python_code(do_plot=do_plot)

        if self.get_beamline_elements_number() > 0:
            text_code += "\n\n\n##########  OPTICAL SYSTEM ##########\n\n\n"


            for index in range(self.get_beamline_elements_number()):
                text_code += "\n\n\n##########  OPTICAL ELEMENT NUMBER %i ##########\n\n\n" % (index+1)
                oe_name = "oe_" + str(index)
                beamline_element = self.get_beamline_element_at(index)
                optical_element = beamline_element.get_optical_element()
                coordinates = beamline_element.get_coordinates()

                text_code += "\ninput_wavefront = output_wavefront.duplicate()"

                # OPTICAL ELEMENT ----------------
                text_code += optical_element.to_python_code(do_plot=do_plot)

                if (coordinates.p() == 0.0) and (coordinates.q() == 0.0): # NO DRIFT
                    text_code += "\n# no drift in this element "
                    text_code += "\noutput_wavefront = optical_element.applyOpticalElement(input_wavefront)"
                else:
                    if coordinates.p() != 0.0:
                        text_code += "\n# drift_before %g m" % coordinates.p()
                    if coordinates.q() != 0.0:
                        text_code += "\n# drift_after %g m " % coordinates.q()

##########################
# 1D
# ==
#
# propagators_list = ["Fresnel",    "Fresnel (Convolution)",  "Fraunhofer",    "Integral",    "Fresnel Zoom",    "Fresnel Zoom Scaled"]
# class_name       = ["Fresnel1D",  "FresnelConvolution1D",   "Fraunhofer1D",  "Integral1D",  "FresnelZoom1D",   "FresnelZoomScaling1D"]
# handler_name     = ["FRESNEL_1D", "FRESNEL_CONVOLUTION_1D", "FRAUNHOFER_1D", "INTEGRAL_1D", "FRESNEL_ZOOM_1D", "FRESNEL_ZOOM_SCALING_1D"]
#
# 2D
# ==
# propagators_list = ["Fresnel",   "Fresnel (Convolution)",  "Fraunhofer",    "Integral",    "Fresnel Zoom XY"   ]
# class_name       = ["Fresnel2D", "FresnelConvolution2D",   "Fraunhofer2D",  "Integral2D",  "FresnelZoomXY2D"   ]
# handler_name     = ["FRESNEL_2D","FRESNEL_CONVOLUTION_2D", "FRAUNHOFER_2D", "INTEGRAL_2D", "FRESNEL_ZOOM_XY_2D"]

                    propagation_info = self.get_propagation_info_at(index)

                    propagator_class_name                   = propagation_info["propagator_class_name"]
                    propagator_handler_name                 = propagation_info["propagator_handler_name"]
                    propagator_additional_parameters_names  = propagation_info["propagator_additional_parameters_names"]
                    propagator_additional_parameters_values = propagation_info["propagator_additional_parameters_values"]


                    # text_code += "\n#"
                    # text_code += "\n# Import section"
                    # text_code += "\n#"
                    # text_code += "\nimport numpy"
                    # text_code += "\nfrom wofry.propagator.propagator import PropagationManager, PropagationElements, PropagationParameters"
                    # text_code += "\nfrom syned.beamline.beamline_element import BeamlineElement"
                    # text_code += "\nfrom syned.beamline.element_coordinates import ElementCoordinates"
                    # text_code += "\nfrom wofry.propagator.propagators2D.fresnel_zoom_xy import FresnelZoomXY2D"
                    # text_code += "\nfrom wofry.propagator.propagators2D.fresnel import Fresnel2D"
                    # text_code += "\nfrom wofry.propagator.propagators2D.fresnel_convolution import FresnelConvolution2D"
                    # text_code += "\nfrom wofry.propagator.propagators2D.fraunhofer import Fraunhofer2D"
                    # text_code += "\nfrom wofry.propagator.propagators2D.integral import Integral2D"
                    # text_code += "\nfrom wofry.propagator.propagators2D.fresnel_zoom_xy import FresnelZoomXY2D"
                    text_code += "\n#"
                    text_code += "\n# propagating\n#"
                    text_code += "\n#"
                    text_code += "\npropagation_elements = PropagationElements()"
                    text_code += "\nbeamline_element = BeamlineElement(optical_element=optical_element,"
                    text_code += "    coordinates=ElementCoordinates(p=%f," % (coordinates.p())
                    text_code += "    q=%f," % (coordinates.q())
                    text_code += "    angle_radial=numpy.radians(%f)," % (coordinates.angle_radial())
                    text_code += "    angle_azimuthal=numpy.radians(%f)))" % (coordinates.angle_azimuthal())
                    text_code += "\npropagation_elements.add_beamline_element(beamline_element)"
                    text_code += "\npropagation_parameters = PropagationParameters(wavefront=input_wavefront,"
                    text_code += "    propagation_elements = propagation_elements)"
                    text_code += "\n#self.set_additional_parameters(propagation_parameters)"
                    text_code += "\n#"

                    for i in range(len(propagator_additional_parameters_names)):
                        text_code += "\npropagation_parameters.set_additional_parameters('%s', %s)" % \
                        (propagator_additional_parameters_names[i], str(propagator_additional_parameters_values[i]))

                    text_code += "\n#"
                    text_code += "\npropagator = PropagationManager.Instance()"
                    text_code += "\ntry:"
                    text_code += "\n    propagator.add_propagator(%s())" % propagator_class_name
                    text_code += "\nexcept:"
                    text_code += "\n    pass"
                    text_code += "\noutput_wavefront = propagator.do_propagation(propagation_parameters=propagation_parameters,"
                    text_code += "    handler_name='%s')" % (propagator_handler_name)
##########################

                if do_plot:
                        text_code += "\n\n\nfrom srxraylib.plot.gol import plot, plot_image"
                        text_code += "\nif output_wavefront.get_dimension() == 1:"
                        text_code += "\n  plot(output_wavefront.get_abscissas(),output_wavefront.get_intensity(),title='OPTICAL ELEMENT NR %d')" % (index+1)
                        text_code += "\nelse:"
                        text_code += "\n  plot_image(output_wavefront.get_intensity(),output_wavefront.get_coordinate_x(),output_wavefront.get_coordinate_y(),aspect='auto',title='OPTICAL ELEMENT NR %d')" % (index+1)

        #######################
        # txt = "#"
        # txt += "\n# Import section"
        # txt += "\n#"
        # txt += "\nimport numpy"
        # txt += "\nfrom wofry.propagator.propagator import PropagationManager, PropagationElements, PropagationParameters"
        # txt += "\nfrom syned.beamline.beamline_element import BeamlineElement"
        # txt += "\nfrom syned.beamline.element_coordinates import ElementCoordinates"
        # txt += "\nfrom wofry.propagator.propagators2D.fresnel_zoom_xy import FresnelZoomXY2D"
        #
        # if write_wavefront_template:
        #     txt += "\n\n#"
        #     txt += "\n# create/import your input_wavefront (THIS IS A PLACEHOLDER - REPLACE WITH YOUR SOURCE)"
        #     txt += "\n#"
        #     txt += "\nfrom wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D"
        #     txt += "\ninput_wavefront = GenericWavefront2D.load_h5_file('wavefront2D_input.h5',filepath='wfr')"
        #     txt += "\n\n"
        #
        # txt += "\n\n#"
        # txt += "\n# info on current oe\n#"
        # txt += "\n#"
        # txt_info = self.get_optical_element().info()
        # lines = txt_info.split("\n")
        #
        # for line in lines:
        #     txt += "\n#"+line
        #
        # txt += "\n\n#"
        # txt += "\n# define current oe"
        # txt += "\n#"
        #
        # txt += self.get_optical_element_python_code()
        #
        # txt += "\n#"
        # txt += "\n# propagating (***  ONLY THE ZOOM PROPAGATOR IS IMPLEMENTED ***)\n#"
        # txt += "\n#"
        #
        # txt += "\npropagation_elements = PropagationElements()"
        # txt += "\nbeamline_element = BeamlineElement(optical_element=optical_element,"
        # txt += "    coordinates=ElementCoordinates(p=%f,"%(self.p)
        # txt += "    q=%f,"%(self.q)
        # txt += "    angle_radial=numpy.radians(%f),"%(self.angle_radial)
        # txt += "    angle_azimuthal=numpy.radians(%f)))"%(self.angle_azimuthal)
        # txt += "\npropagation_elements.add_beamline_element(beamline_element)"
        # txt += "\npropagation_parameters = PropagationParameters(wavefront=input_wavefront.duplicate(),"
        # txt += "    propagation_elements = propagation_elements)"
        # txt += "\n#self.set_additional_parameters(propagation_parameters)"
        #
        # txt += "\n#"
        # txt += "\npropagation_parameters.set_additional_parameters('shift_half_pixel', 1)"
        # txt += "\npropagation_parameters.set_additional_parameters('magnification_x', %f)"%(self.magnification_x)
        # txt += "\npropagation_parameters.set_additional_parameters('magnification_y', %f)"%(self.magnification_y)
        #
        # txt += "\n#"
        # txt += "\npropagator = PropagationManager.Instance()"
        # txt += "\ntry:"
        # txt += "\n    propagator.add_propagator(FresnelZoomXY2D())"
        # txt += "\nexcept:"
        # txt += "\n    pass"
        # txt += "\noutput_wavefront = propagator.do_propagation(propagation_parameters=propagation_parameters,"
        # txt += "    handler_name='FRESNEL_ZOOM_XY_2D')"
        #
        # txt += "\n\nfrom srxraylib.plot.gol import plot_image"
        # txt += "\nplot_image(output_wavefront.get_intensity(),output_wavefront.get_coordinate_x(), output_wavefront.get_coordinate_y(), aspect='auto')"

#######################
        return text_code