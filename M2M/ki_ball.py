"""แบมือแล้วเกิดลูกไฟพลังงานบนฝ่ามือ (สไตล์ดราก้อนบอล)

ตรวจจับมือด้วย MediaPipe (landmark 21 จุด) แล้ววาดลูกพลังทับตรงกลางฝ่ามือ

วิธีเล่น:
    แบมือ  -> ลูกไฟก่อตัวและค่อยๆ ชาร์จโตขึ้น
    กำมือ  -> ถ้าชาร์จเต็มจะยิงออกไป ไม่เต็มก็แค่ดับ

ปุ่มลัด:  q = ออก   s = เซฟภาพ   c = สลับสี ไฟ/พลังคลื่นเต่า   d = โชว์โครงมือ
"""

import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000"

import math
import random
import time
from datetime import datetime

import cv2
import numpy as np
import mediapipe as mp

# ---------------- ตั้งค่า ----------------

USE_WEBCAM = False          # True = ใช้เว็บแคมโน้ตบุ๊ก, False = กล้อง Hikvision
WEBCAM_INDEX = 0

HOST = "192.168.1.115"
PORT = 554
USER = "admin"
PASSWORD = os.environ.get("CAM_PASS", "pk007Z01")
CHANNEL, STREAM = 1, 2      # 1,2 -> Channels/102 (substream)

STYLE = "fire"              # "fire" = ลูกไฟ, "ki" = พลังคลื่นเต่าสีฟ้า
CHARGE_SECONDS = 1.2        # ชาร์จกี่วินาทีถึงเต็ม
SPRITE_MAX = 360            # ความละเอียดของ sprite ลูกไฟ (ยิ่งมากยิ่งเนียน/หนัก)

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")

# ---------------- สร้างภาพลูกไฟ ----------------

# ไล่สีจากขอบนอก (จาง) เข้าหาแกนกลาง (ขาวโพลน) — ค่าเป็น BGR
PALETTES = {
    "fire": [(0.00, (0, 0, 0)), (0.30, (0, 10, 90)), (0.55, (0, 80, 220)),
             (0.78, (70, 200, 255)), (1.00, (255, 255, 255))],
    "ki":   [(0.00, (0, 0, 0)), (0.30, (110, 30, 0)), (0.55, (255, 130, 20)),
             (0.78, (255, 225, 130)), (1.00, (255, 255, 255))],
}


def build_lut(style):
    """แปลงจุดไล่สีเป็นตาราง 256 ระดับ"""
    stops = PALETTES[style]
    xs = [s[0] for s in stops]
    lut = np.zeros((256, 3), np.uint8)
    t = np.linspace(0, 1, 256)
    for ch in range(3):
        ys = [s[1][ch] for s in stops]
        lut[:, ch] = np.interp(t, xs, ys).astype(np.uint8)
    return lut


def build_sprite(style, size=SPRITE_MAX):
    """สร้างลูกกลมเรืองแสง: แกนกลางสว่างจัด ขอบนอกฟุ้งจาง"""
    r = size / 2.0
    y, x = np.ogrid[:size, :size]
    dist = np.sqrt((x - r) ** 2 + (y - r) ** 2) / r
    falloff = np.clip(1.0 - dist, 0.0, 1.0)

    core = falloff ** 3.0          # แกนกลางร้อนจัด
    halo = falloff ** 1.4 * 0.55   # รัศมีฟุ้งรอบนอก ไล่จางเนียนๆ
    ring = np.exp(-((dist - 0.55) ** 2) / 0.03) * 0.18    # วงแหวนพลังงานบางๆ

    inten = np.clip(core + halo + ring, 0, 1)
    inten = cv2.GaussianBlur(inten, (0, 0), size * 0.02)  # กันสีเป็นวงๆ (banding)
    idx = (inten * 255).astype(np.uint8)
    return build_lut(style)[idx]


def additive(frame, sprite, cx, cy, gain=1.0):
    """แปะ sprite แบบบวกแสง (additive) ให้ดูเรืองแสงทะลุฉากหลัง"""
    h, w = sprite.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(frame.shape[1], x0 + w), min(frame.shape[0], y0 + h)
    if fx0 >= fx1 or fy0 >= fy1:
        return
    sub = sprite[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    if gain != 1.0:
        sub = cv2.convertScaleAbs(sub, alpha=gain)
    roi = frame[fy0:fy1, fx0:fx1]
    frame[fy0:fy1, fx0:fx1] = cv2.add(roi, sub)


# ---------------- อ่านท่ามือ ----------------

FINGERS = [(8, 6), (12, 10), (16, 14), (20, 18)]   # (tip, pip) ของ ชี้/กลาง/นาง/ก้อย
PALM_IDS = [0, 5, 9, 13, 17]


def hand_metrics(lm, w, h):
    """คืน (จุดกลางฝ่ามือ, ขนาดมือ, จำนวนนิ้วที่กาง)"""
    pts = np.array([[p.x * w, p.y * h] for p in lm.landmark], np.float32)
    wrist = pts[0]

    extended = 0
    for tip, pip in FINGERS:
        if np.linalg.norm(pts[tip] - wrist) > np.linalg.norm(pts[pip] - wrist) * 1.15:
            extended += 1
    # นิ้วโป้งกางออกด้านข้าง วัดเทียบกับโคนนิ้วก้อยแทน
    if np.linalg.norm(pts[4] - pts[17]) > np.linalg.norm(pts[2] - pts[17]) * 1.1:
        extended += 1

    center = pts[PALM_IDS].mean(axis=0)
    center = center * 0.65 + pts[9] * 0.35        # ขยับเข้าหากลางฝ่ามือจริง
    scale = np.linalg.norm(pts[9] - wrist)
    return center, scale, extended


# ---------------- เอฟเฟกต์ประกอบ ----------------

def draw_arcs(layer, cx, cy, radius, style, count=3):
    """สายฟ้าแลบรอบลูกพลัง — วาดลงเลเยอร์เอฟเฟกต์เพื่อให้เบลอเป็นแสงเรืองทีหลัง"""
    color = (150, 235, 255) if style == "fire" else (255, 240, 200)
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        pts, r = [], radius * 0.35
        limit = radius * random.uniform(0.85, 1.2)       # เกาะใกล้ลูกไฟ ไม่แผ่เป็นใยแมงมุม
        while r < limit:
            ang += random.uniform(-0.5, 0.5)
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
            r += radius * random.uniform(0.09, 0.18)     # ช่วงสั้น = หยักถี่ขึ้น
        # ไล่ความสว่างจากโคน (สว่าง) ไปปลาย (จาง) ทีละท่อน
        for k in range(len(pts) - 1):
            f = 1.0 - k / max(len(pts) - 1, 1)
            c = tuple(int(v * 0.55 * (0.2 + 0.8 * f)) for v in color)
            cv2.line(layer, (int(pts[k][0]), int(pts[k][1])),
                     (int(pts[k + 1][0]), int(pts[k + 1][1])), c, 1, cv2.LINE_AA)


class Particles:
    """เศษพลังงานที่ถูกดูดเข้าหาลูกไฟ"""

    def __init__(self):
        self.items = []

    def spawn(self, cx, cy, radius, n=2):
        for _ in range(n):
            self.items.append({
                "a": random.uniform(0, math.tau),
                "r": radius * random.uniform(1.7, 3.0),
                "spin": random.uniform(-3.5, 3.5), "life": 1.0,
                "bright": random.uniform(0.5, 1.0),
                "cx": cx, "cy": cy,
            })

    def update_draw(self, layer, dt, color):
        """อัปเดตแล้ววาดลงเลเยอร์เอฟเฟกต์ (จะถูกเบลอให้เรืองแสงทีหลัง)"""
        alive = []
        for p in self.items:
            p["r"] -= p["r"] * 2.4 * dt          # ถูกดูดเข้ากลาง
            p["a"] += p["spin"] * dt
            p["life"] -= dt * 1.4
            if p["life"] <= 0 or p["r"] < 3:
                continue
            x = int(p["cx"] + math.cos(p["a"]) * p["r"])
            y = int(p["cy"] + math.sin(p["a"]) * p["r"])
            if 0 <= x < layer.shape[1] and 0 <= y < layer.shape[0]:
                # จางลงทั้งตามอายุและตอนเพิ่งเกิด (โผล่มาแบบ fade in)
                a = p["bright"] * min(1.0, p["life"] * 1.6) * min(1.0, (1 - p["life"]) * 6 + 0.2)
                c = tuple(int(v * a) for v in color)
                cv2.circle(layer, (x, y), 1, c, -1, cv2.LINE_AA)
            alive.append(p)
        self.items = alive


# ---------------- แหล่งภาพ ----------------

def open_source():
    if USE_WEBCAM:
        cap = cv2.VideoCapture(WEBCAM_INDEX, cv2.CAP_DSHOW)
    else:
        code = CHANNEL * 100 + STREAM
        url = f"rtsp://{USER}:{PASSWORD}@{HOST}:{PORT}/Streaming/Channels/{code}/"
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


# ---------------- ลูปหลัก ----------------

def main():
    global STYLE

    cap = open_source()
    if not cap.isOpened():
        print("เปิดภาพไม่ได้ — เช็คกล้อง/รหัสผ่าน หรือลองตั้ง USE_WEBCAM = True")
        return 1

    hands = mp.solutions.hands.Hands(
        max_num_hands=2, model_complexity=0,
        min_detection_confidence=0.6, min_tracking_confidence=0.5)
    drawer = mp.solutions.drawing_utils

    sprite = build_sprite(STYLE)
    charges = {}        # index มือ -> ระดับพลัง 0..1
    blasts = []         # ลูกที่ยิงออกไปแล้ว
    particles = Particles()
    fx = None
    show_skeleton = False

    window = "Ki Ball"
    prev = time.time()
    fps_t0, frames, fps = prev, 0, 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("อ่านเฟรมไม่ได้ — กำลังต่อใหม่...")
                cap.release()
                time.sleep(1.5)
                cap = open_source()
                continue

            if USE_WEBCAM:
                frame = cv2.flip(frame, 1)      # เว็บแคมกลับด้านให้เหมือนส่องกระจก

            now = time.time()
            dt = min(now - prev, 0.1)
            prev = now

            # เลเยอร์สำหรับเศษพลัง/สายฟ้า — เบลอแล้วบวกกลับเข้าภาพให้เรืองแสง
            if fx is None or fx.shape != frame.shape:
                fx = np.zeros_like(frame)
            else:
                fx[:] = 0

            res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            seen = set()

            if res.multi_hand_landmarks:
                for i, lm in enumerate(res.multi_hand_landmarks):
                    seen.add(i)
                    if show_skeleton:
                        drawer.draw_landmarks(
                            frame, lm, mp.solutions.hands.HAND_CONNECTIONS)

                    center, scale, extended = hand_metrics(
                        lm, frame.shape[1], frame.shape[0])
                    open_palm = extended >= 4
                    ch = charges.get(i, 0.0)

                    if open_palm:
                        ch = min(1.0, ch + dt / CHARGE_SECONDS)
                    else:
                        if ch > 0.8:                     # กำมือตอนพลังเต็ม = ยิง!
                            blasts.append({"x": center[0], "y": center[1],
                                           "r": scale * 0.75, "life": 1.0})
                        ch = max(0.0, ch - dt * 4.0)     # ไม่เต็มก็ดับเร็วๆ
                    charges[i] = ch

                    if ch > 0.02:
                        cx, cy = int(center[0]), int(center[1])
                        radius = scale * (0.35 + 0.55 * ch)
                        size = max(8, int(radius * 2))
                        s = cv2.resize(sprite, (size, size),
                                       interpolation=cv2.INTER_LINEAR)
                        flicker = 0.85 + 0.15 * math.sin(now * 22) + \
                            random.uniform(-0.05, 0.05)
                        additive(frame, s, cx, cy, gain=ch * flicker)

                        if ch > 0.35:
                            particles.spawn(cx, cy, radius, n=2)
                        if ch > 0.6 and random.random() < 0.6:
                            draw_arcs(fx, cx, cy, radius, STYLE,
                                      count=int(1 + ch * 3))

            for i in list(charges):                     # มือหายไปจากเฟรม
                if i not in seen:
                    charges[i] = max(0.0, charges[i] - dt * 4.0)

            particles.update_draw(
                fx, dt, (140, 235, 255) if STYLE == "fire" else (255, 240, 200))

            # เบลอเลเยอร์แล้วบวกซ้อนของเดิม = ได้ทั้งเส้นคมและรัศมีเรืองรอบเส้น
            glow = cv2.GaussianBlur(fx, (0, 0), 3.0)
            frame = cv2.add(frame, cv2.add(fx, cv2.convertScaleAbs(glow, alpha=1.6)))

            for b in blasts[:]:                         # ลูกที่ยิงไปแล้ว
                b["r"] *= 1 + 3.5 * dt
                b["life"] -= dt * 1.6
                if b["life"] <= 0:
                    blasts.remove(b)
                    continue
                size = max(8, int(b["r"] * 2))
                s = cv2.resize(sprite, (size, size), interpolation=cv2.INTER_LINEAR)
                additive(frame, s, int(b["x"]), int(b["y"]), gain=b["life"])

            frames += 1
            el = now - fps_t0
            if el >= 1.0:
                fps, frames, fps_t0 = frames / el, 0, now

            top = max(charges.values()) if charges else 0.0
            bar_w = int(160 * top)
            cv2.rectangle(frame, (10, 42), (170, 56), (60, 60, 60), 1)
            if bar_w:
                cv2.rectangle(frame, (11, 43), (10 + bar_w, 55),
                              (0, 200, 255) if STYLE == "fire" else (255, 180, 0), -1)

            label = f"{STYLE} | charge {top*100:3.0f}% | {fps:.1f} fps"
            for color, thick in (((0, 0, 0), 4), ((0, 255, 0), 1)):
                cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.65, color, thick, cv2.LINE_AA)

            cv2.imshow(window, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("c"):
                STYLE = "ki" if STYLE == "fire" else "fire"
                sprite = build_sprite(STYLE)
            if key == ord("d"):
                show_skeleton = not show_skeleton
            if key == ord("s"):
                os.makedirs(SNAPSHOT_DIR, exist_ok=True)
                path = os.path.join(
                    SNAPSHOT_DIR, datetime.now().strftime("ki_%Y%m%d_%H%M%S.jpg"))
                cv2.imwrite(path, frame)
                print(f"บันทึกภาพ: {path}")
    finally:
        cap.release()
        hands.close()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
