import time
import curses
from Donkibot_i import Comm

# 시리얼 포트 설정
PORT = '/dev/ttyUSB0'  # ttyUSB0
BAUDRATE = 115200

def draw_menu(stdscr):
    """메인 메뉴를 화면에 그립니다."""
    stdscr.clear()
    stdscr.addstr(0, 0, "AGV 제어 프로그램 (q: 종료)")
    stdscr.addstr(2, 2, "1. 데이터 실시간 표시")
    stdscr.addstr(3, 2, "2. TFS 와이어 제어")
    stdscr.addstr(5, 0, "원하는 메뉴의 번호를 누르세요...")
    stdscr.refresh()

def display_data_mode(stdscr, agv):
    """실시간 데이터를 화면에 출력하는 모드"""
    stdscr.clear()
    stdscr.nodelay(True)
    
    while True:
        key = stdscr.getch()
        if key in [ord('m'), ord('M'), 27]: # 'm' 또는 ESC 키
            break

        try:
            agv_status = agv.get_latest_data()
            
            stdscr.addstr(0, 0, "실시간 데이터 표시 (m: 메뉴로 돌아가기)")
            stdscr.addstr(2, 0, f"AGV 상태        | {agv_status.agvStatus:>10d}")
            stdscr.addstr(3, 0, f"배터리 SOC      | {agv_status.SOC:>9d} %")
            stdscr.addstr(4, 0, f"라인 위치       | {agv_status.LinePos:>10d}")
            stdscr.addstr(5, 0, f"비상정지 플래그 | {agv_status.EmgFlag:>10d}")
            stdscr.addstr(6, 0, f"라이다 거리     | {agv_status.LidarDistance:>7d} mm")
            stdscr.addstr(7, 0, f"TFS 각도        | {agv_status.TfsAngle:>9d} °")
            stdscr.addstr(8, 0, f"TFS 거리        | {agv_status.TfsDistance:>7d} mm")
            stdscr.addstr(9, 0, f"속도            | {agv_status.Speed:>10d}")
            stdscr.addstr(10, 0, f"주행거리        | {agv_status.Odometer:>10d}")
            
            stdscr.addstr(12, 0, f"마지막 업데이트: {time.strftime('%H:%M:%S')}")
            stdscr.refresh()
            
        except Exception as e:
            stdscr.addstr(14, 0, f"데이터 수신 오류: {e}")
            stdscr.refresh()
        
        time.sleep(0.1)
    
    stdscr.nodelay(False)

def tfs_control_mode(stdscr, agv):
    """TFS 센서 값에 따라 AGV를 제어하는 모드"""
    stdscr.clear()
    stdscr.nodelay(True)
    
    # 제어 파라미터 (필요시 조정)
    BASE_SPEED = 200  # 기본 전진 속도
    MAX_TURN_SPEED = 150 # 최대 회전 속도
    DISTANCE_THRESHOLD = 100 # 전진을 시작하는 최소 거리 (mm)
    SPEED_LIMIT = 200 # 최대 속도 제한
    
    # 제어 주기 설정
    CONTROL_INTERVAL = 0.05  # 50ms
    last_control_time = 0
    
    while True:
        key = stdscr.getch()
        if key in [ord('m'), ord('M'), 27]:
            agv.CLR(0, 0) # 메뉴로 돌아가기 전 정지
            break

        current_time = time.time()
        
        # 50ms 마다 제어 명령 전송
        if current_time - last_control_time < CONTROL_INTERVAL:
            time.sleep(0.005) # 짧은 대기
            continue
            
        last_control_time = current_time

        try:
            s = agv.get_latest_data()
            vl, vr = 0, 0 # 기본값은 정지

            # 제어 로직 (CLR 사용)
            if s.TfsDistance >= DISTANCE_THRESHOLD:
                # 각도에 따라 좌우 바퀴 속도 차등 분배
                # TfsAngle: 양수 -> 왼쪽으로 당김, 음수 -> 오른쪽으로 당김
                turn_effect = int((s.TfsAngle / 90.0) * MAX_TURN_SPEED) * 4
                
                vl = BASE_SPEED + turn_effect
                vr = BASE_SPEED - turn_effect
                
                # 속도 범위 제한
                vl = max(-SPEED_LIMIT, min(SPEED_LIMIT, vl))
                vr = max(-SPEED_LIMIT, min(SPEED_LIMIT, vr))

            agv.CLR(-vl, -vr)

            # 화면 표시 (매번 갱신)
            stdscr.clear()
            stdscr.addstr(0, 0, "TFS 와이어 제어 모드 (m: 메뉴로 돌아가기)")
            stdscr.addstr(2, 0, f"TFS Pulled Distance: {s.TfsDistance:4d} mm")
            stdscr.addstr(3, 0, f"TFS Rotary Angle   : {s.TfsAngle:4d} °")
            stdscr.addstr(5, 0, f"명령: Left Wheel={vl}, Right Wheel={vr}")
            
            if vl == 0 and vr == 0:
                stdscr.addstr(7, 0, "상태: 정지")
            else:
                stdscr.addstr(7, 0, "상태: 주행 중")

            stdscr.refresh()

        except Exception as e:
            stdscr.addstr(9, 0, f"제어 오류: {e}")
            stdscr.refresh()
        
    stdscr.nodelay(False)
    agv.CLR(0, 0) # 모드 종료 시 확실히 정지
    
def main(stdscr):
    """메인 함수: 메뉴를 표시하고 선택된 모드를 실행합니다."""
    # curses 설정
    curses.curs_set(0)
    stdscr.nodelay(False) # 키 입력을 기다리도록 blocking 모드로 시작
    stdscr.timeout(-1)

    # 시리얼 포트 연결
    try:
        agv = Comm(port=PORT, baudrate=BAUDRATE)
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"오류: 포트 {PORT}를 열 수 없습니다. {e}")
        stdscr.addstr(1, 0, "포트 번호, 권한, 연결 상태를 확인하세요.")
        stdscr.addstr(3, 0, "아무 키나 누르면 종료됩니다.")
        stdscr.refresh()
        stdscr.getch()
        return

    running = True
    while running:
        draw_menu(stdscr)
        key = stdscr.getch()

        if key == ord('1'):
            display_data_mode(stdscr, agv)
        elif key == ord('2'):
            tfs_control_mode(stdscr, agv)
        elif key in [ord('q'), ord('Q'), 27]:
            running = False

    # 종료 처리
    agv.destroy()
    stdscr.clear()
    stdscr.addstr(0, 0, "프로그램이 종료되었습니다.")
    stdscr.refresh()
    time.sleep(1)

if __name__ == "__main__":
    curses.wrapper(main)
