# Optomotorics-Bachelor-Thesis

This project is part of my Bachelor Thesis in Biology. The Opt_Moto code runs a machine desinged to test optomotoric walking behavior in fruit flies. Data is being aquired through an Analog/Digital-Converter which receives a signal from a sensor controlled by the fly and another signal from the arena turning around the fly. 

3 primary programs:
1. Opt_Moto.py: 
- modified version of the ULAIO01.py program from the mcculw library
- 
- succedes in writing some of the input directly to a text document called "rawtext.txt" in real time, which can be used by the following program for live real time plotting
- writes a more accurate list of the collected data at the end of one run to "KHZtext.txt"
- this list contains data collected at a specific frequency (normally 100 Hz)

2. live_graph.py:
- takes data from rawdata.txt, stores it and shows at most 150 datapoints from the fly position and at most 500 datapoints from the arena position
- 
