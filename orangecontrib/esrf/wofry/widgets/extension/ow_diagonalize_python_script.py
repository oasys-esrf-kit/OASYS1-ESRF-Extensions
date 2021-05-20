import sys
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QTextCursor

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.widgets import widget
from oasys.util.oasys_util import TriggerIn, TriggerOut, EmittingStream

from orangecontrib.wofry.util.wofry_objects import WofryData
from orangecontrib.esrf.shadow.util.python_script import PythonConsole


# from oasys.widgets import gui as oasysgui
# from oasys.widgets import congruence
# from oasys.widgets import congruence
# from oasys.util.oasys_util import TriggerIn, TriggerOut, EmittingStream
# from syned.storage_ring.magnetic_structures.undulator import Undulator
# from syned.beamline.beamline import Beamline
# import inspect
# import numpy
# import os, sys

from wofryimpl.propagator.light_source import WOLightSource
from orangecontrib.esrf.wofry.util.light_source import WOLightSourceCMD


class DiagonalizePythonScript(widget.OWWidget):

    name = "Diagonalize Python Script"
    description = "Diagonalize Python Script"
    icon = "icons/diagonalize_python_script.png"
    maintainer = "Manuel Sanchez del Rio"
    maintainer_email = "srio(@at@)esrf.eu"
    priority = 500
    category = "Tools"
    keywords = ["script"]

    inputs = [("WofryData", WofryData, "set_input")]

    outputs = [
               {"name":"WofryData",
                "type":WofryData,
                "doc":"WofryData",
                "id":"WofryData"}
                ]

    mode_index_max = Setting(10)

    show_graph_flag = Setting(1)
    script_file_flag = Setting(0)
    script_file_name = Setting("tmp.py")
    graph_file_flag = Setting(0)
    data_file_flag = Setting(0)
    root_file_name = Setting("tmp")

    #
    #
    #
    IMAGE_WIDTH = 890
    IMAGE_HEIGHT = 680

    # want_main_area=1

    is_automatic_run = Setting(True)

    error_id = 0
    warning_id = 0
    info_id = 0

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 560

    input_data = None



    def __init__(self, show_automatic_box=True, show_general_option_box=True):
        super().__init__() # show_automatic_box=show_automatic_box)


        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width()*0.05),
                               round(geom.height()*0.05),
                               round(min(geom.width()*0.98, self.MAX_WIDTH)),
                               round(min(geom.height()*0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        self.general_options_box = gui.widgetBox(self.controlArea, "General Options", addSpace=True, orientation="horizontal")
        self.general_options_box.setVisible(show_general_option_box)

        if show_automatic_box :
            gui.checkBox(self.general_options_box, self, 'is_automatic_run', 'Automatic Execution')


        #
        #
        #
        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Refresh Script", callback=self.refresh_script)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)


        gui.separator(self.controlArea)

        gen_box = oasysgui.widgetBox(self.controlArea, "Scan modes", addSpace=False, orientation="vertical", width=self.CONTROL_AREA_WIDTH-5)
        oasysgui.lineEdit(gen_box, self, "mode_index_max", "Max mode (index)", labelWidth=150, valueType=int,
                          orientation="horizontal", callback=self.refresh_script)

        gen_box = oasysgui.widgetBox(self.controlArea, "Script file", addSpace=False, orientation="vertical", width=self.CONTROL_AREA_WIDTH-5)
        gui.comboBox(gen_box, self, "script_file_flag", label="write file with script",
                     items=["No", "Yes"], labelWidth=300,
                     sendSelectedValue=False, orientation="horizontal")
        box1 = gui.widgetBox(gen_box, orientation="horizontal")
        oasysgui.lineEdit(box1, self, "script_file_name", "Script File Name", labelWidth=150, valueType=str,
                          orientation="horizontal")
        self.show_at("self.script_file_flag == 1", box1)


        gen_box = oasysgui.widgetBox(self.controlArea, "Output Graph and Data", addSpace=False, orientation="vertical", width=self.CONTROL_AREA_WIDTH-5)
        gui.comboBox(gen_box, self, "show_graph_flag", label="show plots",
                     items=["No", "Yes"], labelWidth=300,
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(gen_box, self, "graph_file_flag", label="dump plots to file",
                     items=["No", "Yes [png]", "Yes [pdf]"], labelWidth=300,
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(gen_box, self, "data_file_flag", label="dump plot data to file",
                     items=["No", "Yes"], labelWidth=300,
                     sendSelectedValue=False, orientation="horizontal")

        box3 = gui.widgetBox(gen_box, orientation="horizontal")
        oasysgui.lineEdit(box3, self, "root_file_name", "Data File Name Root", labelWidth=150, valueType=str,
                          orientation="horizontal")

        self.show_at("self.graph_file_flag > 0 or self.data_file_flag == 1", box3)


        tabs_setting = oasysgui.tabWidget(self.mainArea)
        tabs_setting.setFixedHeight(self.IMAGE_HEIGHT)
        tabs_setting.setFixedWidth(self.IMAGE_WIDTH)

        tab_scr = oasysgui.createTabPage(tabs_setting, "Python Script")
        tab_out = oasysgui.createTabPage(tabs_setting, "System Output")

        self.pythonScript = oasysgui.textArea(readOnly=False)
        self.pythonScript.setStyleSheet("background-color: white; font-family: Courier, monospace;")
        self.pythonScript.setMaximumHeight(self.IMAGE_HEIGHT - 250)

        script_box = oasysgui.widgetBox(tab_scr, "", addSpace=False, orientation="vertical", height=self.IMAGE_HEIGHT - 10, width=self.IMAGE_WIDTH - 10)
        script_box.layout().addWidget(self.pythonScript)

        console_box = oasysgui.widgetBox(script_box, "", addSpace=True, orientation="vertical",
                                          height=150, width=self.IMAGE_WIDTH - 10)

        self.console = PythonConsole(self.__dict__, self)
        console_box.layout().addWidget(self.console)

        self.wofry_output = oasysgui.textArea()

        out_box = oasysgui.widgetBox(tab_out, "System Output", addSpace=True, orientation="horizontal", height=self.IMAGE_WIDTH - 45)
        out_box.layout().addWidget(self.wofry_output)

        #############################

        button_box = oasysgui.widgetBox(tab_scr, "", addSpace=True, orientation="horizontal")

        gui.button(button_box, self, "Run Script", callback=self.execute_script, height=40)
        # gui.button(button_box, self, "Save Script to File", callback=self.save_script, height=40)

        gui.rubber(self.controlArea)

        self.process_showers()

    def set_input(self, wofry_data):
        if not wofry_data is None:
            if isinstance(wofry_data, WofryData):
                self.input_data = wofry_data
            else:
                raise Exception("Bad input.")

            if self.is_automatic_run:
                self.refresh_script()


    def callResetSettings(self):
        pass

    def execute_script(self):

        self._script = str(self.pythonScript.toPlainText())
        self.console.write("\nRunning script:\n")
        self.console.push("exec(_script)")
        self.console.new_prompt(sys.ps1)


    def save_script(self):
        # file_name = QFileDialog.getSaveFileName(self, "Save File to Disk", os.getcwd(), filter='*.py')[0]
        file_name = self.script_file_name
        if not file_name is None:
            if not file_name.strip() == "":
                file = open(file_name, "w")
                file.write(str(self.pythonScript.toPlainText()))
                file.close()


    def refresh_script(self):

        self.wofry_output.setText("")

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        if self.input_data is None:
            raise Exception("No input data")

        beamline = self.input_data.get_beamline()
        self.pythonScript.setText(to_python_code(beamline,
                                                 do_plot=False,
                                                 mode_index_max=self.mode_index_max,
                                                 show_graph_flag=self.show_graph_flag,
                                                 graph_file_flag=self.graph_file_flag,
                                                 data_file_flag=self.data_file_flag,
                                                 root_file_name=self.root_file_name,
                                                 ))

        if self.script_file_flag:
            self.save_script()

    def writeStdOut(self, text):
        cursor = self.wofry_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.wofry_output.setTextCursor(cursor)
        self.wofry_output.ensureCursorVisible()

def to_python_code(self, # self is beamline
                    do_plot=True,
                    mode_index_max=2,
                    show_graph_flag=1,
                    graph_file_flag=0,
                    data_file_flag=0,
                    root_file_name="tmp",
                   ):

    import_text_code = ""
    import_text_code += "\n#"
    import_text_code += "\n# Import section"
    import_text_code += "\n#"
    import_text_code += "\nimport numpy"
    import_text_code += "\n\nfrom syned.beamline.beamline_element import BeamlineElement"
    import_text_code += "\nfrom syned.beamline.element_coordinates import ElementCoordinates"
    import_text_code += "\nfrom wofry.propagator.propagator import PropagationManager, PropagationElements, PropagationParameters"

    if self.get_light_source() is None:
        source_dimension = 0
        import_text_code += "\n\n#\n# UNDEFINED SOURCE (please complete...)!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! \n#"
        import_text_code += "\noutput_wavefront = None"
        import_text_code += "\n#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    else:
        source_dimension = self.get_light_source().get_dimension()
        if source_dimension == 1:
            import_text_code += "\n\nfrom wofry.propagator.wavefront1D.generic_wavefront import GenericWavefront1D"
            import_text_code += "\n\nfrom wofryimpl.propagator.propagators1D.fresnel import Fresnel1D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators1D.fresnel_convolution import FresnelConvolution1D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators1D.fraunhofer import Fraunhofer1D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators1D.integral import Integral1D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators1D.fresnel_zoom import FresnelZoom1D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators1D.fresnel_zoom_scaling_theorem import FresnelZoomScaling1D"
        elif source_dimension == 2:
            import_text_code += "\n\nfrom wofry.propagator.wavefront2D.generic_wavefront import GenericWavefront2D"
            import_text_code += "\n\nfrom wofryimpl.propagator.propagators2D.fresnel_zoom_xy import FresnelZoomXY2D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators2D.fresnel import Fresnel2D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators2D.fresnel_convolution import FresnelConvolution2D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators2D.fraunhofer import Fraunhofer2D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators2D.integral import Integral2D"
            import_text_code +=   "\nfrom wofryimpl.propagator.propagators2D.fresnel_zoom_xy import FresnelZoomXY2D"

        source_text_code = ""
        if do_plot:
            source_text_code += "\n\nfrom srxraylib.plot.gol import plot, plot_image"
            source_text_code += "\nplot_from_oe = 0 # set to a large number to avoid plots"


        source_text_code  +=  "\n\n\n##########  SOURCE ##########\n\n\n"
        source_text_code += self.get_light_source().to_python_code(do_plot=False, add_import_section=False)


        if do_plot:
            if source_dimension == 1:
                source_text_code += "\n\n\nif plot_from_oe <= 0: plot(output_wavefront.get_abscissas(),output_wavefront.get_intensity(),title='SOURCE')"
            elif source_dimension == 2:
                source_text_code += "\n\n\nif plot_from_oe <= 0: plot_image(output_wavefront.get_intensity(),output_wavefront.get_coordinate_x(),output_wavefront.get_coordinate_y(),aspect='auto',title='SOURCE')"


    beamline_text_code = ""
    if self.get_beamline_elements_number() > 0:
        beamline_text_code += "\n\n\n##########  OPTICAL SYSTEM ##########\n\n\n"


        for index in range(self.get_beamline_elements_number()):
            beamline_text_code += "\n\n\n##########  OPTICAL ELEMENT NUMBER %i ##########\n\n\n" % (index+1)
            oe_name = "oe_" + str(index)
            beamline_element = self.get_beamline_element_at(index)
            optical_element = beamline_element.get_optical_element()
            coordinates = beamline_element.get_coordinates()

            beamline_text_code += "\ninput_wavefront = output_wavefront.duplicate()"

            # OPTICAL ELEMENT ----------------
            beamline_text_code += optical_element.to_python_code()

            propagation_info = self.get_propagation_info_at(index)

            if (coordinates.p() == 0.0) and (coordinates.q() == 0.0): # NO DRIFT
                beamline_text_code += "\n# no drift in this element "
                beamline_text_code += "\noutput_wavefront = optical_element.applyOpticalElement(input_wavefront)"
            else:
                if coordinates.p() != 0.0:
                    beamline_text_code += "\n# drift_before %g m" % coordinates.p()
                if coordinates.q() != 0.0:
                    beamline_text_code += "\n# drift_after %g m " % coordinates.q()

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

                propagator_class_name                   = propagation_info["propagator_class_name"]
                propagator_handler_name                 = propagation_info["propagator_handler_name"]
                propagator_additional_parameters_names  = propagation_info["propagator_additional_parameters_names"]
                propagator_additional_parameters_values = propagation_info["propagator_additional_parameters_values"]

                beamline_text_code += "\n#"
                beamline_text_code += "\n# propagating\n#"
                beamline_text_code += "\n#"
                beamline_text_code += "\npropagation_elements = PropagationElements()"
                beamline_text_code += "\nbeamline_element = BeamlineElement(optical_element=optical_element,"
                beamline_text_code += "    coordinates=ElementCoordinates(p=%f," % (coordinates.p())
                beamline_text_code += "    q=%f," % (coordinates.q())
                beamline_text_code += "    angle_radial=numpy.radians(%f)," % (coordinates.angle_radial())
                beamline_text_code += "    angle_azimuthal=numpy.radians(%f)))" % (coordinates.angle_azimuthal())
                beamline_text_code += "\npropagation_elements.add_beamline_element(beamline_element)"
                beamline_text_code += "\npropagation_parameters = PropagationParameters(wavefront=input_wavefront,"
                beamline_text_code += "    propagation_elements = propagation_elements)"
                beamline_text_code += "\n#self.set_additional_parameters(propagation_parameters)"
                beamline_text_code += "\n#"

                for i in range(len(propagator_additional_parameters_names)):
                    beamline_text_code += "\npropagation_parameters.set_additional_parameters('%s', %s)" % \
                    (propagator_additional_parameters_names[i], str(propagator_additional_parameters_values[i]))

                beamline_text_code += "\n#"
                beamline_text_code += "\npropagator = PropagationManager.Instance()"
                beamline_text_code += "\ntry:"
                beamline_text_code += "\n    propagator.add_propagator(%s())" % propagator_class_name
                beamline_text_code += "\nexcept:"
                beamline_text_code += "\n    pass"
                beamline_text_code += "\noutput_wavefront = propagator.do_propagation(propagation_parameters=propagation_parameters,"
                beamline_text_code += "    handler_name='%s')" % (propagator_handler_name)

            if do_plot:
                beamline_text_code += "\n\n\n#\n#---- plots -----\n#"
                if source_dimension == 1:
                    beamline_text_code += "\nif plot_from_oe <= %d: plot(output_wavefront.get_abscissas(),output_wavefront.get_intensity(),title='OPTICAL ELEMENT NR %d')" % (index+1, index+1)
                elif source_dimension == 2:
                    beamline_text_code += "\nif plot_from_oe <= %d: plot_image(output_wavefront.get_intensity(),output_wavefront.get_coordinate_x(),output_wavefront.get_coordinate_y(),aspect='auto',title='OPTICAL ELEMENT NR %d')" % (index+1, index+1)

    full_text_code = import_text_code

    indent = '    '

    full_text_code += "\n\n\n#\n# SOURCE========================\n#\n\n"
    full_text_code += "\n\n\ndef run_source(my_mode_index=0):"

    if isinstance(self.get_light_source(), WOLightSourceCMD):
        full_text_code += "\n" + indent + "global coherent_mode_decomposition"
        full_text_code += "\n" + indent + "try:"
        full_text_code += "\n" + indent*2 + "if my_mode_index == 0: raise Exception()"
        full_text_code += "\n" + indent*2 + "tmp = coherent_mode_decomposition"
        full_text_code += "\n" + indent + "except:"

        indented = indent*2 + source_text_code.replace('\n', '\n' + indent*2)
        full_text_code += indented

        full_text_code += "\n" + indent + "output_wavefront = coherent_mode_decomposition.get_eigenvector_wavefront(my_mode_index)"
        full_text_code += "\n" + indent + "return output_wavefront"
    elif isinstance(self.get_light_source(), WOLightSource):
        indented = indent + source_text_code.replace('\n', '\n' + indent)
        full_text_code += indented
        full_text_code += "\n" + indent + "# previous command is useless but..."
        full_text_code += "\n" + indent + "output_wavefront.set_gaussian_hermite_mode(sigma_x=%g,amplitude=%g,mode_x=my_mode_index,shift=%g,beta=%g)" % \
               (self.get_light_source()._sigma_h,
                self.get_light_source()._amplitude,
                self.get_light_source()._gaussian_shift,
                self.get_light_source()._beta_h)

        full_text_code += "\n" + indent + "return output_wavefront"


    full_text_code += "\n\n\n#\n# BEAMLINE========================\n#\n\n"
    full_text_code += "\n\n\ndef run_beamline(output_wavefront):"
    indented = indent + beamline_text_code.replace('\n', '\n' + indent)
    full_text_code += indented
    full_text_code += "\n" + indent + "return output_wavefront"

    full_text_code += "\n\n\n#\n# MAIN FUNCTION========================\n#\n\n"
    full_text_code += "\n\n\ndef main():"

    full_text_code += "\n" + indent + "from srxraylib.plot.gol import plot, plot_image"
    full_text_code += "\n" + indent + "from orangecontrib.esrf.wofry.util.tally import TallyCoherentModes"
    full_text_code += "\n" + indent + ""
    full_text_code += "\n" + indent + "tally = TallyCoherentModes()"
    full_text_code += "\n" + indent + "for my_mode_index in range(%g):" % mode_index_max
    full_text_code += "\n" + indent * 2 + "output_wavefront = run_source(my_mode_index=my_mode_index)"
    full_text_code += "\n" + indent * 2 + "output_wavefront = run_beamline(output_wavefront)"
    full_text_code += "\n" + indent * 2 + "tally.append(output_wavefront)"
    full_text_code += "\n" + indent + ""


    if graph_file_flag == 0:
        dump_file = ""
    elif graph_file_flag == 1:
        dump_file = "%s_cross_spectral_density.png" % root_file_name
    elif graph_file_flag == 2:
        dump_file = "%s_cross_spectral_density.pdf" % root_file_name

    full_text_code += "\n\n" + indent + 'tally.plot_cross_spectral_density(show=%d,filename="%s")' % (show_graph_flag, dump_file)

    if graph_file_flag == 0:
        dump_file = ""
    elif graph_file_flag == 1:
        dump_file = "%s_spectral_density.png" % root_file_name
    elif graph_file_flag == 2:
        dump_file = "%s_spectral_density.pdf" % root_file_name
    full_text_code += "\n" + indent + 'tally.plot_spectral_density(show=%d,filename="%s")' % (show_graph_flag, dump_file)

    if graph_file_flag == 0:
        dump_file = ""
    elif graph_file_flag == 1:
        dump_file = "%s_occupation.png" % root_file_name
    elif graph_file_flag == 2:
        dump_file = "%s_occupation.pdf" % root_file_name
    full_text_code += "\n" + indent + 'tally.plot_occupation(show=%d,filename="%s")' % (show_graph_flag, dump_file)

    if data_file_flag:
        full_text_code += "\n\n" + indent + 'tally.save_spectral_density(filename="%s_spectral_density.dat")' % (root_file_name)
        full_text_code += "\n" + indent + 'tally.save_occupation(filename="%s_occupation.dat")' % (root_file_name)

    full_text_code += "\n\n\n#\n# MAIN========================\n#\n\n"
    full_text_code += "\n\n\nmain()"
    return full_text_code



if __name__ == "__main__":
    import sys

    a = QApplication(sys.argv)
    ow = DiagonalizePythonScript()
    ow.show()
    a.exec_()
    ow.saveSettings()