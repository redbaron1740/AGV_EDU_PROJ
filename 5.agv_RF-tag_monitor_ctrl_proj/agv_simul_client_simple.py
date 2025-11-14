#!/usr/bin/env python3
"""
간단한 시뮬레이션 AGV 제어 클라이언트
- 실제 하드웨어 없이 경로 기반 시뮬레이션
- 서버의 상태 관리에 종속
- Mission Planning 모듈 통합
"""

import requests
import time
import math
from datetime import datetime
from flask import Flask, jsonify
from threading import Thread

# Mission Planning 모듈 임포트
try:
    from mission_planning import execute_mission
    MISSION_MODULE_AVAILABLE = True
    print("✅ Mission Planning 모듈 로드 완료")
except ImportError as e:
    print(f"⚠️ Mission Planning 모듈 로드 실패: {e}")
    MISSION_MODULE_AVAILABLE = False

# === 설정 ===
SERVER_URL = "http://127.0.0.1:5000/update"
CLIENT_HOST = "127.0.0.1"
CLIENT_PORT = 5001

# === 전역 변수 ===
is_running = False
is_paused = False
current_speed = 0
total_distance = 0

# 시뮬레이션 AGV 데이터
agv_data = {
    "position": {"x": 1491, "y": 620},
    "rotation": 0,
    "speed": 0,
    "battery_soc": 100,
    "tag1": 0,  # 현재 감지된 RF-Tag ID (0 = 없음)
    "tag2": 200,  # 속도 제한값
    "ultrasonic": 5000,  # 초음파 거리 (mm)
    "push_button": 0,  # 비상정지 버튼 (0=정상, 1=눌림)
    "odometry": {
        "left": 0,
        "right": 0,
        "total_distance": 0
    },
    "timestamp": datetime.now().isoformat()
}

last_data_update = time.time()
last_tag_detected = 0
mission_in_progress = False

# === 경로 데이터 (서버와 동일) ===
driving_path = [
    {"type": "line", "x1": 1491, "y1": 620, "x2": 1491, "y2": 375},
    {"type": "curve", "cx": 1487, "cy": 310, "x2": 1416, "y2": 300},
    {"type": "line", "x1": 1416, "y1": 300, "x2": 918, "y2": 300},
    {"type": "line", "x1": 920, "y1": 300, "x2": 843, "y2": 248},
    {"type": "line", "x1": 844, "y1": 248, "x2": 680, "y2": 248},
    {"type": "line", "x1": 680, "y1": 248, "x2": 605, "y2": 300},
    {"type": "line", "x1": 605, "y1": 300, "x2": 180, "y2": 300},
    {"type": "curve", "cx": 132, "cy": 310, "x2": 116, "y2": 375},
    {"type": "line", "x1": 116, "y1": 375, "x2": 116, "y2": 620}
]

# === Flask 앱 (명령 수신) ===
client_app = Flask(__name__)

@client_app.route('/start', methods=['POST'])
def start_agv():
    """서버로부터 START 명령 수신"""
    global is_running, is_paused, current_speed
    if agv_data["push_button"] == 1:
        return jsonify({"status": "error", "message": "E-Stop active"}), 400
    
    is_running = True
    is_paused = False
    current_speed = min(agv_data["tag2"], 200)
    print(f"✅ START 명령 수신 - 시뮬레이션 시작 (속도: {current_speed}mm/s)")
    return jsonify({"status": "success", "message": "Simulation started"}), 200

@client_app.route('/pause', methods=['POST'])
def pause_agv():
    """서버로부터 PAUSE 명령 수신"""
    global is_paused, current_speed
    is_paused = True
    current_speed = 0
    agv_data["speed"] = 0
    print("⏸️ PAUSE 명령 수신 - 시뮬레이션 일시정지")
    return jsonify({"status": "success", "message": "Simulation paused"}), 200

@client_app.route('/resume', methods=['POST'])
def resume_agv():
    """서버로부터 RESUME 명령 수신"""
    global is_paused, current_speed
    if agv_data["push_button"] == 1:
        return jsonify({"status": "error", "message": "E-Stop active"}), 400
    
    is_paused = False
    current_speed = min(agv_data["tag2"], 200)
    agv_data["speed"] = current_speed
    print(f"▶️ RESUME 명령 수신 - 시뮬레이션 재개 (속도: {current_speed}mm/s)")
    return jsonify({"status": "success", "message": "Simulation resumed"}), 200

@client_app.route('/estop', methods=['POST'])
def estop_agv():
    """서버로부터 E-STOP 명령 수신"""
    global is_running, is_paused, current_speed
    is_running = False
    is_paused = False
    current_speed = 0
    agv_data["push_button"] = 1
    agv_data["speed"] = 0
    print("🚨 E-STOP 명령 수신 - 긴급 정지")
    return jsonify({"status": "success", "message": "Emergency stop"}), 200

@client_app.route('/health_check', methods=['GET'])
def health_check():
    """서버의 헬스 체크 요청에 응답"""
    global last_data_update
    
    data_updating = (time.time() - last_data_update) < 2.0
    emergency_flag = agv_data["push_button"] == 1  # 1이면 비상정지
    battery_ok = agv_data["battery_soc"] > 20
    
    health_status = {
        "hardware_connected": True,  # 시뮬레이션이므로 항상 연결
        "serial_port": "SIMULATION",  # 시뮬레이션 표시
        "data_updating": data_updating,
        "last_update": datetime.now().isoformat(),
        "emergency_flag": emergency_flag,  # True면 비상정지 활성화
        "battery_soc": agv_data["battery_soc"],
        "battery_ok": battery_ok,
        "communication_ok": True,
        "mission_module_available": MISSION_MODULE_AVAILABLE,
        "ready": True and not emergency_flag and battery_ok and data_updating
    }
    
    return jsonify(health_status), 200

@client_app.route('/status', methods=['GET'])
def status():
    """현재 시뮬레이션 상태 반환"""
    return jsonify({
        "running": is_running,
        "paused": is_paused,
        "speed": current_speed,
        "position": agv_data["position"],
        "battery": agv_data["battery_soc"],
        "tag1": agv_data["tag1"]
    }), 200

def run_client_server():
    """Flask 서버 실행"""
    client_app.run(host=CLIENT_HOST, port=CLIENT_PORT)

# === 시뮬레이션 로직 ===

def send_data_to_server():
    """서버로 AGV 데이터 전송"""
    global last_data_update
    try:
        agv_data["timestamp"] = datetime.now().isoformat()
        response = requests.post(SERVER_URL, json=agv_data, timeout=3)
        response.raise_for_status()
        last_data_update = time.time()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 데이터 전송 오류: {e}")

def simulate_rf_tag_detection(x, y):
    """위치 기반 RF-Tag 시뮬레이션"""
    tag_positions = {
        1: (1491, 500),
        2: (1400, 300),
        3: (1200, 300),
        4: (1000, 300),
        5: (850, 250),
        6: (700, 250),
        7: (600, 280),
        8: (400, 300),
        9: (200, 300),
        10: (116, 500)
    }
    
    detection_range = 80
    closest_tag = 0
    min_distance = float('inf')
    
    for tag_id, (tag_x, tag_y) in tag_positions.items():
        distance = math.sqrt((x - tag_x)**2 + (y - tag_y)**2)
        if distance < detection_range and distance < min_distance:
            min_distance = distance
            closest_tag = tag_id
    
    return closest_tag

def update_battery():
    """배터리 소모 시뮬레이션"""
    agv_data["battery_soc"] = max(0, agv_data["battery_soc"] - 0.0005)

def simulation_loop():
    """메인 시뮬레이션 루프"""
    global is_running, is_paused, current_speed, agv_data, total_distance
    global last_tag_detected, mission_in_progress, last_data_update
    
    print("🚗 AGV 시뮬레이션 클라이언트 시작")
    print(f"서버 URL: {SERVER_URL}")
    print(f"명령 대기 중... (http://{CLIENT_HOST}:{CLIENT_PORT})")
    
    # 초기 데이터 전송하여 서버가 클라이언트를 인식하도록 함
    print("📡 초기 데이터 전송 중...")
    for _ in range(3):
        send_data_to_server()
        time.sleep(0.1)
    print("✅ 초기 데이터 전송 완료")
    
    path_position = 0.0  # 전체 경로에서의 위치 (0.0 ~ 1.0)
    
    while True:
        if is_running and not is_paused:
            # 주행 중: 경로를 따라 이동
            path_position += 0.001  # 이동 속도
            
            if path_position >= 1.0:
                path_position = 0.0  # 경로 완료 시 처음으로
                is_running = False
                print("✅ 경로 완료 - 대기 모드")
            
            # 현재 위치 계산 (간단히 선형 보간)
            total_path_length = len(driving_path)
            segment_idx = int(path_position * total_path_length)
            if segment_idx >= len(driving_path):
                segment_idx = len(driving_path) - 1
            
            segment = driving_path[segment_idx]
            
            # 직선 세그먼트 처리
            if segment["type"] == "line":
                x1, y1, x2, y2 = segment["x1"], segment["y1"], segment["x2"], segment["y2"]
                local_t = (path_position * total_path_length) - segment_idx
                
                agv_data["position"]["x"] = int(x1 + (x2 - x1) * local_t)
                agv_data["position"]["y"] = int(y1 + (y2 - y1) * local_t)
                agv_data["rotation"] = int(math.degrees(math.atan2(y2 - y1, x2 - x1)) + 90) % 360
                agv_data["speed"] = current_speed
            
            # RF-Tag 감지
            detected_tag = simulate_rf_tag_detection(
                agv_data["position"]["x"],
                agv_data["position"]["y"]
            )
            
            # 새로운 태그 감지 시 미션 실행
            if detected_tag != 0 and detected_tag != last_tag_detected:
                print(f"🏷️ RF-Tag {detected_tag} 감지!")
                agv_data["tag1"] = detected_tag
                last_tag_detected = detected_tag
                
                # Mission Planning 모듈 호출
                if MISSION_MODULE_AVAILABLE and not mission_in_progress:
                    mission_in_progress = True
                    try:
                        # 시뮬레이션용 간단한 통신 객체
                        class SimComm:
                            def CLR(self, left, right):
                                global current_speed
                                current_speed = (left + right) // 2
                                agv_data["speed"] = current_speed
                                print(f"🎯 Mission: 모터 제어 L={left}, R={right}")
                        
                        sim_comm = SimComm()
                        result = execute_mission(detected_tag, sim_comm, agv_data["tag2"])
                        print(f"✅ Mission 완료: {result}")
                    except Exception as e:
                        print(f"⚠️ Mission 실행 오류: {e}")
                    finally:
                        mission_in_progress = False
            elif detected_tag == 0 and last_tag_detected != 0:
                # 태그 영역 벗어남
                agv_data["tag1"] = 0
                last_tag_detected = 0
            
            # 오도미터 업데이트
            total_distance += current_speed * 0.1 / 1000  # mm -> m
            agv_data["odometry"]["total_distance"] = round(total_distance, 2)
            agv_data["odometry"]["left"] = round(total_distance, 2)
            agv_data["odometry"]["right"] = round(total_distance, 2)
            
            # 배터리 업데이트
            update_battery()
            
        else:
            # 정지 중: 현재 위치 유지
            agv_data["speed"] = 0
        
        # 서버로 데이터 전송
        send_data_to_server()
        time.sleep(0.1)  # 100ms 주기

if __name__ == "__main__":
    # Flask 서버 시작 (별도 스레드)
    server_thread = Thread(target=run_client_server, daemon=True)
    server_thread.start()
    
    # 시뮬레이션 루프 시작
    simulation_loop()
