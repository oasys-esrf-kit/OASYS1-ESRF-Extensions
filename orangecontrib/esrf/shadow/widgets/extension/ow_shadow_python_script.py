import os, sys

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QApplication, QFileDialog

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from orangecontrib.esrf.shadow.util.python_script import PythonConsole

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPlot
from oasys.widgets import widget
from PyQt5.QtCore import QRect

import inspect
import numpy
import Shadow




class ShadowPythonScript(widget.OWWidget):

    name = "Shadow Python Script"
    description = "Shadow Python Script"
    icon = "icons/python_script.png"
    maintainer = "Manuel Sanchez del Rio"
    maintainer_email = "srio(@at@)esrf.eu"
    priority = 5
    category = "Tools"
    keywords = ["script"]

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    input_shadow_data=None

    # sampFactNxNyForProp = Setting(1.0) #0.6 #sampling factor for adjusting nx, ny (effective if > 0)
    # nMacroElec = Setting(500000) #T otal number of Macro-Electrons (Wavefronts)
    # nMacroElecAvgOneProc = Setting(5) # Number of Macro-Electrons (Wavefronts) to average on each node (for MPI calculations)
    # nMacroElecSavePer = Setting(20) # Saving periodicity (in terms of Macro-Electrons) for the Resulting Intensity
    # srCalcMeth = Setting(1) # SR calculation method (1- undulator)
    # srCalcPrec = Setting(0.01) # SR calculation rel. accuracy
    # strIntPropME_OutFileName = Setting("output_srw_script_me.dat")
    # _char = Setting(0)


    script_file_flag = Setting(0)
    script_file_name = Setting("tmp.py")
    source_flag = Setting(0)
    source_file_name = Setting("begin.dat")
    do_run = Setting(1)
    iwrite = Setting(1)

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

    # srw_live_propagation_mode = "Unknown"




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

        # button = gui.button(button_box, self, "Reset Fields", callback=self.callResetSettings)
        # font = QFont(button.font())
        # font.setItalic(True)
        # button.setFont(font)
        # palette = QPalette(button.palette()) # make a copy of the palette
        # palette.setColor(QPalette.ButtonText, QColor('Dark Red'))
        # button.setPalette(palette) # assign new palette
        # button.setFixedHeight(45)
        # button.setFixedWidth(150)

        gui.separator(self.controlArea)

        gen_box = oasysgui.widgetBox(self.controlArea, "Script Generation", addSpace=False, orientation="vertical", height=530, width=self.CONTROL_AREA_WIDTH-5)

        gui.comboBox(gen_box, self, "script_file_flag", label="write file with script",
                     items=["No", "Yes"], labelWidth=300,
                     sendSelectedValue=False, orientation="horizontal")

        box1 = gui.widgetBox(gen_box, orientation="horizontal")
        oasysgui.lineEdit(box1, self, "script_file_name", "Script File Name", labelWidth=150, valueType=str,
                          orientation="horizontal")
        self.show_at("self.script_file_flag == 1", box1)


        gui.comboBox(gen_box, self, "source_flag", label="source from",
                     items=["Oasys wire", "shadow3 file"], labelWidth=300,
                     sendSelectedValue=False, orientation="horizontal")

        box1 = gui.widgetBox(gen_box, orientation="horizontal")
        oasysgui.lineEdit(box1, self, "source_file_name", "Source File Name", labelWidth=150, valueType=str,
                          orientation="horizontal")
        self.show_at("self.source_flag == 1", box1)

        gui.comboBox(gen_box, self, "do_run", label="run shadow3 (in script)",
                     items=["No (only definitions)", "Yes (define and run)"], labelWidth=300,
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(gen_box, self, "iwrite", label="when running, write shadow files",
                     items=["No", "Yes"], labelWidth=300,
                     sendSelectedValue=False, orientation="horizontal")


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

        self.shadow_output = oasysgui.textArea()

        out_box = oasysgui.widgetBox(tab_out, "System Output", addSpace=True, orientation="horizontal", height=self.IMAGE_WIDTH - 45)
        out_box.layout().addWidget(self.shadow_output)

        #############################

        button_box = oasysgui.widgetBox(tab_scr, "", addSpace=True, orientation="horizontal")

        gui.button(button_box, self, "Run Script", callback=self.execute_script, height=40)
        # gui.button(button_box, self, "Save Script to File", callback=self.save_script, height=40)

        gui.rubber(self.controlArea)

        self.process_showers()

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


    def setBeam(self, beam):
        if ShadowCongruence.checkEmptyBeam(beam):
            if ShadowCongruence.checkGoodBeam(beam):
                # sys.stdout = EmittingStream(textWritten=self.writeStdOut)

                self.input_beam = beam

                if self.is_automatic_run:
                    self.refresh_script()

            else:
                QtWidgets.QMessageBox.critical(self, "Error",
                                           "Data not displayable: No good rays or bad content",
                                           QtWidgets.QMessageBox.Ok)

    def refresh_script(self):
        optical_element_list_start = []
        optical_element_list_end = []

        self.pythonScript.setText("")

        for history_element in self.input_beam.getOEHistory():
            if not history_element._shadow_source_start is None:
                optical_element_list_start.append(history_element._shadow_source_start.src)
            elif not history_element._shadow_oe_start is None:
                optical_element_list_start.append(history_element._shadow_oe_start._oe)

            if not history_element._shadow_source_end is None:
                optical_element_list_end.append(history_element._shadow_source_end.src)
            elif not history_element._shadow_oe_end is None:
                optical_element_list_end.append(history_element._shadow_oe_end._oe)


        try:
            if self.script_file_flag == 0:
                script_file = ""
            else:
                script_file = self.script_file_name
            self.pythonScript.setText(make_python_script_from_list(optical_element_list_start,
                                                                   script_file=script_file,
                                                                   source_flag=self.source_flag,
                                                                   source_file_name=self.source_file_name,
                                                                   do_run=self.do_run,
                                                                   iwrite=self.iwrite) )
        except:
            self.pythonScript.setText(
                "Problem in writing python script:\n" + str(sys.exc_info()[0]) + ": " + str(sys.exc_info()[1]))

        if self.script_file_flag:
            self.save_script()


        # if not self.input_shadow_data is None:
        #     self.pythonScript.setText("")
        #
        #     try:
        #         received_light_source = self.input_shadow_data.get_srw_beamline().get_light_source()
        #
        #         if not (isinstance(received_light_source, SRWBendingMagnetLightSource) or isinstance(received_light_source, SRWUndulatorLightSource)):
        #             raise ValueError("ME Script is not available with this source")
        #
        #         _char = 0 if self._char == 0 else 4
        #
        #         parameters = [self.sampFactNxNyForProp,
        #                       self.nMacroElec,
        #                       self.nMacroElecAvgOneProc,
        #                       self.nMacroElecSavePer,
        #                       self.srCalcMeth,
        #                       self.srCalcPrec,
        #                       self.strIntPropME_OutFileName,
        #                       _char]
        #
        #         self.pythonScript.setText(self.input_shadow_data.get_srw_beamline().to_python_code([self.input_shadow_data.get_srw_wavefront(), True, parameters]))
        #     except Exception as e:
        #         self.pythonScript.setText("Problem in writing python script:\n" + str(sys.exc_info()[0]) + ": " + str(sys.exc_info()[1]))
        #
        #         if self.IS_DEVELOP: raise e


#
# automatic creation of python scripts
#

def make_python_script_from_list(list_optical_elements1, script_file="", source_flag=0, source_file_name="",
                                 iwrite=0, do_run=1):
    """
    program to build automatically a python script to run shadow3

    the system is read from a list of instances of Shadow.Source and Shadow.OE

    :argument list of optical_elements A python list with intances of Shadow.Source and Shadow.OE objects
    :param script_file: a string with the name of the output file (default="", no output file)
    :return: template with the script
    """

    # make sure that the list does not contain lists

    haslist = sum([isinstance(i, list) for i in list_optical_elements1])

    list_optical_elements = list_optical_elements1
    if haslist:
        while (haslist > 0):
            newlist = []
            for i in list_optical_elements:
                if isinstance(i, list):
                    newlist.extend(i)
                else:
                    newlist.append(i)
            list_optical_elements = newlist
            haslist = sum([isinstance(i, list) for i in list_optical_elements])

    # make sure that the list does not contain compoundOE (developed)

    hascomp = sum(
        [isinstance(i, (Shadow.CompoundOE, Shadow.ShadowLibExtensions.CompoundOE)) for i in list_optical_elements])

    if hascomp:
        newlist = []
        for i in list_optical_elements:
            if isinstance(i, (Shadow.CompoundOE, Shadow.ShadowLibExtensions.CompoundOE)):
                newlist.extend(i.list)
            else:
                newlist.append(i)
        list_optical_elements = newlist

    template_import = """#
# Python script to run shadow3. Created automatically with make_python_script_from_list().
#
import Shadow
import numpy

"""

    n_elements = len(list_optical_elements)
    #
    # source
    #


    template_define_source = """
def define_source():
    #
    # initialize shadow3 source (oe0) and beam
    #
    oe0 = Shadow.Source()

    # Define variables. See https://raw.githubusercontent.com/oasys-kit/shadow3/master/docs/source.nml
"""

    isource = -1
    for i, element in enumerate(list_optical_elements):
        if isinstance(element, Shadow.Source):
            isource = i

    if isource == -1:
        raise Exception("Source not found")

    ioe = isource
    oe1B = list_optical_elements[isource]
    template_define_source += "\n"
    if isinstance(oe1B, Shadow.Source):
        oe1 = Shadow.Source()


    memB = inspect.getmembers(oe1B)
    mem = inspect.getmembers(oe1)
    for i, var in enumerate(memB):
        ivar = mem[i]
        ivarB = memB[i]
        if ivar[0].isupper():
            if isinstance(ivar[1], numpy.ndarray):

                if not ((ivar[1] == ivarB[1]).all()):
                    line = "    oe" + str(ioe) + "." + ivar[0] + " = numpy.array(" + str(ivarB[1].tolist()) + ")\n"
                    template_define_source += line

            else:
                if ivar[1] != ivarB[1]:
                    if isinstance(ivar[1], (str, bytes)):
                        line = "    oe" + str(ioe) + "." + ivar[0] + " = " + str(ivarB[1]).strip() + "\n"
                        if "SPECIFIED" in line:
                            pass
                        else:
                            template_define_source += line
                    else:
                        line = "    oe" + str(ioe) + "." + ivar[0] + " = " + str(ivarB[1]) + "\n"
                        template_define_source += line

    template_define_source += """
    return oe0
    """

    template_run_source = """
def run_source(oe0, iwrite=False):
    # iwrite (1) or not (0) SHADOW files start.xx end.xx star.xx

    #Run SHADOW to create the source

    if iwrite:
        oe0.write("start.00")

    beam = Shadow.Beam()
    beam.genSource(oe0)

    if iwrite:
        oe0.write("end.00")
        beam.write("begin.dat")

    return beam
"""

    #
    # trace
    #

    template_define_beamline = """

def define_beamline():
    # initialize elements
    oe_list = []

    """

    for i, element in enumerate(list_optical_elements):
        if isinstance(element, Shadow.OE):
            template_i = """
    oe{} = Shadow.OE()
    oe_list.append(oe{})"""
            template_define_beamline += template_i.format("%d" % (i), "%d" % (i))
        elif isinstance(element, Shadow.IdealLensOE):
            template_i = """
    oe{} = Shadow.IdealLensOE()
    oe_list.append(oe{})"""
            template_define_beamline += template_i.format("%d" % (i), "%d" % (i))

    template_define_beamline += """

    # Define variables. See https://raw.githubusercontent.com/oasys-kit/shadow3/master/docs/oe.nml
"""

    for ioe, oe1B in enumerate(list_optical_elements):
        template_define_beamline += "\n"
        if isinstance(oe1B, Shadow.Source):
            oe1 = Shadow.Source()
        elif isinstance(element, Shadow.OE):
            oe1 = Shadow.OE()
        elif isinstance(element, Shadow.IdealLensOE):
            oe1 = Shadow.IdealLensOE()

        if ioe != 0:

            if isinstance(oe1B, Shadow.IdealLensOE):
                template_define_beamline += "   oe" + str(ioe) + ".T_SOURCE = " + str(oe1B.T_SOURCE).strip() + "\n"
                template_define_beamline += "   oe" + str(ioe) + ".T_IMAGE = " + str(oe1B.T_IMAGE).strip() + "\n"
                template_define_beamline += "   oe" + str(ioe) + ".focal_x = " + str(oe1B.focal_x).strip() + "\n"
                template_define_beamline += "   oe" + str(ioe) + ".focal_z = " + str(oe1B.focal_z).strip() + "\n"
            else:
                memB = inspect.getmembers(oe1B)
                mem = inspect.getmembers(oe1)
                for i, var in enumerate(memB):
                    ivar = mem[i]
                    ivarB = memB[i]
                    if ivar[0].isupper():
                        if isinstance(ivar[1], numpy.ndarray):
                            # print("                  are ALL different ? ", (ivar[1] != ivarB[1]).all())
                            # print("                  are the same ? ", (ivar[1] == ivarB[1]).all())
                            # print("                  there is at least ONE diff ? ", not((ivar[1] == ivarB[1]).all()))

                            if not ((ivar[1] == ivarB[1]).all()):
                                line = "    oe" + str(ioe) + "." + ivar[0] + " = numpy.array(" + str(
                                    ivarB[1].tolist()) + ")\n"
                                template_define_beamline += line

                            # if (ivar[1] != ivarB[1]).all():
                            #     line = "oe"+str(ioe)+"."+ivar[0]+" = "+str(ivarB[1])+"\n"
                            #     if ("SPECIFIED" in line):
                            #         pass
                            #     else:
                            #         template += line
                        else:
                            if ivar[1] != ivarB[1]:
                                if isinstance(ivar[1], (str, bytes)):
                                    line = "    oe" + str(ioe) + "." + ivar[0] + " = " + str(ivarB[1]).strip() + "\n"
                                    # line = re.sub('\s{2,}', ' ',line)
                                    if "SPECIFIED" in line:
                                        pass
                                    else:
                                        template_define_beamline += line
                                else:
                                    line = "    oe" + str(ioe) + "." + ivar[0] + " = " + str(ivarB[1]) + "\n"
                                    template_define_beamline += line



    template_define_beamline += """\n

    return oe_list

    """

    ###########################

    template_run_beamline = """
def run_beamline(beam_in, oe_list, iwrite=0):
    beam = beam_in.duplicate()
        """

    template_oeA = """
    #
    #run optical element {0}
    #
    print("    Running optical element: %d"%({0}))
    oe{0} = oe_list[{0}-1]
    if iwrite:
        oe{0}.write("start.{1}")
    """

    template_oeB = """
    oe{0} = oe_list[{0}-1]
    if iwrite:
        oe{0}.write("end.{1}")
        beam.write("star.{1}")
"""

    for i in range(1, n_elements):
        template_run_beamline += template_oeA.format(i, "%02d" % (i))
        if isinstance(list_optical_elements[i], Shadow.OE):
            template_run_beamline += "\n" + "    beam.traceOE(oe%d,%d)" % (i, i)
        elif isinstance(list_optical_elements[i], Shadow.IdealLensOE):
            template_run_beamline += "\n" + "    beam.traceIdealLensOE(oe%d,%d)" % (i, i)
        template_run_beamline += template_oeB.format(i, "%02d" % (i))

    template_run_beamline += """
    return beam
"""
    ###########################
    #
    # put together all pieces
    #
    template = ""
    template += template_import

    if source_flag == 0:
        template += template_define_source
        if do_run: template += template_run_source

#         template += """
# oe0 = define_source()
# """

    if n_elements > 1:
        template += template_define_beamline
        if do_run:
            template += template_run_beamline

    #
    # run
    #

    template += """
#
# main
#
"""

    if source_flag == 0:
        template += """
oe0 = define_source()
"""
        if do_run:
            template_i = """
beam = run_source(oe0, iwrite={})
    """
            template += template_i.format("%d" % iwrite)
    elif source_flag == 1:

        template_i = """
beam = Shadow.Beam()
beam.load("{}")
        """
        template += template_i.format("%s" % source_file_name)

    if n_elements > 1:
        template += """
oe_list = define_beamline()
"""
        if do_run:
            template_i = """
beam = run_beamline(beam, oe_list, iwrite={})
"""
            template += template_i.format("%s" % iwrite)

    template += """
# Shadow.ShadowTools.plotxy(beam,1,3,nbins=101,nolost=1,title="Real space")
# Shadow.ShadowTools.plotxy(beam,1,4,nbins=101,nolost=1,title="Phase space X")
# Shadow.ShadowTools.plotxy(beam,3,6,nbins=101,nolost=1,title="Phase space Z")
"""


    if script_file != "":
        open(script_file, "wt").write(template)
        print("File written to disk: %s" % (script_file))

    return template



if __name__ == "__main__":
    import sys
    import Shadow

    class MyBeam():
        pass
    beam_to_analize = Shadow.Beam()
    beam_to_analize.load("/Users/srio/Oasys/screen.0101")
    my_beam = MyBeam()
    my_beam._beam = beam_to_analize

    a = QApplication(sys.argv)
    ow = ShadowPythonScript()
    # ow.pythonScript.setText("#\n#\n#\nprint('Hello world')\n")
    ow.show()
    ow.input_beam = my_beam
    a.exec_()
    ow.saveSettings()