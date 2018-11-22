import _elementtree as et
from tkinter import Tk
from tkinter.filedialog import askopenfilenames

Tk().withdraw()
filenames = askopenfilenames()
print(filenames)
for filename in filenames:
    xml = et.parse(filename)

    variables = xml.find("timeseries/variables")
    variables[1][0].text = "a_pos"

    xml.write(str(filename))