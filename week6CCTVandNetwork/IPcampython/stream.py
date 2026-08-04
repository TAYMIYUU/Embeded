import os
import sys
import time

import cv2

# บังคับให้ FFmpeg (ที่ OpenCV ใช้อ่าน RTSP) ใช้ TCP transport
# ช่วยลดปัญหาภาพแตก/ขาดหายที่มักเกิดกับ UDP บนเครือข่าย Wi-Fi
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp"
)

RTSP_URL = "rtsp://admin:Admin25226085)@192.168.1.204:554/stream1"
WINDOW_NAME = "IP Camera Stream"
RECONNECT_DELAY_SEC = 3
DISPLAY_WIDTH = 960  # ความกว้างภาพที่ต้องการแสดงผล (px) ความสูงจะถูกคำนวณตามสัดส่วนเดิม


def open_stream(url: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    return cap


def resize_to_width(frame, width: int):
    h, w = frame.shape[:2]
    if w == width:
        return frame
    height = int(h * (width / w))
    return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)


def main() -> int:
    cap = open_stream(RTSP_URL)
    if not cap.isOpened():
        print("เปิดสตรีมไม่ได้ ตรวจสอบ URL / user / password / เครือข่ายอีกครั้ง", file=sys.stderr)
        return 1

    print("เชื่อมต่อสำเร็จ กด 'q' เพื่อออกจากโปรแกรม")

    try:
        while True:
            ok, frame = cap.read()

            if not ok or frame is None:
                print("อ่านเฟรมไม่สำเร็จ กำลังลองเชื่อมต่อใหม่...")
                cap.release()
                time.sleep(RECONNECT_DELAY_SEC)
                cap = open_stream(RTSP_URL)
                continue

            frame = resize_to_width(frame, DISPLAY_WIDTH)
            cv2.imshow(WINDOW_NAME, frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
