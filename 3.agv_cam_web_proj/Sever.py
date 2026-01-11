from flask import Flask, Response, render_template, request, jsonify
from realsense_cam import RealSenseCamera
from Donkibot_i import Comm
import threading
import time



app = Flask(__name__)
camera = RealSenseCamera(width=848,height=480,fps=30)
agv = Comm('/dev/ttyUSB0',115200) 

last_key = ""
last_key_time = 0
streaming = False
frame_lock = threading.Lock()

KEY_SPEED_MAP = {
    0: (0,0),
    1: (0,0),   # 키 릴리즈 시 정지 처리
    2: (-200,-200),   # ↑ 전진
    3: (200,200),   # ↓ 후진
    4: (100,-100),   # ← 좌회전
    5: (-100,100)    # → 우회전
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/toggle_stream', methods=['POST'])
def toggle_stream():
    global streaming, last_key
    data = request.get_json()
    streaming = bool(data.get('streaming', False))
    if not streaming:
        last_key = ""
    return jsonify(success=True)

@app.route('/key_event', methods=['POST'])
def key_event():
    global last_key, streaming, last_key_time
    if not streaming:
        return jsonify(success=False)
    data = request.get_json()
    key = data.get('key', '')
    now = time.time()
    # 0.2초 이내 같은 키는 무시 (debounce)
    if key == last_key and now - last_key_time < 0.1:
        return jsonify(success=True)
    last_key = key
    last_key_time = now

    try: 
        left_speed, right_speed = KEY_SPEED_MAP.get(key,(0,0))
        agv.CLR(left_speed,right_speed)

    except Exception as e:
        print(f'[Error] AGV 제어 실패:{e}')
        return jsonify(success = False)

    return jsonify(success=True)

def generate_frames():
    global streaming, last_key
    while True:
        with frame_lock:
            if not streaming:
                # 스트리밍이 꺼져 있으면 빈 프레임 반환
                time.sleep(0.1)
                continue
            frame = camera.get_frame(last_key)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
#                       b'Content-Type: image/webp\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
