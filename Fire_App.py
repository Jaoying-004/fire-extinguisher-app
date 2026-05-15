import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# เช็คว่าไฟล์กุญแจอยู่ในโฟลเดอร์ credentials และชื่อ key.json หรือยัง
import streamlit as st


# --- 1. การดึงความลับ (Secrets) ---
try:
    # ดึงค่าจาก Secrets ออกมาใช้ตรงๆ
    key_data = st.secrets["gcp_service_account"]

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_data, scope)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อกุญแจ: {e}")
    st.stop()

files = [s.title for s in client.openall()]


# --- 2. ดึงข้อมูลจาก Google Sheets ---
sheet_name = "FireExtinguisher_MasterList_2026"

# บรรทัดนี้คือการเปิดแท็บหลัก
sheet = client.open(sheet_name).worksheet("FireExtinguisher")

# *** เพิ่มบรรทัดนี้ลงไปเพื่อให้โปรแกรมรู้จัก log_sheet ***
log_sheet = client.open(sheet_name).worksheet("Inspection_Log")

# --- 3. หน้าตาแอป (UI) และ Tabs ---
st.title("🔥 FireExtinguisher")

tab1, tab2 = st.tabs(["📅 รายการตรวจวันนี้", "📋 ฐานข้อมูลถังทั้งหมด"])

#ดึงข้อมูลจากชีตมาโชว์

with tab1:
    st.subheader("รายการที่ตรวจเช็คแล้ววันนี้")
    from datetime import datetime
        # 1. ดึงข้อมูลทั้งหมดจากแท็บ Inspection_Log
    log_rows = log_sheet.get_all_values()

    if len(log_rows) > 1:
            # แยกหัวตารางและข้อมูลออกมา
        header = log_rows[0]
        data = log_rows[1:]

            # 2. สร้างวันที่ของ "วันนี้" ในรูปแบบปี-เดือน-วัน (YYYY-MM-DD)
        today_str = datetime.now().strftime("%Y-%m-%d")

            # 3. กรองข้อมูลเฉพาะแถวที่คอลัมน์ Timestamp (แถวแรก index 0) ตรงกับวันนี้
            # เราใช้ .startswith เพราะใน Sheets อาจมีเวลาต่อท้าย เช่น 2026-05-14 10:30:00
        today_data = [row for row in data if row[0].startswith(today_str)]

        if today_data:
                # 4. แปลงเป็น DataFrame และแสดงผล
            df_log = pd.DataFrame(today_data, columns=header)
            st.dataframe(df_log, use_container_width=True)
        else:
                # กรณีวันนี้ยังไม่มีใครบันทึกข้อมูลเลย
            st.info(f"📌 ยังไม่มีข้อมูลการตรวจบันทึกในวันที่ {today_str}")
    else:
        st.info("ยังไม่มีข้อมูลการตรวจบันทึกในแท็บ Log")


with tab2:
    st.subheader("ฐานข้อมูลสถานะถังดับเพลิงล่าสุด")
    # ดึงข้อมูลจากแท็บ MasterList (เหมือนที่คุณเคยเขียนไว้)
    master_rows = sheet.get_all_values()
    if master_rows:
        df_master = pd.DataFrame(master_rows[1:], columns=master_rows[0])
        # ลบคอลัมน์ที่ไม่มีชื่อออก
        df_master = df_master.loc[:, df_master.columns != '']
        st.dataframe(df_master, use_container_width=True)
    else:
        st.warning("⚠️ ไม่พบข้อมูลในแผ่นงานฐานข้อมูล")
# เพิ่มปุ่มกด Refresh ข้อมูล
if st.button("🔄 อัปเดตข้อมูลล่าสุด"):
    st.rerun()


# --- 4. ส่วนของแบบฟอร์มการตรวจเช็ค (เพิ่มต่อท้าย) ---
st.sidebar.header("📝 แบบฟอร์มบันทึกการตรวจ")
# ฟอร์มกรอกข้อมูล
@st.cache_data(ttl=600)
def get_tank_options():
    # ย้ายโค้ดดึงข้อมูลชื่อถังมาไว้ในนี้
    rows = sheet.get_all_values()
    return [row[0] for row in rows[1:]] # สมมติว่ารหัสถังอยู่คอลัมน์แรก

options = get_tank_options()

# 1. ดึงค่าจาก URL (ถ้ามี) เช่น ?tank_id=OF01
query_params = st.query_params
default_index = 0
target_tank = query_params.get("tank_id")
is_locked = False  # ตั้งค่าเริ่มต้นไว้ก่อน (กันพัง)
default_index = 0

# 2. หาว่ารหัสถังที่ส่งมา อยู่ในลำดับที่เท่าไหร่ของรายการ
if target_tank and target_tank in options:
    default_index = options.index(target_tank)
    is_locked = True


def upload_to_drive(file, folder_id):
    try:
        # สร้าง Service สำหรับ Drive API โดยใช้ credentials เดิมที่คุณมี
        # (หมายเหตุ: ตัวแปร creds ต้องเป็นชื่อเดียวกับที่คุณใช้ต่อ Sheets นะครับ)
        drive_service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': file.name,
            'parents': ['1iRHhotsmY6k2mDWY8fasi0S8LVthSyTi?hl']
        }

        # เตรียมไฟล์เพื่อส่งขึ้น Drive
        media = MediaIoBaseUpload(io.BytesIO(file.getvalue()),
                                  mimetype=file.type,
                                  resumable=True)

        uploaded_file = drive_service.files().create(body=file_metadata,
                                                     media_body=media,
                                                     fields='id, webViewLink').execute()

        return uploaded_file.get('webViewLink')  # คืนค่าเป็นลิงก์รูปภาพ
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอัปโหลดรูป: {e}")
        return None

with st.sidebar.form("check_form"):
    # ต้องมีคำว่า selected_tank มารับค่าตรงนี้ เพื่อเอาไปใช้บันทึกลง Sheets
    selected_tank = st.selectbox(
        "เลือกชื่อถังที่ต้องการตรวจ",
        options,
        index=default_index,
        disabled=is_locked  # ย้ายคำสั่งล็อกมาไว้ที่ตัวนี้แทน!
    )

    # --- ดึงประเภทถังมาจาก Master List ---
    # ประเภทถังอยู่ที่คอลัมน์ที่ 3 ใน Master List
    tank_info = sheet.find(selected_tank)
    tank_type = sheet.cell(tank_info.row, 3).value  # ดึงค่าประเภทถังออกมา
    st.write(f"🔍 ประเภทถัง: **{tank_type}**")
    inspector = st.text_input("ชื่อผู้ตรวจ")
    # --- ส่วนเช็คลิสต์ตามประเภท ---
    if tank_type == "ผงเคมีแห้ง":
        st.info("รายการตรวจเช็ค: ผงเคมีแห้ง")
        q1 = st.radio("1. เกจวัดความดัน (ปกติ/ไม่ปกติ)", ["ปกติ", "ไม่ปกติ"])
        q2 = st.radio("2. สายฉีด (ปกติ/ไม่ปกติ)", ["ปกติ", "ไม่ปกติ"])
        q3 = st.radio("3. สภาพตัวถัง (ไม่บุบ/บุบพัง)", ["ปกติ", "ไม่ปกติ"])
        q4 = st.radio("4. ซีลและสลัก (ครบ/ไม่ครบ)", ["ปกติ", "ไม่ปกติ"])

    elif tank_type == "CO2":
        st.info("รายการตรวจเช็ค: CO2")
        q1 = st.radio("1. น้ำหนักถัง (ได้มาตรฐานหรือไม่)", ["ปกติ", "ไม่ปกติ"])
        q2 = st.radio("2. คันบีบและสลัก", ["ปกติ", "ไม่ปกติ"])
        q3 = st.radio("3. หัวฉีด (ไม่มีน้ำแข็งเกาะ/ไม่อุดตัน)", ["ปกติ", "ไม่ปกติ"])

    else:
        # กรณีทั่วไปถ้าหาประเภทไม่เจอ
        status = st.radio("สถานะถังโดยรวม", ["ปกติ", "ไม่ปกติ"])

    # --- ส่วนแนบรูป (บังคับให้แนบเพื่อยืนยันว่าไปจริง) ---
    img_file = st.file_uploader("📸 แนบรูปถ่ายขณะตรวจเช็ค", type=['jpg', 'png', 'jpeg'])
    status = st.radio("สถานะถัง", ["ปกติ", "ไม่ปกติ (ต้องแก้ไข)"])
    # หมายเหตุ (กรณีมีข้อที่ไม่ปกติ)
    remarks = st.text_area("ระบุรายละเอียดเพิ่มเติม (ถ้าไม่ปกติ)")
    submit_button = st.form_submit_button("บันทึกข้อมูล")
    log_sheet = client.open(sheet_name).worksheet("Inspection_Log")

    if submit_button:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # สร้างตัวแปร now ไว้ที่นี่
        image_link = "ไม่มีรูปแนบ"
        try:
            # 1. อัปโหลดรูปภาพ (ถ้ามี)
            if img_file is not None:
                FOLDER_ID = "1iRHhotsmY6k2mDWY8fasi0S8LVthSyTi"  # ใส่ ID จริงของคุณ
                image_link = upload_to_drive(img_file, FOLDER_ID)

            # 2. บันทึกลง Log Sheet (ใช้ now และ image_link ได้แล้ว)
            new_log_entry = [now, selected_tank, inspector, status, remarks, image_link]
            log_sheet.append_row(new_log_entry)

            # 3. อัปเดตตารางหลัก (Master List)
            cell = sheet.find(selected_tank)
            sheet.update_cell(cell.row, 7, now)  # อัปเดตวันที่
            sheet.update_cell(cell.row, 6, status)  # อัปเดตสถานะ

            st.sidebar.success(f"✅ บันทึกข้อมูลถัง {selected_tank} เรียบร้อย!")
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"❌ เกิดข้อผิดพลาด: {e}")




