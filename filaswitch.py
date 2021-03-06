#!/usr/bin/env python3.5

"""
# filaswitch

G-code post processor for adding proper purge tower for 2 extruder - one hotend setup.

Disclaimer: i'm not responsible if anything, good or bad, happens due to use of this script.

"""
import argparse
import os
import sys
from tkinter import *
import tkinter.filedialog as fdialog
from tkinter.messagebox import showerror
from tkinter.ttk import *

#from slicer_cura import CuraPrintFile
#from slicer_kisslicer import KissPrintFile
from slicer_simplify3d import Simplify3dGCodeFile
from slicer_prusa_slic3r import PrusaSlic3rCodeFile

from logger import Logger
from switch_tower import PEEK, PTFE, E3DV6, HW_CONFIGS
from switch_tower import AUTO, LEFT, RIGHT, TOP, BOTTOM, TOWER_POSITIONS
from switch_tower import LINES, LINE_COUNT_DEFAULT

import utils

prog_dir = os.path.dirname(os.path.realpath(__file__))

status_file = os.path.join(prog_dir, '.status')
status = utils.load_status(status_file)

version = "0.13"

def detect_file_type(gcode_file, log):
    with open(gcode_file, 'r') as gf:
        line1 = gf.readline()
        if line1.startswith('; G-Code generated by Simplify3D(R)'):
            log.info("Detected Simplify3D format")
            return Simplify3dGCodeFile
        #elif line1.startswith('; KISSlicer'):
        #    log.info("Detected KISSlicer format")
        #    return KissPrintFile
        #elif line1.startswith('; CURA'):
        #    log.info("Detected Cura format")
        #    return CuraPrintFile
        elif line1.startswith('; generated by Slic3r 1.36.2-prusa3d') or \
                line1.startswith('; generated by Slic3r 1.37.1-prusa3d'):
            log.info("Detected Prusa Slic3r format")
            return PrusaSlic3rCodeFile

        else:
            log.error("No supported gcode file detected.")
            exit(1)


class TopFrame(Frame):
    def __init__(self, logger, master, gui):
        super().__init__(master)
        self.log = logger
        self.gui = gui
        self.grid(row=0, column=0, columnspan=5)
        self.create_widgets()

    def create_widgets(self):

        # labels
        self.hwlabel = Label(self, text="1. Select HW config").grid(row=0, column=0, sticky=W, padx=5, pady=3)
        self.gc_label = Label(self, text="2. Select g-code to process").grid(row=2, column=0, sticky=W, padx=5, pady=3)

        # HW config
        self.hw_var = StringVar(self)
        if self.gui.last_hwconfig and self.gui.last_hwconfig in HW_CONFIGS:
            self.hw_var.set(self.gui.last_hwconfig)
        else:
            self.hw_var.set(PTFE)

        self.option = OptionMenu(self, self.hw_var, self.hw_var.get(), *HW_CONFIGS)
        self.option.grid(row=0, column=1, sticky=W, padx=5, pady=3)

        # browse
        self.f_button = Button(self)
        self.f_button["text"] = "Browse..."
        self.f_button["command"] = self.load_file
        self.f_button.grid(row=2, column=1, sticky=W, padx=5, pady=3)

        # quit
        style = Style()
        style.configure("red_fg.TButton", foreground="red")
        self.quit = Button(self, text="QUIT", command=self.quit, style="red_fg.TButton")
        self.quit.grid(row=3, column=1, sticky=W, padx=5, pady=3)

    def update_status(self):
        status["last_hwconfig"] = self.hw_var.get()
        status["last_position"] = self.gui.adv_frame.position_var.get()
        status["last_line_count"] = self.gui.adv_frame.lines_var.get()

    def quit(self):
        self.update_status()
        self.gui.quit()

    def load_file(self):
        self.gui.info.update_status("----------------------")
        last_dir = status.get("last_dir")
        if last_dir and os.path.exists(status["last_dir"]):
            gcode_file = fdialog.askopenfilename(filetypes=(("G-code files", "*.gcode"), ("all files","*.*")),
                                                 initialdir=status["last_dir"])
        else:
            gcode_file = fdialog.askopenfilename(filetypes=(("G-code files", "*.gcode"), ("all files", "*.*")))

        if gcode_file:
            try:
                print_type = detect_file_type(gcode_file, self.log)
                pf = print_type(self.log, self.hw_var.get(), self.gui.adv_frame.position_var.get(),
                                self.gui.adv_frame.lines_var.get())
                result_file = pf.process(gcode_file)
                if self.gui.info:
                    self.log.info("New file saved: %s" % result_file)
                # save last used dir for later use
                file_dir = os.path.dirname(gcode_file)
                status["last_dir"] = file_dir

            except Exception as e:
                self.log.error(str(e))
                #showerror("File open error", "Cannot open file %s" % gcode_file)
        else:
            self.log.info("Aborted")


class AdvancedFrame(Frame):

    def __init__(self, logger, master, gui):
        super().__init__(master)
        self.log = logger
        self.gui = gui
        self.grid(row=0, column=0, columnspan=5)
        self.create_widgets()

    def create_widgets(self):

        self.position_label = Label(self, text="Purge tower position").grid(row=0, column=0, sticky=W, padx=5, pady=3)
        self.size_label = Label(self, text="Purge lines (default: 6)").grid(row=1, column=0, sticky=W, padx=5, pady=3)

        # position
        self.position_var = StringVar(self)

        if self.gui.last_position and self.gui.last_position in TOWER_POSITIONS:
            self.position_var.set(self.gui.last_position)
        else:
            self.position_var.set(AUTO)

        self.position_option = OptionMenu(self, self.position_var, self.position_var.get(), *TOWER_POSITIONS)
        self.position_option.grid(row=0, column=1, sticky=W, padx=5, pady=3)

        # size
        self.lines_var = StringVar(self)
        if self.gui.last_line_count:
            val = int(self.gui.last_line_count)
            if val in LINES:
                self.lines_var.set(val)
        else:
            self.lines_var.set(LINE_COUNT_DEFAULT)

        self.lines_box = OptionMenu(self, self.lines_var, self.lines_var.get(), *LINES)
        self.lines_box.grid(row=1, column=1, sticky=W, padx=5, pady=3)

class BottomFrame(Frame):

    def __init__(self, master, gui):
        super().__init__(master)
        self.gui = gui
        self.grid(row=6)
        self.line_count = 0
        self.create_widgets()

    def create_widgets(self):
        self.scrollbar = Scrollbar(self)
        self.scrollbar.grid(row=3,column=3)

        self.status = Text(self, height=10, width=90, yscrollcommand=self.scrollbar.set)
        self.status.grid(row=3, columnspan=2)

        self.scrollbar.config(command=self.status.yview)
        self.update_status("Idling...")

    def update_status(self, text):
        self.status.configure(state=NORMAL)
        self.status.insert(END, text + os.linesep)
        self.status.configure(state=DISABLED)
        if not self.status.see(END):
            self.scrollbar.set(100, 0)
        self.line_count += 1


class GUI:

    def __init__(self):

        self.log = Logger(prog_dir)

        self.last_hwconfig = status.get("last_hwconfig")
        self.last_position = status.get("last_position")
        self.last_line_count = status.get("last_line_count")

    def show_gui(self):

        self.top = Tk()
        self.top.title('FilaSwitch v%s' % version)
        # top.geometry('500x500')
        self.top.rowconfigure(6, weight=1)
        self.top.columnconfigure(5, weight=1)

        self.nb = Notebook(self.top)
        self.info = BottomFrame(self.top, self)

        self.log.set_gui(self.info)

        self.topframe = TopFrame(self.log, self.nb, self)

        self.adv_frame = AdvancedFrame(self.log, self.nb, self)

        self.nb.add(self.topframe, text="Main")
        self.nb.add(self.adv_frame, text="Advanced")
        self.nb.grid(row=0, column=0, columnspan=5, rowspan=5, sticky='NESW')
        self.top.protocol("WM_DELETE_WINDOW", self.quit)
        self.top.mainloop()

    def quit(self):
        self.topframe.update_status()
        utils.save_status_file(status_file, status)
        self.top.destroy()


def main():

    if len(sys.argv) < 2:
        # GUI mode
        gui = GUI()
        gui.show_gui()
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("file", help="Path to g-code file to process")
        parser.add_argument("hw_config", help="Extruder/hotend configuration", choices=HW_CONFIGS)
        parser.add_argument("--debug", help="Show debug prints", action="store_true")
        parser.add_argument("--lines", help="Purge lines to print after filament change", type=int,
                            default=LINE_COUNT_DEFAULT)
        parser.add_argument("--position", help="Purge tower position. Default Auto. Auto will try to find a position with enough free space for the tower",
                            choices=TOWER_POSITIONS, default=AUTO)
        args = parser.parse_args()

        log = Logger(prog_dir, gui=False, debug=args.debug)
        print_type = detect_file_type(args.file, log)
        pf = print_type(log, args.hw_config, args.position, args.lines)
        result_file = pf.process(args.file)
        log.info("New file saved: %s" % result_file)


if __name__ == "__main__":
    main()