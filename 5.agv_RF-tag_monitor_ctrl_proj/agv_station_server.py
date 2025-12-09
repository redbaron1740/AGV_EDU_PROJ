from flask import Flask, jsonify, render_template, request
import threading
import time
import math
from enum import Enum

# AGV Path & Waypoints Backend for start.html
app = Flask(__name__, template_folder='templates')

client_list = set()  # 접속 중인 클라이언트 관리

# [삭제 용이] AGV 궤적 로그 함수
def log_agv_info(str):
    with open('agv_log.txt', 'a') as f:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        f.write(f"{timestamp} - {str}\n")
        
        
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
        
agv_info_to_web = {
    "rf_tag": 0,
    "target_tag": 0,
    "lidar_distance": 0,
    "speed_limit": 0,
    "current_speed": 0,
    "state": "INITIAL"
} 

agv_client_info = {
    "SOC": 100, # State of Charge
    "LIDAR": 1200, # LIDAR distance in mm
    "RF_TAG": 0, # Current RF-Tag ID
    "SPEED_LIMIT": 0, # Speed limit from RF-Tag
    "CURRENT_SPEED": 0, # Current speed in mm/s
    "STATE": 0, # AGV 상태: INITIAL : communicated with AGV and sensors
                       #  READY  - Ready for lane-tracing, connected to server, Tx with agv data 
                       #  RUNNING - Detect rf-tag, obstacle, monitoring pushed button and lane-tracing 
                       #  OBS_ESTOP
                       #  PUSH_BUTTON_ESTOP
                       #  abnormal
    "Alv_cnt": 0
}

server_state = AGV_STATE_INITIAL
server_cmd_agv = CMD_AGV.NONE
web_push_estop = False
agv_push_estop = False
agv_client_state = AGV_STATE_INITIAL
agv_client_cnt = 0
wp_id = 0
warning_msg_box = ""
warning_type = None

cmd_data_to_client = {
    'From_server_cmd': 0,
    'Alv_cnt' : 0
}

# 서버에서 클라이언트로 송신할 데이터 REST API
@app.route('/server_data')
def api_server_data():
    global cmd_data_to_client ,server_cmd_agv
    
    cmd_data_to_client["From_server_cmd"] = CMD_AGV.NONE.value if server_cmd_agv == CMD_AGV.NONE else server_cmd_agv.value
    cmd_data_to_client["Alv_cnt"] += 1
    return jsonify(cmd_data_to_client)

@app.route('/client_data', methods=['POST'])
def receive_client_data():
    global agv_client_info, agv_client_cnt, agv_client_state, wp_id,agv_speed

    agv_client_info = request.get_json()
    
    agv_info_to_web["battery_soc"] = agv_client_info["SOC"]
    agv_info_to_web["lidar_distance"] = agv_client_info["LIDAR"]
    wp_id = agv_info_to_web["rf_tag"] = agv_client_info["RF_TAG"]
    agv_info_to_web["target_tag"] = agv_client_info["RF_TAG"]+1
    
    agv_speed = agv_info_to_web["speed_limit"] = agv_client_info["SPEED_LIMIT"]
    agv_speed /= 100
    agv_info_to_web["current_speed"] = agv_client_info["CURRENT_SPEED"]
     
    agv_client_cnt = agv_client_info["Alv_cnt"]    
    agv_client_state = agv_client_info["STATE"]
    
    return jsonify({'status': 'ok'})


def on_operating_state():
    global server_state, agv_info_to_web,  server_cmd_agv, target_reached, target_wp_id, wp_id
    global web_push_estop, agv_push_estop, agv_client_state, agv_client_cnt, warning_msg_box, warning_type
    
    
    timeout : int = 0
    time_elapsed : float = 0.1
    
    curr_target_wp_id = 0
    
    while True:

        if server_state == AGV_STATE_INITIAL:
    
            agv_info_to_web["state"] = "INITIAL"   
            server_cmd_agv = CMD_AGV.NONE
            time_elapsed = 0.1


            if agv_client_state == AGV_STATE_READY:
                server_state = AGV_STATE_READY
            else:
                timeout += 1
                
                if timeout > 100:
                    server_state = AGV_STATE_ABNORMAL
                    warning_type = ''
                    
        elif server_state == AGV_STATE_READY:
            time_elapsed = 0.1
            agv_info_to_web["state"] = "READY"
            
            if server_cmd_agv == CMD_AGV.GO:
                server_state = AGV_STATE_RUNNING
                
            if server_cmd_agv == CMD_AGV.ESTOP:
                server_state = AGV_STATE_SERVER_BUTTON_ESTOP    
                
            if agv_client_state == AGV_STATE_PUSH_BUTTON_ESTOP:
                server_state = AGV_STATE_PUSH_BUTTON_ESTOP

        elif server_state == AGV_STATE_RUNNING:
            time_elapsed = 0.02

            #log_agv_info(f"server_cmd_agv: {server_cmd_agv}, target_id: {target_wp_id}, wp_id: {wp_id}, target_reached: {target_reached}")
            agv_info_to_web["state"] = "RUNNING"


                
            if server_cmd_agv == CMD_AGV.ESTOP:
                server_state = AGV_STATE_SERVER_BUTTON_ESTOP    
                
            if agv_client_state == AGV_STATE_OBSTACLE_ESTOP:
                server_state = AGV_STATE_OBSTACLE_ESTOP
                
            if agv_client_state == AGV_STATE_PUSH_BUTTON_ESTOP:
                server_state = AGV_STATE_PUSH_BUTTON_ESTOP                
                
            if server_cmd_agv == CMD_AGV.PAUSE:
                time_elapsed = 0.1
            elif server_cmd_agv == CMD_AGV.GO or server_cmd_agv == CMD_AGV.RESUME:
                # log_agv_info(f"AGV Target WP ID: {target_wp_id}, current Target: {wp_id}, Reached: {target_reached}, \
                #             cmd: {server_cmd_agv}, state: {agv_client_state}")

                if curr_target_wp_id != wp_id:
                    if target_wp_id == None and any(w['id'] == wp_id for w in waypoints):
                        target_wp_id = wp_id
                        curr_target_wp_id = wp_id
                        target_reached = False     
                        
                    


                move_agv()
                

        elif server_state == AGV_STATE_OBSTACLE_ESTOP:
            time_elapsed = 0.1
            warning_type = 'OBSTACLE_ESTOP'
            agv_info_to_web["state"] = "OBSTACLE E-STOP"
            warning_msg_box = "장애물 감지! AGV 일시 정지!"
            
            if agv_client_state == AGV_STATE_RUNNING:
                server_state = AGV_STATE_RUNNING
                warning_type = 'OBSTACLE_RELEASE'
                warning_msg_box = ""

        elif server_state == AGV_STATE_PUSH_BUTTON_ESTOP:  # state 4
            time_elapsed = .2
            agv_info_to_web["state"] = "AGV E-STOP"
            warning_type = 'PUSH_ESTOP'
            server_state = AGV_STATE_ABNORMAL
    
        elif server_state == AGV_STATE_SERVER_BUTTON_ESTOP:
            time_elapsed = .2
            agv_info_to_web["state"] = "SERVER E-STOP"
            warning_type = 'SERVER_ESTOP'
            server_state = AGV_STATE_ABNORMAL

        elif server_state == AGV_STATE_ABNORMAL:
            time_elapsed = 10
            agv_info_to_web["state"] = "ABNORMAL"
            
            if warning_type is None:
                warning_msg_box = "AGV 장애 발생! 새로 시작 필요!!"
            elif warning_type == 'PUSH_ESTOP':
                warning_msg_box = "AGV의 물리적 비상정지 버튼이 눌렸습니다."
            elif warning_type == 'SERVER_ESTOP':
                warning_msg_box = "서버에서 비상정지 명령이 실행되었습니다."
            
            
        time.sleep(time_elapsed)


# AGV simulation state
agv_position = {'x': 1491, 'y': 640, 'heading': 0}  # heading=0으로 초기화 (정방향)
agv_segment_index = 0  # Segment in path
agv_step = 0.0         # Progress along segment (0~1)
agv_speed = 1.0        # pixels per update (can be tuned)

target_wp_id = None
target_reached = True

driving_path = [
    {"type": "line",  "x1": 1491, "y1": 640, "x2": 1491, "y2": 600},
    {"type": "line",  "x1": 1491, "y1": 600, "x2": 1491, "y2": 375},
    {"type": "curve", "d": "M 1491 375 Q 1487 310 1400 300"},
    {"type": "line",  "x1": 1400, "y1": 300, "x2": 918,  "y2": 300},
    {"type": "line",  "x1": 920,  "y1": 300, "x2": 843,  "y2": 248},
    {"type": "line",  "x1": 844,  "y1": 248, "x2": 680,  "y2": 248},
    {"type": "line",  "x1": 680,  "y1": 248, "x2": 605,  "y2": 300},
    {"type": "line",  "x1": 605,  "y1": 300, "x2": 180,  "y2": 300},
    {"type": "curve", "d": "M 181 300 Q 132 310 116 375"},
    {"type": "line",  "x1": 116,  "y1": 375, "x2": 116,  "y2": 620}
]
        
waypoints = [
    {"id": 0, "x": 1491, "y": 640, "visible": False, "offset_x": 0, "offset_y": 0},
    {"id": 1, "x": 1491, "y": 600, "visible": True, "offset_x": +25, "offset_y": 0},
    {"id": 2, "x": 1491, "y": 375, "visible": True, "offset_x": +25, "offset_y": 0},
    {"id": 3, "x": 1400, "y": 300, "visible": True, "offset_x": 0, "offset_y": -25},
    {"id": 4, "x": 918,  "y": 300, "visible": True, "offset_x": 0, "offset_y": -25},
    {"id": 5, "x": 843,  "y": 248, "visible": True, "offset_x": 0, "offset_y": -25},
    {"id": 6, "x": 680,  "y": 248, "visible": True, "offset_x": 0, "offset_y": -25},
    {"id": 7, "x": 605,  "y": 300, "visible": True, "offset_x": 0, "offset_y": -25},
    {"id": 8, "x": 180,  "y": 300, "visible": True, "offset_x": 0, "offset_y": -25},
    {"id": 9, "x": 116,  "y": 375, "visible": True, "offset_x": -25, "offset_y": 0},
    {"id": 10, "x": 116, "y": 620, "visible": True, "offset_x": -25, "offset_y": 0}
]

def get_segment_length(seg):
    if seg['type'] == 'line':
        dx = seg['x2'] - seg['x1']
        dy = seg['y2'] - seg['y1']
        return math.hypot(dx, dy)
    elif seg['type'] == 'curve':

        import re
        nums = list(map(float, re.findall(r"[-+]?[0-9]*\.?[0-9]+", seg['d'])))

        if len(nums) >= 6:
            x0, y0, cx, cy, x1, y1 = nums[0], nums[1], nums[2], nums[3], nums[4], nums[5]
            length = 0.0
            prev = (x0, y0)
            
            for i in range(1, 51):
                t = i / 50.0
                mt = 1 - t
                bx = mt*mt*x0 + 2*mt*t*cx + t*t*x1
                by = mt*mt*y0 + 2*mt*t*cy + t*t*y1
                length += math.hypot(bx - prev[0], by - prev[1])
                prev = (bx, by)
                
            return length
        return 1.0

def get_position_and_heading(seg, t):
    if seg['type'] == 'line':
        x = seg['x1'] + (seg['x2'] - seg['x1']) * t
        y = seg['y1'] + (seg['y2'] - seg['y1']) * t
        heading = math.atan2(seg['y2'] - seg['y1'], seg['x2'] - seg['x1'])
        return x, y, heading

    elif seg['type'] == 'curve':
        import re
        nums = list(map(float, re.findall(r"[-+]?[0-9]*\.?[0-9]+", seg['d'])))
        if len(nums) >= 6:
            x0, y0, cx, cy, x1, y1 = nums[0], nums[1], nums[2], nums[3], nums[4], nums[5]
            mt = 1 - t
            x = mt*mt*x0 + 2*mt*t*cx + t*t*x1
            y = mt*mt*y0 + 2*mt*t*cy + t*t*y1
            dx = 2*mt*(cx-x0) + 2*t*(x1-cx)
            dy = 2*mt*(cy-y0) + 2*t*(y1-cy)
            heading = math.atan2(dy, dx)
            return x, y, heading

    return 0, 0, 0

def move_agv():
    global target_wp_id, target_reached, agv_speed
    
    
    #log_agv_info(f"AGV Position: x={agv_position['x']:.2f}, y={agv_position['y']:.2f}, heading={math.degrees(agv_position['heading']):.2f} deg")
        
    if target_wp_id is not None:
        # Find target waypoint index in waypoints
        wp_idx = next((i for i, w in enumerate( waypoints) if w['id'] == target_wp_id), None)
        if wp_idx is not None and wp_idx > 0:
            # AGV는 이전 waypoint에서 target waypoint까지 경로 segment를 따라 이동
            prev_wp = waypoints[wp_idx-1]
            target_wp = waypoints[wp_idx]
            # 경로 segment 찾기 (가장 가까운 segment)
            seg_idx = min(len(driving_path)-1, wp_idx-1)
            seg = driving_path[seg_idx]
            # AGV가 segment를 따라 t=0~1로 이동
            # t 계산: 현재 위치에서 segment 시작점까지 거리, segment 전체 길이
            seg_len = get_segment_length(seg)
            # [삭제 용이] 각 segment별 속도 적용
            seg_speed = agv_speed
            # t 증가 속도: seg_speed/seg_len
            if 't' not in agv_position:
                agv_position['t'] = 0.0
                # t=0에서 heading 계산
                _, _, heading0 = get_position_and_heading(seg, 0.0)
                # dx, dy가 0이면(heading0==0) t=0.01에서 heading을 강제 설정
                if abs(heading0) < 1e-6:
                    _, _, heading = get_position_and_heading(seg, 0.01)
                    agv_position['heading'] = heading
                else:
                    agv_position['heading'] = heading0
                    
            t = agv_position['t']
            t += seg_speed / seg_len
            
            if t >= .99:
                # 도착: 정확히 target waypoint 위치로 이동
                agv_position['x'] = target_wp['x']
                agv_position['y'] = target_wp['y']
                x, y, heading = get_position_and_heading(seg, 1.0)
                # heading이 0(즉, dx=0, dy=0)이면 이전 heading 유지
                if abs(heading) < 1e-6 and 'heading' in agv_position:
                    heading = agv_position['heading']
                agv_position['heading'] = heading
                agv_position['t'] = 1.0  # t를 1.0으로 고정 (0으로 초기화하지 않음)
                target_reached = True
                target_wp_id = None
            else:
                x, y, heading = get_position_and_heading(seg, t)
                agv_position['x'] = x
                agv_position['y'] = y
                agv_position['heading'] = heading
                agv_position['t'] = t
                target_reached = False
        else:
            target_wp_id = None
    else:
        agv_position['t'] = 0.0
         
# API to get current AGV position
@app.route('/agv_position')
def api_agv_position():
    pos = dict(agv_position)
    return jsonify(pos)

@app.route('/set_cmd_agv', methods=['POST'])
def api_agv_cmd():
    global server_cmd_agv #, target_wp_id, target_reached

    data = request.get_json()
    cmd = data.get('command') if data else None
    wp_id1 = data.get('wp_id') if data else None

    if cmd == 'GO':
        server_cmd_agv = CMD_AGV.GO
        return jsonify({'status': 'ok', 'target': wp_id1, 'msg': 'AGV started'})
    
    elif cmd == 'ESTOP':
        server_cmd_agv = CMD_AGV.ESTOP
        return jsonify({'status': 'ok', 'msg': 'AGV stopped'})
    elif cmd == 'PAUSE':
        server_cmd_agv = CMD_AGV.PAUSE
        return jsonify({'status': 'ok', 'msg': 'AGV paused'})
    elif cmd == 'RESUME':
        server_cmd_agv = CMD_AGV.RESUME
        return jsonify({'status': 'ok', 'msg': 'AGV resumed'})
    else:
        server_cmd_agv = CMD_AGV.NONE
        return jsonify({'status': 'error', 'msg': 'Invalid command'})

#API to send Warning Message Box to Web
@app.route('/check_warning')
def api_send_warning():
    global server_state , warning_msg_box, warning_type
    # warning_type is set in on_operating_state, but ensure it's global

    #log_agv_info(f"Warning check: server_state={server_state}, type={warning_type}, msg={warning_msg_box}")

    # ABNORMAL 상태
    if server_state == AGV_STATE_ABNORMAL:
        if warning_type == 'PUSH_ESTOP':
            return jsonify({'warning_type': 'Push-estop', 'msg': warning_msg_box})
        elif warning_type == 'SERVER_ESTOP':
            return jsonify({'warning_type': 'Srv-estop', 'msg': warning_msg_box})
        else:
            return jsonify({'warning_type': 'Abnormal', 'msg': warning_msg_box})
    # 장애물 E-STOP 상태
    elif server_state == AGV_STATE_OBSTACLE_ESTOP:
        if warning_type == 'OBSTACLE_ESTOP':
            return jsonify({'warning_type': 'Obstacle-estop', 'msg': warning_msg_box})
        elif warning_type == 'OBSTACLE_RELEASE':
            return jsonify({'warning_type': 'Release-Obstacle', 'msg': ''})
        else:
            return jsonify({'warning_type': 'Obstacle-estop', 'msg': warning_msg_box})
    # 경고 없음
    return jsonify({})

# API to get driving path
@app.route('/driving_path')
def api_driving_path():
    return jsonify(driving_path)

# API to get waypoints
@app.route('/waypoints')
def api_waypoints():
    return jsonify(waypoints)

# AGV 상태 정보를 웹페이지로 전송하는 API
@app.route('/agv_data')
def agv_data():
    return jsonify(agv_info_to_web)

# Serve index.html at root
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    #threading.Thread(target=move_agv, daemon=True).start()
    threading.Thread(target=on_operating_state, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)


