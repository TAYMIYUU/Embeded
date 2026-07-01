# Siemens LOGO!8 — Lab Notes

บันทึกการทดลอง 10 ภารกิจ ตั้งแต่พื้นฐานจนถึง Modbus TCP/IP และ HMI

---

## 1. Input / Output พื้นฐาน

ต่อวงจร Input–Output แบบง่ายที่สุด สร้างโปรเจกต์แรกด้วย FBD แล้ว transfer ลงเครื่องจริง

**Tool:** LOGOSoft Comfort V8.3

[ใส่รูป]

---

## 2. Toggle ด้วย Ladder Diagram

เขียนวงจรกดปุ่มครั้งเดียวสลับสถานะ (toggle) แบบ Ladder โดยใช้ Memory Bit เก็บสถานะ

**Tool:** LOGOSoft Comfort — Ladder mode

[ใส่รูป]

---

## 3. Toggle ด้วย FBD

วงจรเดียวกับข้อ 2 แต่เขียนด้วย Function Block Diagram แทน (AND Edge, Flag, XOR)

**Tool:** LOGOSoft Comfort — FBD mode

[ใส่รูป]

---

## 4. Press On – Hold Off

วงจรกดติด ปล่อยค้างตามเวลาที่ตั้งไว้ ใช้ Pulse Timer ตั้งค่า on-delay/off-delay

**Tool:** LOGOSoft Comfort — FBD

[ใส่รูป]

---

## 5. การใช้ Cursor Key

ใช้ปุ่มกดบนตัวเครื่อง (ESC + Cursor) ควบคุม Output โดยตรง พร้อมแสดงข้อความบนจอ LOGO!8

**Tool:** LOGOSoft Comfort — Message Text editor

[ใส่รูป]

---

## 6. Counter นับค่าและแสดงผล

นับขึ้น/ลงด้วยปุ่ม แสดงค่าบนจอผ่าน Message Text

**Tool:** LOGOSoft Comfort

[ใส่รูป]

---

## 7. Counter แบบเร่งความเร็ว

เพิ่ม Timer เข้าไปคู่กับ Counter ให้กดค้างแล้วนับเร็วขึ้นเรื่อยๆ

**Tool:** LOGOSoft Comfort

[ใส่รูป]

---

## 8. Modbus TCP

ตั้งค่า Modbus Server ใน LOGO!8 แล้วทดสอบอ่าน/เขียนค่าจากภายนอกผ่านหลายเครื่องมือ

- ตั้งค่า Server Connection, Port 502 ใน LOGOSoft
- ทดสอบอ่าน/เขียน register ด้วย Modbus Poll
- เขียนสคริปต์อ่าน/เขียนด้วย Python (pymodbus)
- ทำ flow อ่าน/เขียนด้วย Node-RED (node-red-contrib-modbus)

**Tool:** LOGOSoft Comfort, Modbus Poll, Python (pymodbus), Node-RED

[ใส่รูป]

---

## 9. เชื่อมต่อ HMI (Samkoon)

สร้างหน้าจอ monitor และควบคุมผ่าน HMI ยี่ห้อ Samkoon โดยเชื่อมต่อ Modbus TCP ไปยัง LOGO!8

- สร้าง Link แบบ Modbus Master TCP/IP
- วาง Numeric Display, Bit Lamp เพื่อ monitor
- วาง Bit Switch พร้อมเขียน Script ควบคุม output
- ทดสอบ Online Simulation แล้ว download ลงจอจริง

**Tool:** SKTOOL7.0 (Samkoon), จอ SK-070HS

[ใส่รูป]

---

## 10. โปรเจกต์รวม — ไฟจราจร

รวมทุกความรู้ที่เรียนมาไว้ในระบบเดียว: ไฟจราจร 1 ชุด (แดง/เหลือง/เขียว) มี 3 โหมดการทำงาน คือ อัตโนมัติ, เหลืองกระพริบ, และควบคุมด้วยมือ พร้อมควบคุมระยะไกลผ่าน Modbus-TCP

- เลือกโหมดด้วย Toggle Bit Counter + Binary Decoder
- โหมดกระพริบใช้ Pulse Timer สลับกันเอง
- โหมดอัตโนมัติใช้ Pulse Timer 3 ตัวต่อลูกโซ่ (เขียว 4 วิ → เหลือง 1 วิ → แดง 5 วิ)
- โหมดแมนนวลใช้ Toggle Switch + On-Delay Timer + RS Flip-Flop
- Map bit ควบคุม/สถานะไว้ใน Holding Register สำหรับสั่งงานผ่าน Modbus-TCP

**Tool:** LOGOSoft Comfort

[ใส่รูป]

---

## แหล่งข้อมูลเพิ่มเติม

- SIMATIC LOGO!8 พื้นฐาน: https://blog.ibcon.com/?p=882
- SIMATIC LOGO!8 → Modbus TCP: https://www.youtube.com/watch?v=8IOzlCiDTCc
- LOGO!8 + CiRA CORE ผ่าน Modbus TCP/IP (Part 1): https://www.youtube.com/watch?v=hJtMs00vtdI
- LOGO!8 + CiRA CORE ผ่าน Modbus TCP/IP (Part 2): https://youtu.be/EPwq_RtFvUI
