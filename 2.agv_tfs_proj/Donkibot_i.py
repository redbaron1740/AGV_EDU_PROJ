
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STM -> Ubuntu 로 송신되는 $STS 프레임 수신/파싱/로그 (개선된 버전)
- 한 줄 단위로 데이터를 읽어 안정성과 가독성 향상
- dataclass를 사용하여 데이터 구조를 명확하게 정의
- 복잡한 상태 머신을 제거하고 단순한 파싱 로직으로 변경

$STS,1,95,12,0,532, -15, 420, 120, 34567,123,255\r\n

"""


import threading
import time
import serial
from dataclasses import dataclass, fields
from typing import Optional

SPEED_LIMIT = 300

# 데이터 구조를 명확하게 정의하기 위해 dataclass 사용
@dataclass
class STSFrame:
    agvStatus: int = 0      # 0: agv_mode, 1: python_mode, 2: ros_mode 
    SOC: int = 0            # 0 -100 %
    LinePos: int = 0        #  Left -15:   0     15: right
    EmgFlag: int = 0        # 0: release, 1: pushed
    LidarDistance: int = 0  #  200 ~ 1200 mm
    TfsAngle: int = 0       #  -80 ~ 80
    TfsDistance: int = 0    #  0 ~ 2800 mm
    Speed: int = 0          #  2 wheel average /2
    Odometer: int = 0       #  count 값   100,000cnt/rev
    RF_tag1: int = 0        # Mission index
    RF_tag2: int = 0        # 속도 제한 mm/s 

    # 클래스 메서드로 파싱 로직을 분리하여 코드 구조 개선
    @classmethod
    def parser(cls, line: str) -> Optional['STSFrame']:
        """
        "$STS,..." 문자열 한 줄을 파싱하여 STSFrame 객체를 생성합니다.
        형식이 맞지 않으면 None을 반환합니다.
        """
        if not line.startswith("$STS,") or not line.endswith("\r\n"):
            return None

        # "$STS," 와 "\r\n" 부분을 제거하고 ',' 로 분리
        parts = line[5:-2].split(',')       

        # 프로토콜 필드 개수 확인 (9개)
        if len(parts) != len(fields(cls)):
            return None

        try:
            # 모든 필드를 정수로 변환
            int_parts = [int(p.strip()) for p in parts]
            return cls(*int_parts)

        except (ValueError, TypeError) as e:
            print(f"[Parser Error] 데이터 변환 실패: {e}, 원본: {parts}")
            return None

class Comm:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baudrate
        self.ser.timeout = 0.1

        self.latest_data: STSFrame = STSFrame() # 항상 최신 데이터를 담고 있음
        self._is_running = False

        try:
            self.ser.open()
            self.ser.reset_input_buffer()
            #print(f'시리얼 포트 {port} 연결 성공.')
        except serial.SerialException as e:
            print(f'시리얼 포트 {port} 연결 실패: {e}')
            raise  # 에러 발생 시 프로그램 중단

        # 데이터 수신을 위한 스레드 시작
        self._is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        #print('시리얼 수신 스레드 시작.')

    def _read_loop(self):
        """백그라운드에서 시리얼 데이터를 계속 읽고 파싱하는 내부 메서드"""
        #print("수신 루프 진입...")
        while self._is_running:
            if self.ser.in_waiting > 0:

                try:
                    # 한 줄을 통째로 읽어 파싱 (훨씬 안정적이고 간단함)
                    line = self.ser.readline().decode('latin-1', errors='ignore')

                    if not line:
                        #print("[Parser Error] 빈 라인 수신")
                        continue

                    parsed_frame = STSFrame.parser(line)
                    if parsed_frame:
                        self.latest_data = parsed_frame
                        #print(f"Parsed: {self.latest_data}") # 디버깅 시 주석 해제

                except Exception as e:
                    print(f"수신 루프 에러: {e}")
            time.sleep(0.001) # CPU 사용량 감소

    def destroy(self):
        """리소스 정리 (스레드 및 시리얼 포트 종료)"""

        self._is_running = False

        if self.thread.is_alive():
            self.thread.join(0.2)
        if self.ser.is_open:
            self.ser.close()
            #print('시리얼 포트가 닫혔습니다.')

    def send_command(self, command: str):
        """명령어 문자열을 시리얼로 전송"""
        if self.ser.is_open and self.ser.writable():
            full_command = (command + '\r\n').encode('latin-1')
            self.ser.write(full_command)
            #print(f"Sent: {command}") # 디버깅 시 주석 해제
        else:
            print("경고: 시리얼 포트가 쓰기 가능 상태가 아닙니다.")
    def CLR(self, vl: int, vr: int):
        """좌측 바퀴 속도(vl), 우측 바퀴 속도(vr) 명령 전송"""
        """SPEED_LIMIT에 따라 속도 제한 적용"""
        send_vl = max(-SPEED_LIMIT, min(SPEED_LIMIT, vl))
        send_vr = max(-SPEED_LIMIT, min(SPEED_LIMIT, vr))
        self.send_command(f"$CLR,{send_vl},{send_vr}")

    def get_latest_data(self) -> STSFrame:
        """가장 최근에 파싱된 데이터 반환"""
        return self.latest_data

if __name__ == '__main__':
    try:
        # '/dev/ttyUSB0'는 실제 환경에 맞게 수정 필요
        # 윈도우 예시: 'COM3'
        agv = Comm(port='/dev/ttyUSB0', baudrate=115200)
    except Exception as e:
        #print("프로그램을 시작할 수 없습니다. 종료합니다.")
        exit()

    #print("메인 루프 시작. 1초마다 AGV 데이터를 출력합니다. (Ctrl+C로 종료)")
    try:
        while True:
            agv_status = agv.get_latest_data()
            #print(f"현재 AGV 데이터: {agv_status}")
            
            # --- 명령 전송 테스트 (필요 시 주석 해제) ---
            #agv.CLR(100, 100) # 양쪽 바퀴 속도 100으로 전진
            
            time.sleep(.01)

    except KeyboardInterrupt:
        print("\n사용자에 의해 프로그램 종료 요청.")
    finally:
        agv.destroy()
        print("프로그램이 안전하게 종료되었습니다.")