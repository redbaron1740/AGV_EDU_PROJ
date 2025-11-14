import curses
from Donkibot_i import Comm

def main(stdscr):
    port = '/dev/ttyUSB0'
    baudrate = 115200
    agv = Comm(port, baudrate)
    #curses initialization
    curses.curs_set(0)   # hide cursor
    stdscr.clear()
    stdscr.addstr(0,0,"Move the robot.(stop 'q')\n\r")
    while True:
        key = stdscr.getch()   # Gain a word
        
        if key == ord('q') or key == ord('Q'):
            print("Exiting...", end='\n\r')
            break
      
        elif key == curses.KEY_UP:
            print("Moving Forward", end='\n\r')
            agv.CLR(-100,-100)

        elif key == curses.KEY_DOWN:
            print("Moving Backward", end='\n\r')
            agv.CLR(100,100)
          
        elif key == curses.KEY_LEFT:
            print("Steering Left", end='\n\r')
            agv.CLR(50,-100)

        elif key == curses.KEY_RIGHT:
            print("Steering Right", end='\n\r')
            agv.CLR(-100,50)

        elif key == ord('r'):  # pivot left
            print("Pivoting Left", end= '\n\r')
            agv.CLR(0,-100)

        elif key == ord('t'):  # pivot right
            print("Pivoting Right", end= '\n\r')
            agv.CLR(-100,0)


        elif key == 48:     # ascii code 48 == '0'
            print("Stop moving", end= '\n\r')
            agv.CLR(0,0)
          

curses.wrapper(main)

if __name__ == "__main__":
    main(curses.initscr())