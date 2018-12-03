# Optomotorics-Bachelor-Thesis

This project is part of my Bachelor Thesis in Biology. The Opt_Moto code runs a machine desinged to test optomotoric walking behavior in fruit flies. Data is being aquired through an Analog/Digital-Converter which receives a signal from a sensor controlled by the fly and another signal from the arena turning around the fly. 
For further information on the topic see my Bachelor Thesis " " (LINK)

3 primary programs:
1. Opt_Moto.py: 
- modified version of the ULAIO01.py program from the mcculw library
- 
- succedes in writing some of the input directly to a text document called "rawtext.txt" in real time, which can be used by the following program for live real time plotting
- writes a more accurate list of the collected data at the end of one run to "KHZtext.txt" and then to a user specified xml document
- The UI allows the user to control the experiment and specify the metadata to then create a xml file which can be used for further examination

2. live_graph.py:
- takes data from rawdata.txt, stores it and shows at most 150 datapoints from the fly position and at most 500 datapoints from the arena position
- uses that data to plot the before mentioned live graph
- can be called by pressing a button on the Opt_Moto.py UI

3. easy_plot.R:
- early version of data evaluation
- used for experimentation with the data to find plots that should be implemented in the main evaluation program (https://github.com/brembslab/DTSevaluations.git)

INSTALLATION
1. Install the “MCC Universal Library Python API for Windows” from Github (https://github.com/mccdaq/mcculw.git) and follow the installation instructions in the readme file.
2. Download the files from this repository (the easy_plot programs are optional).
3. Save them all in the same folder (important!) and in the same drive as the Universal Library from MCC and Python.
4. Use the pip install command in the Windows command center to install all the packages needed in the programs: tkinter, etree, os, winsoud, shutil, datetime, sys, tkMessageBox, matplotlib, pycompile
5. To be able to call the live graph, live_graph.py first has to be compiled. Just run setup.py and this should be resolved.
