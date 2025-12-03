import threading
import time
import json
import curses
import requests
from enum import Enum
from Donkibot_i import Comm
import functools

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

OBSTACLE_THRESHOLD = 150  # 장애물 감지 임계값 (mm)

    
class AGV_MACHINE_OPERATE:

    def __init__(self):
        self.agv_client_info = {
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
        self.arg_rf_tag = 0
        self.agv_process_state = AGV_STATE_INITIAL
        
        self.cmd_data_to_client = {
            "From_server_cmd": CMD_AGV.NONE.value,
            "Alv_cnt": 0
        }
        
        self.server_post_url = 'http://localhost:5000/client_data'
        self.server_get_url = 'http://localhost:5000/server_data'
        self.isRunning = True
        
        self.agv_comm = None  # 하드웨어 통신 객체 초기화
        self.agv_port = '/dev/ttyUSB0'  # 실제 AGV와 연결된 포트 설정
        self.agv_baudrate = 115200
        self.comm_lock = threading.Lock()
        self.agv_data = {
            "line_pos": 0,
            "lidar_distance": 1500,
            "emg_flag": 0,
            "speed": 0,
            "tag1": 0,
            "tag2": 200,
            "battery_soc": 100,
        }
        self.isConnected_to_agv = False
        
        self.initialize_hardware()
        
        self.tx_thread = threading.Thread(target=self.send_data_to_server, daemon=True)
        self.rx_thread = threading.Thread(target=self.rx_data_from_server, daemon=True)
        
        self.tx_thread.start()
        self.rx_thread.start()

    def __del__(self):
        self.isRunning = False
        self.tx_thread.join()
        self.rx_thread.join()
        self.menu_thread.join()

# === 하드웨어 Serial 제어 ===
    def initialize_hardware(self):
        """AGV 하드웨어 초기화"""
        try:
            self.agv_comm = Comm(self.agv_port, self.agv_baudrate)
            self.isConnected_to_agv = True
            print("AGV 하드웨어에 연결되었습니다:", self.agv_port)
        except Exception as e:
            print("AGV 하드웨어 연결 실패:", e)
            self.isConnected_to_agv = False
         
    def send_motor_commands(self, left_speed, right_speed):
        """모터 속도 명령 전송"""
        with self.comm_lock:
            if self.agv_comm is not None:
                try:
                    self.agv_comm.CLR(left_speed, right_speed)
                except Exception as e:
                    print("Error sending motor commands:", e)
        
    def get_sensor_data(self):
        """센서 데이터 수신"""
        with self.comm_lock:
            if self.agv_comm is not None:
                try:
                    data = self.agv_comm.get_latest_data()
                    self.agv_data.update(
                        {
                            "line_pos": data.LinePos,
                            "lidar_distance": data.LidarDistance,
                            "emg_flag": data.EmgFlag,
                            "speed": data.Speed,
                            "tag1": data.RF_tag1,
                            "tag2": data.RF_tag2,
                            "battery_soc": data.SOC,
                        }
                    )
                except Exception as e:
                    print("Error receiving sensor data:", e)
                    return None
            return None

    
# 송신 스레드: 100ms마다 AGV 상태 전송
    def send_data_to_server(self):

        while self.isRunning:
            try:
                response = requests.post(self.server_post_url, json=self.agv_client_info)
                self.agv_client_info["Alv_cnt"] += 1
                
            except Exception as e:
                print("Error sending data to server:", e)
            time.sleep(.033)  # 33ms 간격으로 전송        

# 수신 스레드: 100ms마다 서버 메시지 수신 및 처리
    def rx_data_from_server(self):

        while self.isRunning:
            try:
                response = requests.get(self.server_get_url)
                self.cmd_data_to_client = response.json()
                    
            except Exception as e:
                print("Error receiving data from server:", e)
            time.sleep(.1)  # 100ms 간격으로 수신
            
        
    def main_control_loop(self):
        """메인 제어 루프"""


        while self.isRunning:
            # AGV 상태 업데이트
            try:
                self.get_sensor_data()
                
                self.agv_client_info["LIDAR"] = self.agv_data["lidar_distance"]
                self.agv_client_info["RF_TAG"] = self.agv_data["tag1"]
                self.agv_client_info["SPEED_LIMIT"] = self.agv_data["tag2"]
                self.agv_client_info["CURRENT_SPEED"] = self.agv_data["speed"]

                #state machine
                if self.agv_process_state == AGV_STATE_INITIAL:
                    # 초기화 상태 처리
                    self.agv_client_info["STATE"] = AGV_STATE_INITIAL
                    # 하드웨어 초기화 등 필요한 작업 수행
                    if self.isConnected_to_agv:
                        self.agv_process_state = AGV_STATE_READY
                        
                elif self.agv_process_state == AGV_STATE_READY:
                    # 준비 상태 처리
                    self.agv_client_info["STATE"] = AGV_STATE_READY
                    
                    if self.cmd_data_to_client["From_server_cmd"] == CMD_AGV.GO.value:
                        self.agv_process_state = AGV_STATE_RUNNING 
                        
                        
                elif self.agv_process_state == AGV_STATE_RUNNING:
                    
                    self.agv_client_info["STATE"] = AGV_STATE_RUNNING
                    if self.cmd_data_to_client["From_server_cmd"] == CMD_AGV.ESTOP.value:
                        self.agv_process_state = AGV_STATE_PUSH_BUTTON_ESTOP
                        
                    else:
                        if self.check_obstacle() == True:
                            self.agv_process_state = AGV_STATE_OBSTACLE_ESTOP
                        else:
                            if self.cmd_data_to_client["From_server_cmd"] == CMD_AGV.PAUSE.value:
                                self.send_motor_commands(0, 0)  # 모터 정지 명령
                            elif self.cmd_data_to_client["From_server_cmd"] == CMD_AGV.RESUME.value \
                                or self.cmd_data_to_client["From_server_cmd"] == CMD_AGV.GO.value:
                                vl, vr = self.line_following_control()
                                self.send_motor_commands(vl, vr)
                            
                elif self.agv_process_state == AGV_STATE_OBSTACLE_ESTOP:
                    self.send_motor_commands(0, 0)  # 모터 정지 명령
                    
                    # 장애물 비상정지 상태 처리
                    if self.check_obstacle() == False:
                        self.agv_process_state = AGV_STATE_RUNNING
                    
                    self.agv_client_info["STATE"] = AGV_STATE_OBSTACLE_ESTOP
                    
                elif self.agv_process_state == AGV_STATE_SERVER_BUTTON_ESTOP:
                    self.send_motor_commands(0, 0)  # 모터 정지 명령

                    # 서버 비상정지 상태 처리
                    self.agv_process_state = AGV_STATE_ABNORMAL    
                    
                elif self.agv_process_state == AGV_STATE_PUSH_BUTTON_ESTOP:
                    self.send_motor_commands(0, 0)  # 모터 정지 명령

                    # 푸시 버튼 비상정지 상태 처리
                    self.agv_client_info["STATE"] = AGV_STATE_PUSH_BUTTON_ESTOP
                    self.agv_process_state = AGV_STATE_ABNORMAL
                    
                elif self.agv_process_state == AGV_STATE_ABNORMAL:
                    self.send_motor_commands(0, 0)  # 모터 정지 명령

                    # 비정상 상태 처리
                    self.agv_client_info["STATE"] = AGV_STATE_ABNORMAL
                
                time.sleep(0.05)  # 50ms 제어 루프 주기    
            except Exception as e:
                print("Error in main control loop:", e) 
                time.sleep(1)
        
        
    def check_obstacle(self):
        """장애물 감지 함수"""
        if self.agv_data["lidar_distance"] < OBSTACLE_THRESHOLD:  # 예: 150mm 이내에 장애물이 있으면 True 반환
            return True
        return False
    
    
    def line_following_control(self):
        """라인 추종 제어 알고리즘 (예시)"""
        line_pos = self.agv_data["line_pos"]
        base_speed = self.agv_data["speed_limit"]  # 기본 속도 설정

        # 조향 제어        
        if abs(line_pos) > 8: # -12 ~ 12
            if line_pos < -8:
                # 제자리 좌회전
                left_speed , right_speed = -base_speed//2, base_speed//2
            else:
                # 제자리 우회전
                left_speed , right_speed = base_speed//2, -base_speed//2
        elif line_pos == 0: # 직진
            left_speed, right_speed = base_speed, base_speed
        else: #미세 조정
            max_correction = int(base_speed * 0.3)  # 최대 보정값 설정
            correction = min(int(abs(line_pos) * 8), max_correction)
            
            if line_pos < 0:    #좌측 보정 좌측 휠 느리게
                left_speed,right_speed = base_speed - correction, base_speed + correction                
            else:               #우측 보정 우측 휠 느리게
                left_speed, right_speed = base_speed + correction, base_speed - correction
        
        return int(left_speed), int(right_speed)


def menu(stdscr, agv_machine):
    curses.curs_set(0)  # 커서 숨기기
    stdscr.nodelay(True)  # 논블로킹 입력 모드
    stdscr.clear()
    while True:
        stdscr.addstr(0, 0, "AGV Control Client Simulator")
        stdscr.addstr(2, 0, f"SOC: {agv_machine.agv_client_info['SOC']}%")
        stdscr.addstr(3, 0, f"LIDAR: {agv_machine.agv_client_info['LIDAR']} mm")
        stdscr.addstr(4, 0, f"RF_TAG: {agv_machine.agv_client_info['RF_TAG']}")
        stdscr.addstr(5, 0, f"SPEED_LIMIT: {agv_machine.agv_client_info['SPEED_LIMIT']} mm/s")
        stdscr.addstr(6, 0, f"CURRENT_SPEED: {agv_machine.agv_client_info['CURRENT_SPEED']} mm/s")
        stdscr.addstr(7, 0, f"STATE: {agv_machine.agv_client_info['STATE']}")
        stdscr.addstr(8, 0, f"From_server info: {agv_machine.cmd_data_to_client}")
        
        stdscr.refresh()

if __name__ == "__main__":
    agv_machine = AGV_MACHINE_OPERATE()
    try:
        while True:
            curses.wrapper(functools.partial(menu, agv_machine=agv_machine))
            time.sleep(1)
    except KeyboardInterrupt:
        del agv_machine