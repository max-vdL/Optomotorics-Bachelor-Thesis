from __future__ import absolute_import, division, print_function

import math

from builtins import *  # @UnusedWildImport
from mcculw import ul
from mcculw.enums import ScanOptions, Status, FunctionType
from mcculw.ul import ULError
from tkinter import messagebox

from examples.props.ai import AnalogInputProps
from examples.props.ao import AnalogOutputProps
from examples.ui.uiexample import UIExample
import tkinter as tk
import xml.etree.ElementTree as et
import time as t
import os as os
from winsound import Beep
from shutil import copy, move
from datetime import datetime
import sys as sys
from tkMessageBox import showwarning

class ULAIO01(UIExample):
    def __init__(self, master=None):
        super(ULAIO01, self).__init__(master)

        self.period = 1
        self.period_switch = []

        self.tempo = None   # for arena output

        self.board_num = 0
        self.ai_props = AnalogInputProps(self.board_num)
        self.ao_props = AnalogOutputProps(self.board_num)

        # Initialize tkinter
        self.create_widgets()

    def start_input_scan(self):
        self.input_low_chan = self.get_input_low_channel_num()
        self.input_high_chan = self.get_input_high_channel_num()
        self.num_input_chans = (
            self.input_high_chan - self.input_low_chan + 1)

        self.periodtime = int(self.periodbox.get())  # variable of the duration in sec
        self.periodtimevar = self.periodtime  # a placeholder of periodtime which can be changed

        if self.input_low_chan > self.input_high_chan:
            messagebox.showerror(
                "Error",
                "Low Channel Number must be greater than or equal to High "
                "Channel Number")
            self.set_input_ui_idle_state()
            return

        rate = int(self.input_Samplingrate.get()) # data sampling rate per second
        # self.samplingrate = rate
        points_per_channel = self.test_time()
        total_count = points_per_channel * self.num_input_chans
        range_ = self.ai_props.available_ranges[0]
        scan_options = ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS

        # Allocate a buffer for the scan
        if self.ai_props.resolution <= 16:
            # Use the win_buf_alloc method for devices with a resolution <=
            # 16
            self.input_memhandle = ul.win_buf_alloc(total_count)
        else:
            # Use the win_buf_alloc_32 method for devices with a resolution
            # > 16
            self.input_memhandle = ul.win_buf_alloc_32(total_count)

        if not self.input_memhandle:
            messagebox.showerror("Error", "Failed to allocate memory")
            self.set_input_ui_idle_state()
            return

        # Create the frames that will hold the data
        self.recreate_input_data_frame()
        try:
            # Run the scan
            ul.a_in_scan(
                self.board_num, self.input_low_chan, self.input_high_chan,
                total_count, rate, range_, self.input_memhandle,
                scan_options)
        except ULError as e:
            self.show_ul_error(e)
            self.set_input_ui_idle_state()
            return

        # Convert the input_memhandle to a ctypes array
        # Note: the ctypes array will no longer be valid after win_buf_free is called.
        # A copy of the buffer can be created using win_buf_to_array
        # or win_buf_to_array_32 before the memory is freed. The copy can
        # be used at any time.
        if self.ai_props.resolution <= 16:
            # self.copied_array = ul.win_buf_to_array(self.iput_memhandle)
            # Use the memhandle_as_ctypes_array method for devices with a
            # resolution <= 16
            self.ctypes_array = self.memhandle_as_ctypes_array(
                self.input_memhandle)
        else:
            # Use the memhandle_as_ctypes_array_32 method for devices with a
            # resolution > 16
            self.ctypes_array = self.memhandle_as_ctypes_array_32(
                self.input_memhandle)

        # Start updating the displayed values
        self.update_input_displayed_values(range_)

        # Start the arena output
        self.tempo = 2.2
        self.update_arena_output()


    def update_input_displayed_values(self, range_):
        # Get the status from the device
        status, curr_count, curr_index = ul.get_status(
            self.board_num, FunctionType.AIFUNCTION)

        # Display the status info
        self.update_input_status_labels(status, curr_count, curr_index)

        # Update period if necessary
        self.update_input_period(curr_count)

        # Display the values
        self.display_input_values(range_, curr_index, curr_count)

        # Open the directory text file
        self.textfile = open("Rawtext.txt", "a+")  # textfile that the data will be written to

        # Function for the writing of the complete buffer to a text file and stopping the process
        if curr_count >= self.test_time() - 100:
            self.full_file()

        # Call this method again until the stop_input button is pressed
        if status == Status.RUNNING:
            self.after(10, self.update_input_displayed_values, range_)
        else:
            # Free the allocated memory
            ul.win_buf_free(self.input_memhandle)
            self.set_input_ui_idle_state()

    def update_input_status_labels(self, status, curr_count, curr_index):
        if status == Status.IDLE:
            self.input_status_label["text"] = "Idle"
        else:
            self.input_status_label["text"] = "Running"

        self.input_period_label["text"] = self.period
        self.input_index_label["text"] = str(curr_index)
        self.input_count_label["text"] = str(curr_count)

    def update_input_period(self, curr_count):
        if t.clock() > self.periodtimevar:
            # Beep(2000, 500)
            self.period += 1 # switch to next period
            self.periodtimevar = self.periodtimevar + self.periodtime
            self.period_switch.append(curr_count) # documentation of period switch

            if self.tempo == 1.8:
                print("twmpo", self.tempo)
                self.tempo = 2.2 # make it relative to input!!!!
            else:
                self.tempo = 1.8
            self.update_arena_output()

    def display_input_values(self, range_, curr_index, curr_count):
        per_channel_display_count = 1
        array = self.ctypes_array
        low_chan = self.input_low_chan
        high_chan = self.input_high_chan
        ULAIO01.channel_text = []

        # Add the headers
        for chan_num in range(low_chan, high_chan + 1):
            ULAIO01.channel_text.append("Channel " + str(chan_num) + "\n")

        # If no data has been gathered, don't add data to the labels
        if curr_count > 1:
            chan_count = high_chan - low_chan + 1

            chan_num = low_chan
            # curr_index points to the start_input of the last completed channel scan that
            # was transferred between the board and the data buffer. Based on this,
            # calculate the first index we want to display using subtraction.
            first_index = max(
                curr_index - ((per_channel_display_count - 1) * chan_count),
                0)
            # Add (up to) the latest 10 values for each channel to the text
            for data_index in range(
                    first_index,
                    first_index + min(chan_count * per_channel_display_count, curr_count)):
                raw_value = array[data_index]
                if self.ai_props.resolution <= 16:
                    ULAIO01.eng_value = ul.to_eng_units(
                        self.board_num, range_, raw_value)
                else:
                    ULAIO01.eng_value = ul.to_eng_units_32(
                        self.board_num, range_, raw_value)
                ULAIO01.channel_text[chan_num - low_chan] += (
                    '{:.3f}'.format(ULAIO01.eng_value) + "\n")
                self.datasheet() # custom datahandling

                if chan_num == high_chan:
                    chan_num = low_chan
                else:
                    chan_num += 1

        # Update the labels for each channel
        for chan_num in range(low_chan, high_chan + 1):
            ULAIO01.chan_index = chan_num - low_chan
            self.chan_labels[ULAIO01.chan_index]["text"] = ULAIO01.channel_text[ULAIO01.chan_index]

    def recreate_input_data_frame(self):
        low_chan = self.input_low_chan
        high_chan = self.input_high_chan

        new_data_frame = tk.Frame(self.input_inner_data_frame)

        self.chan_labels = []
        # Add the labels for each channel
        for chan_num in range(low_chan, high_chan + 1):
            chan_label = tk.Label(new_data_frame, justify=tk.LEFT, padx=3)
            chan_label.grid(row=0, column=chan_num - low_chan)
            self.chan_labels.append(chan_label)

        self.data_frame.destroy()
        self.data_frame = new_data_frame
        self.data_frame.grid()

    def exit(self):
        status, curr_count, curr_index = ul.get_status(
            self.board_num, FunctionType.AIFUNCTION)
        if status == status.RUNNING:
            self.full_file()
        else: # else just stop the arena (whether turning or not)
            self.tempo = 2
            self.update_arena_output()
        self.save_inputs()
        self.master.destroy()

    def save_inputs(self):
        self.save_firstname.text = str(self.input_firstname.get())

        self.save_lastname.text = str(self.input_lastname.get())

        self.save_orcid.text = str(self.input_orcid.get())

        self.save_flytype.text = str(self.input_flytype.get())

        self.save_flyname.text = str(self.input_flyname.get())

        self.save_flydescription.text = str(self.input_flydescription.get())

        self.save_experimenttype.text = str(self.input_experimenttype.get())

        self.save_experimentdescription.text = str(self.input_ExperimentDescription.get())

        self.save_filename.text = str(self.input_filename.get())

        self.save_samplingrate.text = str(self.input_Samplingrate.get())

        self.save_outcome.text = str(self.input_outcome.get())

        self.save_pattern.text = str(self.input_Pattern.get())

        self.save_lowchan.text = str(self.input_low_channel_entry.get())

        self.save_highchan.text = str(self.input_high_channel_entry.get())

        self.save_periodtime.text = str(self.periodbox.get())

        self.save_testtime.text = str(self.testtimebox.get())

        self.save_tree.write("Input_save.xml")

    def update_arena_output(self):
        channel = self.get_channel_num()
        ao_range = self.ao_props.available_ranges[0]
        data_value = self.get_speed()

        if self.tempo is not None:
            ULAIO01.output_value = ul.from_eng_units(self.board_num, ao_range, self.tempo)
        else:
            ULAIO01.output_value = ul.from_eng_units(self.board_num, ao_range, data_value)
            print(ULAIO01.output_value)

        try:
            ul.a_out(self.board_num, channel, ao_range, ULAIO01.output_value)
        except ULError as e:
            self.show_ul_error(e)

    def get_speed(self):
        try:
            return float(self.arena_speed_out.get())
        except ValueError:
            return 2 # 2 will put the arena to rest

    def get_channel_num(self):
        if self.ao_props.num_chans == 1:
            return 0
        try:
            return int(self.channel_entry.get())
        except ValueError:
            return 0

    def validate_channel_entry(self, p):
        if p == '':
            return True
        try:
            value = int(p)
            if(value < 0 or value > self.ao_props.num_chans - 1):
                return False
        except ValueError:
            return False

        return True


    def stop_input(self):
        self.tempo = 2 # stop turning arena
        self.update_arena_output()

        status, curr_count, curr_index = ul.get_status(
            self.board_num, FunctionType.AIFUNCTION)
        my_array = self.ctypes_array # save all the collected data
        ul.stop_background(self.board_num, FunctionType.AIFUNCTION)
        open("KHZtext.txt", "w")  # clear existing file
        endfile = open("KHZtext.txt", "a+")  # textfile that the data will be written to (kiloherztext)
        millisec = 0  # the time column parameter in milliseconds
        ULAIO01.txt_count = 0  # for the order of the KHZtext file
        self.period = 1
        print("count", curr_count)
        for i in list(range(0, curr_count)):  # curr_count should represent the length of the ctypes_array
            eng_value = ul.to_eng_units(
                self.board_num, self.ai_props.available_ranges[0], my_array[i])
            eng_value_proper = ("%f " % (
                eng_value))  # thats how it is supposed to be written into the txt file, but right now it isn't unicode
            endfile.write(eng_value_proper.decode(
                "unicode-escape"))  # eng_value returns float, but after (4) floats all channels are printed (also: encode to utf8 format)
            ULAIO01.txt_count = ULAIO01.txt_count + 1  # thats why we need the count (know when to newline)
            if self.period < len(self.period_switch) and i == self.period_switch[
                self.period-1]:  # when we iterated to the point where a new period was started, we need to switch the period parameter
                self.period = self.period + 1
                print("hat funktioniert", self.period)
            if ULAIO01.txt_count == ((self.input_high_chan - self.input_low_chan) + 1):
                endfile.write(u"%d %d\n" % (millisec, self.period))
                ULAIO01.txt_count = 0
                millisec = millisec + 10  # for each loop the next millisecond is measured
        Beep(3000, 500)

    def set_input_ui_idle_state(self):
        self.input_high_channel_entry["state"] = tk.NORMAL
        self.input_low_channel_entry["state"] = tk.NORMAL
        self.periodbox["state"] = tk.NORMAL
        self.testtimebox["state"] = tk.NORMAL
        self.input_start_button["command"] = self.start_input
        self.input_start_button["text"] = "Start Analog Input"

    def start_input(self):
        self.input_high_channel_entry["state"] = tk.DISABLED
        self.input_low_channel_entry["state"] = tk.DISABLED
        self.periodbox["state"] = tk.DISABLED
        self.testtimebox["state"] = tk.DISABLED
        #self.input_start_button["command"] = self.stop_input()
        if self.input_start_button["text"] == "Stop Analog Input":
            self.full_file()
            self.input_start_button["text"] = "Start Analog Input"
        else:
            self.input_start_button["text"] = "Stop Analog Input"
            self.start_input_scan()

    def get_input_low_channel_num(self):
        if self.ai_props.num_ai_chans == 1:
            return 0
        try:
            return int(self.input_low_channel_entry.get())
        except ValueError:
            return 0

    def get_input_high_channel_num(self):
        if self.ai_props.num_ai_chans == 1:
            return 0
        try:
            return int(self.input_high_channel_entry.get())
        except ValueError:
            return 0

    def get_output_low_channel_num(self):
        if self.ao_props.num_chans == 1:
            return 0
        try:
            return int(self.output_low_channel_entry.get())
        except ValueError:
            return 0

    def get_output_high_channel_num(self):
        if self.ao_props.num_chans == 1:
            return 0
        try:
            return int(self.output_high_channel_entry.get())
        except ValueError:
            return 0

    def validate_channel_entry(self, p):
        if p == '':
            return True
        try:
            value = int(p)
            if(value < 0 or value > self.ai_props.num_ai_chans - 1):
                return False
        except ValueError:
            return False

        return True

    # Function for preparing the textfile, which will be read by the live plotter
    def makecheck(self):
        ULAIO01.txt_count = 0 # for the txt file order
        open("Rawtext.txt", "w").close() # delete any existing contents of the rawtext file
        os.startfile("live_graph.pyc")
        global check # to recognise if the "write to xml" checkbox was clicked
        check="on"
        return check

    # Function for writing some data to the text file, which will be read by the live plotter
    def datasheet(self):
        try: # the try because there is no "check" if the checkbox hasn't been clicked
            if check == "on":
                eng_value_proper = ("%f " % (ULAIO01.eng_value))  # thats how it is supposed to be written into the txt file, but right now it isn't unicode
                self.textfile.write(eng_value_proper.decode("unicode-escape")) # eng_value returns float, but after (4) floats all channels are printed (also: encode to utf8 format)
                ULAIO01.txt_count = ULAIO01.txt_count + 1   # thats why we need the count (know when to newline)
                time = t.clock()    # for the time column
                if ULAIO01.txt_count == ((self.input_high_chan - self.input_low_chan) + 1):
                    self.textfile.write(u"%f %d\n" % (time, self.period))
                    ULAIO01.txt_count = 0
            else:
                print ("xml off")
        except NameError:
           return None

    # Function for writing all data to the text file, which will be used for the xml file
    def full_file(self):
        self.stop_input()


    # The process of writing the finished text file to the xml file
    def txt_to_xml(self):


        # del last line in KHZtext: (source: https://stackoverflow.com/questions/1877999/delete-final-line-in-file-with-python)

        file = open("KHZtext.txt", "r+")
        # Move the pointer (similar to a cursor in a text editor) to the end of the file.
        file.seek(0, os.SEEK_END)

        # This code means the following code skips the very last character in the file -
        # i.e. in the case the last line is null we delete the last line
        # and the penultimate one
        pos = file.tell() - 1

        # Read each character in the file one at a time from the penultimate
        # character going backwards, searching for a newline character
        # If we find a new line, exit the search
        while pos > 0 and file.read(1) != "\n":
            pos -= 1
            file.seek(pos, os.SEEK_SET)

        # So long as we're not at the start of the file, delete all the characters ahead of this position
        if pos > 0:
            file.seek(pos, os.SEEK_SET)
            file.truncate()


        status, curr_count, curr_index = ul.get_status(
            self.board_num, FunctionType.AOFUNCTION)
        if status == Status.IDLE:
            datafile = open("KHZtext.txt", "r") # text with periods for xml
            data = datafile.read()
            xml_name = self.input_filename.get() + ".xml"
            print(xml_name)
            target_folder = os.path.join(os.curdir, "AndersSoft")
            target_file = os.path.join(target_folder, "Optomotorics_blueprint.xml")
            xml_location = os.path.join(target_folder, xml_name)
            copy("Optomotorics_blueprint.xml", "AndersSoft")
            if os.path.exists(xml_location):
                print("warning")
                showwarning("Warning",
                            "The specified file already exists, rename the existing one NOW if overwriting should be avoided")
            move(target_file, xml_location)
            tree = et.parse(xml_location)#C:\Bachelor\FinishedSoft\

            self.firstname = tree.find("./metadata/experimenter/firstname")
            self.firstname.text = str(self.input_firstname.get())

            self.lastname = tree.find("./metadata/experimenter/lastname")
            self.lastname.text = str(self.input_lastname.get())

            self.orcid = tree.find("./metadata/experimenter/orcid")
            self.orcid.text = str(self.input_orcid.get())

            self.fly = tree.find("./metadata/fly")
            self.fly.attribute = str(self.input_flytype.get())

            self.fly_name = tree.find("./metadata/fly/name")
            self.fly_name.text = str(self.input_flyname.get())

            self.fly_description = tree.find("./metadata/fly/description")
            self.fly_description.text = str(self.input_flydescription.get())

            # x = tree.find("./metadata/experiment")
            # x.attribute = str(self.input_experimenttype

            self.experiment_dateTime = tree.find("./metadata/experiment/dateTime")
            self.experiment_dateTime.text = str(self.input_dateTime.get())

            self.experiment_duration = tree.find("./metadata/experiment/duration")
            self.experiment_duration.text = str(self.durationtime())

            self.experiment_description = tree.find("./metadata/experiment/description")
            self.experiment_description.text = str(self.input_ExperimentDescription.get())

            self.sample_rate = tree.find("./metadata/experiment/sample_rate")
            self.sample_rate.text = str(self.input_Samplingrate.get())

            self.sequences = int(int(self.testtimebox.get()) * 60 / int(self.periodbox.get())) + 1
            sequence = tree.find("./sequence")
            sequence.attribute = self.sequences

            # perioddescription
            for i in list(range(1, self.sequences)):
                period = et.SubElement(sequence, "period")
                period.set("number", "%d" %i)
                print(et.tostring(period))
                if i % 2 == 0:
                    type = et.SubElement(period, "type")
                    type.text = "OptomotorR"
                else:
                    type = et.SubElement(period, "type")
                    type.text = "OptomotorL"
                duration = et.SubElement(period, "duration")
                duration.text = str(self.periodbox.get())
                outcome = et.SubElement(period, "outcome")
                outcome.text = str(self.input_outcome.get())
                pattern = et.SubElement(period, "pattern")
                pattern.text = str(self.input_Pattern.get())


            csv = tree.find("./timeseries/csv_data")  # adress the right spot for the data
            csv.text = data  # implement the data in the xml
            tree.write(xml_location)

        file.close()

    def restart_program(self): # source: https://www.daniweb.com/programming/software-development/code/260268/restart-your-python-program
        """Restarts the current program.
        Note: this function does not return. Any cleanup action (like
        saving data) must be done before calling this function."""
        python = sys.executable
        os.execl(python, python, *sys.argv)


    # small function for test time calculus
    def test_time(self):
        self.testtime = self.num_input_chans * 60 * 100 * int(self.testtimebox.get())  # variable of the duration in sec
        # (number of channels) * 60 (minute to sec)* 1000 (sec to millisec)
        while self.testtime % 31 != 0:  # the variable has to be divisible by 31 (COUNTINOUS mode restriction)
            self.testtime += 1
        return self.testtime

    def duration_time(self):
        self.durationtime =60 * int(self.testtimebox.get())  # Multiply the total duration with 60 to get seconds.
        # Will be used later to fill the xml sheet.
        return self.durationtime

    def give_curr_count(self):
        status, curr_count, curr_index = ul.get_status(
            self.board_num, FunctionType.AOFUNCTION)
        return curr_count

    def create_widgets(self):
        '''Create the tkinter UI'''
        example_supported = (
            self.ao_props.num_chans > 0
            and self.ao_props.supports_scan
            and self.ai_props.num_ai_chans > 0
            and self.ai_props.supports_scan)

        if example_supported:
            self.save_tree = et.parse("Input_save.xml") # load the latest input
            print(self.save_tree.find("./input/firstname"), "save")

            channel_vcmd = self.register(self.validate_channel_entry)

            main_frame = tk.Frame(self)
            main_frame.pack(fill=tk.X, anchor=tk.NW)

            input_groupbox = tk.LabelFrame(main_frame, text="Analog Input")
            input_groupbox.pack(side=tk.LEFT, anchor=tk.NW)

            if self.ai_props.num_ai_chans > 1:
                curr_row = 0

                input_channels_frame = tk.Frame(input_groupbox)
                input_channels_frame.pack(fill=tk.X, anchor=tk.NW)

                input_low_channel_entry_label = tk.Label(
                    input_channels_frame)
                input_low_channel_entry_label["text"] = (
                    "Low Channel Number:")
                input_low_channel_entry_label.grid(
                    row=curr_row, column=0, sticky=tk.W)

                self.input_low_channel_entry = tk.Spinbox(
                    input_channels_frame, from_=0,
                    to=max(self.ai_props.num_ai_chans - 1, 0),
                    validate='key', validatecommand=(channel_vcmd, '%P'))
                self.save_lowchan = self.save_tree.find("./input/lowchan") # load latest input
                self.input_low_channel_entry.delete(0, tk.END) # clear the entry
                self.input_low_channel_entry.insert(int(self.save_lowchan.text), self.save_lowchan.text)
                self.input_low_channel_entry.grid(
                    row=curr_row, column=1, sticky=tk.W)

                curr_row += 1
                input_high_channel_entry_label = tk.Label(
                    input_channels_frame)
                input_high_channel_entry_label["text"] = (
                    "High Channel Number:")
                input_high_channel_entry_label.grid(
                    row=curr_row, column=0, sticky=tk.W)

                self.input_high_channel_entry = tk.Spinbox(
                    input_channels_frame, from_=0,
                    to=max(self.ai_props.num_ai_chans - 1, 0),
                    validate='key', validatecommand=(channel_vcmd, '%P'))
                self.save_highchan = self.save_tree.find("./input/highchan") # load latest input
                self.input_high_channel_entry.delete(0, tk.END) # clear the entry
                self.input_high_channel_entry.insert(int(self.save_highchan.text), self.save_highchan.text)
                self.input_high_channel_entry.grid(
                    row=curr_row, column=1, sticky=tk.W)


                curr_row += 1

                # selfmade, for length of period choice
                periodbox_label = tk.Label(
                    input_channels_frame)
                periodbox_label["text"] = ("Time per period (sec):")
                periodbox_label.grid(row=curr_row, column=0, sticky=tk.W)

                self.periodbox = tk.Spinbox(
                    input_channels_frame,
                    from_=10,
                    to=500,
                    increment=5,
                    validate='key', validatecommand=(channel_vcmd, '%P'))
                self.save_periodtime = self.save_tree.find("./input/periodtime") # load latest input
                self.periodbox.delete(0, tk.END) # clear the entry
                self.periodbox.insert(int(self.save_periodtime.text), self.save_periodtime.text)
                self.periodbox.grid(
                    row=curr_row, column=1, sticky=tk.W)

                curr_row += 1

                # selfmade, for length of test time choice
                testtime_label = tk.Label(
                    input_channels_frame)
                testtime_label["text"] = ("Test time overall (min):")
                testtime_label.grid(row=curr_row, column=0, sticky=tk.W)

                self.testtimebox = tk.Spinbox(
                    input_channels_frame,
                    from_=0,
                    to=100,
                    increment=1,
                    validate='key')
                self.save_testtime = self.save_tree.find("./input/testtime") # load latest input
                self.testtimebox.delete(0, tk.END) # clear the entry
                self.testtimebox.insert(int(self.save_testtime.text), self.save_testtime.text)
                self.testtimebox.grid(
                    row=curr_row, column=1, sticky=tk.W)


            # selfmade, for datasheet option (source: effbot tkinter checkbutton)
            self.checkmarker = tk.Checkbutton(
                input_groupbox,
                text="Write to TXT and plot live graph",
                command=self.makecheck)
            self.checkmarker.pack(anchor=tk.NW, side=tk.TOP)



            self.txt_to_xml_button = tk.Button(input_groupbox)
            self.txt_to_xml_button["text"] = "Transfer data to XML (only when IDLE)"
            self.txt_to_xml_button["command"] = self.txt_to_xml
            self.txt_to_xml_button.pack(
                anchor=tk.NW, side=tk.TOP)



            self.input_start_button = tk.Button(input_groupbox)
            self.input_start_button["text"] = "Start Analog Input"
            self.input_start_button["command"] = self.start_input
            self.input_start_button.pack(
                fill=tk.X, anchor=tk.NW, padx=3, pady=3)

            self.input_results_group = tk.LabelFrame(
                input_groupbox, text="Results", padx=3, pady=3)
            self.input_results_group.pack(
                fill=tk.X, anchor=tk.NW, padx=3, pady=3)

            self.input_results_group.grid_columnconfigure(1, weight=1)

            curr_row = 0
            input_status_left_label = tk.Label(self.input_results_group)
            input_status_left_label["text"] = "Status:"
            input_status_left_label.grid(
                row=curr_row, column=0, sticky=tk.W)

            self.input_status_label = tk.Label(self.input_results_group)
            self.input_status_label["text"] = "Idle"
            self.input_status_label.grid(
                row=curr_row, column=1, sticky=tk.W)

            curr_row += 1
            input_period_left_label = tk.Label(self.input_results_group)
            input_period_left_label["text"] = "Period:"
            input_period_left_label.grid(row=curr_row, column=0, sticky=tk.W)

            self.input_period_label = tk.Label(self.input_results_group)
            self.input_period_label["text"] = "-1"
            self.input_period_label.grid(row=curr_row, column=1, sticky=tk.W)

            curr_row += 1
            input_index_left_label = tk.Label(self.input_results_group)
            input_index_left_label["text"] = "Index:"
            input_index_left_label.grid(row=curr_row, column=0, sticky=tk.W)

            self.input_index_label = tk.Label(self.input_results_group)
            self.input_index_label["text"] = "-1"
            self.input_index_label.grid(row=curr_row, column=1, sticky=tk.W)

            curr_row += 1
            input_count_left_label = tk.Label(self.input_results_group)
            input_count_left_label["text"] = "Count:"
            input_count_left_label.grid(row=curr_row, column=0, sticky=tk.W)

            self.input_count_label = tk.Label(self.input_results_group)
            self.input_count_label["text"] = "0"
            self.input_count_label.grid(row=curr_row, column=1, sticky=tk.W)

            curr_row += 1
            self.input_inner_data_frame = tk.Frame(self.input_results_group)
            self.input_inner_data_frame.grid(
                row=curr_row, column=0, columnspan=2, sticky=tk.W)

            self.data_frame = tk.Frame(self.input_inner_data_frame)
            self.data_frame.grid()


            ########## METADATA ###########################

            xml_groupbox = tk.LabelFrame(
                main_frame, text="Metadata")
            xml_groupbox.pack(side=tk.LEFT, anchor=tk.NW)
            curr_row = 0

            label = tk.Label(xml_groupbox, text = "Firstname")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_firstname = tk.Entry(xml_groupbox)
            self.input_firstname.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_firstname = self.save_tree.find("./input/firstname") # load the latest input
            self.input_firstname.insert(0, self.save_firstname.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Lastname")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_lastname = tk.Entry(xml_groupbox)
            self.input_lastname.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_lastname = self.save_tree.find("./input/lastname") # load the latest input
            self.input_lastname.insert(0, self.save_lastname.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="orcid ID")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_orcid = tk.Entry(xml_groupbox)
            self.input_orcid.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_orcid = self.save_tree.find("./input/orcid") # load the latest input
            self.input_orcid.insert(0, self.save_orcid.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Flytype")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_flytype = tk.Entry(xml_groupbox)
            self.input_flytype.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_flytype = self.save_tree.find("./input/flytype") # load the latest input
            self.input_flytype.insert(0, self.save_flytype.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Flyname")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_flyname = tk.Entry(xml_groupbox)
            self.input_flyname.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_flyname = self.save_tree.find("./input/flyname") # load the latest input
            self.input_flyname.insert(0, self.save_flyname.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Flydescription")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_flydescription = tk.Entry(xml_groupbox)
            self.input_flydescription.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_flydescription = self.save_tree.find("./input/flydescription") # load the latest input
            self.input_flydescription.insert(0, self.save_flydescription.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Experimenttype")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_experimenttype = tk.Entry(xml_groupbox)
            self.input_experimenttype.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_experimenttype = self.save_tree.find("./input/experimenttype") # load the latest input
            self.input_experimenttype.insert(0, self.save_experimenttype.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Date and Time")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_dateTime = tk.Entry(xml_groupbox)
            self.input_dateTime.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_dateTime.insert(0, datetime.now().isoformat()) # display current datetime

            # curr_row += 1
            # label = tk.Label(xml_groupbox, text="Period Duration")
            # label.grid(row=curr_row, column=1, sticky=tk.W)
            # self.input_duration = tk.Entry(xml_groupbox)
            # self.input_duration.grid(row=curr_row, column=2, sticky=tk.W)
            # self.input_duration.insert(20, "20")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Experiment Description")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_ExperimentDescription = tk.Entry(xml_groupbox)
            self.input_ExperimentDescription.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_experimentdescription = self.save_tree.find("./input/experimentdescription") # load the latest input
            self.input_ExperimentDescription.insert(0, self.save_experimentdescription.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="File Name")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_filename = tk.Entry(xml_groupbox)
            self.input_filename.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_filename = self.save_tree.find("./input/filename") # load the latest input
            self.input_filename.insert(0, self.save_filename.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Samplingrate(Hz)")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_Samplingrate = tk.Entry(xml_groupbox)
            self.input_Samplingrate.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_samplingrate = self.save_tree.find("./input/samplingrate") # load the latest input
            self.input_Samplingrate.insert(int(self.save_samplingrate.text), self.save_samplingrate.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Outcome (number)")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_outcome = tk.Entry(xml_groupbox)
            self.input_outcome.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_outcome = self.save_tree.find("./input/outcome") # load the latest input
            self.input_outcome.insert(int(self.save_outcome.text), self.save_outcome.text)

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Pattern(number)")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_Pattern = tk.Entry(xml_groupbox)
            self.input_Pattern.grid(row=curr_row, column=2, sticky=tk.W)
            self.save_pattern = self.save_tree.find("./input/pattern") # load the latest input
            self.input_Pattern.insert(int(self.save_pattern.text), self.save_pattern.text)

            ####################### OUTPUT #############################

            output_groupbox = tk.LabelFrame(
                main_frame, text="Analog Output")
            output_groupbox.pack(side=tk.RIGHT, anchor=tk.NW)

            channel_vcmd = self.register(self.validate_channel_entry)
            float_vcmd = self.register(self.validate_float_entry)

            curr_row = 0
            if self.ao_props.num_chans > 1:
                channel_vcmd = self.register(self.validate_channel_entry)

                channel_entry_label = tk.Label(output_groupbox)
                channel_entry_label["text"] = "Channel Number:"
                channel_entry_label.grid(
                    row=curr_row, column=0, sticky=tk.W)

                self.channel_entry = tk.Spinbox(
                    output_groupbox, from_=0,
                    to=max(self.ao_props.num_chans - 1, 0),
                    validate='key', validatecommand=(channel_vcmd, '%P'))
                self.channel_entry.grid(
                    row=curr_row, column=1, sticky=tk.W)
                self.channel_entry.insert(1, "1")
                self.channel_entry["state"] = tk.DISABLED

                curr_row += 1

            units_text = self.ao_props.get_units_string(
                self.ao_props.available_ranges[0])
            # value_label_text = "Value (" + units_text + "):"
            value_label_text = "Arena Speed:"
            data_value_label = tk.Label(output_groupbox)
            data_value_label["text"] = value_label_text
            data_value_label.grid(row=curr_row, column=0, sticky=tk.W)
            #
            # self.data_value_entry = tk.Entry(
            #     output_groupbox, validate='key', validatecommand=(float_vcmd, '%P'))
            # self.data_value_entry.grid(row=curr_row, column=1, sticky=tk.W)
            # self.data_value_entry.insert(2, "2")

            self.arena_speed_out = tk.StringVar(output_groupbox)
            self.arena_speed_out.set("slow")
            self.arena_speed_out_options = tk.OptionMenu(
                output_groupbox, self.arena_speed_out, "very slow", "slow", "medium")
            self.arena_speed_out_options.grid(row=curr_row, column=1, sticky=tk.W)


            update_button = tk.Button(output_groupbox)
            update_button["text"] = "Update"
            update_button["command"] = self.update_arena_output
            update_button.grid(row=curr_row, column=2, padx=3, pady=3)

            button_frame = tk.Frame(self)
            button_frame.pack(fill=tk.X, side=tk.RIGHT, anchor=tk.SE)

            self.quit_button = tk.Button(button_frame)
            self.quit_button["text"] = "Quit"
            self.quit_button["command"] = self.exit
            self.quit_button.grid(row=0, column=2, padx=3, pady=3)

            self.restart_button = tk.Button(button_frame)
            self.restart_button["text"] = "Restart"
            self.restart_button["command"] = self.restart_program
            self.restart_button.grid(row=0, column=1, padx=3, pady=3)
        else:
            self.create_unsupported_widgets(self.board_num)


if __name__ == "__main__":
    # Start the example
    ULAIO01(master=tk.Tk()).mainloop()
