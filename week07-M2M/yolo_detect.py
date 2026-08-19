"""ตรวจจับวัตถุแบบเรียลไทม์ด้วย YOLOv8

*** รันบน Raspberry Pi ***  (VNC -> Thonny -> Run)

ต่างจาก face_detect.py ตรงที่ตัวนี้รู้จักวัตถุ 80 ชนิด (คน รถ หมา ขวด เก้าอี้ ...)
และบอกค่าความมั่นใจเป็นเปอร์เซ็นต์ด้วย

ก่อนรันครั้งแรก:
    pip install ultralytics
ไฟล์โมเดล yolov8n.pt (~6MB) จะถูกดาวน์โหลดอัตโนมัติตอนรันครั้งแรก

ปุ่มลัด:  q = ออก   s = เซฟภาพ   p = สลับโหมดเฉพาะคน
"""

import os
import sys
import time
from collections import Counter

import cv2

# ---------------- ตั้งค่า ----------------

SOURCE = 0                  # 0 = กล้อง USB ที่เสียบกับ Pi
# SOURCE = "rtsp://admin:pk007Z01@192.168.1.115:554/Streaming/Channels/102/"

MODEL = "yolov8n.pt"        # n = nano เล็กและเร็วสุด เหมาะกับ Pi
                            # ถ้าอยากได้กรอบที่ "ใบหน้า" ใช้ "yolov8n-face.pt" แทน

IMG_SIZE = 320              # ขนาดภาพที่ป้อนเข้าโมเดล เล็ก = เร็ว (320 เหมาะกับ Pi)
CONF = 0.4                  # ความมั่นใจขั้นต่ำ ต่ำลง = เจอเยอะขึ้นแต่มั่วมากขึ้น

PERSON_ONLY = False         # True = แสดงเฉพาะคน ตัดวัตถุอื่นทิ้ง
FRAME_W, FRAME_H = 640, 480

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolo")


def open_camera():
    if isinstance(SOURCE, str):
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
        cap = cv2.VideoCapture(SOURCE, cv2.CAP_FFMPEG)
    else:
        cap = cv2.VideoCapture(SOURCE, cv2.CAP_V4L2)
        if not cap.isOpened():
            cap = cv2.VideoCapture(SOURCE)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def status_bar(frame, counts, fps, person_only):
    """แถบล่าง: บอกว่าเจออะไรกี่ชิ้น และ fps"""
    total = sum(counts.values())
    top = ", ".join(f"{name} {n}" for name, n in counts.most_common(4))
    mode = "person only" if person_only else "all classes"
    text = f"[{mode}] total {total}" + (f" | {top}" if top else "")

    y = frame.shape[0] - 40
    for color, thick in (((0, 0, 0), 4), ((0, 255, 255), 1)):
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, color, thick, cv2.LINE_AA)
        cv2.putText(frame, f"YOLOv8 | {fps:.1f} fps", (10, y + 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, thick, cv2.LINE_AA)
    return frame


def main():
    global PERSON_ONLY

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ยังไม่ได้ติดตั้ง ultralytics — ติดตั้งด้วย:")
        print("   pip install ultralytics")
        return 1

    print(f"กำลังโหลดโมเดล {MODEL} ...")
    print("(ครั้งแรกจะดาวน์โหลดไฟล์จากอินเทอร์เน็ต ~6MB รอสักครู่)")
    model = YOLO(MODEL)
    names = model.names
    print(f"โหลดสำเร็จ — รู้จัก {len(names)} ชนิด\n")

    # หาหมายเลขคลาสของ 'person' ไว้ใช้ตอนกรอง
    person_id = next((i for i, n in names.items() if n == "person"), None)

    cap = open_camera()
    if not cap.isOpened():
        print(f"เปิดกล้องไม่ได้ (SOURCE = {SOURCE!r})")
        print("ดูว่ามีกล้องตัวไหนบ้าง:  ls -l /dev/video*")
        return 1

    print("กำลังทำงาน — q = ออก, s = เซฟภาพ, p = สลับโหมดเฉพาะคน\n")

    window = "YOLOv8"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, 960, 540)

    fps_t0, frames, fps = time.time(), 0, 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("อ่านเฟรมไม่ได้")
                break

            classes = [person_id] if (PERSON_ONLY and person_id is not None) else None
            results = model(frame, imgsz=IMG_SIZE, conf=CONF,
                            classes=classes, verbose=False)
            r = results[0]

            # นับว่าเจออะไรกี่ชิ้น
            counts = Counter()
            if r.boxes is not None:
                for c in r.boxes.cls.tolist():
                    counts[names[int(c)]] += 1

            annotated = r.plot()        # ultralytics วาดกรอบ+ชื่อ+% ให้เอง

            frames += 1
            el = time.time() - fps_t0
            if el >= 1.0:
                fps, frames, fps_t0 = frames / el, 0, time.time()

            status_bar(annotated, counts, fps, PERSON_ONLY)
            cv2.imshow(window, annotated)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("p"):
                PERSON_ONLY = not PERSON_ONLY
                print(f"โหมด: {'เฉพาะคน' if PERSON_ONLY else 'ทุกชนิด'}")
            if key == ord("s"):
                os.makedirs(SNAPSHOT_DIR, exist_ok=True)
                path = os.path.join(
                    SNAPSHOT_DIR, time.strftime("yolo_%Y%m%d_%H%M%S.jpg"))
                cv2.imwrite(path, annotated)
                print(f"บันทึก: {path}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nหยุดโดยผู้ใช้")
