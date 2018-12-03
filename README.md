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
