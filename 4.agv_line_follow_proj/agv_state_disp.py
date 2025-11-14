import time
import curses
from Donkibot_i import Comm

# 시리얼 포트 설정
PORT = '/dev/ttyUSB0'  # 실제 환경에 맞게 변경
BAUDRATE = 115200

# AGV 제어 상태
agv_running = False
agv_paused = False

def draw_menu(stdscr):
    """메인 메뉴를 화면에 그립니다."""
    global agv_running, agv_paused
    stdscr.clear()
    stdscr.addstr(0, 0, "=" * 60)
    stdscr.addstr(1, 0, "           AGV LCU 라인 트레이싱 제어 실습 프로그램")
    stdscr.addstr(2, 0, "=" * 60)
    
    stdscr.addstr(4, 2, "1. 센서 데이터 실시간 모니터링")
    stdscr.addstr(6, 2, "q. 프로그램 종료")
  
    stdscr.addstr(8, 0, "메뉴를 선택하세요...")
    stdscr.refresh()

def display_data_mode(stdscr, agv):
    """실시간 데이터를 화면에 출력하는 모드"""
    stdscr.clear()
    stdscr.nodelay(True)
    
    while True:
        agv.CLR(0,0)      # 최소 명령을 주어야 응답함
        key = stdscr.getch()
        if key in [ord('m'), ord('M'), 27]: # 'm' 또는 ESC 키
            break

        try:
            #agv_status = None
            agv_status = agv.get_latest_data()


            str_temp = "agv_mode"
            if agv_status.agvStatus == 1:
                str_temp = "agv_python_mode"
            elif agv_status.agvStatus == 2:
                str_temp = "agv_ros_mode"

            stdscr.addstr(0, 0, "실시간 데이터 표시 (m: 메뉴로 돌아가기)")
            stdscr.addstr(2, 0, f"AGV 상태         | {str_temp:^10s}")
            stdscr.addstr(3, 0, f"배터리 SOC       | {agv_status.SOC:^10d} %")
            stdscr.addstr(4, 0, f"라인 위치        | {agv_status.LinePos:^10d}")
            stdscr.addstr(5, 0, f"비상정지 플래그  | {agv_status.EmgFlag:^10d}")
            stdscr.addstr(6, 0, f"라이다 거리      | {agv_status.LidarDistance:^10d} mm")
            stdscr.addstr(7, 0, f"TFS 각도         | {agv_status.TfsAngle:^10d} °")
            stdscr.addstr(8, 0, f"TFS 거리         | {agv_status.TfsDistance:^10d} mm")
            stdscr.addstr(9, 0, f"속도             | {agv_status.Speed:^10d} mm/s")
            stdscr.addstr(10, 0, f"주행거리         | {agv_status.Odometer:^10d} mm")
            stdscr.addstr(11, 0, f"RF_tag1 INDEX    | {agv_status.RF_tag1:^10d}")
            stdscr.addstr(12, 0, f"RF_tag2 제한속도 | {agv_status.RF_tag2:^10d} mm/s")

            stdscr.addstr(14, 0, f"마지막 업데이트: {time.strftime('%H:%M:%S')}")
            stdscr.refresh()
            
        except Exception as e:
            stdscr.addstr(14, 0, f"데이터 수신 오류: {e}")
            stdscr.refresh()
        
        time.sleep(0.1)
    
    stdscr.nodelay(False)

def main(stdscr):
    """메인 함수: 메뉴를 표시하고 선택된 모드를 실행합니다."""
    global agv_running, agv_paused
    
    # curses 설정
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.timeout(-1)

    # 시리얼 포트 연결 시도 (여러 포트 확인)
    agv = None
    
    stdscr.clear()

    try:
        agv = Comm(port=PORT, baudrate=BAUDRATE)
        stdscr.addstr(0, 0, f"✅ AGV 연결 성공: {PORT}")
        stdscr.addstr(1, 0, "2초 후 메뉴로 이동합니다...")
        stdscr.refresh()

    except Exception as e:
        stdscr.addstr(0, 0, "❌ AGV 연결 실패!")
        stdscr.addstr(1, 0, f"시도한 포트: {PORT}")
        stdscr.addstr(2, 0, "포트 번호, 권한, 연결 상태를 확인하세요.")
        stdscr.addstr(4, 0, "아무 키나 누르면 종료됩니다.")
        stdscr.refresh()
        stdscr.getch()
        return

    time.sleep(2)

    running = True
    while running:
        draw_menu(stdscr)
        key = stdscr.getch()

        if key == ord('1'):
            display_data_mode(stdscr, agv)
            
        elif key in [ord('q'), ord('Q'), 27]:
            running = False

    # 종료 처리
    agv_running = False
    agv_paused = False
    agv.CLR(0, 0)  # 안전 정지
    agv.destroy()
    stdscr.clear()
    stdscr.addstr(0, 0, "프로그램이 안전하게 종료되었습니다.")
    stdscr.refresh()
    time.sleep(1)

if __name__ == "__main__":
    curses.wrapper(main)
