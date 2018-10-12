# source: youtube/sentdex matlib tutorials(part16)

#import pylab


import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import Opt_Moto


style.use("fivethirtyeight")

fig = plt.figure()
ax1 = fig.add_subplot(2, 1, 1)
ax2 = fig.add_subplot(2, 1, 2)

def animate(i):

    graph_data = open("Rawtext.txt", "r").read()
    lines = graph_data.split('\n')
    xs = []
    ys =[]
    x = 0
    for line in lines[:-1]:
        datapoints = line.split(" ")
        y = datapoints[0]
        x = x+1
        xs.append(float(x))
        ys.append(float(y))
        if x > 150:
            del ys[0]
            del xs[0]

    ax1.clear()
    ax1.set_title("Channel 1 / Fly Position")
    ax1.set_ylabel("V")
    ax1.plot(xs, ys)
    ax1.set_ylim(0, 2.5)

    xs2 = []
    ys2 =[]
    x2 = 0
    for line2 in lines[:-1]:
        datapoints2 = line2.split(" ")
        y2 = datapoints2[1]
        x2 = x2+1
        xs2.append(float(x2))
        ys2.append(float(y2))
        if x2 > 500:
            del ys2[0]
            del xs2[0]

    ax2.clear()
    ax2.set_title("Channel 2 / Arena Position", )
    ax2.set_ylabel("V")
    ax2.set_xlabel("count")
    ax2.plot(xs2, ys2)
    ax2.set_ylim(-4, 1, auto=False)


ani = animation.FuncAnimation(fig, animate, interval=10)

plt.show()
