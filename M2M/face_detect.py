"""ตรวจจับใบหน้าแบบเรียลไทม์ — รันบน Raspberry Pi

*** รันบนตัว Pi ***  (VNC -> Thonny -> Run)

รองรับสองเครื่องมือ เลือกให้เองตามเวอร์ชัน OpenCV ที่มี:
  - Haar cascade  : OpenCV 4.x (ที่ Pi OS bullseye ลงมาให้) ไม่ต้องโหลดอะไรเพิ่ม
  - YuNet (DNN)   : OpenCV 5.x ที่ตัด Haar ออกแล้ว ต้องมีไฟล์โมเดล .onnx

ปุ่มลัด:  q = ออก   s = เซฟภาพ
"""

import os
import sys
import time

import cv2

# ---------------- ตั้งค่า ----------------

SOURCE = 0                  # 0 = กล้องตัวแรกที่เสียบกับ Pi
# SOURCE = "rtsp://admin:pk007Z01@192.168.1.115:554/Streaming/Channels/102/"

# ความละเอียดสูงขึ้น = จับหน้าคนที่อยู่ไกล/ในภาพหมู่ได้ (โจทย์ต้องการ 7-10 คน)
FRAME_W, FRAME_H = 1280, 720

DETECT_EVERY = 3            # ตรวจทุกกี่เฟรม (เลขมาก = ลื่นขึ้นแต่กรอบตามช้าลง)
DETECT_SCALE = 0.5          # ย่อภาพก่อนตรวจ ช่วยให้เร็วขึ้นมากบน Pi
MIN_FACE = 24               # ขนาดหน้าเล็กสุดที่ยอมรับ (วัดบนภาพที่ย่อแล้ว)

YUNET_MODEL = "face_detection_yunet_2023mar.onnx"   # ใช้เฉพาะตอนไม่มี Haar

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faces")


# ---------------- ตัวตรวจจับ ----------------

HAAR_DIRS = [
    getattr(getattr(cv2, "data", None), "haarcascades", None),
    "/usr/share/opencv4/haarcascades/",
    "/usr/share/opencv/haarcascades/",
    "/usr/local/share/opencv4/haarcascades/",
]


class HaarDetector:
    name = "Haar cascade"

    def __init__(self):
        path = None
        for d in HAAR_DIRS:
            if not d:
                continue
            p = os.path.join(d, "haarcascade_frontalface_default.xml")
            if os.path.isfile(p):
                path = p
                break
        if path is None:
            raise FileNotFoundError("หาไฟล์ haarcascade_frontalface_default.xml ไม่เจอ")

        self.cc = cv2.CascadeClassifier(path)
        if self.cc.empty():
            raise RuntimeError(f"โหลด cascade ไม่สำเร็จ: {path}")
        self.path = path

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)      # ช่วยมากเวลาแสงไม่สม่ำเสมอ
        # scaleFactor ละเอียดขึ้น + minNeighbors ต่ำลง = จับหน้าเล็กในภาพหมู่ได้ดีขึ้น
        faces = self.cc.detectMultiScale(
            gray, scaleFactor=1.08, minNeighbors=4,
            minSize=(MIN_FACE, MIN_FACE))
        return [tuple(int(v) for v in f) for f in faces]


class YuNetDetector:
    name = "YuNet (DNN)"

    def __init__(self, model_path):
        if not os.path.isfile(model_path):
            raise FileNotFoundError(model_path)
        # score ต่ำลงเล็กน้อยเพื่อให้ติดหน้าเล็กๆ ในภาพหมู่ด้วย
        self.net = cv2.FaceDetectorYN.create(model_path, "", (320, 320), 0.6, 0.3, 5000)

    def detect(self, frame):
        h, w = frame.shape[:2]
        self.net.setInputSize((w, h))
        _, faces = self.net.detect(frame)
        if faces is None:
            return []
        return [tuple(int(v) for v in f[:4]) for f in faces]


def pick_detector():
    """เลือกตัวตรวจจับที่ใช้ได้จริงบนเครื่องนี้"""
    print(f"OpenCV {cv2.__version__}")

    if hasattr(cv2, "CascadeClassifier"):
        try:
            d = HaarDetector()
            print(f"ใช้ {d.name}: {d.path}")
            return d
        except Exception as e:
            print(f"Haar ใช้ไม่ได้: {e}")
    else:
        print("OpenCV เวอร์ชันนี้ตัด CascadeClassifier ออกแล้ว")

    if hasattr(cv2, "FaceDetectorYN"):
        model = os.path.join(os.path.dirname(os.path.abspath(__file__)), YUNET_MODEL)
        try:
            d = YuNetDetector(model)
            print(f"ใช้ {d.name}: {model}")
            return d
        except FileNotFoundError:
            print(f"ไม่มีไฟล์โมเดล: {model}")
            print("ดาวน์โหลด face_detection_yunet_2023mar.onnx มาวางข้างไฟล์นี้ก่อน")

    return None


# ---------------- แหล่งภาพ ----------------

def open_camera():
    if isinstance(SOURCE, str):
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
        cap = cv2.VideoCapture(SOURCE, cv2.CAP_FFMPEG)
    else:
        cap = cv2.VideoCapture(SOURCE, cv2.CAP_V4L2)
        if not cap.isOpened():                 # เผื่อ V4L2 ไม่ติด ลองแบบปกติ
            cap = cv2.VideoCapture(SOURCE)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def draw(frame, faces, fps, detector_name):
    for i, (x, y, w, h) in enumerate(faces, 1):
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        tag = f"Face {i}"
        tw = 9 * len(tag)
        # ปกติวางป้ายเหนือกรอบ แต่ถ้าชนขอบบนให้ย้ายลงมาไว้ในกรอบแทน
        top = y - 22 if y - 22 >= 0 else y
        tx = min(x, frame.shape[1] - tw - 1)
        cv2.rectangle(frame, (tx, top), (tx + tw, top + 22), (0, 255, 0), -1)
        cv2.putText(frame, tag, (tx + 3, top + 16), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 0), 1, cv2.LINE_AA)

    # วางแถบสถานะไว้ล่างซ้าย กันไปทับป้ายของหน้าที่อยู่ขอบบน
    label = f"{detector_name} | faces: {len(faces)} | {fps:.1f} fps"
    y = frame.shape[0] - 14
    for color, thick in (((0, 0, 0), 4), ((0, 255, 255), 1)):
        cv2.putText(frame, label, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, color, thick, cv2.LINE_AA)
    return frame


def scale_boxes(faces, factor):
    return [(int(x / factor), int(y / factor), int(w / factor), int(h / factor))
            for x, y, w, h in faces]


def main():
    detector = pick_detector()
    if detector is None:
        print("\nไม่มีตัวตรวจจับใบหน้าที่ใช้ได้ — ติดตั้งด้วย:")
        print("   sudo apt install python3-opencv opencv-data")
        return 1

    cap = open_camera()
    if not cap.isOpened():
        print(f"\nเปิดกล้องไม่ได้ (SOURCE = {SOURCE!r})")
        print("ดูว่ามีกล้องตัวไหนบ้าง:  ls -l /dev/video*")
        print("ถ้าเป็นกล้อง USB ลองเปลี่ยน SOURCE เป็น 1 หรือ 2")
        return 1

    print("\nกำลังทำงาน — กด q เพื่อออก, s เพื่อเซฟภาพ\n")

    window = "Face Detection"
    faces = []
    n = 0
    fps_t0, frames, fps = time.time(), 0, 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("อ่านเฟรมไม่ได้")
                break

            # ตรวจเฉพาะบางเฟรม และตรวจบนภาพย่อ เพื่อให้ Pi ตามทัน
            if n % DETECT_EVERY == 0:
                small = cv2.resize(frame, None, fx=DETECT_SCALE, fy=DETECT_SCALE)
                faces = scale_boxes(detector.detect(small), DETECT_SCALE)
            n += 1

            frames += 1
            el = time.time() - fps_t0
            if el >= 1.0:
                fps, frames, fps_t0 = frames / el, 0, time.time()

            draw(frame, faces, fps, detector.name)
            cv2.imshow(window, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                os.makedirs(SNAPSHOT_DIR, exist_ok=True)
                path = os.path.join(
                    SNAPSHOT_DIR, time.strftime("face_%Y%m%d_%H%M%S.jpg"))
                cv2.imwrite(path, frame)
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
