import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import pytz
from datetime import datetime


# ตั้งค่าเวลาไทยไว้ใช้ทั้งแอป
tz = pytz.timezone('Asia/Bangkok')
def get_now():
    return datetime.now(tz)
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
sheet = client.open(sheet_name).worksheet("FireExtinguisher_Data")

# *** เพิ่มบรรทัดนี้ลงไปเพื่อให้โปรแกรมรู้จัก log_sheet ***
log_sheet = client.open(sheet_name).worksheet("Inspection_Log")

# --- 3. หน้าตาแอป (UI) และ Tabs ---
st.title("🔥 FireExtinguisher")

tab1, tab2 = st.tabs(["📅 รายการตรวจวันนี้", "📋 ฐานข้อมูลถังทั้งหมด"])

#ดึงข้อมูลจากชีตมาโชว์

with tab1:
    st.subheader("รายการที่ตรวจเช็คแล้ววันนี้")
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
# 1. เลือกประเภทอุปกรณ์ (ถังดับเพลิง / Fire Alarm)
# ==========================================
# รองรับการรับค่าประเภทอุปกรณ์จาก URL (ถ้ามี) เช่น ?type=fire_extinguisher&id=0F01
query_params = st.query_params
url_type = query_params.get("type", "ถังดับเพลิง") # ค่าเริ่มต้นถ้าไม่มีคือถังดับเพลิง

device_type = st.sidebar.selectbox(
    "เลือกประเภทอุปกรณ์ที่ต้องการตรวจ",
    ["ถังดับเพลิง", "Fire Alarm"],
    index=0 if url_type == "ถังดับเพลิง" else 1
)

# 2. ดึงข้อมูล Master List ตามประเภทที่เลือก
# ==========================================
sheet_name_var = "FireExtinguisher_MasterList_2026"
@st.cache_data(ttl=600)
def get_device_options(sheet_name):
    # ปรับให้รับ sheet_name ตามประเภทอุปกรณ์ เช่น "Master_Extinguisher" หรือ "Master_FireAlarm"
    try:
        target_sheet = client.open(sheet_name_var).worksheet(sheet_name)
        rows = target_sheet.get_all_values()
        return [row[0] for row in rows[1:]] # สมมติรหัสอุปกรณ์อยู่คอลัมน์แรก
    except:
        return []

if device_type == "ถังดับเพลิง":
    options = get_device_options("FireExtinguisher_Data") # ชื่อ Sheet ของถังดับเพลิง
    id_label = "เลือก/สแกนรหัสถังดับเพลิง"
else:
    options = get_device_options("FireAlarm_Data") # ชื่อ Sheet ของ Fire Alarm
    id_label = "เลือกโซน/รหัส Fire Alarm"

# จัดการดึงค่า ID จาก URL (โค้ดส่วนนี้ยกมาจากรูปที่ 1 ของคุณ)
default_index = 0
target_id = query_params.get("id") # เปลี่ยนชื่อตัวแปรให้กลางขึ้น (จาก target_tank)

if target_id and target_id in options:
    default_index = options.index(target_id)

selected_device = st.sidebar.selectbox(id_label, options, index=default_index)

if device_type == "ถังดับเพลิง":
    options = get_device_options("FireExtinguisher_Data")  # ชื่อ worksheet ของถังดับเพลิง
    id_label = "เลือก/สแกนรหัสถังดับเพลิง"

    # ตรวจสอบว่ามี target_id จาก QR Code หรือไม่
    is_locked_by_qr = False

    if target_id and target_id in options:
        # มี QR Code และรหัสถูกต้อง
        default_index = options.index(target_id)
        is_locked_by_qr = True
        st.sidebar.success(f"🔒 **ล็อกจาก QR Code**: {target_id}")
    else:
        # ไม่มี QR Code หรือรหัสผิด
        if target_id:
            st.sidebar.error(f"⚠️ รหัสถัง '{target_id}' ไม่ถูกต้อง")
        st.sidebar.warning("⚠️ **กรุณาสแกน QR Code** ก่อนเริ่มตรวจสอบถังดับเพลิง")

    # แสดง selectbox
    selected_device = st.sidebar.selectbox(
        id_label,
        options,
        index=default_index,
        disabled=not is_locked_by_qr,  # ล็อกถ้าไม่มี QR
        key="selected_extinguisher"
    )

    # ปุ่มปลดล็อก
    if is_locked_by_qr:
        if st.sidebar.button("🔓 ปลดล็อกและสแกนใหม่"):
            st.query_params.clear()
            st.rerun()

    show_form = is_locked_by_qr
    form_disabled = not is_locked_by_qr

else:  # Fire Alarm
    options = get_device_options("FireAlarm_Data")  # ชื่อ worksheet ของ Fire Alarm
    id_label = "เลือกโซน/รหัส Fire Alarm"

    # Fire Alarm ไม่ต้องสแกน QR
    selected_device = st.sidebar.selectbox(
        id_label,
        options,
        key="selected_firealarm"
    )

    is_locked_by_qr = False
    show_form = True
    form_disabled = False


#ส่วนของการจัดการรูปภาพ
import cloudinary
import cloudinary.uploader
cloudinary.config(
    cloud_name="drac2fch1",
    api_key="111436524955713",
    api_secret="dKOBl29NIqRzeZ-CALZ22fgmHI8"
    )

    # อัปโหลดรูป
def upload_image(image_file):
    result = cloudinary.uploader.upload(image_file)
    return result["secure_url"]  # ← ได้ URL รูปกลับมา


with st.sidebar.form("check_form"):
    # ต้องมีคำว่า selected_tank มารับค่าตรงนี้ เพื่อเอาไปใช้บันทึกลง Sheets
    selected_tank = st.selectbox(
        "เลือกชื่อถังที่ต้องการตรวจ",
        options,
        index=default_index,
        disabled=is_locked_by_qr  # ย้ายคำสั่งล็อกมาไว้ที่ตัวนี้แทน!
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
        q1 = st.radio("1. เกจวัดความดันชี้ที่สีเขียว หน้าปัดไม่แตก", ["ใช่", "ไม่ใช่"])
        q2 = st.radio("2. สายฉีดไม่แตกลายงา ไม่อุดตัน", ["ใช่", "ไม่ใช่"])
        q3 = st.radio("3. สภาพตัวถังไม่บุบ ไม่มีสิ่งผิดปกติ", ["ใช่", "ไม่ใช่"])
        q4 = st.radio("4. ซีลและสลักอยู่ครบ ไม่ฉีกขาด", ["ใช่", "ไม่ใช่"])
        q5 = st.radio("5. ระยะรอบถังไม่มีสิ่งกีดขวาง เข้าใข้งานถังได้สะดวก", ["ใช่", "ไม่ใช่"])

    elif tank_type == "CO2":
        st.info("รายการตรวจเช็ค: CO2")
        q1 = st.radio("1. น้ำหนักถังปกติ (ยกประเมินด้วยมือต้องไม่เบาโหวง)", ["ใช่", "ไม่ใช่"])
        q2 = st.radio("2. คันบีบและสลักไม่เป็นสนิม ไม่หักงอ", ["ใช่", "ไม่ใช่"])
        q3 = st.radio("3. หัวฉีดไม่มีน้ำแข็งเกาะ/ไม่อุดตัน)", ["ใช่", "ไม่ใช่"])
        q4 = st.radio("4. ระยะรอบถังไม่มีสิ่งกีดขวาง เข้าใข้งานถังได้สะดวก", ["ใช่", "ไม่ใช่"])
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
    now_dt = get_now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    image_link = "ไม่มีรูปแนบ"
    try:
            # 1. อัปโหลดรูปภาพ (ถ้ามี)
        if img_file is not None:
            result = cloudinary.uploader.upload(img_file)  # ✅ Cloudinary
            image_link = result["secure_url"]

            # 2. บันทึกลง Log Sheet (ใช้ now และ image_link ได้แล้ว)
            new_log_entry = [now_str, selected_tank, inspector, status, remarks, image_link]
            log_sheet.append_row(new_log_entry)

            # 3. อัปเดตตารางหลัก (Master List)
            cell = sheet.find(selected_tank)
            sheet.update_cell(cell.row, 7, now_str)  # อัปเดตวันที่
            sheet.update_cell(cell.row, 6, status)  # อัปเดตสถานะ
            st.sidebar.success(f"✅ บันทึกข้อมูลและรูปภาพถัง {selected_tank} เรียบร้อย!")
    except Exception as e:
        st.sidebar.error(f"❌ เกิดข้อผิดพลาด: {e}")

# ส่วนของ Notification ในไลน์
import requests
import streamlit as st
def send_line_notify(message):
    token = st.secrets["line_api"]["channel_access_token"]
    # 1. ดึงรายชื่อ ID ทั้งหมดออกมาเป็น List
    target_ids = st.secrets["line_api"]["user_ids"]

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    data = {
        "to": "Cc41d99115e9081afa7a799a8964f1926",
        "messages": [{"type": "text", "text": message}]
    }
        # ส่งข้อมูล
    requests.post(url, headers=headers, json=data)


import pandas as pd
if st.button("📊 ส่งสรุปรายงานประจำเดือนเข้า LINE"):
    all_data = log_sheet.get_all_records()
    df = pd.DataFrame(all_data)

    if not df.empty:
        # ระบุตำแหน่งคอลัมน์
        col_date = df.columns[0]  # คอลัมน์วันที่
        col_id = df.columns[1]  # คอลัมน์ถัง
        col_status = df.columns[3]  # คอลัมน์สถานะ
        col_remark = df.columns[4]  # คอลัมน์หมายเหตุ

        # แปลงคอลัมน์วันที่เป็น datetime
        df[col_date] = pd.to_datetime(df[col_date], errors='coerce')
        # ลบแถวที่วันที่แปลงไม่ได้
        df = df.dropna(subset=[col_date])
        now_dt = get_now()
        # เอาเฉพาะเดือน/ปีปัจจุบัน
        df_month = df[
            (df[col_date].dt.month == now_dt.month) &
            (df[col_date].dt.year == now_dt.year)
        ]

        if not df_month.empty:
            # เรียงตามวันที่ก่อน เพื่อให้ keep='last' คือข้อมูลล่าสุดจริง
            df_month = df_month.sort_values(by=col_date)

            # เลือกเฉพาะบันทึกล่าสุดของแต่ละถังในเดือนนี้
            df_latest = df_month.drop_duplicates(subset=[col_id], keep='last')
            total_tanks = len(df_latest)
            passed = len(df_latest[df_latest[col_status] == 'ปกติ'])
            failed_df = df_latest[df_latest[col_status] == 'ไม่ปกติ (ต้องแก้ไข)']
            failed_count = len(failed_df)

            pass_rate = (passed / total_tanks) * 100 if total_tanks > 0 else 0

            msg = f"📊 (For Testing❗❗) Mr. SafePig สรุปผลประจำเดือน {now_dt.strftime('%m/%Y')}\n"
            msg += f"✅ ตรวจผ่าน: {pass_rate:.1f}% ({passed}/{total_tanks})\n"
            msg += f"❌ ไม่ผ่าน: {failed_count} รายการ\n"

            if failed_count > 0:
                msg += "\n🔍 รายการที่ต้องแก้ไข:\n"
                for _, row in failed_df.iterrows():
                    msg += f"- {row[col_id]}: {row[col_remark]}\n"
            else:
                msg += "\n✅ ทุกถังอยู่ในสภาพปกติ"

            send_line_notify(msg)
            st.success("🚀 ส่งรายงานสรุปเข้า LINE OA เรียบร้อยแล้ว!")
        else:
            st.warning("ไม่พบข้อมูลของเดือนปัจจุบันในชีต")




