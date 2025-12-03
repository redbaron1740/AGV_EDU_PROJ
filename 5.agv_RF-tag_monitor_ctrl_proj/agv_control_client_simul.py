import threading
import time
import json
import curses
import requests
from enum import Enum

AGV_STATE_INITIAL = 0
AGV_STATE_READY = 1
AGV_STATE_RUNNING = 2
AGV_STATE_OBSTACLE_ESTOP = 3
AGV_STATE_PUSH_BUTTON_ESTOP = 4
AGV_STATE_SERVER_BUTTON_ESTOP = 5
AGV_STATE_ABNORMAL = 6


class CMD_AGV(Enum):
    GO = 1
    ESTOP = 2
    PAUSE = 3
    RESUME = 4
    NONE = 0

# 공유 데이터 구조
agv_client_info = {
    "SOC": 100,                  # State of Charge
    "LIDAR": 1200,               # LIDAR distance in mm
    "RF_TAG": 0,                 # Current RF-Tag ID
    "SPEED_LIMIT": 0,            # Speed limit from RF-Tag
    "CURRENT_SPEED": 0,          # Current speed in mm/s
    "STATE": 0,  # AGV 상태: INITIAL : communicated with AGV and sensors
                                 #  READY  - Ready for lane-tracing, connected to server, Tx with agv data 
                                 #  RUNNING - Detect rf-tag, obstacle, monitoring pushed button and lane-tracing 
                                 #  OBS_ESTOP
                                 #  PUSH_BUTTON_ESTOP
                                 #  abnormal
    "Alv_cnt": 0
}       

agv_wp_speed = {
    0: 100,
    1: 150,
    2: 150,
    3: 100,
    4: 150,
    5: 100,
    6: 100,
    7: 100,
    8: 150,
    9: 100,
    10: 150,
    11: 0
}

agv_rf_tag = 0

cmd_data_to_client = {
    "From_server_cmd": CMD_AGV.NONE.value,
    "Alv_cnt": 0
}

# 송신 스레드: 100ms마다 AGV 상태 전송
def send_thread():
    server_url = 'http://localhost:5000/client_data'  # Flask 서버 주소
    global agv_client_info
    
    while True:
        try:
            res = requests.post(server_url, json=agv_client_info)
            print("Sent:", agv_client_info, "Response:", res.status_code)
            agv_client_info["Alv_cnt"] += 1

        except Exception as e:
            print("Error sending data:", e)
        time.sleep(.1)

# 수신 스레드: 100ms마다 서버 메시지 수신 및 처리
def poll_server_data_thread():
    global cmd_data_to_client
    
    while True:
        try:
            res = requests.get('http://localhost:5000/server_data', timeout=1)
            cmd_data_to_client = res.json()
        except Exception as e:
            print("[서버 연결 끊김 또는 오류]", e)
        time.sleep(0.1)  # 10Hz


# 사용자 입력 스레드: curses 기반 메뉴
def input_thread(stdscr):
    global agv_client_info, agv_rf_tag, cmd_data_to_client
    
    count = 0
    bPushedEstop = False
    bObstacleEstop = False
    
    curses.curs_set(0)
    stdscr.nodelay(True)
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "AGV Station Client Menu")
        stdscr.addstr(2, 0, f"배터리 용량: {agv_client_info['SOC']}")
        stdscr.addstr(3, 0, f"장애물 거리: {agv_client_info['LIDAR']}")
        stdscr.addstr(4, 0, f"현재 속도: {agv_client_info['CURRENT_SPEED']}")
        stdscr.addstr(5, 0, f"현재 WP: {agv_client_info['RF_TAG']}")
        stdscr.addstr(6, 0, f"최대 속도 제한: {agv_client_info['SPEED_LIMIT']}")
        
        if agv_client_info['STATE'] == AGV_STATE_INITIAL:
            str = "INITIAL"
        elif agv_client_info['STATE'] == AGV_STATE_READY:
            str = "READY"
        elif agv_client_info['STATE'] == AGV_STATE_RUNNING:
            str = "RUNNING"
        elif agv_client_info['STATE'] == AGV_STATE_OBSTACLE_ESTOP:
            str = "OBSTACLE ESTOP"
        elif agv_client_info['STATE'] == AGV_STATE_PUSH_BUTTON_ESTOP:
            str = "PUSH BUTTON ESTOP"
        elif agv_client_info['STATE'] == AGV_STATE_ABNORMAL:
            str = "ABNORMAL"
        stdscr.addstr(7, 0, f"State: {str}")
        if cmd_data_to_client['From_server_cmd'] == CMD_AGV.GO.value:
            cmd_str = "GO"
        elif cmd_data_to_client['From_server_cmd'] == CMD_AGV.ESTOP.value:
            cmd_str = "ESTOP"
        elif cmd_data_to_client['From_server_cmd'] == CMD_AGV.PAUSE.value:
            cmd_str = "PAUSE"
        elif cmd_data_to_client['From_server_cmd'] == CMD_AGV.RESUME.value:
            cmd_str = "RESUME"
        else:
            cmd_str = "NONE"
        stdscr.addstr(8,0, f"서버 명령: {cmd_str}, 서버와 통신 카운트: {cmd_data_to_client['Alv_cnt']}")


        stdscr.addstr(10, 0, "[Q] 종료, [B] 배터리 감소, [+] WP 증가, [-] WP 감소,[S] 속도 증가 ")
        stdscr.addstr(11, 0, "[E] Pushed E-STOP [R] Transform status of AGV [O] Obstacle E-STOP ")
        stdscr.refresh()
        key = stdscr.getch()
        
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('b') or key == ord('B'):
            agv_client_info['SOC'] = max(0, agv_client_info['SOC'] - 1)
        elif key == ord('+') or key == ord('='):
            agv_rf_tag = min(10, agv_rf_tag + 1)
        elif key == ord('-') or key == ord('_'):
            agv_rf_tag = max(0, agv_rf_tag - 1)
        elif key == ord('s') or key == ord('S'):
            agv_client_info['CURRENT_SPEED'] += 10
        elif key == ord('e') or key == ord('E'):
            agv_client_info['STATE'] = AGV_STATE_PUSH_BUTTON_ESTOP 
        elif key == ord('o') or key == ord('O'):
            bObstacleEstop = not bObstacleEstop

            agv_client_info['STATE'] = AGV_STATE_OBSTACLE_ESTOP if bObstacleEstop == True else AGV_STATE_RUNNING
            
        elif key == ord('r') or key == ord('R'):
            count += 1
            
            if count == 0:
                agv_client_info['STATE'] = AGV_STATE_INITIAL
            elif count == 1:
                agv_client_info['STATE'] = AGV_STATE_READY
            elif count == 2:
                agv_client_info['STATE'] = AGV_STATE_RUNNING
            else:
                count = 2


        agv_client_info['RF_TAG'] = agv_rf_tag
        agv_client_info['SPEED_LIMIT'] = agv_wp_speed.get(agv_rf_tag, 0)


                
            
            
        time.sleep(0.1)

if __name__ == "__main__":
    t_send = threading.Thread(target=send_thread, daemon=True)
    t_send.start()
    t_poll = threading.Thread(target=poll_server_data_thread, daemon=True)
    t_poll.start()
    curses.wrapper(input_thread)


