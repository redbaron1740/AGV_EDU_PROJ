import os
import time
import csv
from datetime import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Thread, Lock
import eventlet
from Donkibot_i import Comm

# eventlet을 사용하여 비동기 네트워킹 활성화
eventlet.monkey_patch()

# --- 설정 ---
PORT = '/dev/ttyS0'  # 실제 시리얼 포트
BAUDRATE = 115200
LOG_DIR = 'logs'

# --- Flask 및 SocketIO 설정 ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# --- 전역 변수 및 스레드 관리 ---
thread = None
thread_lock = Lock()
agv_comm = None
is_logging = False
log_file_writer = None
log_file = None

def background_thread():
    """백그라운드에서 AGV 데이터를 읽고 클라이언트로 전송"""
    global agv_comm, is_logging, log_file_writer, log_file

    print("백그라운드 스레드 시작")
    while True:
        try:
            agv_comm.CLR(0,0)  
            s = agv_comm.get_latest_data()
            
            # 순수 센서 데이터만 전송
            data_to_send = {
                'distance': s.TfsDistance,
                'angle': s.TfsAngle,
                'speed': s.Speed,
                'soc': s.SOC,
                'lidar': s.LidarDistance,
                'line_pos': s.LinePos,
                'agv_status': s.agvStatus,
                'emg_flag': s.EmgFlag,
                'odometer': s.Odometer
            }
            
            socketio.emit('update_data', data_to_send)

            # 로깅 처리
            if is_logging and log_file_writer:
                log_file_writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                    s.agvStatus, s.SOC, s.LinePos, s.EmgFlag, s.LidarDistance,
                    s.TfsAngle, s.TfsDistance, s.Speed, s.Odometer
                ])
                log_file.flush()

        except Exception as e:
            print(f"백그라운드 스레드 오류: {e}")
        
        socketio.sleep(0.1) # 100ms 마다 데이터 전송

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """클라이언트 연결 처리"""
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
    print("클라이언트 연결됨")

@socketio.on('toggle_logging')
def handle_toggle_logging(data):
    """로깅 상태 변경 처리"""
    global is_logging, log_file, log_file_writer
    is_logging = data['status']
    
    if is_logging:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        filename = f"log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        filepath = os.path.join(LOG_DIR, filename)
        log_file = open(filepath, 'w', newline='')
        log_file_writer = csv.writer(log_file)
        # CSV 헤더 작성
        log_file_writer.writerow([
            'Timestamp', 'AGVStatus', 'SOC', 'LinePos', 'EmgFlag', 'LidarDist',
            'TfsAngle', 'TfsDist', 'Speed', 'Odometer'
        ])
        print(f"로깅 시작: {filepath}")
    else:
        if log_file:
            log_file.close()
            log_file = None
            log_file_writer = None
            print("로깅 중지")

def main():
    global agv_comm
    try:
        agv_comm = Comm(port=PORT, baudrate=BAUDRATE)
        time.sleep(0.5) # 데이터가 안정될 때까지 잠시 대기
        print(f"시리얼 포트 {PORT} 연결 성공")
        
        print("=" * 60)
        print("🚀 AGV 실시간 대시보드 웹 서버 시작")
        print("=" * 60)
        print(f"📡 로컬 접속: http://127.0.0.1:5000")
        print(f"🌐 네트워크 접속: http://0.0.0.0:5000")
        print(f"📂 로그 저장 위치: {os.path.abspath(LOG_DIR)}/")
        print("=" * 60)

        socketio.run(app, host='0.0.0.0', port=5000)

    except Exception as e:
        print(f"❌ 오류: 포트 {PORT}를 열 수 없습니다. {e}")
        print("포트 번호, 권한, 연결 상태를 확인하세요.")
    finally:
        if agv_comm:
            agv_comm.destroy()
        if log_file:
            log_file.close()
        print("프로그램 종료.")

if __name__ == "__main__":
    main()
