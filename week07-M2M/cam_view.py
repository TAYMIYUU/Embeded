"""ดูภาพสดจากกล้อง Hikvision ผ่าน RTSP

ใช้งาน:
    python cam_view.py              # substream (102) ภาพลื่น
    python cam_view.py --main       # main stream (101) ภาพชัด
    python cam_view.py --ch 2       # กล้องตัวที่ 2

ปุ่มลัดระหว่างดู:  q = ออก   s = บันทึกภาพนิ่ง   f = สลับ main/sub
"""

import os

# ต้องตั้งก่อน import cv2 — บังคับ RTSP วิ่งบน TCP กันภาพแตกเป็นบล็อค
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

import argparse
import time
from datetime import datetime

import cv2

HOST = "192.168.1.115"
PORT = 554
USER = "admin"
# อ่านจาก env var CAM_PASS ถ้ามี ไม่มีก็ใช้ค่าที่ใส่ไว้ตรงนี้
# ("CAM_PASS" = ชื่อตัวแปร, ตัวหลัง = รหัสผ่านจริง)
PASSWORD = "pk007Z01"

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")


def build_url(channel: int, stream: int) -> str:
    """สร้าง RTSP URL ตามรูปแบบของ Hikvision

    เลขท้ายคือ channel*100 + stream เช่น ช่อง 1 สตรีม 2 -> 102, ช่อง 2 สตรีม 1 -> 201
    """
    code = channel * 100 + stream
    return (
        f"rtsp://{USER}:{PASSWORD}@{HOST}:{PORT}"
        f"/Streaming/Channels/{code}/"
    )


def open_stream(url: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    # เก็บเฟรมในบัฟเฟอร์ให้น้อยที่สุด ภาพจะได้ไม่ดีเลย์สะสม
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def masked(url: str) -> str:
    return url.replace(PASSWORD, "*" * len(PASSWORD))


def main() -> int:
    parser = argparse.ArgumentParser(description="ดูภาพสดกล้อง Hikvision")
    parser.add_argument("--ch", type=int, default=1, help="กล้องตัวที่ (default: 1)")
    parser.add_argument("--main", action="store_true", help="ใช้ main stream (101)")
    args = parser.parse_args()

    channel = args.ch
    stream = 1 if args.main else 2
    window = "Hikvision Live"

    url = build_url(channel, stream)
    print(f"กำลังเชื่อมต่อ: {masked(url)}")
    cap = open_stream(url)

    if not cap.isOpened():
        print("เปิดสตรีมไม่ได้ — เช็ค IP / user / password / กล้องเปิดอยู่หรือเปล่า")
        return 1

    fps_t0, frames, fps = time.time(), 0, 0.0
    fails = 0

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                fails += 1
                print(f"อ่านเฟรมไม่ได้ ({fails}) — กำลังต่อใหม่...")
                cap.release()
                time.sleep(min(2 * fails, 10))
                cap = open_stream(build_url(channel, stream))
                if fails >= 5:
                    print("ต่อใหม่ไม่สำเร็จหลายครั้ง หยุดทำงาน")
                    return 1
                continue

            fails = 0
            frames += 1
            elapsed = time.time() - fps_t0
            if elapsed >= 1.0:
                fps, frames, fps_t0 = frames / elapsed, 0, time.time()

            label = f"ch{channel} {'main' if stream == 1 else 'sub'} | {frame.shape[1]}x{frame.shape[0]} | {fps:.1f} fps"
            cv2.putText(frame, label, (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(frame, label, (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 1, cv2.LINE_AA)

            cv2.imshow(window, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break
            if key == ord("s"):
                os.makedirs(SNAPSHOT_DIR, exist_ok=True)
                name = datetime.now().strftime("cam_%Y%m%d_%H%M%S.jpg")
                path = os.path.join(SNAPSHOT_DIR, name)
                cv2.imwrite(path, frame)
                print(f"บันทึกภาพ: {path}")
            if key == ord("f"):
                stream = 2 if stream == 1 else 1
                print(f"สลับไป {'main' if stream == 1 else 'sub'} stream")
                cap.release()
                cap = open_stream(build_url(channel, stream))
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
