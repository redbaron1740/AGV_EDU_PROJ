import time
import curses
from Donkibot_i import Comm

# 시리얼 포트 설정
PORT = '/dev/ttyUSB0'  # ttyUSB0
BAUDRATE = 115200

def tfs_control_mode(stdscr, agv):
    """TFS 센서 값에 따라 AGV를 제어하는 모드"""
    stdscr.clear()
    stdscr.nodelay(True)
    
    # 제어 파라미터 (필요시 조정)
    BASE_SPEED = 300  # 기본 전진 속도
    DISTANCE_THRESHOLD = 300 # 전진을 시작하는 최소 거리 (mm)
    DISTANCE_MAX_LIMIT = 3000 # 와이어 인식 최대 거리 (mm)
    SPEED_LIMIT = BASE_SPEED # 최대 속도 제한
    
    # 제어 주기 설정
    CONTROL_INTERVAL = 0.05  # 20ms
    last_control_time = 0
    vl, vr = 0, 0 # 기본값은 정지
    
    while True:
        key = stdscr.getch()
        if key in [ord('Q'), ord('q')]:
            vl, vr = 0, 0
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

            # 종방향 제어 로직 (CLR 사용)
            if s.TfsDistance >= DISTANCE_THRESHOLD:
                
                vl = int((s.TfsDistance / DISTANCE_MAX_LIMIT) * BASE_SPEED)
                vr = int((s.TfsDistance / DISTANCE_MAX_LIMIT) * BASE_SPEED)
                
                # 속도 범위 제한
                vl = max(-SPEED_LIMIT, min(SPEED_LIMIT, vl))
                vr = max(-SPEED_LIMIT, min(SPEED_LIMIT, vr))

            agv.CLR(-vl, -vr)

            # 화면 표시 (매번 갱신)
            stdscr.clear()
            stdscr.addstr(0, 0, "TFS 와이어 제어 모드 (m: 메뉴로 돌아가기)")
            stdscr.addstr(2, 0, f"TFS Pulled Distance: {s.TfsDistance:4d} mm")

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

    # 시리얼 포트 연결
    try:
        agv = Comm(port=PORT, baudrate=BAUDRATE)
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"오류: 포트 {PORT}를 열 수 없습니다. {e}")
        stdscr.addstr(1, 0, "포트 번호, 권한, 연결 상태를 확인하세요.")
        stdscr.addstr(3, 0, "종료합니다.")
        stdscr.refresh()
        stdscr.getch()
        return

    tfs_control_mode(stdscr, agv)

    # 종료 처리
    agv.destroy()
    stdscr.clear()
    stdscr.addstr(0, 0, "프로그램이 종료되었습니다.")
    stdscr.refresh()
    time.sleep(1)

if __name__ == "__main__":
    curses.wrapper(main)
