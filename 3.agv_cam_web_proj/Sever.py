from flask import Flask, Response, render_template_string, request, jsonify
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
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AGV 원격 제어 프로그램</title>
        <style>
            body { display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f0f0; }
            .container { background: #fff; padding: 40px 30px; border-radius: 12px; box-shadow: 0 0 20px rgba(0,0,0,0.1); text-align: center; }
            #video_area { margin-top: 20px; }
            #key_display { margin-top: 15px; font-size: 1.2em; color: #333; }
            .key-btns { margin-top: 20px; display: flex; justify-content: center; gap: 10px; }
            .key-btn { padding: 10px 18px; font-size: 1.1em; border-radius: 6px; border: 1px solid #ccc; background: #eee; color: #333; cursor: pointer; }
            .key-btn.active { background: #ff69b4; color: #fff; }
            button { padding: 12px 32px; font-size: 1.1em; border-radius: 6px; border: none; background: #007bff; color: #fff; cursor: pointer; margin-top: 10px; }
            button.on { background: #28a745; }
            button.off { background: #007bff; }
        </style>
        <script>
        let streaming = false;
        document.addEventListener('DOMContentLoaded', function() {
            const startBtn = document.getElementById('start_btn');
            const videoArea = document.getElementById('video_area');
            const keyBtns = document.querySelectorAll('.key-btn');

            function highlightKey(num) {
                keyBtns.forEach(btn => {
                    btn.classList.remove('active');
                    if (parseInt(btn.dataset.key) === num) btn.classList.add('active');
                });
            }

            startBtn.addEventListener('click', function() {
                streaming = !streaming;
                fetch('/toggle_stream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({streaming: streaming})
                });
                if (streaming) {
                    videoArea.innerHTML = '<img src="/video_feed" style="max-width:100%;border-radius:8px;">';
                    startBtn.classList.remove('off');
                    startBtn.classList.add('on');
                    startBtn.innerText = "원격 중지";
                } else {
                    videoArea.innerHTML = '';
                    startBtn.classList.remove('on');
                    startBtn.classList.add('off');
                    startBtn.innerText = "원격 시동";
                    highlightKey(0);
                }
            });

            // 키 버튼 클릭 이벤트
            keyBtns.forEach(btn => {
                btn.addEventListener('click', function() {
                    if (!streaming) return;
                    const keyNum = parseInt(btn.dataset.key);
                    fetch('/key_event', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({key: keyNum})
                    });
                    highlightKey(keyNum);
                });
            });

            // 키보드 이벤트
            document.addEventListener('keydown', function(e) {
                if (!streaming) return;
                let keyNum = 0;
                if(e.key === 'ArrowUp') keyNum = 2;
                else if(e.key === 'ArrowDown') keyNum = 3;
                else if(e.key === 'ArrowLeft') keyNum = 4;
                else if(e.key === 'ArrowRight') keyNum = 5;
                if(keyNum) {
                    e.preventDefault();
                    fetch('/key_event', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({key: keyNum})
                    });
                    highlightKey(keyNum);
                }
            });

            document.addEventListener('keyup', function(e) {
                if (!streaming) return;
                // 모든 RELEASE는 정지(1)로 처리
                fetch('/key_event', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({key: 1})
                });
                highlightKey(1);
            });
        });
        </script>
    </head>
    <body>
        <div class="container">
            <h2>AGV 원격 제어 프로그램</h2>
            <button id="start_btn" class="off">원격 시동</button>
            <div class="key-btns" style="display: flex; flex-direction: column; align-items: center; gap: 0;">
                <div>
                    <button class="key-btn" data-key="2" style="margin-bottom:10px;">↑</button>
                </div>
                <div style="display: flex; flex-direction: row; justify-content: center; align-items: center;">
                    <button class="key-btn" data-key="4" style="margin-right:10px;">←</button>
                    <button class="key-btn" data-key="1" style="margin:0 10px;">정지</button>
                    <button class="key-btn" data-key="5" style="margin-left:10px;">→</button>
                </div>
                <div>
                    <button class="key-btn" data-key="3" style="margin-top:10px;">↓</button>
                </div>
            </div>
            <div id="video_area"></div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

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
