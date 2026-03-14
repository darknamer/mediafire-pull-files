# MediaFire Pull File

**Last updated:** 2025-03-14

ดาวน์โหลดไฟล์จากโฟลเดอร์ MediaFire ลงคอมพิวเตอร์ของคุณ โดยคงโครงสร้างโฟลเดอร์ให้เหมือนต้นทาง รองรับทั้งโฟลเดอร์เดียวและหลายโฟลเดอร์ ดาวน์โหลดแบบหลายเธรด (จำนวนเธรดตามจำนวน CPU) และรองรับทั้งลิงก์ direct_download และ normal_download (เมื่อได้หน้า HTML จะดึง URL ไฟล์จริงจากในหน้านั้น)

---

## Updates

| Date       | Change                                                                                                                                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2025-03-14 | Download: รองรับทั้ง `direct_download` และ `normal_download` ถ้า API คืนแค่ normal_download และได้หน้า HTML จะ parse หา URL ไฟล์จริง (download\*.mediafire.com) แล้วดาวน์โหลดต่อ ตรวจ hash (SHA-256) หลังดาวน์โหลด |
| 2025-03-14 | Multi-threaded download (default: CPU count); `-j` / `--threads` and `MEDIAFIRE_THREADS`.                                                                                                                          |
| 2025-03-14 | Multiple folder URLs: comma/newline in `MEDIAFIRE_FOLDER` or multiple CLI args; each folder → subdir under output.                                                                                                 |
| 2025-03-14 | `.env` support via `python-dotenv`; credentials and options from env.                                                                                                                                              |
| 2025-03-14 | English comments added in `main.py`.                                                                                                                                                                               |

_(Edit the table above when you change the project.)_

---

## เริ่มต้นด่วน

**1. ติดตั้ง**

```bash
pip install -r requirements.txt
```

**2. ใส่ข้อมูลล็อกอิน**

คัดลอกไฟล์ตัวอย่าง env แล้วแก้ไข:

```bash
copy .env.example .env
```

เปิดไฟล์ `.env` แล้วตั้งค่าอีเมลและรหัสผ่าน MediaFire:

```env
MEDIAFIRE_EMAIL=your.email@example.com
MEDIAFIRE_PASSWORD=your_password
```

**3. รัน**

```bash
# ดาวน์โหลดโฟลเดอร์เดียว (วางลิงก์โฟลเดอร์ MediaFire ที่ต้องการ)
python main.py "https://www.mediafire.com/folder/XXXXX/YourFolderName"
```

ไฟล์จะถูกบันทึกที่ `./downloads/` โดยค่าเริ่มต้น ใช้ `-o` ถ้าต้องการโฟลเดอร์ปลายทางอื่น

---

## การติดตั้ง (ครั้งเดียว)

### สิ่งที่ต้องมี

- **Python 3.6 ขึ้นไป**
- **บัญชี MediaFire** (อีเมล + รหัสผ่าน) — สคริปต์ใช้ API อย่างเป็นทางการ จึงต้องล็อกอินเพื่อดูรายการและดาวน์โหลด

### ติดตั้งแพ็กเกจ

```bash
pip install -r requirements.txt
```

### ตั้งค่าข้อมูลล็อกอิน

สคริปต์อ่านค่าจากไฟล์ **`.env`** ในโฟลเดอร์โปรเจกต์ (ไม่ต้อง export ตัวแปรเอง)

1. สร้างไฟล์ env:

   ```bash
   copy .env.example .env
   ```

   _(บน Linux/macOS: `cp .env.example .env`)_

2. แก้ไข `.env` แล้วตั้งค่าอย่างน้อย:
   - `MEDIAFIRE_EMAIL` — อีเมลที่ใช้ล็อกอิน MediaFire
   - `MEDIAFIRE_PASSWORD` — รหัสผ่าน MediaFire

3. ตัวเลือกเพิ่มใน `.env`:
   - `MEDIAFIRE_FOLDER` — URL โฟลเดอร์เริ่มต้นที่จะดาวน์โหลด (ดู [หลายโฟลเดอร์](#หลายโฟลเดอร์))
   - `MEDIAFIRE_OUTPUT` — โฟลเดอร์ปลายทางเริ่มต้น (ค่าเริ่มต้น: `./downloads`)
   - `MEDIAFIRE_APP_ID` — ปล่อยตามเดิม ยกเว้นใช้แอปกำหนดเอง (ค่าเริ่มต้น: `42511`)
   - `MEDIAFIRE_THREADS` — จำนวนเธรดสำหรับดาวน์โหลด (ค่าเริ่มต้น: ตามจำนวน CPU)

**ความปลอดภัย:** ไฟล์ `.env` อยู่ใน `.gitignore` ห้าม commit หรือแชร์ เพราะมีรหัสผ่าน

---

## วิธีใช้

### โฟลเดอร์เดียว

ส่ง URL โฟลเดอร์ MediaFire (หรือรหัสโฟลเดอร์ หรือ path) เป็นอาร์กิวเมนต์แรก:

```bash
python main.py "https://www.mediafire.com/folder/1z3vk56tf787k/ImageBasedAttendance"
```

หรือใช้รหัสโฟลเดอร์ 13 ตัวอักษร:

```bash
python main.py 1z3vk56tf787k
```

บันทึกไปยังโฟลเดอร์ที่กำหนด:

```bash
python main.py "https://www.mediafire.com/folder/KEY/Name" -o ./my_backup
```

ถ้าตั้ง `MEDIAFIRE_FOLDER` ใน `.env` ไว้แล้ว สามารถรันโดยไม่ต้องใส่อาร์กิวเมนต์:

```bash
python main.py
```

### หลายโฟลเดอร์

**จากคำสั่ง** — ส่งหลาย URL โฟลเดอร์ แต่ละโฟลเดอร์จะถูกดาวน์โหลดไปยังโฟลเดอร์ย่อยของตัวเองภายใต้โฟลเดอร์ปลายทาง:

```bash
python main.py "https://www.mediafire.com/folder/KEY1/Name1" "https://www.mediafire.com/folder/KEY2/Name2" -o ./downloads
```

ผลลัพธ์: `./downloads/Name1/` และ `./downloads/Name2/` (หรือใช้รหัสโฟลเดอร์ถ้า URL ไม่มีชื่อ)

**จาก `.env`** — ใส่หลาย URL คั่นด้วย comma หรือขึ้นบรรทัดใหม่:

```env
MEDIAFIRE_FOLDER=https://www.mediafire.com/folder/KEY1/Name1,https://www.mediafire.com/folder/KEY2/Name2
```

จากนั้นรัน:

```bash
python main.py
```

### ค่าที่ใช้เป็น "โฟลเดอร์" ได้

| รูปแบบ                | ตัวอย่าง                                                              |
| --------------------- | --------------------------------------------------------------------- |
| URL โฟลเดอร์เต็ม      | `https://www.mediafire.com/folder/1z3vk56tf787k/ImageBasedAttendance` |
| รหัสโฟลเดอร์ (13 ตัว) | `1z3vk56tf787k`                                                       |
| path บัญชีของคุณ      | `/Documents` หรือ `mf:///Documents` (สำหรับไฟล์ของคุณเอง)             |

---

## อ้างอิงคำสั่ง

```text
python main.py [FOLDER ...] [OPTIONS]
```

| ตัวเลือก     | Short | คำอธิบาย                                                                         | ค่าเริ่มต้น   |
| ------------ | ----- | -------------------------------------------------------------------------------- | ------------- |
| `FOLDER`     | —     | URL/รหัส/path โฟลเดอร์หนึ่งหรือมากกว่า ไม่ใส่จะใช้ `MEDIAFIRE_FOLDER` จาก `.env` | —             |
| `--output`   | `-o`  | โฟลเดอร์ที่ใช้เก็บไฟล์                                                           | `./downloads` |
| `--email`    | —     | อีเมล MediaFire (แทนที่ `MEDIAFIRE_EMAIL`)                                       | จาก `.env`    |
| `--password` | —     | รหัสผ่าน MediaFire (แทนที่ `MEDIAFIRE_PASSWORD`)                                 | จาก `.env`    |
| `--app-id`   | —     | MediaFire App ID                                                                 | `42511`       |
| `--threads`  | `-j`  | จำนวนเธรดสำหรับดาวน์โหลด (ค่าเริ่มต้น: ตามจำนวน CPU)                             | ตาม CPU       |
| `--quiet`    | `-q`  | แสดงผลน้อยลง (เฉพาะเมื่อมีข้อผิดพลาด)                                            | ปิด           |

**ตัวอย่าง**

```bash
# โฟลเดอร์เดียว ค่า output เริ่มต้น
python main.py "https://www.mediafire.com/folder/KEY/Name"

# โฟลเดอร์ปลายทางที่กำหนดเอง
python main.py "https://..." -o ./backup

# หลายโฟลเดอร์
python main.py "https://.../folder1" "https://.../folder2" -o ./all

# ใส่ข้อมูลล็อกอินในคำสั่ง (แทนที่ .env)
python main.py "https://..." --email you@example.com --password secret

# โหมดเงียบ
python main.py -q

# กำหนดจำนวนเธรด (เช่น 8 เธรด)
python main.py "https://..." -j 8
```

---

## ตัวแปรสภาพแวดล้อม

ทุกตัวเลือกด้านล่างไม่บังคับถ้าส่งค่าผ่านคำสั่ง สคริปต์โหลด `.env` อัตโนมัติ (ผ่าน `python-dotenv`)

| ตัวแปร               | บังคับ | คำอธิบาย                                                                   |
| -------------------- | ------ | -------------------------------------------------------------------------- |
| `MEDIAFIRE_EMAIL`    | ใช่\*  | อีเมลบัญชี MediaFire                                                       |
| `MEDIAFIRE_PASSWORD` | ใช่\*  | รหัสผ่านบัญชี MediaFire                                                    |
| `MEDIAFIRE_FOLDER`   | ไม่    | โฟลเดอร์เริ่มต้น: หนึ่ง URL หรือหลาย URL คั่นด้วย comma หรือขึ้นบรรทัดใหม่ |
| `MEDIAFIRE_OUTPUT`   | ไม่    | โฟลเดอร์ปลายทางเริ่มต้น                                                    |
| `MEDIAFIRE_APP_ID`   | ไม่    | MediaFire App ID (ค่าเริ่มต้น: `42511`)                                    |
| `MEDIAFIRE_THREADS`  | ไม่    | จำนวนเธรดดาวน์โหลด (ค่าเริ่มต้น: ตามจำนวน CPU)                             |

\*จำเป็นสำหรับการดูรายการ/ดาวน์โหลด ตั้งใน `.env` หรือใช้ `--email` / `--password` ก็ได้

---

## หลักการทำงาน

- **การยืนยันตัวตน:** ล็อกอินด้วยอีเมล/รหัสผ่านผ่าน [MediaFire API](https://pypi.org/project/mediafire/)
- **การดูรายการ:** สำหรับแต่ละโฟลเดอร์ (URL หรือรหัส) จะดึงรายการไฟล์และโฟลเดอร์ย่อยแบบ recursive
- **การดาวน์โหลด:** ดาวน์โหลดแต่ละไฟล์และสร้างโครงสร้างโฟลเดอร์เดียวกันบนดิสก์ ใช้หลายเธรด (ค่าเริ่มต้นเท่ากับจำนวน logical CPU) เพื่อเร่งความเร็ว
- **ลิงก์ดาวน์โหลด:** ใช้ `direct_download` จาก API ก่อน ถ้าไม่มีจะลอง `normal_download` ถ้าได้หน้า HTML จะ parse หา URL ตรง (รูปแบบ `download*.mediafire.com`) แล้วดาวน์โหลดจาก URL นั้น หลังดาวน์โหลดจะตรวจสอบ SHA-256 กับค่าจาก API ถ้าไม่ตรงจะลบไฟล์และแจ้ง error
- **หลายโฟลเดอร์:** เมื่อส่งหลาย URL แต่ละโฟลเดอร์จะถูกเขียนไปยังโฟลเดอร์ย่อยของ path ปลายทาง (เช่น `./downloads/FolderName1/`, `./downloads/FolderName2/`)

**เทคโนโลยี:** Python 3, [mediafire](https://pypi.org/project/mediafire/) SDK, [requests](https://pypi.org/project/requests/) สำหรับ streaming download, [python-dotenv](https://pypi.org/project/python-dotenv/) สำหรับโหลด `.env`

---

## โครงสร้างโปรเจกต์

```text
mediafire_pull_file/
├── main.py           # จุดเข้า CLI, logic ดาวน์โหลด (direct/normal_download, parse HTML)
├── requirements.txt  # mediafire, requests, python-dotenv
├── .env.example      # ตัวอย่าง .env (คัดลอกเป็น .env)
├── .env              # ข้อมูลล็อกอินของคุณ (สร้างจาก .env.example ห้าม commit)
└── README.md
```

---

## สิทธิ์การใช้งาน

นำไปใช้และปรับแก้ได้ตามต้องการ MediaFire Python SDK อยู่ภายใต้ [สัญญาอนุญาต BSD](https://pypi.org/project/mediafire/)
