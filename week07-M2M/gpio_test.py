"""ทดสอบ GPIO บน IRIV PiControl ด้วย Thonny Python

*** ไฟล์นี้ต้องรันบนตัว Pi ไม่ใช่บนโน้ตบุ๊ก ***
(VNC เข้า Pi -> เปิด Thonny -> Run)

เลขขาด้านล่างได้จากการอ่าน flows.json ของ Node-RED บนบอร์ดจริง
Node-RED บนบอร์ดนี้ตั้งเป็นโหมด BCM อยู่แล้ว เลขในนั้นจึงใช้กับ gpiozero ได้ตรงๆ
"""

import sys
import time

from gpiozero import LED, Button, Buzzer

# ---------------- เลขขา (BCM) ของ IRIV PiControl ----------------

PIN_LED0 = 20
PIN_LED1 = 21
PIN_BUZZER = 19
PIN_BUTTON = 4                  # User Button บนบอร์ด

PINS_DO = [23, 24, 25, 26]      # Digital Output DO0-DO3
PINS_DI = [13, 17, 22, 27]      # Digital Input  DI0-DI3

BLINK_TIMES = 10
BLINK_DELAY = 0.5
WATCH_SECONDS = 20


def blink(led0, led1):
    """ขาออก: ไล่ไฟ LED สองดวงสลับกัน"""
    print(f"[1/4] กะพริบ LED0 (BCM {PIN_LED0}) และ LED1 (BCM {PIN_LED1}) "
          f"{BLINK_TIMES} รอบ")
    for i in range(1, BLINK_TIMES + 1):
        led0.on(); led1.off()
        print(f"   รอบ {i:2d}: LED0=ON  LED1=OFF")
        time.sleep(BLINK_DELAY)
        led0.off(); led1.on()
        time.sleep(BLINK_DELAY)
    led0.off(); led1.off()
    print()


def beep(buzzer):
    print(f"[2/4] บัซเซอร์ (BCM {PIN_BUZZER}) บี๊บ 3 ครั้ง")
    for _ in range(3):
        buzzer.on()
        time.sleep(0.15)
        buzzer.off()
        time.sleep(0.25)
    print()


def sweep_outputs(outs):
    """ไล่เปิด-ปิด Digital Output ทีละขา"""
    print(f"[3/4] ไล่ Digital Output DO0-DO3 (BCM {PINS_DO})")
    for i, o in enumerate(outs):
        o.on()
        print(f"   DO{i} (BCM {PINS_DO[i]}) = ON")
        time.sleep(0.8)
        o.off()
    print()


def watch_inputs(button, ins, led0):
    """ขาเข้า: อ่านปุ่มและ DI แล้วสะท้อนออกที่ LED0"""
    print(f"[4/4] อ่านขาเข้า {WATCH_SECONDS} วินาที — กด User Button "
          f"หรือป้อนสัญญาณเข้า DI0-DI3 ได้เลย")
    print("      (กดปุ่มแล้ว LED0 จะติดตาม = พิสูจน์ว่าอ่านค่าเข้ามาได้จริง)")

    end = time.time() + WATCH_SECONDS
    last = None
    presses = 0
    while time.time() < end:
        state = (button.is_pressed, tuple(d.is_pressed for d in ins))
        if state != last:
            btn, di = state
            led0.value = btn
            if btn and (last is None or not last[0]):
                presses += 1
            di_txt = " ".join(f"DI{i}={'1' if v else '0'}" for i, v in enumerate(di))
            print(f"   Button={'กด ' if btn else 'ปล่อย'}  {di_txt}")
            last = state
        time.sleep(0.05)

    led0.off()
    print(f"\nจบการทดสอบ — กด User Button ไป {presses} ครั้ง")


def main():
    led0 = LED(PIN_LED0)
    led1 = LED(PIN_LED1)
    buzzer = Buzzer(PIN_BUZZER)
    button = Button(PIN_BUTTON, pull_up=True)
    outs = [LED(p) for p in PINS_DO]        # LED() ใช้เป็นขาออกทั่วไปได้
    ins = [Button(p, pull_up=True) for p in PINS_DI]

    try:
        blink(led0, led1)
        beep(buzzer)
        sweep_outputs(outs)
        watch_inputs(button, ins, led0)
    finally:
        for dev in [led0, led1, buzzer, *outs]:
            dev.off()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nหยุดโดยผู้ใช้")
