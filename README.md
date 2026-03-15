# MediaFire Pull File

**Last updated:** 2026-03-15

ดาวน์โหลดไฟล์จากโฟลเดอร์ MediaFire ลงคอมพิวเตอร์ของคุณ โดยคงโครงสร้างโฟลเดอร์ให้เหมือนต้นทาง รองรับทั้งโฟลเดอร์เดียวและหลายโฟลเดอร์ ดาวน์โหลดแบบหลายเธรด (จำนวนเธรดตามจำนวน CPU) และรองรับทั้งลิงก์ direct_download และ normal_download (เมื่อได้หน้า HTML จะดึง URL ไฟล์จริงจากในหน้านั้น)

---

## Updates

| Date       | Change                                                                                                                                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-03-15 | GitHub Actions CI: `.github/workflows/test.yml` — run unit tests on push/PR (Python 3.9–3.12); README updated with CI section and project structure.                                                                  |
| 2026-03-15 | Unit tests (pytest) and coverage (pytest-cov) added; `tests/test_main.py`; `requirements-dev.txt`; README updated with Testing section. No changes to `main.py` logic.                                                |
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
| `--log-file` | `-l`  | path ไฟล์ log (ข้อความทั้งหมดจะเขียนลงไฟล์นี้ด้วย)                               | `log-YYYYMMDD.log` |

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
| `MEDIAFIRE_LOG_FILE` | ไม่    | path ไฟล์ log (ค่าเริ่มต้น: `log-YYYYMMDD.log` ตามวันที่รัน)                |

\*จำเป็นสำหรับการดูรายการ/ดาวน์โหลด ตั้งใน `.env` หรือใช้ `--email` / `--password` ก็ได้

---

## หลักการทำงาน

- **การยืนยันตัวตน:** ล็อกอินด้วยอีเมล/รหัสผ่านผ่าน [MediaFire API](https://pypi.org/project/mediafire/)
- **การดูรายการ:** สำหรับแต่ละโฟลเดอร์ (URL หรือรหัส) จะดึงรายการไฟล์และโฟลเดอร์ย่อยแบบ recursive
- **การดาวน์โหลด:** ดาวน์โหลดแต่ละไฟล์และสร้างโครงสร้างโฟลเดอร์เดียวกันบนดิสก์ ใช้หลายเธรด (ค่าเริ่มต้นเท่ากับจำนวน logical CPU) เพื่อเร่งความเร็ว
- **ลิงก์ดาวน์โหลด:** ใช้ `direct_download` จาก API ก่อน ถ้าไม่มีจะลอง `normal_download` ถ้าได้หน้า HTML จะ parse หา URL ตรง (รูปแบบ `download*.mediafire.com`) แล้วดาวน์โหลดจาก URL นั้น หลังดาวน์โหลดจะตรวจสอบ SHA-256 กับค่าจาก API ถ้าไม่ตรงจะลบไฟล์และแจ้ง error
- **หลายโฟลเดอร์:** เมื่อส่งหลาย URL แต่ละโฟลเดอร์จะถูกเขียนไปยังโฟลเดอร์ย่อยของ path ปลายทาง (เช่น `./downloads/FolderName1/`, `./downloads/FolderName2/`)
- **Log:** ข้อความจากกระบวนการหลัก (โฟลเดอร์, การดาวน์โหลด, ข้ามไฟล์ที่มีอยู่, error) จะเขียนลงไฟล์ log (ชื่อตามวัน: `log-YYYYMMDD.log` หรือกำหนด path ด้วย `-l` / `--log-file` / `MEDIAFIRE_LOG_FILE`)

**เทคโนโลยี:** Python 3, [mediafire](https://pypi.org/project/mediafire/) SDK, [requests](https://pypi.org/project/requests/) สำหรับ streaming download, [python-dotenv](https://pypi.org/project/python-dotenv/) สำหรับโหลด `.env`

---

## การทดสอบ (Unit tests & coverage)

โปรเจกต์ใช้ **pytest** และ **pytest-cov** สำหรับ unit test และ coverage โดยไม่แก้ logic ใน `main.py`

### ติดตั้ง dependencies สำหรับทดสอบ

```bash
pip install -r requirements-dev.txt
```

(`requirements-dev.txt` รวม `requirements.txt` + pytest + pytest-cov)

### รัน unit tests

```bash
# รันทุก test
pytest tests/ -v

# รันแบบย่อ
pytest tests/ -q
```

### รัน coverage

```bash
# แสดง coverage บนเทอร์มินัล (มีรายการบรรทัดที่ยังไม่ถูก cover)
pytest tests/ --cov=main --cov-report=term-missing

# สร้างรายงาน HTML (โฟลเดอร์ htmlcov/)
pytest tests/ --cov=main --cov-report=html
```

### สิ่งที่ทดสอบ

- **parse_folder_identifier** — URL, folder key 13 ตัว, path, `mf:` URI
- **parse_folder_identifiers** — ค่าหลายโฟลเดอร์คั่นด้วย comma/newline
- **_folder_display_name** — ชื่อโฟลเดอร์จาก URL/key/path
- **_sanitize_path_component / _sanitize_dirname** — อักขระต้องห้ามในชื่อไฟล์/โฟลเดอร์
- **_default_worker_count** — จำนวน thread ตาม CPU
- **_get_download_url_from_links** — ดึง URL จาก API response (direct_download, normal_download)
- **_extract_direct_url_from_html** — ดึง URL ตรงจากหน้า HTML
- **list_all_files** — รายการไฟล์ (รวม subfolder) ด้วย mock client
- **_download_file_safe** — ดาวน์โหลดไฟล์ด้วย mock client และ requests
- **download_folder** — โฟลเดอร์ว่าง, ข้ามไฟล์ที่มีอยู่แล้ว
- **main()** — CLI: ไม่มีโฟลเดอร์/ไม่มี credentials → exit 1; มี folder + credentials + mock client → เรียก download_folder

### GitHub Actions (CI)

Unit tests รันอัตโนมัติบน GitHub Actions ทุกครั้งที่ push หรือเปิด pull request ไปยัง `main` / `master`

- **Workflow:** `.github/workflows/test.yml`
- **Triggers:** `push` และ `pull_request` ที่ branch `main`, `master`
- **Runner:** `ubuntu-latest`
- **Python versions:** 3.9, 3.10, 3.11, 3.12 (matrix)
- **Steps:** checkout → setup Python (with pip cache) → `pip install -r requirements-dev.txt` → `pytest tests/ -v --tb=short` → `pytest tests/ --cov=main --cov-report=term-missing`
- **Credentials:** ไม่ต้องตั้งค่า secret — tests ใช้ mock ไม่เรียก MediaFire จริง

ผลการรันทดสอบแสดงในแท็บ **Actions** ของ repo และบน pull request เป็น status check

---

## โครงสร้างโปรเจกต์

```text
mediafire_pull_file/
├── .github/
│   └── workflows/
│       └── test.yml     # GitHub Actions: run unit tests on push/PR
├── main.py              # จุดเข้า CLI, logic ดาวน์โหลด (direct/normal_download, parse HTML)
├── requirements.txt     # mediafire, requests, python-dotenv
├── requirements-dev.txt # สำหรับพัฒนา: requirements.txt + pytest, pytest-cov
├── tests/
│   ├── __init__.py
│   └── test_main.py     # unit tests สำหรับ main.py
├── .env.example         # ตัวอย่าง .env (คัดลอกเป็น .env)
├── .env                 # ข้อมูลล็อกอินของคุณ (สร้างจาก .env.example ห้าม commit)
└── README.md
```

---

## สิทธิ์การใช้งาน

นำไปใช้และปรับแก้ได้ตามต้องการ MediaFire Python SDK อยู่ภายใต้ [สัญญาอนุญาต BSD](https://pypi.org/project/mediafire/)
