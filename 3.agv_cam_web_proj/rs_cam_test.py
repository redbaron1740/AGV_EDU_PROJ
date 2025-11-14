import pyrealsense2 as rs
import numpy as np
import cv2
import time

width = 960
height = 540
fps_setting = 15

pipeline = rs.pipeline()
config = rs.config()

config.enable_stream(rs.stream.color, width,  height, rs.format.bgr8,  fps_setting)
config.enable_stream(rs.stream.depth, width,  height, rs.format.z16,  fps_setting)
pipeline.start(config)

try:
       
       while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        if not color_frame or not depth_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())
        frame = cv2.resize(frame, (width, height))
        height, width = frame.shape[:2]

        cv2.imshow('D435 color stream', frame)

        if cv2.waitKey(1) & 0xff == ord('q'):
            break

finally:

        pipeline.stop()
        cv2.destroyAllWindows()




