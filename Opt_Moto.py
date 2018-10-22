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

class ULAIO01(UIExample):
    def __init__(self, master=None):
        super(ULAIO01, self).__init__(master)

        self.period = 0
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

            if self.period == 1:
                self.tempo = ULAIO01.output_value
            # self.tempo = self.tempo * -1
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
        else: self.stop_input()
        # self.stop_output()
        self.master.destroy()



    def update_arena_output(self):
        channel = self.get_channel_num()
        ao_range = self.ao_props.available_ranges[0]
        data_value = self.get_data_value()

        if self.tempo is not None:
            ULAIO01.output_value = self.tempo
        else:
            ULAIO01.output_value = ul.from_eng_units(self.board_num, ao_range, data_value)

        try:
            ul.a_out(self.board_num, channel, ao_range, ULAIO01.output_value)
        except ULError as e:
            self.show_ul_error(e)

    def get_data_value(self):
        try:
            return float(self.data_value_entry.get())
        except ValueError:
            return 0

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

    #
    #
    # def start_output_scan(self):
    #     # Build the data array
    #     self.output_low_chan = self.get_output_low_channel_num()
    #     self.output_high_chan = self.get_output_high_channel_num()
    #     self.num_output_chans = (
    #         self.output_high_chan - self.output_low_chan + 1)
    #
    #     if self.output_low_chan > self.output_high_chan:
    #         messagebox.showerror(
    #             "Error",
    #             "Low Channel Number must be greater than or equal to High "
    #             "Channel Number")
    #         self.set_ui_idle_state()
    #         return
    #
    #     points_per_channel = 992
    #     rate = 992
    #     num_points = self.num_output_chans * points_per_channel
    #     scan_options = (ScanOptions.BACKGROUND |
    #                     ScanOptions.CONTINUOUS | ScanOptions.SCALEDATA)
    #     ao_range = self.ao_props.available_ranges[0]
    #     print("ao range", ao_range)
    #
    #     self.output_memhandle = ul.scaled_win_buf_alloc(num_points)
    #
    #     # Check if the buffer was successfully allocated
    #     if not self.output_memhandle:
    #         messagebox.showerror("Error", "Failed to allocate memory")
    #         self.start_button["state"] = tk.NORMAL
    #         return
    #
    #     try:
    #         data_array = self.memhandle_as_ctypes_array_scaled(
    #             self.output_memhandle)
    #         frequencies = self.add_output_example_data(
    #             data_array, ao_range, self.num_output_chans, rate,
    #             points_per_channel)
    #         print("freq", frequencies)
    #         self.recreate_freq_frame()
    #         self.display_output_signal_info(frequencies)
    #
    #         ul.a_out_scan(
    #             self.board_num, self.output_low_chan, self.output_high_chan,
    #             num_points, rate, ao_range, self.output_memhandle,
    #             scan_options)
    #
    #         # Start updating the displayed values
    #         self.update_output_displayed_values()
    #     except ULError as e:
    #         self.show_ul_error(e)
    #         self.stop_output()
    #         return
    #
    # def display_output_signal_info(self, frequencies):
    #     for channel_num in range(
    #             self.output_low_chan, self.output_high_chan + 1):
    #         curr_row = channel_num - self.output_low_chan
    #         self.freq_labels[curr_row]["text"] = str(
    #             frequencies[curr_row]) + " Hz"
    #
    # def add_output_example_data(self, data_array, ao_range, num_chans,
    #                             rate, points_per_channel):
    #     # Calculate frequencies that will work well with the size of the array
    #     frequencies = []
    #     for channel_num in range(0, num_chans):
    #         frequencies.append(
    #             (channel_num + 1) / (points_per_channel / rate))
    #
    #     # Calculate an amplitude and y-offset for the signal
    #     # to fill the analog output range
    #     amplitude = (ao_range.range_max - ao_range.range_min) / 2
    #     y_offset = (amplitude + ao_range.range_min) / 2
    #
    #     # Fill the array with sine wave data at the calculated frequencies.
    #     # Note that since we are using the SCALEDATA option, the values
    #     # added to data_array are the actual voltage values that the device
    #     # will output
    #     data_index = 0
    #     for point_num in range(0, points_per_channel):
    #         for channel_num in range(0, num_chans):
    #             freq = frequencies[channel_num]
    #             value = amplitude * math.sin(
    #                 2 * math.pi * freq * point_num / rate) + y_offset
    #             data_array[data_index] = value
    #             data_index += 1
    #
    #     print(frequencies)
    #     return frequencies
    #
    # def update_output_displayed_values(self):
    #     # Get the status from the device
    #     status, curr_count, curr_index = ul.get_status(
    #         self.board_num, FunctionType.AOFUNCTION)
    #
    #     # Display the status info
    #     self.update_output_status_labels(status, curr_count, curr_index)
    #
    #     # Call this method again until the stop button is pressed
    #     if status == Status.RUNNING:
    #         self.after(100, self.update_output_displayed_values)
    #     else:
    #         # Free the allocated memory
    #         ul.win_buf_free(self.output_memhandle)
    #         self.set_output_ui_idle_state()
    #
    # def update_output_status_labels(self, status, curr_count, curr_index):
    #     if status == Status.IDLE:
    #         self.output_status_label["text"] = "Idle"
    #     else:
    #         self.output_status_label["text"] = "Running"
    #
    #     self.output_index_label["text"] = str(curr_index)
    #     self.output_count_label["text"] = str(curr_count)
    #
    # def recreate_freq_frame(self):
    #     low_chan = self.output_low_chan
    #     high_chan = self.output_high_chan
    #
    #     new_freq_frame = tk.Frame(self.freq_inner_frame)
    #
    #     curr_row = 0
    #     self.freq_labels = []
    #     for chan_num in range(low_chan, high_chan + 1):
    #         curr_row += 1
    #         channel_label = tk.Label(new_freq_frame)
    #         channel_label["text"] = (
    #             "Channel " + str(chan_num) + " Frequency:")
    #         channel_label.grid(row=curr_row, column=0, sticky=tk.W)
    #
    #         freq_label = tk.Label(new_freq_frame)
    #         freq_label.grid(row=curr_row, column=1, sticky=tk.W)
    #         self.freq_labels.append(freq_label)
    #
    #     self.freq_frame.destroy()
    #     self.freq_frame = new_freq_frame
    #     self.freq_frame.grid()
    #
    # def stop_output(self):
    #     ul.stop_background(self.board_num, FunctionType.AOFUNCTION)
    #
    # def set_output_ui_idle_state(self):
    #     self.output_high_channel_entry["state"] = tk.NORMAL
    #     self.output_low_channel_entry["state"] = tk.NORMAL
    #     self.output_start_button["command"] = self.start_output
    #     self.output_start_button["text"] = "Start Analog Output"
    #
    # def start_output(self):
    #     self.output_high_channel_entry["state"] = tk.DISABLED
    #     self.output_low_channel_entry["state"] = tk.DISABLED
    #     self.output_start_button["command"] = self.stop_output
    #     self.output_start_button["text"] = "Stop Analog Output"
    #     self.start_output_scan()

    def stop_input(self):
        status, curr_count, curr_index = ul.get_status(
            self.board_num, FunctionType.AIFUNCTION)
        my_array = self.ctypes_array
        ul.stop_background(self.board_num, FunctionType.AIFUNCTION)
        open("KHZtext.txt", "w")  # clear existing file
        endfile = open("KHZtext.txt", "a+")  # textfile that the data will be written to (kiloherztext)
        millisec = 0  # the time column parameter in milliseconds
        ULAIO01.txt_count = 0  # for the order of the KHZtext file
        self.period = 0
        print("periodsw", self.period_switch)
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
                self.period]:  # when we iterated to the point where a new period was started, we need to switch the period parameter
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
            xml_name = self.input_ExperimentDescription.get() + ".xml"
            print(xml_name)
            target_folder = os.path.join(os.curdir, "AndersSoft")
            target_file = os.path.join(target_folder, "Optomotorics_blueprint.xml")
            xml_location = os.path.join(target_folder, xml_name)
            copy("Optomotorics_blueprint.xml", "AndersSoft")
            move(target_file, xml_location)
            tree = et.parse(xml_location)#C:\Bachelor\FinishedSoft\

            x = tree.find("./metadata/experimenter/firstname")
            x.text = str(self.input_firstname.get())
            print(x.text)

            x = tree.find("./metadata/experimenter/lastname")
            x.text = str(self.input_lastname.get())

            x = tree.find("./metadata/fly")
            x.attribute = str(self.input_flytype.get())

            x = tree.find("./metadata/fly/name")
            x.text = str(self.input_flyname.get())

            x = tree.find("./metadata/fly/description")
            x.text = str(self.input_flydescription.get())

            # x = tree.find("./metadata/experiment")
            # x.attribute = str(self.input_experimenttype

            x = tree.find("./metadata/experiment/dateTime")
            x.text = str(self.input_dateTime.get())

            x = tree.find("./metadata/experiment/duration")
            x.text = str(self.input_duration.get())

            x = tree.find("./metadata/experiment/description")
            x.text = str(self.input_ExperimentDescription.get())

            x = tree.find("./metadata/experiment/sample_rate")
            x.text = str(self.input_Samplingrate.get())

            self.sequences = int(int(self.testtimebox.get()) * 60 / int(self.periodbox.get())) + 1
            sequence = tree.find("./sequence")
            sequence.attribute = self.sequences

            # perioddescription
            # for period in sequence:
            #     if period.attribute > self.sequences:
            #         sequence.remove(period)
            #     if period.attribute % 2 == 0:
            #         type = et.SubElement(period, "type")
            #         type.text = "OptomotoR"
            #     else:
            #         type = et.SubElement(period, "type")
            #         type.text = "OptomotoL"
            #     duration = et.SubElement(period, "duration")
            #     duration.text = self.periodtime
            #     outcome = et.SubElement(period, "outcome")
            #     outcome.text = self.outcome
            #     pattern = et.SubElement(period, "pattern")
            #     pattern.text = self.pattern
            for i in list(range(1, self.sequences)):
                period = et.SubElement(sequence, "period")
                period.set("number", "%d" %i)
                print(et.tostring(period))
                if i % 2 == 0:
                    type = et.SubElement(period, "type")
                    type.text = "OptomotoR"
                else:
                    type = et.SubElement(period, "type")
                    type.text = "OptomotoL"
                duration = et.SubElement(period, "duration")
                duration.text = str(self.periodbox.get())
                # outcome = et.SubElement(period, "outcome")
                # outcome.text = self.outcome
                pattern = et.SubElement(period, "pattern")
                pattern.text = str(self.input_Pattern.get())


            csv = tree.find("./timeseries/csv_data")  # adress the right spot for the data
            csv.text = data  # implement the data in the xml
            tree.write(xml_location)

        file.close()


    # small function for test time calculus
    def test_time(self):
        self.testtime = self.num_input_chans * 60 * 100 * int(self.testtimebox.get())  # variable of the duration in sec
        # (number of channels) * 60 (minute to sec)* 1000 (sec to millisec)
        while self.testtime % 31 != 0:  # the variable has to be divisible by 31 (COUNTINOUS mode restriction)
            self.testtime += 1
        return self.testtime

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
                    textvariable="1",
                    validate='key', validatecommand=(channel_vcmd, '%P'))
                self.input_high_channel_entry.grid(
                    row=curr_row, column=1, sticky=tk.W)
                initial_value = min(self.ai_props.num_ai_chans - 1, 3)
                self.input_high_channel_entry.delete(0, tk.END)
                self.input_high_channel_entry.insert(0, "0")#str(initial_value)


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
                    validate='key', validatecommand=(channel_vcmd, '%P'))
                self.testtimebox.insert(1, "1")
                # self.testtimevar = self.testtime # a placeholder of testtime which can be changed
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
            self.input_firstname.insert(0, "Maximilian")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Lastname")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_lastname = tk.Entry(xml_groupbox)
            self.input_lastname.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_lastname.insert(0, "von der Linde")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Flytype")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_flytype = tk.Entry(xml_groupbox)
            self.input_flytype.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_flytype.insert(0, "control")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Flyname")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_flyname = tk.Entry(xml_groupbox)
            self.input_flyname.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_flyname.insert(0, "Wildtype Berlin")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Flydescription")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_flydescription = tk.Entry(xml_groupbox)
            self.input_flydescription.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_flydescription.insert(0, "wildtype")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Experimenttype")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_Optomotor = tk.Entry(xml_groupbox)
            self.input_Optomotor.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_Optomotor.insert(0, "Optomotor")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Date and Time")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_dateTime = tk.Entry(xml_groupbox)
            self.input_dateTime.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_dateTime.insert(0, "20018-10-10T15:15:15")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Period Duration")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_duration = tk.Entry(xml_groupbox)
            self.input_duration.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_duration.insert(30, "30")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Experiment Description and file name")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_ExperimentDescription = tk.Entry(xml_groupbox)
            self.input_ExperimentDescription.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_ExperimentDescription.insert(0, "Optmo_closedLoop")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Samplingrate(Hz)")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_Samplingrate = tk.Entry(xml_groupbox)
            self.input_Samplingrate.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_Samplingrate.insert(100, "100")

            curr_row += 1
            label = tk.Label(xml_groupbox, text="Pattern(number)")
            label.grid(row=curr_row, column=1, sticky=tk.W)
            self.input_Pattern = tk.Entry(xml_groupbox)
            self.input_Pattern.grid(row=curr_row, column=2, sticky=tk.W)
            self.input_Pattern.insert(4, "4")


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

                curr_row += 1

            units_text = self.ao_props.get_units_string(
                self.ao_props.available_ranges[0])
            value_label_text = "Value (" + units_text + "):"
            data_value_label = tk.Label(output_groupbox)
            data_value_label["text"] = value_label_text
            data_value_label.grid(row=curr_row, column=0, sticky=tk.W)

            self.data_value_entry = tk.Entry(
                output_groupbox, validate='key', validatecommand=(float_vcmd, '%P'))
            self.data_value_entry.grid(row=curr_row, column=1, sticky=tk.W)
            self.data_value_entry.insert(3, "3")

            update_button = tk.Button(output_groupbox)
            update_button["text"] = "Update"
            update_button["command"] = self.update_arena_output
            update_button.grid(row=curr_row, column=2, padx=3, pady=3)


            # # if self.ao_props.num_chans > 1:
            # #     curr_row = 0
            # #     output_channels_frame = tk.Frame(output_groupbox)
            # #     output_channels_frame.pack(fill=tk.X, anchor=tk.NW)
            # #
            # #     output_low_channel_entry_label = tk.Label(
            # #         output_channels_frame)
            # #     output_low_channel_entry_label["text"] = (
            # #         "Low Channel Number:")
            # #     output_low_channel_entry_label.grid(
            # #         row=curr_row, column=0, sticky=tk.W)
            # #
            # #     self.output_low_channel_entry = tk.Spinbox(
            # #         output_channels_frame, from_=0,
            # #         to=max(self.ao_props.num_chans - 1, 0),
            # #         validate='key', validatecommand=(channel_vcmd, '%P'))
            # #     self.output_low_channel_entry.grid(
            # #         row=curr_row, column=1, sticky=tk.W)
            # #
            # #     curr_row += 1
            # #     output_high_channel_entry_label = tk.Label(
            # #         output_channels_frame)
            # #     output_high_channel_entry_label["text"] = (
            # #         "High Channel Number:")
            # #     output_high_channel_entry_label.grid(
            # #         row=curr_row, column=0, sticky=tk.W)
            # #
            # #     self.output_high_channel_entry = tk.Spinbox(
            # #         output_channels_frame, from_=0,
            # #         to=max(self.ao_props.num_chans - 1, 0),
            # #         validate='key', validatecommand=(channel_vcmd, '%P'))
            # #     self.output_high_channel_entry.grid(
            # #         row=curr_row, column=1, sticky=tk.W)
            # #     initial_value = min(self.ao_props.num_chans - 1, 3)
            # #     self.output_high_channel_entry.delete(0, tk.END)
            # #     self.output_high_channel_entry.insert(0, str(initial_value))
            #
            # self.output_start_button = tk.Button(output_groupbox)
            # self.output_start_button["text"] = "Start Analog Output"
            # self.output_start_button["command"] = self.start_output
            # self.output_start_button.pack(
            #     fill=tk.X, anchor=tk.NW, padx=3, pady=3)
            #
            # output_scan_info_group = tk.LabelFrame(
            #     output_groupbox, text="Scan Information", padx=3, pady=3)
            # output_scan_info_group.pack(
            #     fill=tk.X, anchor=tk.NW, padx=3, pady=3)
            #
            # output_scan_info_group.grid_columnconfigure(1, weight=1)
            #
            # curr_row = 0
            # output_status_left_label = tk.Label(output_scan_info_group)
            # output_status_left_label["text"] = "Status:"
            # output_status_left_label.grid(
            #     row=curr_row, column=0, sticky=tk.W)
            #
            # self.output_status_label = tk.Label(output_scan_info_group)
            # self.output_status_label["text"] = "Idle"
            # self.output_status_label.grid(
            #     row=curr_row, column=1, sticky=tk.W)
            #
            # curr_row += 1
            # output_index_left_label = tk.Label(output_scan_info_group)
            # output_index_left_label["text"] = "Index:"
            # output_index_left_label.grid(
            #     row=curr_row, column=0, sticky=tk.W)
            #
            # self.output_index_label = tk.Label(output_scan_info_group)
            # self.output_index_label["text"] = "-1"
            # self.output_index_label.grid(
            #     row=curr_row, column=1, sticky=tk.W)
            #
            # curr_row += 1
            # output_count_left_label = tk.Label(output_scan_info_group)
            # output_count_left_label["text"] = "Count:"
            # output_count_left_label.grid(
            #     row=curr_row, column=0, sticky=tk.W)
            #
            # self.output_count_label = tk.Label(output_scan_info_group)
            # self.output_count_label["text"] = "0"
            # self.output_count_label.grid(
            #     row=curr_row, column=1, sticky=tk.W)
            #
            # curr_row += 1
            # self.freq_inner_frame = tk.Frame(output_scan_info_group)
            # self.freq_inner_frame.grid(
            #     row=curr_row, column=0, columnspan=2, sticky=tk.W)
            #
            # self.freq_frame = tk.Frame(self.freq_inner_frame)
            # self.freq_frame.grid()

            button_frame = tk.Frame(self)
            button_frame.pack(fill=tk.X, side=tk.RIGHT, anchor=tk.SE)

            self.quit_button = tk.Button(button_frame)
            self.quit_button["text"] = "Quit"
            self.quit_button["command"] = self.exit
            self.quit_button.grid(row=0, column=1, padx=3, pady=3)
        else:
            self.create_unsupported_widgets(self.board_num)


if __name__ == "__main__":
    # Start the example
    ULAIO01(master=tk.Tk()).mainloop()
