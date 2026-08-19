"""ดึงเลขขา GPIO ที่ Node-RED ใช้อยู่ออกมาจาก flows.json

*** รันบนตัว Pi ***  (VNC -> Thonny -> Run)

มันจะบอกว่า ปุ่ม/สวิตช์แต่ละอันบนหน้า Dashboard สั่งขาไหน
พร้อมแปลงเลขขาหัวต่อ (BOARD) เป็นเลข BCM ที่ gpiozero ต้องใช้
"""

import glob
import json
import os

# เลขขาบนหัวต่อ 40 พิน -> เลข BCM ที่ gpiozero/RPi.GPIO ใช้
BOARD_TO_BCM = {
    3: 2, 5: 3, 7: 4, 8: 14, 10: 15, 11: 17, 12: 18, 13: 27, 15: 22,
    16: 23, 18: 24, 19: 10, 21: 9, 22: 25, 23: 11, 24: 8, 26: 7,
    27: 0, 28: 1, 29: 5, 31: 6, 32: 12, 33: 13, 35: 19, 36: 16,
    37: 26, 38: 20, 40: 21,
}

SEARCH = [
    "~/.node-red/flows.json",
    "~/.node-red/flows_*.json",
    "/root/.node-red/flows.json",
    "/home/*/.node-red/flows*.json",
]


def find_flows():
    for pat in SEARCH:
        for path in glob.glob(os.path.expanduser(pat)):
            if os.path.isfile(path) and "cred" not in os.path.basename(path):
                return path
    return None


def is_gpio(node):
    t = node.get("type", "").lower()
    return "gpio" in t or t.startswith("rpi-")


def detect_mode(pins):
    """เดาว่า Node-RED ตั้งเลขขาแบบ BOARD หรือ BCM

    ถ้ามีเลขไหนที่ใช้เป็นขา GPIO แบบ BOARD ไม่ได้ (เช่น 20/25 = GND, 4 = 5V)
    แสดงว่าทั้งไฟล์ต้องเป็นเลข BCM
    """
    nums = []
    for p in pins:
        try:
            nums.append(int(p))
        except (TypeError, ValueError):
            pass
    if not nums:
        return "BCM"
    if all(0 <= n <= 27 for n in nums) and any(n not in BOARD_TO_BCM for n in nums):
        return "BCM"
    return "BOARD"


def bcm_of(pin, mode):
    """คืน (ข้อความอธิบาย, เลข BCM ที่ควรใช้)"""
    try:
        n = int(pin)
    except (TypeError, ValueError):
        return "?", None
    if mode == "BCM":
        return f"BCM {n}", n
    if n in BOARD_TO_BCM:
        return f"BOARD {n} = BCM {BOARD_TO_BCM[n]}", BOARD_TO_BCM[n]
    return f"BOARD {n} (ไม่ใช่ขา GPIO)", None


def main():
    path = find_flows()
    if not path:
        print("หา flows.json ไม่เจอ")
        print("ลองหาเองด้วย:  find / -name 'flows*.json' 2>/dev/null | grep node-red")
        return 1

    print(f"อ่านจาก: {path}\n")
    with open(path, encoding="utf-8") as f:
        flows = json.load(f)

    nodes = {n["id"]: n for n in flows if isinstance(n, dict) and "id" in n}
    gpio_nodes = [n for n in nodes.values() if is_gpio(n)]

    if not gpio_nodes:
        print("ไม่พบ node ที่เกี่ยวกับ GPIO เลย")
        print("อาจสั่งขาผ่าน exec/python แทน ลองดู node ชนิด exec:")
        for n in nodes.values():
            if n.get("type") == "exec":
                print("   exec:", n.get("command", "")[:90])
        return 1

    # ป้ายชื่อจากหน้า Dashboard: หา ui_* ที่ต่อสายไปหา node GPIO
    label_of = {}
    for n in nodes.values():
        if not n.get("type", "").startswith("ui_"):
            continue
        name = n.get("label") or n.get("name") or ""
        for wire in n.get("wires", []):
            for target in wire:
                if target in nodes and is_gpio(nodes[target]) and name:
                    label_of.setdefault(target, name)

    mode = detect_mode(n.get("pin") for n in gpio_nodes)
    print(f"Node-RED ตั้งเลขขาแบบ: {mode}"
          + ("  (ใช้กับ gpiozero ได้ตรงๆ)" if mode == "BCM" else "  (ต้องแปลงก่อนใช้)"))
    print()

    print(f"{'ชนิด node':<20} {'pin':>5}  {'ใช้กับ gpiozero':<22} {'ชื่อ node':<14} ป้ายบน Dashboard")
    print("-" * 92)
    for n in sorted(gpio_nodes, key=lambda x: str(x.get("pin", ""))):
        desc, _ = bcm_of(n.get("pin"), mode)
        print(f"{n.get('type',''):<20} {str(n.get('pin','-')):>5}  {desc:<22} "
              f"{(n.get('name') or '-'):<14} {label_of.get(n['id'], '-')}")

    # สรุปให้เอาไปใส่ gpio_test.py ได้เลย — ชนิดละหนึ่งบรรทัด ที่เหลือขึ้นเป็นหมายเหตุ
    picked = {}
    extra = []
    for n in gpio_nodes:
        tag = f"{n.get('name') or ''} {label_of.get(n['id'], '')}".strip().lower()
        _, bcm = bcm_of(n.get("pin"), mode)
        if bcm is None:
            continue
        # rank ต่ำ = ตรงกว่า ใช้ตัดสินเมื่อมีหลายตัวแย่งชื่อตัวแปรเดียวกัน
        if "led" in tag:
            key, rank = "PIN_LED", 0
        elif "buzz" in tag:
            key, rank = "PIN_BUZZER", 0
        elif "button" in tag or "btn" in tag:
            key, rank = "PIN_BUTTON", 0
        elif " in" in n.get("type", ""):
            key, rank = "PIN_BUTTON", 1      # ขาเข้าทั่วไป (DI) เป็นตัวสำรอง
        else:
            continue

        if key not in picked or rank < picked[key][2]:
            if key in picked:
                old_bcm, old_tag, _ = picked[key]
                extra.append(f"# {key} ตัวอื่น: {old_bcm}  ({old_tag})")
            picked[key] = (bcm, tag, rank)
        else:
            extra.append(f"# {key} ตัวอื่น: {bcm}  ({tag})")

    print("\n--- เอาไปใส่ใน gpio_test.py ---")
    for key in ("PIN_LED", "PIN_BUTTON", "PIN_BUZZER"):
        if key in picked:
            bcm, tag, _ = picked[key]
            print(f"{key} = {bcm}".ljust(22) + f"# {tag}")
        else:
            print(f"{key} = None".ljust(22) + "# หาไม่เจอ ต้องดูเอง")
    for line in extra:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
