#!/usr/bin/env python3
"""
Mission Planning Module
학생들이 수정하는 태그별 임무 로직

각 태그에서 수행할 임무를 정의합니다.
- tag_id: 감지된 RF-Tag ID (1-10)
- agv_comm: AGV 통신 객체 (agv_comm.CLR(left_speed, right_speed)로 모터 제어)
- tag2_speed: Tag2에서 오는 속도 제한값 (0-200 mm/s)

학생들은 이 파일만 수정하면 됩니다!

✨ 라인 트레이싱 제어:
  - pause_line_tracing(): 라인 트레이싱 일시 중단
  - resume_line_tracing(): 라인 트레이싱 재개
  - set_max_speed(speed): Mission 최대 속도 설정 (50~200 mm/s)
  - 임무 수행 중에는 라인 트레이싱이 자동으로 중단됩니다.
"""

import time

# 라인 트레이싱 제어를 위한 콜백 함수들 (클라이언트에서 설정)
_pause_callback = None
_resume_callback = None
_set_max_speed_callback = None

def set_line_tracing_callbacks(pause_func, resume_func, set_speed_func=None):
    """라인 트레이싱 제어 콜백 설정 (클라이언트가 호출)"""
    global _pause_callback, _resume_callback, _set_max_speed_callback
    _pause_callback = pause_func
    _resume_callback = resume_func
    _set_max_speed_callback = set_speed_func

def pause_line_tracing():
    """라인 트레이싱 일시 중단"""
    if _pause_callback:
        _pause_callback()
        print("⏸️ 라인 트레이싱 중단 (임무 수행 중)")

def resume_line_tracing():
    """라인 트레이싱 재개"""
    if _resume_callback:
        _resume_callback()
        print("▶️ 라인 트레이싱 재개")

def set_max_speed(speed):
    """Mission 최대 속도 설정 (50~200 mm/s)"""
    if _set_max_speed_callback:
        _set_max_speed_callback(speed)

def execute_mission(tag_id, agv_comm, tag2_speed=200):
    """
    태그별 임무 실행 함수
    
    Args:
        tag_id (int): 감지된 RF-Tag ID (1-10)
        agv_comm: AGV 통신 객체
        tag2_speed (int): Tag2 속도 제한값 (0-200 mm/s)
    
    Returns:
        dict: 임무 결과 정보
    """
    
    print(f"🎯 Tag {tag_id} 임무 시작 (속도 제한: {tag2_speed}mm/s)")
    
    # 기본 속도는 tag2_speed를 따르되 최대 200으로 제한
    base_speed = min(tag2_speed, 200)
    
    try:
        if tag_id == 0:
            # === 초기 상태 (태그 감지 전) ===
            print("🚀 Tag 0: 초기 상태 - 라인 트레이싱 시작")
            set_max_speed(200)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 1:
            # === 시작점 ===
            print("🏁 Tag 1: 시작점 - 최대 속도 200 설정 후 라인 트레이싱")
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 2:
            # === 사용자 임무 구역 2 ===
            print("🎯 Tag 2: 임무 구역 2 - 라인 트레이싱 계속")
            # 별도 임무 없음, 라인 트레이싱 계속
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 3:
            # === 사용자 임무 구역 3 ===
            print("🎯 Tag 3: 임무 구역 3 - 라인 트레이싱 계속")
            # 별도 임무 없음, 라인 트레이싱 계속
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 4:
            # === 사용자 임무 구역 4 ===
            print("🎯 Tag 4: 임무 구역 4 - 라인 트레이싱 계속")
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 5:
            # === 사용자 임무 구역 5 ===
            print("🎯 Tag 5: 임무 구역 5 - 라인 트레이싱 계속")
            # 별도 임무 없음, 라인 트레이싱 계속
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 6:
            # === 사용자 임무 구역 6 ===
            print("🎯 Tag 6: 임무 구역 6 - 라인 트레이싱 계속")
            # 별도 임무 없음
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 7:
            # === 사용자 임무 구역 7 ===
            print("🎯 Tag 7: 임무 구역 7 - 라인 트레이싱 계속")
            # 별도 임무 없음
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 8:
            # === 사용자 임무 구역 8 ===
            print("🎯 Tag 8: 임무 구역 8 - 라인 트레이싱 계속")
            # 별도 임무 없음
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 9:
            # === 사용자 임무 구역 9 ===
            print("🎯 Tag 9: 임무 구역 9 - 라인 트레이싱 계속")
            # 별도 임무 없음
            set_max_speed(tag2_speed)
            return {"status": "success", "action": "continue", "speed": base_speed}
        
        elif tag_id == 10:
            # === 목적지/완료점 ===
            print("🏆 Tag 10: 목적지 도달 - 완전 정지")
            set_max_speed(tag2_speed)

            pause_line_tracing()


            return {"status": "completed", "action": "pause", "speed": 0}
        
        else:
            # === 알 수 없는 태그 ===
            print(f"❓ Tag {tag_id}: 알 수 없는 태그 - 기본 직진")

            return {"status": "unknown", "action": "default_forward", "speed": base_speed}
    
    except Exception as e:
        print(f"❌ Tag {tag_id} 임무 실행 오류: {e}")
        # 오류 시 안전한 정지
        if agv_comm:
            try:
                agv_comm.CLR(0, 0)
            except:
                pass
        return {"status": "error", "action": "emergency_stop", "error": str(e)}

# ===== 학습자 커스터마이징 영역 =====
def custom_mission_1():
    """사용자 정의 임무 1 - 학생들이 자유롭게 정의"""
    print("🎨 사용자 정의 임무 1")
    # 여기에 학생들이 원하는 임무 로직 추가
    pass

def custom_mission_2():
    """사용자 정의 임무 2 - 학생들이 자유롭게 정의"""
    print("🎨 사용자 정의 임무 2")
    # 여기에 학생들이 원하는 임무 로직 추가
    pass

# ===== 임무 검증 함수 =====
def validate_mission_parameters(tag_id, tag2_speed):
    """임무 파라미터 검증"""
    if not (1 <= tag_id <= 10):
        return False, f"Tag ID는 1-10 사이여야 합니다: {tag_id}"
    
    if not (0 <= tag2_speed <= 200):
        return False, f"Tag2 속도는 0-200 사이여야 합니다: {tag2_speed}"
    
    return True, "OK"

# ===== 임무 결과 로깅 =====
def log_mission_result(tag_id, result):
    """임무 결과를 로그에 기록"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    status = result.get("status", "unknown")
    action = result.get("action", "none")
    speed = result.get("speed", 0)
    
    log_message = f"[{timestamp}] Tag {tag_id}: {status} | {action} | Speed: {speed}mm/s"
    print(f"📝 {log_message}")
    
    # 필요시 파일로 로그 저장
    # with open("mission_log.txt", "a") as f:
    #     f.write(log_message + "\n")

if __name__ == "__main__":
    print("🎯 Mission Planning Module")
    print("=" * 50)
    print("이 모듈은 RF-Tag별 임무를 정의합니다.")
    print("학생들은 execute_mission() 함수를 수정하여")
    print("각 태그에서 수행할 임무를 정의할 수 있습니다.")
    print("=" * 50)
    
    # 테스트 실행 예시
    for test_tag in [1, 5, 10]:
        print(f"\n🧪 Tag {test_tag} 테스트:")
        valid, msg = validate_mission_parameters(test_tag, 150)
        if valid:
            result = execute_mission(test_tag, None, 150)  # None = 시뮬레이션
            log_mission_result(test_tag, result)
        else:
            print(f"❌ 파라미터 오류: {msg}")