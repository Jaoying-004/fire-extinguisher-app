import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# เช็คว่าไฟล์กุญแจอยู่ในโฟลเดอร์ credentials และชื่อ key.json หรือยัง
import streamlit as st
import json

# --- 1. การดึงความลับ (Secrets) ---
try:
    # ดึงค่าจาก Secrets ออกมาใช้ตรงๆ
    key_data = st.secrets["gcp_service_account"]

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
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
with tab1:
    # คราวนี้บรรทัดนี้จะทำงานได้แล้ว เพราะเรารู้จัก log_sheet จากข้างบนแล้ว
    log_rows = log_sheet.get_all_values()
    # ... โค้ดส่วนที่เหลือ ...

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

    # ดึงข้อมูลจากแท็บ Inspection_Log
    log_rows = log_sheet.get_all_values()
    if len(log_rows) > 1:
        df_log = pd.DataFrame(log_rows[1:], columns=log_rows[0])
        st.dataframe(df_log, use_container_width=True)
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

# สร้างรายการ ID ถังดับเพลิงจากตารางเพื่อให้เลือกง่ายๆ
target_id = st.sidebar.selectbox("เลือกชื่อถังที่ต้องการตรวจ", df_master['ID'].tolist())

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

selected_tank = st.selectbox(
        "เลือกชื่อถังที่ต้องการตรวจ",
        options,
        index=default_index,
        disabled=is_locked  # ล็อกตรงนี้! (ค่า is_locked ถูกตั้งไว้ที่บรรทัด 98 แล้ว)
    )

with st.sidebar.form("check_form"):
    inspector = st.text_input("ชื่อผู้ตรวจ")
    status = st.radio("สถานะถัง", ["ปกติ", "ไม่ปกติ (ต้องแก้ไข)"])
    remarks = st.text_area("หมายเหตุ (ถ้ามี)")
    submit_button = st.form_submit_button("บันทึกข้อมูล")
    log_sheet = client.open(sheet_name).worksheet("Inspection_Log")

    if submit_button:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_log_entry = [now, target_id, inspector, status, remarks]
        log_sheet.append_row(new_log_entry)

        st.sidebar.info("📌 บันทึกประวัติลง Log เรียบร้อย")

# 3. อัปเดตข้อมูลในแผ่นงานหลัก (Master List)
        try:
    # ค้นหาว่า ID ที่เราเลือก อยู่ในแถว (Row) ไหนของแผ่นงานหลัก
            cell = sheet.find(target_id)

    # สมมติว่า:
    # คอลัมน์ที่ 6 คือ Last Inspected (วันที่ตรวจ)
    # คอลัมน์ที่ 7 คือ Status (สถานะ)
    # คุณสามารถเปลี่ยนเลข 6 หรือ 7 ให้ตรงกับคอลัมน์ใน Sheets ของคุณได้เลยครับ
            sheet.update_cell(cell.row, 7, now)
            sheet.update_cell(cell.row, 6, status)

            st.sidebar.success(f"✅ อัปเดตสถานะถัง {target_id} ในตารางหลักแล้ว!")

    # สั่งให้แอปรีเฟรชเพื่อดึงข้อมูลใหม่มาโชว์ในตารางบนหน้าจอ
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"❌ เกิดข้อผิดพลาด: {e}")




