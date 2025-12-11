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
    stdscr.addstr(1, 0, "           AGV LCU 라인 트레이싱 제어 시스템")
    stdscr.addstr(2, 0, "=" * 60)
    
    stdscr.addstr(4, 2, "1. 센서 데이터 실시간 모니터링")
    stdscr.addstr(5, 2, "2. 라인 추종 제어")
    stdscr.addstr(6, 2, "q. 프로그램 종료")
    
    # 현재 상태 표시
    if agv_running and not agv_paused:
        status = "[ON] 라인 추종 활성화 중"
    elif agv_running and agv_paused:
        status = "[PAUSE] 일시정지 중" 
    else:
        status = "[OFF] 정지됨"
        
    stdscr.addstr(8, 2, f"현재 상태: {status}")
    stdscr.addstr(10, 0, "메뉴를 선택하세요...")
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
            if agv_status.agvStatus == 1:
                str_temp = "python mode"
            elif agv_status.agvStatus == 2:
                str_temp = "ros mode"
            else: 
                str_temp = "agv mode"
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



def line_follow_control_mode(stdscr, agv):
    """라인 추종 제어 모드 - 단순화된 LCU 기반 제어"""
    global agv_running, agv_paused
    
    stdscr.clear()
    stdscr.nodelay(True)
    
    # 제어 파라미터 설정 (단순화)
    BASE_SPEED = 150          # 기본 전진 속도 (최대 1m/s 고려)
    MAX_SPEED = 200           # 최대 속도 제한
    TURN_SPEED_DIFF = 50      # 회전시 좌우 바퀴 속도 차이
    OBSTACLE_E_STOP_DISTANCE = 150  # 장애물 감지 거리 임계값 (mm)
    
    # 제어 주기
    CONTROL_INTERVAL = 0.05  # 50ms
    last_control_time = 0
    
    while True:
        key = stdscr.getch()
        
        # 키 입력 처리
        if key in [ord('m'), ord('M'), 27]:  # M 또는 ESC: 메뉴로 돌아가기
            agv.CLR(0, 0)  # 안전 정지
            break
        elif key in [ord('s'), ord('S')]:  # S: 시작/재개
            if not agv_running:
                agv_running = True
                agv_paused = False
            elif agv_paused:
                agv_paused = False
        elif key in [ord('p'), ord('P')]:  # P: 일시정지
            if agv_running:
                agv_paused = True
                agv.CLR(0, 0)  # 즉시 정지
        elif key in [ord('x'), ord('X')]:  # X: 완전정지
            agv_running = False
            agv_paused = False
            agv.CLR(0, 0)  # 즉시 정지

        current_time = time.time()
        
        # 제어 주기 체크
        if current_time - last_control_time < CONTROL_INTERVAL:
            time.sleep(0.005)
            continue
            
        dt = current_time - last_control_time
        last_control_time = current_time

        
        try:
            s = agv.get_latest_data()
            vl, vr = 0, 0
            status_msg = ""

            # 라이다 장애물 감지 플래그 (예: 200mm 이내)
            agv_obstacle_detected = False

            if s.LidarDistance < OBSTACLE_E_STOP_DISTANCE:
                agv_obstacle_detected = True

            # 1단계: 안전 조건 확인
            if s.EmgFlag == 1:
                vl, vr = 0, 0
                status_msg = "🚨 비상정지 활성화"
                agv_running = False
                agv_paused = False

            elif agv_obstacle_detected == True:  # 장애물 감지 
                vl, vr = 0, 0
                status_msg = "🚧 장애물 감지 - 정지"    
                agv_running = False
                agv_paused = False

            elif not agv_running:
                vl, vr = 0, 0
                status_msg = "⏹️ 정지 상태 (메뉴에서 시작하세요)"
                
            elif agv_paused:
                vl, vr = 0, 0
                status_msg = "⏸️ 일시정지 중"
                
            else:
                line_pos = s.LinePos  # -15 ~ +15 범위

                line_pos *= -1 #제어편의를 위해 부호 반전
                
                # 라인 센서 기반 제어 로직
                if abs(line_pos) > 8:
                    # ±8을 넘어가면 제자리 턴
                    if line_pos < -8:
                        # 라인이 왼쪽에 많이 벗어남 - 제자리 좌회전
                        vl = -TURN_SPEED_DIFF
                        vr = TURN_SPEED_DIFF
                        status_msg = "[TURN-L] 제자리 좌회전"
                    else:
                        # 라인이 오른쪽에 많이 벗어남 - 제자리 우회전
                        vl = TURN_SPEED_DIFF
                        vr = -TURN_SPEED_DIFF
                        status_msg = "[TURN-R] 제자리 우회전"
                elif line_pos == 0:
                    # 중앙에 있으면 직진
                    vl = BASE_SPEED
                    vr = BASE_SPEED
                    status_msg = "[FORWARD] 직진"
                elif line_pos < 0:
                    # 라인이 왼쪽에 있으면 왼쪽으로 부드럽게 회전
                    turn_intensity = abs(line_pos) / 8.0  # 0~1 정규화 (±8 범위)
                    speed_reduction = int(TURN_SPEED_DIFF * turn_intensity)
                    vl = BASE_SPEED - speed_reduction
                    vr = BASE_SPEED
                    status_msg = "[LEFT] 좌회전"
                else:
                    # 라인이 오른쪽에 있으면 오른쪽으로 부드럽게 회전
                    turn_intensity = abs(line_pos) / 8.0  # 0~1 정규화 (±8 범위)
                    speed_reduction = int(TURN_SPEED_DIFF * turn_intensity)
                    vl = BASE_SPEED
                    vr = BASE_SPEED - speed_reduction
                    status_msg = "[RIGHT] 우회전"
                
            # 속도 제한
            vl = max(-MAX_SPEED, min(MAX_SPEED, vl))
            vr = max(-MAX_SPEED, min(MAX_SPEED, vr))

            # 명령 전송
            agv.CLR(int(vl), int(vr))

            # 화면 표시
            stdscr.clear()
            stdscr.addstr(0, 0, "=" * 70)
            stdscr.addstr(1, 0, "         AGV LCU 라인 트레이싱 제어")
            stdscr.addstr(2, 0, "=" * 70)
            stdscr.addstr(3, 0, "키 제어: S=시작/재개 | P=일시정지 | X=완전정지 | M=메뉴")
            
            # 센서 데이터
            stdscr.addstr(5, 2, "[SENSOR] 센서 데이터")
            stdscr.addstr(6, 4, f"LCU 라인 위치  : {s.LinePos:5d} (-15:왼쪽 <- 0:중앙 -> 15:오른쪽)")
            stdscr.addstr(7, 4, f"LiDAR 거리     : {s.LidarDistance:5d} mm")
            stdscr.addstr(8, 4, f"배터리 SOC     : {s.SOC:5d} %")
            stdscr.addstr(9, 4, f"비상정지       : {'[ACTIVE]' if s.EmgFlag else '[OFF]'}")
            stdscr.addstr(10, 4, f"속도           : {s.Speed:5d} mm/s") 
            stdscr.addstr(11, 4, f"오도미터       : {s.Odometer:6d} mm")
            stdscr.addstr(12, 4, f"TAG #1       : {s.RF_tag1:5d} index") 
            stdscr.addstr(13, 4, f"TAG #2       : {s.RF_tag2:6d} mm/s")
            
            # 라인 위치 시각화 (300mm 기준)
            stdscr.addstr(15, 2, "[VISUAL] LCU 라인 위치 시각화")
            line_visual = "L" + "=" * 15 + "C" + "=" * 15 + "R"
            marker_pos = 15 + s.LinePos + 1  # 중앙(15) + 위치(-15~15) + 여백(1)
            marker_pos = max(0, min(len(line_visual), marker_pos))
            marker_line = " " * marker_pos + "^"
            stdscr.addstr(18, 4, line_visual)
            stdscr.addstr(19, 4, marker_line)
            
            # 제어 상태
            stdscr.addstr(21, 2, "[CONTROL] 제어 상태")
            stdscr.addstr(22, 4, f"상태: {status_msg}")
            stdscr.addstr(23, 4, f"좌측 바퀴: {int(vl):4d}, 우측 바퀴: {int(vr):4d}")
            
            if agv_running and not agv_paused and s.EmgFlag == 0:
                stdscr.addstr(28, 4, f"라인 위치: {s.LinePos:3d}, 속도 차이: {abs(vr-vl):3d}")
                stdscr.addstr(29, 4, f"기본 속도: {BASE_SPEED}, 회전 강도: {TURN_SPEED_DIFF}")
            
            # 제어 방식 설명 (안전한 출력)
            try:
                max_y, max_x = stdscr.getmaxyx()     #현재 콘솔의 크기 반환
                if max_y > 21:
                    stdscr.addstr(21, 2, "[INFO] 라인 추종 제어 (제자리 턴 포함)")
                if max_y > 22:
                    stdscr.addstr(22, 4, "±8 이하: 부드러운 회전 | ±8 초과: 제자리 턴")
                if max_y > 23:
                    stdscr.addstr(23, 4, "중앙(0): 직진 | 왼쪽(-): 좌회전 | 오른쪽(+): 우회전")
                if max_y > 25:
                    stdscr.addstr(25, 2, f"업데이트: {time.strftime('%H:%M:%S')}")
            except:
                pass

            stdscr.refresh()

        except Exception as e:
            try:
                max_y, max_x = stdscr.getmaxyx()
                if max_y > 20:
                    stdscr.addstr(20, 0, f"[ERROR] 제어 오류: {str(e)}")
                stdscr.refresh()
            except:
                pass
        
    stdscr.nodelay(False)
    agv.CLR(0, 0)
    
def main(stdscr):
    """메인 함수: 메뉴를 표시하고 선택된 모드를 실행합니다."""
    global agv_running, agv_paused
    
    # curses 설정
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.timeout(-1)

    # 시리얼 포트 연결 시도 (여러 포트 확인)
    agv = None
    
    try:
        agv = Comm(port=PORT, baudrate=BAUDRATE)
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, "❌ AGV 연결 실패!")
        stdscr.addstr(1, 0, f"시도한 포트: {PORT}")
        stdscr.addstr(2, 0, "포트 번호, 권한, 연결 상태를 확인하세요.")
        stdscr.addstr(4, 0, "아무 키나 누르면 종료됩니다.")
        stdscr.refresh()
        stdscr.getch()
        return

    stdscr.clear()
    stdscr.addstr(0, 0, f"✅ AGV 연결 성공: {PORT}")
    stdscr.addstr(1, 0, "2초 후 메뉴로 이동합니다...")
    stdscr.refresh()
    time.sleep(2)

    running = True
    while running:
        draw_menu(stdscr)
        key = stdscr.getch()

        if key == ord('1'):
            display_data_mode(stdscr, agv)
            
        elif key == ord('2'):
            line_follow_control_mode(stdscr, agv)
            
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
