from flask import Flask, Response, render_template_string
from realsense_cam import RealSenseCamera
import threading
import time
import numpy as np
import cv2

width = 640
height = 480
fps = 30

app = Flask(__name__)
camera = RealSenseCamera(width, height, fps)  # Initialize RealSense camera with desired resolution and FPS
frame_lock = threading.Lock()
streaming = True

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Streaming Program</title>
        <style>
            body { margin: 0; background-color: black; display: flex; justify-content: center; align-items: center; height: 100vh; flex-direction: column; }
            h1 { color: white; margin-bottom: 20px; }
            img { max-width: 90%; border: 4px solid white; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>Video Streaming Program</h1>
        <img src="/video_feed">
    </body>
    </html>
    """
    return render_template_string(html)

def generate_frames():
    global streaming
    while True:
        with frame_lock:
            if not streaming:
                time.sleep(0.1)
                continue
            frame = camera.get_frame("")
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                # Return black frame if camera is not connected
                black_frame = np.zeros((height, width, 3), dtype=np.uint8)
                _, jpeg = cv2.imencode('.jpg', black_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
