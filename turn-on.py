import board
import adafruit_dotstar as dotstar
import sys
import time

num_dots = 121

dots = dotstar.DotStar(board.SCK, board.MOSI, num_dots, brightness=0.9, auto_write=False)

#red
#on = (255,1,1)
#off = (6,0,0)

#purple
# on = (150,0,150)
# off = (0,0,5)

#white
on = (175,175,175)
off = (0,0,0)

dots.fill(off)
dots.show()

for arg in sys.argv[1:]:
	print("arg:", arg)
	[start,end] = arg.split(",")
	
	for dot in range(int(start), int(end)):
		dots[dot] = on

dots.show()
