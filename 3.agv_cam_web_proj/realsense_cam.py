import pyrealsense2 as rs
import numpy as np
import cv2
import time

class RealSenseCamera:
    def __init__(self, width=640, height=480, fps=30):
        self.width = width   # 640
        self.height = height   # 480
        self.fps_setting = fps  #fps 셋팅은 60, 30, 15 fps만 허용

        self.pipeline = rs.pipeline()
        
        config = rs.config()
        config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps_setting)
        config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps_setting)
        self.pipeline.start(config)

        self.font = cv2.FONT_HERSHEY_COMPLEX_SMALL
        self.prev_time = time.time()
        self.fps = 0

    def __del__(self):
        self.pipeline.stop()


    def draw_overlay(self, frame, depth, fps):
        # 오버레이 텍스트 준비
        text = f"Res: {self.width}x{self.height} | FPS: {fps:04.1f} | Depth: {depth:04.1f}m"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        thickness = 1

        # 텍스트 크기 측정
        (text_w, text_h), _ = cv2.getTextSize(text, font, scale, thickness)
        margin = 10
        padding = 5

        # 하단 오른쪽 좌표 계산
        x1 = self.width  - margin
        y1 = self.height - margin
        x0 = x1 - (text_w  + 2 * padding)
        y0 = y1 - (text_h + 2 * padding)

        # 배경 박스 (흰색) 그리기
        cv2.rectangle(frame, (x0, y0), (x1, y1), (255, 255, 255), -1)

        # 텍스트 (빨간색, 얇게) 그리기
        text_org = (x0 + padding, y0 + text_h + padding)
        cv2.putText(frame, text, text_org, font, scale, (0, 0, 255), thickness)


    def get_frame(self, key_value=0):
        time.sleep(1/self.fps_setting)
        frames = self.pipeline.wait_for_frames()
        #frames = self.pipeline.poll_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        if not color_frame or not depth_frame:
            blank = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            cv2.putText(blank, "Camera Error", (10, self.height//2), self.font, 0.7, (0,0,255), 2, cv2.LINE_AA)
            ret, jpeg = cv2.imencode('.jpg', blank)
            return jpeg.tobytes()

        frame = np.asanyarray(color_frame.get_data())
        frame = cv2.resize(frame, (self.width, self.height))
        height, width = frame.shape[:2]

        # FPS 계산
        curr_time = time.time()
        self.fps = 1.0 / (curr_time - self.prev_time)
        self.prev_time = curr_time

        # 거리값: 화면 중앙 픽셀의 거리(m), 최대 10m, 최소 0.2m
        center_x, center_y = int(width / 2), int(height / 2)
        distance = depth_frame.get_distance(center_x, center_y)

        # 키 이벤트와 거리값 영상 하단에 오버레이
        self.draw_overlay(frame, distance,self.fps)

        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        return jpeg.tobytes()
#        ret, webp = cv2.imencode('.webp',frame, [int(cv2.IMWRITE_AVIF_QUALITY),60])
#        return webp.tobytes()