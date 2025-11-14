import pyrealsense2 as rs
import numpy as np
import cv2
import time

class RealSenseOverlay:
    def __init__(self,width=640,height=480,fps=30):
        self.width = width
        self.height = height
        self.fps_setting = fps
        # RealSense 파이프라인 및 스트림 설정
        self.pipeline = rs.pipeline()
        cfg=rs.config()
        cfg.enable_stream(rs.stream.color,self.width,self.height, rs.format.bgr8,self.fps_setting)
        cfg.enable_stream(rs.stream.depth,self.width,self.height, rs.format.z16,self.fps_setting)
        self.pipeline.start(cfg)
        
        # FPS 계산용 변수
        self.prev_time=time.time()
        self.frame_count=0
        
    def draw_overlay(self,frame,depth,fps):
        # 오버레이 텍스트 준비
        text =f"Res: {self.width}x{self.height}| FPS: {fps:.2f}| Depth: {depth:.2f}m"
        font =cv2.FONT_HERSHEY_SIMPLEX
        scale =0.5
        thickness =1
        # 텍스트 크기 측정
        (text_w,text_h),_=cv2.getTextSize(text,font,scale,thickness)
        margin =10
        padding =5
        # 하단 오른쪽 좌표 계산
        x1 =self.width -margin
        y1 =self.height-margin
        x0 =x1 -(text_w +2 *padding)
        y0 =y1 -(text_h+2 *padding)
        # 배경 박스 (흰색) 그리기
        cv2.rectangle(frame,(x0,y0),(x1,y1),(255,255,255),-1)
        # 텍스트 (빨간색, 얇게) 그리기
        text_org=(x0 +padding, y0 +text_h+padding)
        cv2.putText(frame,text,text_org,font,scale,(0,0,255),thickness)
        
    def start(self):
        try:
            while True:
                frames =self.pipeline.wait_for_frames()
                color_frame=frames.get_color_frame()
                depth_frame=frames.get_depth_frame()
                if not color_frame or not depth_frame:
                    continue
                # 컬러 프레임 → NumPy 배열
                frame = np.asanyarray(color_frame.get_data())
                frame = cv2.resize(frame,(self.width,self.height))
                # 중앙 픽셀 깊이(m) 취득
                cx, cy = self.width//2, self.height //2
                depth =depth_frame.get_distance(cx,cy)
                # FPS 계산
                self.frame_count+=1
                now =time.time()
                elapsed = now -self.prev_time
                fps = self.frame_count/elapsed if elapsed >0 else 0
                # 오버레이 그리기
                self.draw_overlay(frame,depth,fps)
                # 화면 표시 및 종료 조건
                cv2.imshow('D435 Stream With Overlay',frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            self.stop()
            
    def stop(self):
        self.pipeline.stop()
        cv2.destroyAllWindows()
        
if __name__== "__main__":
    app = RealSenseOverlay(width = 640, height = 480, fps = 30) 
    app.start()