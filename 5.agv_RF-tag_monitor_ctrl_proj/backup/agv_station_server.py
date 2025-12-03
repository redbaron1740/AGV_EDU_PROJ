from flask import Flask, request, jsonify, render_template
from threading import Thread
import requests
import time
import math
import re
import json
import os
from datetime import datetime
import socket
import math

app = Flask(__name__)

# AGV 클라이언트의 주소 (agv_simul_client.py 또는 agv_real_client.py가 실행되는 곳)
AGV_CLIENT_URL = "http://127.0.0.1:5001"

# === 상태 정의 및 State Machine ===
class AGVState:
    INITIAL = 1
    READY = 2
    RUNNING = 3
    PAUSED = 31
    RESUME = 32
    ESTOP = 33
    PUSH_ESTOP = 4
    OBS_ESTOP = 42
    SRV_ESTOP = 43
    ABNORMAL = 6
    # COMPLETED 제거 - 모든 임무는 mission_planning에서 관리

# 서버 측 상태 머신 변수
current_agv_state = AGVState.INITIAL
state_change_time = time.time()
last_tag_detected = 0
initial_retry_count = 0  # 초기화 재시도 횟수
initial_start_time = time.time()  # INITIAL 시작 시간

def get_state_name(state=None):
    """상태 번호를 이름으로 변환"""
    if state is None:
        state = current_agv_state
    
    # 문자열 상태명 처리 (클라이언트에서 온 데이터)
    if isinstance(state, str):
        return state
    
    # 숫자 상태코드 처리
    state_names = {
        AGVState.INITIAL: "Initial",
        AGVState.READY: "Ready", 
        AGVState.RUNNING: "Running",
        AGVState.PAUSED: "Paused",
        AGVState.RESUME: "Running",
        AGVState.PUSH_ESTOP: "Push-EStop",
        AGVState.OBS_ESTOP: "OBS-EStop",
        AGVState.SRV_ESTOP: "SRV-EStop",
        AGVState.ABNORMAL: "Abnormal"
    }
    return state_names.get(state, "Unknown")

def change_agv_state(new_state, reason=""):
    """AGV 상태 변경"""
    global current_agv_state, state_change_time
    prev_state = get_state_name(current_agv_state)
    current_agv_state = new_state
    state_change_time = time.time()
    new_state_name = get_state_name(new_state)
    
    print(f"🔄 State Change: {prev_state} → {new_state_name} ({reason})")
    
    # 상태별 AGV 명령 전송
    send_agv_command_for_state(new_state)

def send_agv_command_for_state(state):
    """상태에 따른 AGV 명령 전송"""
    try:
        if state == AGVState.READY:
            # Ready 상태: 특별한 명령 없음 (대기)
            pass
        elif state == AGVState.RUNNING:
            # Running 상태: 시작 명령
            response = requests.post(f"{AGV_CLIENT_URL}/start", timeout=3)
            print(f"✅ START 명령 전송: {response.status_code}")
        elif state == AGVState.PAUSED:
            # Paused 상태: 일시정지 명령
            response = requests.post(f"{AGV_CLIENT_URL}/pause", timeout=3)
            print(f"⏸️ PAUSE 명령 전송: {response.status_code}")
        elif state in [AGVState.PUSH_ESTOP, AGVState.OBS_ESTOP, AGVState.SRV_ESTOP]:
            # EStop 상태: 비상정지 명령
            response = requests.post(f"{AGV_CLIENT_URL}/estop", timeout=3)
            print(f"🚨 ESTOP 명령 전송: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ AGV 명령 전송 실패: {e}")

def check_client_health():
    """클라이언트 상태 점검 - health 딕셔너리 반환"""
    print("🔍 AGV 클라이언트 상태 점검 시작...")
    
    try:
        # 1. 클라이언트 헬스 체크 요청
        print(f"   📡 클라이언트 연결 시도: {AGV_CLIENT_URL}/health_check")
        response = requests.get(f"{AGV_CLIENT_URL}/health_check", timeout=5)
        if response.status_code != 200:
            print(f"   ❌ 클라이언트 응답 오류: {response.status_code}")
            return None
        
        print(f"   ✅ 클라이언트 응답 성공")
        health = response.json()
        print(f"   📋 Health Data: {health}")
        
        # 2. 시리얼 연결 확인
        if not health.get("hardware_connected"):
            print(f"   ❌ 하드웨어 연결 안됨: {health.get('serial_port')}")
        else:
            print(f"   ✅ 하드웨어 연결: {health.get('serial_port')}")
        
        # 3. 데이터 업데이트 확인
        if not health.get("data_updating"):
            print(f"   ❌ 센서 데이터 업데이트 안됨")
        else:
            print(f"   ✅ 센서 데이터 업데이트 중: {health.get('last_update')}")
        
        # 4. 비상정지 상태 확인
        if health.get("emergency_flag"):
            print(f"   ⚠️ 비상정지 버튼 눌림")
        else:
            print(f"   ✅ 비상정지 상태: 정상")
        
        # 5. 배터리 확인
        battery = health.get("battery_soc", 0)
        if battery < 10:
            print(f"   ⚠️ 배터리 부족: {battery}%")
        else:
            print(f"   ✅ 배터리: {battery}%")
        
        # 6. 서버-클라이언트 통신 확인
        if not health.get("communication_ok"):
            print(f"   ❌ 통신 상태 불안정")
        else:
            print(f"   ✅ 서버-클라이언트 통신: 정상")
        
        # 7. 미션 모듈 확인
        if health.get("mission_module_available"):
            print(f"   ✅ Mission Planning 모듈: 로드됨")
        else:
            print(f"   ⚠️ Mission Planning 모듈: 없음 (시뮬레이션 가능)")
        
        # 모든 체크 통과 여부 출력
        if health.get("ready"):
            print("   🎉 모든 안전 점검 통과!")
        else:
            print("   ⚠️ 일부 점검 실패")
        
        # health 딕셔너리 반환 (RUNNING/PAUSED에서 사용)
        return health
            
    except requests.exceptions.Timeout:
        print(f"   ❌ 클라이언트 응답 시간 초과 (5초)")
        print(f"   💡 클라이언트가 실행 중인지 확인하세요: {AGV_CLIENT_URL}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 클라이언트 연결 실패 - {AGV_CLIENT_URL}")
        print(f"   💡 클라이언트를 먼저 실행하세요: python agv_control_client_simple.py")
        return None
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 클라이언트 통신 오류: {e}")
        return None
    except Exception as e:
        print(f"   ❌ 예상치 못한 오류: {e}")
        return None

def process_server_state_machine():
    """서버 측 상태 머신 처리"""
    global current_agv_state, last_tag_detected, initial_retry_count, initial_start_time
    
    # 클라이언트로부터 받은 데이터 확인 (두 가지 형식 지원)
    client_rf_tag = agv_data.get("rf_tag", {}).get("current_tag", 0)
    if client_rf_tag is None or client_rf_tag == 0:
        # 시뮬레이션 클라이언트 형식 확인
        client_rf_tag = agv_data.get("tag1", 0)
    
    client_status = agv_data.get("status", "")
    
    # 헬스 체크 정보 가져오기 (RUNNING/PAUSED 상태에서 사용)
    client_health = check_client_health() if current_agv_state in [AGVState.RUNNING, AGVState.PAUSED] else None
    
    # INITIAL 상태에서 클라이언트 연결 확인 → READY로 전환
    if current_agv_state == AGVState.INITIAL:
        # 경과 시간 확인
        elapsed_time = time.time() - initial_start_time
        
        # 클라이언트가 데이터를 보내기 시작하면 헬스 체크 수행
        if agv_data.get("timestamp"):
            # 10초마다 헬스 체크 수행 (최대 3번)
            if elapsed_time >= 10 * (initial_retry_count + 1):
                initial_retry_count += 1
                print("\n" + "="*60)
                print(f"   🚀 AGV 시스템 초기화 검증 시도 ({initial_retry_count}/3)")
                print("="*60)
                
                health_data = check_client_health()
                
                if health_data and health_data.get("ready"):
                    change_agv_state(AGVState.READY, "All safety checks passed")
                    print("="*60)
                    print("   ✅ AGV 시스템 준비 완료 - Ready 상태")
                    print("="*60 + "\n")
                    initial_retry_count = 0  # 성공 시 카운터 리셋
                else:
                    if initial_retry_count >= 3:
                        # 3번 실패 → ABNORMAL
                        print("="*60)
                        print("   ❌ 초기화 검증 3회 실패 - 비정상 상태")
                        print("   ⚠️  수동 종료 후 재시작 필요")
                        print("="*60 + "\n")
                        change_agv_state(AGVState.ABNORMAL, "Health check failed 3 times - Manual restart required")
                    else:
                        # 재시도 대기
                        print(f"   ⏳ 10초 후 재시도 예정... ({initial_retry_count}/3)")
                        print("="*60 + "\n")
            return
        else:
            # 클라이언트로부터 데이터를 아직 받지 못함
            if elapsed_time >= 30:
                print("\n" + "="*60)
                print("   ❌ 클라이언트 연결 타임아웃 (30초) - 비정상 상태")
                print("   ⚠️  클라이언트를 실행하고 서버를 재시작하세요")
                print("="*60 + "\n")
                change_agv_state(AGVState.ABNORMAL, "Client connection timeout")
            return
    
    # READY 상태: 클라이언트가 준비된 상태, 시작 대기
    if current_agv_state == AGVState.READY:
        print("[DEBUG] READY 상태 - 시작 대기 중")
        # Tag 1 감지 시 자동 시작은 아래 Tag 처리에서 수행
        pass
    
    # RUNNING 상태: 주행 중 - 비상정지 및 이상 감시
    elif current_agv_state == AGVState.RUNNING:
        print("[DEBUG] RUNNING 상태 처리 중")
        
        # 1. 비상정지 버튼 확인 (emergency_flag)
        if client_health and client_health.get("emergency_flag"):
            change_agv_state(AGVState.PUSH_ESTOP, "Emergency button pressed during RUNNING")
            print(f"🚨 RUNNING 중 비상정지 버튼 눌림 → PUSH_ESTOP")
            return
        
        # 2. 데이터 업데이트 확인
        if not client_health or not client_health.get("data_updating"):
            change_agv_state(AGVState.ABNORMAL, "Data not updating during RUNNING")
            print(f"❌ RUNNING 중 데이터 업데이트 멈춤 → ABNORMAL")
            return
        
        # 3. 통신 상태 확인
        if not client_health or not client_health.get("communication_ok"):
            change_agv_state(AGVState.ABNORMAL, "Communication lost during RUNNING")
            print(f"❌ RUNNING 중 통신 끊김 → ABNORMAL")
            return
        
        # 4. 배터리 확인 (경고만)
        if client_health and client_health.get("battery_soc", 100) < 20:
            print(f"⚠️ 배터리 부족: {client_health.get('battery_soc')}%")
        
        # 5. 클라이언트에서 보고한 EStop 처리
        if "Push-EStop" in client_status:
            change_agv_state(AGVState.PUSH_ESTOP, "Client reported Push-EStop")
            print(f"🚨 클라이언트 Push-EStop 보고 → PUSH_ESTOP")
            return
        elif "OBS-EStop" in client_status:
            change_agv_state(AGVState.OBS_ESTOP, "Client reported OBS-EStop")
            print(f"🚨 클라이언트 OBS-EStop 보고 → OBS_ESTOP")
            return
        
        print(f"   ✅ RUNNING 중... (정상 운행)")
    
    # PAUSED 상태: 일시정지 중 - 비상정지만 감시
    elif current_agv_state == AGVState.PAUSED:
        print("[DEBUG] PAUSED 상태 - 일시정지 중")
        
        # 비상정지 버튼 확인
        if client_health and client_health.get("emergency_flag"):
            change_agv_state(AGVState.PUSH_ESTOP, "Emergency button pressed during PAUSED")
            print(f"🚨 PAUSED 중 비상정지 버튼 눌림 → PUSH_ESTOP")
            return
        
        # 클라이언트에서 보고한 EStop 처리
        if "Push-EStop" in client_status:
            change_agv_state(AGVState.PUSH_ESTOP, "Client reported Push-EStop")
            print(f"🚨 클라이언트 Push-EStop 보고 → PUSH_ESTOP")
            return
        elif "OBS-EStop" in client_status:
            change_agv_state(AGVState.OBS_ESTOP, "Client reported OBS-EStop")
            print(f"🚨 클라이언트 OBS-EStop 보고 → OBS_ESTOP")
            return
    
    # PUSH_ESTOP 상태: 비상정지 버튼 눌림 → 버튼 해제 시 자동 복구
    elif current_agv_state == AGVState.PUSH_ESTOP:
        print("[DEBUG] PUSH_ESTOP 상태 - 비상정지 버튼 눌림")
        
        # 비상정지 버튼 해제 확인 (client_status에서 "Push-EStop" 사라지면 해제됨)
        if "Push-EStop" not in client_status:
            # 버튼 해제됨 → PAUSED로 전환 (사용자가 Resume 버튼 누를 때까지 대기)
            change_agv_state(AGVState.PAUSED, "Emergency button released")
            print(f"✅ 비상정지 버튼 해제됨 → PAUSED (Resume 대기)")
            return
        else:
            print(f"🚨 비상정지 버튼 눌림 중... 대기")
        return
    
    # OBS_ESTOP 상태: 장애물 감지 → 장애물 제거 시 자동 복구
    elif current_agv_state == AGVState.OBS_ESTOP:
        print("[DEBUG] OBS_ESTOP 상태 - 장애물 감지 중")
        
        # 장애물 상태 확인 (client_status에서 "OBS-EStop" 사라지면 장애물 제거됨)
        if "OBS-EStop" not in client_status:
            # 장애물 제거됨 → RUNNING으로 자동 복구
            change_agv_state(AGVState.RUNNING, "Obstacle cleared, auto-resume")
            print(f"✅ 장애물 제거됨 → RUNNING (자동 복구)")
            return
        else:
            print(f"⚠️ 장애물 감지 중... 대기")
    
    # SRV_ESTOP 상태: 서버 명령 E-Stop → 바로 PAUSED로 전환
    elif current_agv_state == AGVState.SRV_ESTOP:
        print("[DEBUG] SRV_ESTOP 상태 - 서버 비상정지 명령")
        # 서버 E-Stop은 즉시 PAUSED로 전환 (Resume으로 재개 가능)
        change_agv_state(AGVState.PAUSED, "SRV E-Stop processed")
        print(f"✅ 서버 비상정지 처리 → PAUSED (Resume 대기)")
        return
    
    # ABNORMAL (비정상) 상태: 치명적 오류 - 수동 종료 및 재시작 필요
    elif current_agv_state == AGVState.ABNORMAL:
        # 비정상 상태에서는 아무 작업도 하지 않음 (정지 상태 유지)
        # 웹 대시보드에서 경고 메시지 표시, 사용자가 수동으로 프로그램 종료 후 재시작해야 함
        print("[DEBUG] 비정상 상태 - 시스템 정지 (수동 재시작 필요)")
        return
    
    # Tag 감지 처리 (Tag 1만 시작 신호, 나머지는 mission_planning에서 처리)
    if client_rf_tag > 0 and client_rf_tag != last_tag_detected:
        last_tag_detected = client_rf_tag
        print(f"🏷️ Server: Tag {client_rf_tag} 감지됨")
        
        # Tag 1 감지시 자동 시작
        if client_rf_tag == 1 and current_agv_state == AGVState.READY:
            change_agv_state(AGVState.RUNNING, "Tag 1 (Start) detected")
        
        # 웹에서 AGV 위치를 해당 태그 위치로 리셋
        reset_agv_position_to_tag(client_rf_tag)

def reset_agv_position_to_tag(tag_id):
    """웹에서 AGV 위치를 특정 태그 위치로 리셋"""
    global web_agv_position, web_agv_target, path_segment_index, last_tag_detected
    
    if tag_id in RF_TAG_POSITIONS:
        tag_pos = RF_TAG_POSITIONS[tag_id]
        
        # agv_data 업데이트
        agv_data["position"] = {"x": tag_pos["x"], "y": tag_pos["y"]}
        print(f"🎯 웹 AGV 위치 리셋: Tag {tag_id} → ({tag_pos['x']}, {tag_pos['y']})")
        
        # 웹 AGV 시뮬레이션 변수도 리셋
        web_agv_position = {"x": tag_pos["x"], "y": tag_pos["y"]}
        
        # 현재 태그에서 다음 태그로 향하도록 경로 인덱스 조정
        # Tag ID는 1, 2, 3, 4, 5, 10 순서이므로 인덱스 매핑 필요
        tag_to_segment_map = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 10: 8}
        if tag_id in tag_to_segment_map:
            path_segment_index = tag_to_segment_map[tag_id]
        
        # 마지막 감지된 태그 업데이트
        last_tag_detected = tag_id
        
        # 궤적 리셋 (새로운 시작점)
        agv_data["trajectory"] = [{"x": tag_pos["x"], "y": tag_pos["y"]}]

# 웹 AGV 위치 시뮬레이션 변수
web_agv_position = {"x": 1491, "y": 620}
web_agv_target = {"x": 1491, "y": 620}
web_agv_speed = 2.0  # 픽셀/프레임
path_segment_index = 0
web_agv_moving = False

def update_web_agv_position(real_position):
    """실제 AGV 위치 대신 웹 시뮬레이션 위치 업데이트"""
    global web_agv_position, web_agv_target, web_agv_moving, path_segment_index, current_agv_state
    
    # Running 상태일 때만 자동 이동
    if current_agv_state == AGVState.RUNNING:
        # 웹 AGV가 이동 중이 아니면 천천히 경로 따라 이동 시작
        if not web_agv_moving:
            start_web_agv_movement()
        
        # 다음 태그 근처 도달 시 대기 체크
        if not check_web_agv_near_tag():
            # 대기 중이 아니면 천천히 목표점을 향해 이동
            move_web_agv_smoothly()
    
    # 웹 AGV 위치를 agv_data에 반영
    agv_data["position"] = {"x": int(web_agv_position["x"]), "y": int(web_agv_position["y"])}
    
    # 궤적 업데이트 (중복 방지)
    if len(agv_data["trajectory"]) == 0 or agv_data["trajectory"][-1] != agv_data["position"]:
        agv_data["trajectory"].append({"x": int(web_agv_position["x"]), "y": int(web_agv_position["y"])})

def start_web_agv_movement():
    """웹 AGV 경로 이동 시작"""
    global web_agv_moving, web_agv_target, path_segment_index
    
    web_agv_moving = True
    # 다음 경로 세그먼트의 목표점 설정
    if path_segment_index < len(driving_path):
        segment = driving_path[path_segment_index]
        if segment["type"] == "line":
            web_agv_target = {"x": segment["x2"], "y": segment["y2"]}
        elif segment["type"] == "curve":
            # curve는 SVG path에서 끝점 추출 (예: "M 1491 375 Q 1487 310 1416 300")
            try:
                nums = list(map(float, re.findall(r"[-+]?[0-9]*\.?[0-9]+", segment['d'])))
                if len(nums) >= 8:
                    # Quadratic Bezier의 끝점 (x1, y1)
                    web_agv_target = {"x": nums[6], "y": nums[7]}
                else:
                    # 파싱 실패 시 현재 위치 유지
                    web_agv_target = web_agv_position.copy()
            except Exception:
                web_agv_target = web_agv_position.copy()
        path_segment_index += 1
    else:
        # 모든 경로 완료
        web_agv_moving = False
    
def move_web_agv_smoothly():
    """웹 AGV를 목표점까지 천천히 이동"""
    global web_agv_position, web_agv_target, web_agv_moving, path_segment_index
    
    # 목표점까지의 거리 계산
    dx = web_agv_target["x"] - web_agv_position["x"]
    dy = web_agv_target["y"] - web_agv_position["y"]
    distance = math.sqrt(dx*dx + dy*dy)
    
    # 목표점에 도달했으면 다음 세그먼트로
    if distance < web_agv_speed:
        web_agv_position = web_agv_target.copy()
        # 다음 세그먼트 설정
        if path_segment_index < len(driving_path):
            start_web_agv_movement()
        else:
            web_agv_moving = False
    else:
        # 천천히 이동
        web_agv_position["x"] += (dx / distance) * web_agv_speed
        web_agv_position["y"] += (dy / distance) * web_agv_speed

def check_web_agv_near_tag():
    """웹 AGV가 다음 태그 근처에 있는지 확인하고 대기 처리"""
    global last_tag_detected, web_agv_moving, web_agv_speed
    
    next_expected_tag = last_tag_detected + 1
    if next_expected_tag <= 10 and next_expected_tag in RF_TAG_POSITIONS:
        tag_pos = RF_TAG_POSITIONS[next_expected_tag]
        
        # 웹 AGV와 다음 태그 사이의 거리
        distance_to_tag = math.sqrt(
            (web_agv_position["x"] - tag_pos["x"])**2 + 
            (web_agv_position["y"] - tag_pos["y"])**2
        )
        
        # 태그 근처(50픽셀 이내)에 도달했는데 실제 태그가 감지되지 않았다면 대기
        if distance_to_tag < 50:
            print(f"🚧 웹 AGV가 Tag {next_expected_tag} 근처 도달 - 실제 감지 대기 중")
            web_agv_moving = False  # 이동 중지
            return True
    
    return False

# waypoints.json 파일에서 RF-Tag 위치 정보 로드
def load_waypoints():
    """내장 RF-Tag 좌표를 반환합니다. (waypoints.json 비활성화)"""
    print("ℹ️ Using built-in RF-Tag positions (waypoints.json disabled).")
    return {
        1: {'x': 1491, 'y': 620, 'description': '시작점', 'type': 'start', 'speed_limit': 200},
        2: {'x': 1491, 'y': 375, 'description': '우측 상단', 'type': 'waypoint', 'speed_limit': 150},
        3: {'x': 918, 'y': 300, 'description': '중간 직선부', 'type': 'waypoint', 'speed_limit': 200},
        4: {'x': 680, 'y': 248, 'description': '좌측 구간 (급회전)', 'type': 'waypoint', 'speed_limit': 150},
        5: {'x': 180, 'y': 300, 'description': '최좌단', 'type': 'waypoint', 'speed_limit': 150},
        10: {'x': 116, 'y': 620, 'description': '목적지', 'type': 'finish', 'speed_limit': 200}
    }

# RF-Tag 위치 정보 로드
# 1번: 무조건 시작점, 10번: 무조건 회차/정지점
RF_TAG_POSITIONS = load_waypoints()

# 경로 자동 생성 함수
def generate_driving_path(waypoints):
    """waypoints로부터 직선 경로를 자동 생성합니다."""
    sorted_tags = sorted([tag_id for tag_id in waypoints.keys()])
    path = []
    
    for i in range(len(sorted_tags) - 1):
        current_id = sorted_tags[i]
        next_id = sorted_tags[i + 1]
        current_wp = waypoints[current_id]
        next_wp = waypoints[next_id]
        
        path.append({
            "type": "line",
            "x1": current_wp['x'],
            "y1": current_wp['y'],
            "x2": next_wp['x'],
            "y2": next_wp['y']
        })
    
    return path

# AGV가 주행할 경로 데이터 (고정 경로: 이전에 사용하던 곡선/직선 포함)
driving_path = [
    {"type": "line",  "x1": 1491, "y1": 620, "x2": 1491, "y2": 375},
    {"type": "curve", "d": "M 1491 375 Q 1487 310 1416 300"},
    {"type": "line",  "x1": 1416, "y1": 300, "x2": 918,  "y2": 300},
    {"type": "line",  "x1": 920,  "y1": 300, "x2": 843,  "y2": 248},
    {"type": "line",  "x1": 844,  "y1": 248, "x2": 680,  "y2": 248},
    {"type": "line",  "x1": 680,  "y1": 248, "x2": 605,  "y2": 300},
    {"type": "line",  "x1": 605,  "y1": 300, "x2": 180,  "y2": 300},
    {"type": "curve", "d": "M 181 300 Q 132 310 116 375"},
    {"type": "line",  "x1": 116,  "y1": 375, "x2": 116,  "y2": 620}
]

def load_tag_nums():
    """ 태그 번호(1~10)를 생성합니다."""  
    tags = [
        {'id': 1, 'x': 1491, 'y': 620, 'visible': True, 'location': 'right'},
        { "id": 2,  "x": 1491, "y": 390, "visible": True,  "location": "right" },
        { "id": 3,  "x": 1370, "y": 300, "visible": True,  "location": "right" },
        { "id": 4,  "x": 918,  "y": 300, "visible": True,  "location": "right" },
        { "id": 5,  "x": 843,  "y": 248, "visible": True,  "location": "right" },
        { "id": 6,  "x": 680,  "y": 248, "visible": True,  "location": "right" },
        { "id": 7,  "x": 605,  "y": 300, "visible": True,  "location": "right"  },
        { "id": 8,  "x": 220,  "y": 300, "visible": True,  "location": "right"  },
        { "id": 9,  "x": 116,  "y": 390, "visible": True,  "location": "right"  },
        { "id": 10, "x": 116,  "y": 600, "visible": True, "location": "right"  }        
    ]

    normalized = { int(t['id']): {
        'x': int(t['x']),
        'y': int(t['y']),
        'visible': bool(t.get('visible', True)),
        'location': t.get('location', 'right')
    } for t in tags }
    print(f"🔢 tag_num.json loaded: {len(normalized)} tags")
    return normalized

# 태그 번호(사각형 표시용) 로드
TAG_NUMS = load_tag_nums()

# --- Utilities to place tag numbers along path normal ---
def _sample_line(x1, y1, x2, y2, n=40):
    pts = []
    for i in range(n+1):
        t = i / n
        pts.append((x1 + (x2 - x1)*t, y1 + (y2 - y1)*t))
    return pts

def _sample_quad_bezier(x0, y0, cx, cy, x1, y1, n=60):
    pts = []
    for i in range(n+1):
        t = i / n
        mt = 1 - t
        bx = mt*mt*x0 + 2*mt*t*cx + t*t*x1
        by = mt*mt*y0 + 2*mt*t*cy + t*t*y1
        pts.append((bx, by))
    return pts

def _polyline_from_path(path):
    pts = []
    for seg in path:
        if seg.get('type') == 'line':
            pts.extend(_sample_line(seg['x1'], seg['y1'], seg['x2'], seg['y2'], n=40))
        elif seg.get('type') == 'curve':
            try:
                import re as _re
                nums = list(map(float, _re.findall(r"[-+]?[0-9]*\.?[0-9]+", seg['d'])))
                if len(nums) >= 8:
                    x0, y0, cx, cy, x1, y1 = nums[0], nums[1], nums[2], nums[3], nums[6], nums[7]
                    pts.extend(_sample_quad_bezier(x0, y0, cx, cy, x1, y1, n=60))
            except Exception:
                pass
    return pts

_PATH_POINTS = _polyline_from_path(driving_path)

def _nearest_index(pts, x, y):
    best_i, best_d2 = 0, float('inf')
    for i, (px, py) in enumerate(pts):
        d2 = (px - x)*(px - x) + (py - y)*(py - y)
        if d2 < best_d2:
            best_d2, best_i = d2, i
    return best_i

def _normal_at_index(pts, i):
    # approximate tangent by neighbors
    if i <= 0:
        x0, y0 = pts[i]
        x1, y1 = pts[i+1]
    elif i >= len(pts)-1:
        x0, y0 = pts[i-1]
        x1, y1 = pts[i]
    else:
        x0, y0 = pts[i-1]
        x1, y1 = pts[i+1]
    tx, ty = (x1 - x0), (y1 - y0)
    L = math.hypot(tx, ty) or 1.0
    tx, ty = tx / L, ty / L
    # left normal = (-ty, tx); right normal = (ty, -tx)
    return (-ty, tx), (ty, -tx)

def _offset_by_normal(x, y, side='right', offset=14):
    i = _nearest_index(_PATH_POINTS, x, y)
    nleft, nright = _normal_at_index(_PATH_POINTS, i)
    # 화면 좌표계(y가 아래로 증가)에서는 수학적 좌/우가 시각적으로 반대로 느껴질 수 있음
    # 사용자가 기대하는 시각적 좌/우에 맞추기 위해 매핑을 반전한다.
    # 즉, side=='left' -> nright, side=='right' -> nleft
    nx, ny = (nright if side == 'left' else nleft)
    return (x + nx*offset, y + ny*offset)

def _get_local_ip():
    """시작 시 안내를 위해 이 장치의 LAN IP를 추정합니다."""
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 외부로 실제 송신하지 않지만, 라우팅 인터페이스를 통해 로컬 IP를 얻습니다.
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        pass
    finally:
        try:
            s.close()
        except Exception:
            pass
    return ip

# Store latest AGV data including position, trajectory and rotation
agv_data = {
    "timestamp": None,
    "odometry": {"left": 0, "right": 0, "total_distance": 0},
    "rf_tag": {"current_tag": 0, "last_detected": 0, "next_target": 1, "passed_tags": []},
    "position": {"x": 1491, "y": 620},  # Default center position
    "rotation": 0,  # Rotation angle in degrees (0-360)
    "trajectory": [],
    "speed": 0,
    "battery_soc": 100,
    "lidar_distance": 0,  # LiDAR 거리 측정값
    "status": "Ready"  # Ready, Initial, Running, Paused, OBS-EStop, Push-EStop, Stop, Home, Completed
}

# --- AGV 상태 변수 ---
agv_state = "IDLE" # "IDLE", "RUNNING", "HOMING"
current_position = {"x": 1491, "y": 620}
current_rotation = 0
path_segment_index = 0
path_step_index = 0

# Stop 상태 진입 시 5초 후 Ready 및 위치 초기화를 위한 서버측 타이머 플래그
stop_reset_timer_active = False

# HTML template with background image, AGV image, and trajectory

@app.route('/')
def index():
    # 템플릿 파일을 사용하여 렌더링합니다.
    lan_ip = _get_local_ip()
    return render_template('index.html', agv_data=agv_data, driving_path=driving_path, lan_ip=lan_ip)

@app.route('/data')
def get_data():
    """최신 AGV 데이터를 JSON으로 제공하는 새 엔드포인트."""
    return jsonify({
        "position": agv_data["position"],
        "rotation": agv_data["rotation"],
        "trajectory": agv_data["trajectory"],
        "agv_status": agv_data["status"],
        "current_tag": agv_data["rf_tag"].get("current_tag", "-"),
        "passed_tags": agv_data["rf_tag"].get("passed_tags", []),
        "battery": agv_data["battery_soc"],
        "current_speed": agv_data["speed"],
        "total_distance": agv_data["odometry"].get("total_distance", 0),
        "lidar_distance": agv_data.get("lidar_distance", 0),
        "timestamp": agv_data["timestamp"],
        "rf_tag": agv_data["rf_tag"]
    })

@app.route('/update', methods=['POST'])
def update_data():
    global agv_data, current_agv_state
    data = request.get_json()
    if data:
        # 먼저 기본 데이터 업데이트 (timestamp 등)
        for key in ["timestamp", "odometry", "speed", "battery_soc", "tag1", "tag2", "ultrasonic", "push_button"]:
            if key in data:
                if key == "odometry" and isinstance(data[key], dict):
                    if "left" in data[key] and "right" in data[key]:
                        avg_distance = (data[key]["left"] + data[key]["right"]) / 2
                        agv_data["odometry"]["total_distance"] = avg_distance
                    agv_data["odometry"].update(data[key])
                else:
                    agv_data[key] = data[key]
        
        # 수신된 데이터 터미널에 출력
        print("--- AGV Data Received ---")
        print(f"  Timestamp: {data.get('timestamp')}")
        print(f"  Position:  {data.get('position')}")
        print(f"  Tag1:      {data.get('tag1', 0)}")
        print(f"  Speed:     {data.get('speed', 0)}")
        print("-------------------------\n")

        # 서버 상태 머신 처리 (기본 데이터 업데이트 후)
        print(f"[DEBUG] process_server_state_machine() 호출: current_state={get_state_name()}")
        process_server_state_machine()

        # Update position and append to trajectory
        if "position" in data:
            # 실제 AGV 위치 대신 웹 시뮬레이션 위치 업데이트
            # (내부에서 check_web_agv_near_tag 자동 호출)
            update_web_agv_position(data["position"])

        # Update rotation angle
        if "rotation" in data:
            agv_data["rotation"] = data["rotation"]

        # RF-Tag 데이터 처리 (두 가지 형식 지원)
        # 1. rf_tag 형식 (기존 클라이언트)
        # 2. tag1, tag2 형식 (시뮬레이션 클라이언트)
        detected_tag = 0
        speed_limit = 200
        
        if "rf_tag" in data and data["rf_tag"] and isinstance(data["rf_tag"], dict):
            client_rf_tag = data["rf_tag"]
            # None 체크 추가
            if "tag_id" in client_rf_tag and client_rf_tag["tag_id"] is not None:
                detected_tag = int(client_rf_tag["tag_id"])
            if "speed_limit" in client_rf_tag and client_rf_tag["speed_limit"] is not None:
                speed_limit = int(client_rf_tag["speed_limit"])
        
        # tag1, tag2 형식 우선 처리 (있으면 덮어쓰기)
        if "tag1" in data:
            detected_tag = data.get("tag1", 0) or 0
        if "tag2" in data:
            speed_limit = data.get("tag2", 200) or 200
        
        if detected_tag > 0:
            prev_tag = agv_data["rf_tag"].get("current_tag", 0)
            
            agv_data["rf_tag"]["current_tag"] = detected_tag
            agv_data["rf_tag"]["last_detected"] = detected_tag
            agv_data["rf_tag"]["speed_limit"] = speed_limit
            
            if "passed_tags" not in agv_data["rf_tag"]:
                agv_data["rf_tag"]["passed_tags"] = []
            if detected_tag not in agv_data["rf_tag"]["passed_tags"]:
                agv_data["rf_tag"]["passed_tags"].append(detected_tag)
                current_pos = agv_data.get("position", {})
                print(f"🏷️ RF-Tag {detected_tag} 감지! at ({current_pos.get('x', 0)}, {current_pos.get('y', 0)})")
                print(f"🚀 속도 제한: {speed_limit} mm/s")
                
                # ✅ 핵심: 태그 감지 시 웹 AGV 위치를 해당 태그로 리셋
                reset_agv_position_to_tag(detected_tag)
                
                # 태그 감지시 웹 AGV 이동 재시작
                global web_agv_moving
                web_agv_moving = True
        elif detected_tag == 0:
            # 태그 영역 벗어남
            agv_data["rf_tag"]["current_tag"] = 0

        # lidar_distance 업데이트 (여러 형식 지원)
        if "lidar_distance" in data:
            agv_data["lidar_distance"] = data["lidar_distance"]
        elif "ultrasonic" in data:
            agv_data["lidar_distance"] = data["ultrasonic"]
        elif "sensors" in data and isinstance(data["sensors"], dict):
            if "lidar_distance" in data["sensors"]:
                agv_data["lidar_distance"] = data["sensors"]["lidar_distance"]
        
        # estop_status 처리 (클라이언트가 보내는 OBS-EStop, Push-EStop 등)
        if "estop_status" in data:
            agv_data["estop_status"] = data["estop_status"]
            # estop_status를 status에도 반영 (process_server_state_machine에서 사용)
            if data["estop_status"]:
                agv_data["status"] = data["estop_status"]
        
        # 서버에서 관리하는 상태를 agv_data에 반영 (estop이 없을 때만)
        if not agv_data.get("estop_status"):
            agv_data["status"] = get_state_name(current_agv_state)

        # Stop 상태 감지 시 5초 후 Ready 전환 및 시작점으로 위치 초기화 스케줄
        try:
            from threading import Thread as _Thread
            import time as _time
            global stop_reset_timer_active
            if agv_data.get("status") == "Stop" and not stop_reset_timer_active:
                stop_reset_timer_active = True
                def _delayed_reset():
                    try:
                        _time.sleep(5)
                        # 클라이언트 포즈 리셋 시도
                        try:
                            r2 = requests.post(f"{AGV_CLIENT_URL}/reset_pose", timeout=3)
                            print(f"'RESET_POSE' (delayed) 전송: {r2.status_code}")
                        except requests.exceptions.RequestException as _e:
                            print(f"RESET_POSE (delayed) 전송 실패: {_e}")
                        # 서버 시각화 리셋 및 Ready 전환
                        start_wp = RF_TAG_POSITIONS.get(1, {"x": 1491, "y": 620})
                        agv_data["position"] = {"x": start_wp["x"], "y": start_wp["y"]}
                        agv_data["rotation"] = 0
                        agv_data["trajectory"] = []
                        # 상태가 아직 Stop이면 Ready로 갱신
                        if agv_data.get("status") == "Stop":
                            agv_data["status"] = "Ready"
                        print("⏱️ Stop → 5초 경과: Ready 전환 및 시작점으로 위치 초기화 완료")
                    finally:
                        global stop_reset_timer_active
                        stop_reset_timer_active = False
                _Thread(target=_delayed_reset, daemon=True).start()
        except Exception as _e:
            print(f"Stop 지연 초기화 스케줄 실패: {_e}")
                    
        return jsonify({
            "status": "success", 
            "message": "Data updated",
            "rf_tag_status": agv_data["rf_tag"]
        }), 200
    return jsonify({"status": "error", "message": "Invalid data"}), 400

def check_rf_tag_proximity(x, y, threshold=50):
    """현재 위치에서 가장 가까운 RF-Tag를 찾습니다."""
    for tag_id, tag_info in RF_TAG_POSITIONS.items():
        distance = math.sqrt((x - tag_info["x"])**2 + (y - tag_info["y"])**2)
        if distance <= threshold:
            return tag_id
    return None

@app.route('/command', methods=['POST'])
def send_command():
    global current_agv_state
    command = request.form.get("command")
    try:
        if command == "go":
            # GO 버튼: Ready 또는 Paused 상태에서 Running으로 전환
            if current_agv_state == AGVState.READY:
                change_agv_state(AGVState.RUNNING, "GO button pressed (Ready → Running)")
                print(f"'GO' 명령: Ready → Running 전환")
                return jsonify({"status": "success", "message": "Started from Ready"}), 200
            elif current_agv_state == AGVState.PAUSED:
                change_agv_state(AGVState.RUNNING, "GO button pressed (Paused → Running)")
                print(f"'GO' 명령: Paused → Running 전환")
                return jsonify({"status": "success", "message": "Resumed from Paused"}), 200
            else:
                print(f"'GO' 명령 무시: 현재 상태 = {get_state_name()}")
                return jsonify({"status": "warning", "message": f"Cannot GO from {get_state_name()}"}), 200
        elif command == "pause":
            if current_agv_state == AGVState.RUNNING:
                change_agv_state(AGVState.PAUSED, "PAUSE button pressed")
                print(f"'PAUSE' 명령: Running → Paused 전환")
                return jsonify({"status": "success", "message": "Paused"}), 200
            else:
                print(f"'PAUSE' 명령 무시: 현재 상태 = {get_state_name()}")
                return jsonify({"status": "warning", "message": f"Cannot PAUSE from {get_state_name()}"}), 200
        elif command == "E-stop":
            change_agv_state(AGVState.SRV_ESTOP, "E-STOP button pressed")
            print(f"'E-STOP' 비상정지 명령")
            return jsonify({"status": "success", "message": "E-STOP activated"}), 200
        elif command == "resume":
            # RESUME 버튼은 이제 GO 버튼으로 대체됨 (호환성 유지)
            if current_agv_state == AGVState.PAUSED:
                change_agv_state(AGVState.RUNNING, "RESUME button pressed")
                print(f"'RESUME' 명령: Paused → Running 전환")
                return jsonify({"status": "success", "message": "Resumed"}), 200
            else:
                print(f"'RESUME' 명령 무시: 현재 상태 = {get_state_name()}")
                return jsonify({"status": "warning", "message": f"Cannot RESUME from {get_state_name()}"}), 200
        elif command == "stop":
            response = requests.post(f"{AGV_CLIENT_URL}/stop", timeout=3)
            response.raise_for_status()
            print(f"'STOP' 명령 전송: {response.json()}")
            return jsonify({"status": "success", "message": "STOP command sent (reset scheduled on Stop state)"}), 200
        elif command == "home":
            response = requests.post(f"{AGV_CLIENT_URL}/home", timeout=3)
            # 일부 클라이언트에 /home 미구현일 수 있으므로 실패 시 메시지 안내
            if response.status_code >= 400:
                return jsonify({"status": "error", "message": "Client does not support HOME"}), 501
            print(f"'HOME' 명령 전송: {response.json()}")
            return jsonify({"status": "success", "message": "HOME command sent"}), 200
        else:
            print(f"Unknown command received: {command}")
            return jsonify({"status": "error", "message": "Unknown command"}), 400
    except requests.exceptions.RequestException as e:
        print(f"AGV 클라이언트에 명령 전송 실패: {e}")
        return jsonify({"status": "error", "message": "Failed to send command to AGV"}), 500

@app.route('/acknowledge_estop', methods=['POST'])
def acknowledge_estop():
    """E-Stop 확인 후 ABNORMAL로 전환"""
    global current_agv_state
    
    if current_agv_state in [AGVState.PUSH_ESTOP, AGVState.SRV_ESTOP]:
        estop_type = get_state_name(current_agv_state)
        change_agv_state(AGVState.ABNORMAL, f"User acknowledged {estop_type}")
        print(f"✅ 사용자가 {estop_type} 확인 → ABNORMAL 전환")
        return jsonify({"status": "success", "message": f"Acknowledged {estop_type}, transitioned to Abnormal"}), 200
    else:
        return jsonify({"status": "warning", "message": f"Not in E-Stop state (current: {get_state_name()})"}), 200

@app.route('/rf_tags')
def get_rf_tags():
    """RF-Tag 위치 정보를 반환합니다."""
    return jsonify(RF_TAG_POSITIONS)

@app.route('/tag_nums')
def get_tag_nums():
    """사각형으로 표시할 태그 번호 정보(visible=true만)를 반환합니다."""
    result = {}
    for tid, info in TAG_NUMS.items():
        if info.get('visible', True):
            side = info.get('location', 'right')
            # 기존 대비 5px 더 멀리 배치 (14 -> 19)
            ox, oy = _offset_by_normal(info['x'], info['y'], side=side, offset=19)
            result[str(tid)] = {
                'x': int(ox),
                'y': int(oy),
                'location': side
            }
    return jsonify(result)

@app.route('/agv_status')
def get_agv_status():
    """AGV의 현재 상태를 반환합니다."""
    return jsonify({
        "position": agv_data["position"],
        "status": agv_data["status"],
        "current_rf_tag": agv_data["rf_tag"].get("current_tag", 0),
        "total_distance": agv_data["odometry"].get("total_distance", 0),
        "speed": agv_data["speed"],
        "battery": agv_data["battery_soc"]
    })

if __name__ == '__main__':
    # 웹 AGV 초기 위치를 시작점(Tag 1)으로 설정
    start_tag = RF_TAG_POSITIONS.get(1, {"x": 1491, "y": 620})
    web_agv_position["x"] = start_tag["x"]
    web_agv_position["y"] = start_tag["y"]
    web_agv_target["x"] = start_tag["x"]
    web_agv_target["y"] = start_tag["y"]
    agv_data["position"] = {"x": start_tag["x"], "y": start_tag["y"]}
    print(f"🚀 웹 AGV 초기 위치: Tag 1 → ({start_tag['x']}, {start_tag['y']})")
    
    # 서버 프로그램은 5000번 포트로 실행됩니다.
    # LAN 내 다른 기기에서도 접속할 수 있도록 0.0.0.0에 바인딩
    # 보안이 필요한 환경에서는 방화벽 또는 리버스 프록시로 보호하세요.
    lan_ip = _get_local_ip()
    print("")
    print("========================================")
    print(" AGV Station Server Ready")
    print("----------------------------------------")
    print(f" 이 장치에서 접속:   http://{lan_ip}:5000")
    print(f" 다른 PC/모바일에서: http://{lan_ip}:5000")
    print("========================================")
    app.run(host="0.0.0.0", port=5000, debug=False)

