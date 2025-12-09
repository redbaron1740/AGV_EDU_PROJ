import serial
import curses
import threading
import time

PORT = '/dev/ttyS0'
BAUDRATE = 115200

###########################################################
# Example AGV status message format
# "STS": "$STS,1,95,12,0,532,-15,420,120,34567,123,255\r\n"
###########################################################

AGV_info_msg = {
    'agvStatus': 0,     # "AGV 상태 모드 (0: agv_mode, 1: python_mode, 2: ros_mode)",
    "SOC": 100,         # "State of Charge (0 -100 %)",
    "LinePos": 0,       # "Line Position (Left -15:   0     15: right)",
    "EmgFlag": 0,       # "Emergency Flag (0: release, 1: pushed)",
    "LidarDistance": 500, # "Lidar Distance (200 ~ 1200 mm)",
    "TfsAngle": 0,      # "TFS Angle (-80 ~ 80)",
    "TfsDistance": 0,   # "TFS Distance (0 ~ 2800 mm)",
    "Speed": 0,         # "Speed (2 wheel average /2)",
    "Odometer": 0,      # "Odometer (count 값   100,000cnt/rev)",
    "RF_tag1": 0,       # "Mission index",
    "RF_tag2": 0        # "Speed limit mm/s"
}

isOperating = True
str_rx = ""

def on_sending_message():
    """시리얼 포트로 메시지 송신"""
    global AGV_info_msg,ser,isOperating

    msg = f"$STS,{AGV_info_msg['agvStatus']},{AGV_info_msg['SOC']},{AGV_info_msg['LinePos']},{AGV_info_msg['EmgFlag']},{AGV_info_msg['LidarDistance']},{AGV_info_msg['TfsAngle']},{AGV_info_msg['TfsDistance']},{AGV_info_msg['Speed']},{AGV_info_msg['Odometer']},{AGV_info_msg['RF_tag1']},{AGV_info_msg['RF_tag2']}\r\n"


    try:
        if ser.is_open:
            ser.write(msg.encode('latin-1'))
            # print(f"송신: {msg.strip()}")
        else:
            print("시리얼 포트가 열려 있지 않습니다.")
    except Exception as e:
        print(f"송신 에러: {e}")

def tx_thread_func():
    global isOperating
    while isOperating:
        on_sending_message()
        time.sleep(0.05)

def rx_thread_func():
    global isOperating, str_rx, ser
    while isOperating:
        try:
            if ser.in_waiting > 0:
                str_rx = ser.readline().decode('latin-1').strip()
        except Exception as e:
            print(f"수신 에러: {e}")
        time.sleep(0.05)


def main(stdscr):
    
    while True:
        choice = menu(stdscr)
        if choice == 'q':
            break
        try:
            if choice == '1':
                set_soc_value(stdscr)
            elif choice == '2':
                set_linepos_value(stdscr)
            elif choice == '3':
                set_emgflag_value(stdscr)
            elif choice == '4':
                set_lidardistance_value(stdscr)
            elif choice == '5':
                set_tfsangle_value(stdscr)
            elif choice == '6':
                set_tfsdistance_value(stdscr)
            elif choice == '7':
                set_speed_value(stdscr)
            elif choice == '8':
                set_odometer_value(stdscr)
            elif choice == '9':
                set_rftag1_value(stdscr)
            elif choice == 'a' or choice == 'A':
                set_rftag2_value(stdscr)
        except ValueError:
            stdscr.addstr(15, 0, "잘못된 입력입니다. 다시 시도하세요.")
            stdscr.refresh()
            time.sleep(1)    
          
def menu(stdscr):
        global AGV_info_msg, str_rx
    
        stdscr.clear()
        stdscr.addstr(0, 0, "AGV 시리얼 송신기 (입력 후 Enter)")
        stdscr.addstr(2, 0, f"1) SOC (0-100): {AGV_info_msg['SOC']}")
        stdscr.addstr(3, 0, f"2) LinePos (-15 to 15): {AGV_info_msg['LinePos']}")
        stdscr.addstr(4, 0, f"3) EmgFlag (0 or 1): {AGV_info_msg['EmgFlag']}")
        stdscr.addstr(5, 0, f"4) LidarDistance (200-1200): {AGV_info_msg['LidarDistance']}")
        stdscr.addstr(6, 0, f"5) TfsAngle (-80 to 80): {AGV_info_msg['TfsAngle']}")
        stdscr.addstr(7, 0, f"6) TfsDistance (0-2800): {AGV_info_msg['TfsDistance']}")
        stdscr.addstr(8, 0, f"7) Speed (0-300): {AGV_info_msg['Speed']}")
        stdscr.addstr(9, 0, f"8) Odometer: {AGV_info_msg['Odometer']}")
        stdscr.addstr(10, 0, f"9) RF_tag1: {AGV_info_msg['RF_tag1']}")
        stdscr.addstr(11, 0, f"a) RF_tag2 (speed limit mm/s): {AGV_info_msg['RF_tag2']}")
        stdscr.addstr(12, 0, f"rx: {str_rx} ")
        stdscr.addstr(13, 0, "원하는 번호 (1-a) 선택하시거나 종료하려면 'q'를 누르세요.")
        
        stdscr.refresh()
        getchar = stdscr.getkey()
        
        if '1' <= getchar <= '9' or getchar == 'q' or getchar == 'a' or getchar == 'A':
            return getchar
        else:
            return ''
    
def set_soc_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "SOC 값을 입력하세요 (0-100): ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 3).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if 0 <= value <= 100:
        AGV_info_msg['SOC'] = value
        return True
    else:
        raise False

def set_linepos_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "LinePos 값을 입력하세요 (-15 to 15): ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 3).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if -15 <= value <= 15:
        AGV_info_msg['LinePos'] = value
        return True
    else:
        raise False
    
def set_emgflag_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "EmgFlag 값을 입력하세요 (0 or 1): ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 1).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if value == 0 or value == 1:
        AGV_info_msg['EmgFlag'] = value
        return True
    else:
        raise False
    
def set_lidardistance_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "LidarDistance 값을 입력하세요 (200-1200): ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 4).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if 100 <= value <= 1200:
        AGV_info_msg['LidarDistance'] = value
        return True
    else:
        raise False
    
def set_tfsangle_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "TfsAngle 값을 입력하세요 (-80 to 80): ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 3).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if -80 <= value <= 80:
        AGV_info_msg['TfsAngle'] = value
        return True
    else:
        raise False
    
def set_tfsdistance_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "TfsDistance 값을 입력하세요 (0-2800): ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 4).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if 0 <= value <= 2800:
        AGV_info_msg['TfsDistance'] = value
        return True
    else:
        raise False

def set_speed_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "Speed 값을 입력하세요 (0-300): ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 3).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if 0 <= value <= 300:
        AGV_info_msg['Speed'] = value
        return True
    else:
        raise False

def set_odometer_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "Odometer 값을 입력하세요: ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 10).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if value >= 0:
        AGV_info_msg['Odometer'] = value
        return True
    else:
        raise False
    
def set_rftag1_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "RF_tag1 값을 입력하세요: ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 2).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if value >= 0:
        AGV_info_msg['RF_tag1'] = value
        return True
    else:
        raise False
    
def set_rftag2_value(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "RF_tag2 값을 입력하세요 (speed limit mm/s): ")
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr(1, 0, 4).decode('utf-8')
    curses.noecho()
    value = int(input_str)
    if value >= 0:
        AGV_info_msg['RF_tag2'] = value
        return True
    else:
        raise False
    

if __name__ == "__main__":
    
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=0.1)
        print(f"시리얼 포트 {PORT} 연결 성공.")
    except serial.SerialException as e:
        print(f"시리얼 포트 {PORT} 연결 실패: {e}")
        exit(1)

    isOperating = True
    tx_thread = threading.Thread(target=tx_thread_func, daemon=True)
    tx_thread.start()

    rx_thread = threading.Thread(target=rx_thread_func, daemon=True)
    rx_thread.start()

    curses.wrapper(main)

    isOperating = False
    tx_thread.join()
    rx_thread.join()
    try:
        ser.close()
    except Exception as e:
        print(f"시리얼 포트 닫기 실패: {e}")

