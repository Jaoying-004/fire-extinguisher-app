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
#-----------------------------------------------------------------------------------------------------------------------
#หน้าล็อคอิน
st.set_page_config(
    page_title="ระบบตรวจเช็คถังดับเพลิง",
    page_icon="🧯",
    layout="wide"
)

# -----------------------------
# CSS
# -----------------------------
st.markdown("""
<style>
/* ซ่อนเมนู streamlit ถ้าต้องการ */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* พื้นหลังหลัก */
.stApp {
    background: linear-gradient(135deg, #f8fbff 0%, #eef4ff 100%);
}

/* กล่อง login */
.login-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 80vh;
}

.login-card {
    background: white;
    padding: 2.2rem 2rem 1.8rem 2rem;
    border-radius: 22px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.10);
    width: 100%;
    max-width: 460px;
    border: 1px solid #e9eef7;
}

.login-title {
    text-align: center;
    font-size: 1.8rem;
    font-weight: 700;
    color: #1f3b73;
    margin-bottom: 0.2rem;
}

.login-subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

.login-icon {
    text-align: center;
    font-size: 3rem;
    margin-bottom: 0.4rem;
}

.login-note {
    text-align: center;
    font-size: 0.88rem;
    color: #6b7280;
    margin-top: 0.8rem;
}
</style>
""", unsafe_allow_html=True)

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

@st.cache_resource
def get_gspread_client():
    creds = ServiceAccountCredentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)

client = get_gspread_client()
workbook = client.open_by_key(st.secrets["sheet_id"])

sheet_emp = workbook.worksheet("employee_list")
sheet_log = workbook.worksheet("login_log")

tz = pytz.timezone("Asia/Bangkok")

def get_now():
    return datetime.now(tz)

# -----------------------------
# AUTH FUNCTIONS
# -----------------------------
def is_valid_employee(emp_id):
    records = sheet_emp.get_all_records()
    for row in records:
        if str(row.get("employee_id", "")).strip() == str(emp_id).strip():
            return True
    return False

def has_logged_in_today(emp_id):
    from datetime import datetime, date
    today = date.today().isoformat()
    records = sheet_log.get_all_records()
    for row in records:
        if (
            str(row.get("employee_id", "")).strip() == str(emp_id).strip()
            and str(row.get("date", "")).strip() == today
        ):
            return True
    return False

def save_login_log(emp_id):
    now = get_now()
    sheet_log.append_row([
        str(emp_id).strip(),
        now.date().isoformat(),
        now.strftime("%H:%M:%S")
    ])

def check_auth_status():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "emp_id" not in st.session_state:
        st.session_state.emp_id = ""

    return st.session_state.authenticated

# -----------------------------
# LOGIN PAGE
# -----------------------------
def show_login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        st.markdown("""
            <div class="login-card">
                <div class="login-icon">🧯</div>
                <div class="login-title">ระบบตรวจเช็คถังดับเพลิง</div>
                <div class="login-subtitle">
                    กรุณาเข้าสู่ระบบด้วยรหัสพนักงานก่อนใช้งาน
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            emp_id = st.text_input(
                "รหัสพนักงาน",
                placeholder="กรอกรหัสพนักงาน",
                key="login_emp_id"
            )
            submitted = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)

        if submitted:
            emp_id = emp_id.strip()

            if not emp_id:
                st.warning("กรุณากรอกรหัสพนักงาน")
            elif not is_valid_employee(emp_id):
                st.error("ไม่พบรหัสพนักงานนี้ในระบบ")
            else:
                st.session_state.authenticated = True
                st.session_state.emp_id = emp_id

                if not has_logged_in_today(emp_id):
                    save_login_log(emp_id)

                st.success("เข้าสู่ระบบสำเร็จ")
                st.rerun()

        st.markdown(
            '<div class="login-note">เข้าใช้งานได้วันละ 1 ครั้งต่ออุปกรณ์/เบราว์เซอร์</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)













# --- 2. ดึงข้อมูลจาก Google Sheets ---
sheet_name = "FireExtinguisher_MasterList_2026"
spreadsheet = client.open(sheet_name)
# บรรทัดนี้คือการเปิดแท็บหลัก
sheet = client.open(sheet_name).worksheet("FireExtinguisher_Data")

# *** เพิ่มบรรทัดนี้ลงไปเพื่อให้โปรแกรมรู้จัก log_sheet ***
log_sheet = client.open(sheet_name).worksheet("Inspection_Log")

# --- 3. หน้าตาแอป (UI) และ Tabs ---
st.title("🔥 FireExtinguisher")

tab1, tab2, tab3, tab4 = st.tabs(["📅 รายการตรวจวันนี้", "📋 FireExtinguisher_Data", "🚨 Emergency_Safety_Equipment", "🔧 ติดตามการแก้ไข"])

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
    st.subheader("📋 FireExtinguisher_Data")
    # ดึงข้อมูลจากแท็บ MasterList (เหมือนที่คุณเคยเขียนไว้)
    master_rows = sheet.get_all_values()
    if master_rows:
        df_master = pd.DataFrame(master_rows[1:], columns=master_rows[0])
        # ลบคอลัมน์ที่ไม่มีชื่อออก
        df_master = df_master.loc[:, df_master.columns != '']
        st.dataframe(df_master, use_container_width=True)
    else:
        st.warning("⚠️ ไม่พบข้อมูลในแผ่นงานฐานข้อมูล")

with tab3:
    st.subheader("🚨 Emergency_Safety_Equipment")

    try:
        # 1. สั่งเปิดหน้าแท็บฐานข้อมูลหลักของระบบ Fire Alarm
        fa_sheet = client.open(sheet_name).worksheet("Emergency_Safety_Equipment")
        fa_master_rows = fa_sheet.get_all_values()

        if fa_master_rows:
            # 2. แปลงเป็นตาราง DataFrame (เอาแถวที่ 1 เป็นหัวคอลัมน์)
            df_fa_master = pd.DataFrame(fa_master_rows[1:], columns=fa_master_rows[0])

            # 3. ลบคอลัมน์ที่ไม่มีหัวข้อหรือคอลัมน์ว่างออก
            df_fa_master = df_fa_master.loc[:, df_fa_master.columns != '']

            # 4. แสดงผลตาราง Master ข้อมูลทั้งหมดบนหน้าจอตรงกลาง
            st.dataframe(df_fa_master, use_container_width=True)
        else:
            st.warning("⚠️ ไม่พบข้อมูลในแผ่นงานฐานข้อมูล FireAlarm_Data")

    except Exception as e:
        st.error(f"❌ ไม่สามารถโหลดตารางฐานข้อมูลได้เนื่องจาก: {e}")

with tab4:
    st.subheader("🔧 ติดตามการแก้ไข")
    try:
        inspection_sheet = client.open(sheet_name).worksheet("Inspection_Log")
        inspection_rows = inspection_sheet.get_all_values()

        if inspection_rows and len(inspection_rows) > 1:
            df_inspection = pd.DataFrame(inspection_rows[1:], columns=inspection_rows[0])
            df_inspection = df_inspection.loc[:, df_inspection.columns != '']

            if 'Status' in df_inspection.columns:
                df_need_repair = df_inspection[
                    df_inspection['Status'].str.strip() == 'ไม่ปกติ (ต้องแก้ไข)'
                    ]

                # สถิติ
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📋 ทั้งหมด", len(df_inspection))
                with col2:
                    st.metric("⚠️ ต้องแก้ไข", len(df_need_repair))
                with col3:
                    if len(df_inspection) > 0:
                        percent = (len(df_need_repair) / len(df_inspection)) * 100
                        st.metric("📊 %", f"{percent:.1f}%")

                st.divider()

                # ตาราง
                if not df_need_repair.empty:
                    st.warning(f"พบ {len(df_need_repair)} รายการ")
                    st.dataframe(df_need_repair, use_container_width=True)
                else:
                    st.success("🎉 ไม่มีรายการที่ต้องแก้ไข")

    except Exception as e:
        st.error(f"❌ Error: {e}")

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
        return [row[1] for row in rows[1:]] # สมมติรหัสอุปกรณ์อยู่คอลัมน์แรก
    except:
        return []





#-----------------------------------------------------------------------------
query_params = st.query_params
target_id = query_params.get("tank_id") # ดึงค่ารหัสอุปกรณ์จาก URL
default_index = 0
is_locked_by_qr = False

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
        # ปุ่มปลดล็อก
    if is_locked_by_qr:
        if st.sidebar.button("🔓 ปลดล็อกและสแกนใหม่"):
            st.query_params.clear()
            st.rerun()

    show_form = is_locked_by_qr
    form_disabled = not is_locked_by_qr

else:  # Fire Alarm
    options = get_device_options("Emergency_Safety_Equipment")
    id_label = "เลือกโซน/รหัส Fire Alarm"
    show_form = True
    form_disabled = False

# ปุ่ม Selectbox
# =======================================================
selected_device = st.sidebar.selectbox(
    id_label,
    options,
    index=default_index, # ทีนี้พอสลับเป็น Fire Alarm ตัวแปรนี้จะมีค่าเป็น 0 และทำงานได้ฉลุยครับ
    disabled=is_locked_by_qr,
    key=f"select_{device_type}"
)

#---------------------------------------------------------------------------------------------------------------
# --- สั่งเปิดชีตหลักแยกตามหน้างานจริงของคุณ ---
if device_type == "ถังดับเพลิง":
    sheet = client.open(sheet_name).worksheet("FireExtinguisher_Data")
else:
    sheet = client.open(sheet_name).worksheet("Emergency_Safety_Equipment")

# --- โดดเข้าโฟลวการค้นหาข้อมูลในตารางหลัก ---
if selected_device:
    cell_info = sheet.find(selected_device)

    if cell_info is not None:
        # 💡 ดึงค่าจากคอลัมน์ที่ 3 ของชีตที่เปิดอยู่มาเก็บไว้ (เป็นได้ทั้งประเภทถัง และประเภทอุปกรณ์)
        device_sub_type = sheet.cell(cell_info.row, 3).value

    else:
        device_sub_type = None
        st.warning(f"⚠️ ไม่พบข้อมูลของรหัส {selected_device} ในตาราง Master List")
else:
    device_sub_type = None
#-----------------------------------------------------------------------------------------------------------------
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
#-------------------------------------------------------------------------------------------------------------------
#ส่วนของแบบฟอร์มการตรวจเช็ค
with st.sidebar.form("check_form", clear_on_submit=True):
    inspector = st.text_input("ชื่อผู้ตรวจ", key="inspector_input")

    # --- ส่วนเช็คลิสต์ตามประเภท ---
    if device_type == "ถังดับเพลิง":
        if device_sub_type == "ผงเคมีแห้ง":
            st.write(f"🔍 ประเภทถัง: **{device_sub_type}**")
            q1 = st.radio("1. เกจวัดความดันชี้ที่สีเขียว หน้าปัดไม่แตก", ["ใช่", "ไม่ใช่"], key="chk_dry_1")
            q2 = st.radio("2. สายฉีดไม่แตกลายงา ไม่อุดตัน", ["ใช่", "ไม่ใช่"], key="chk_dry_2")
            q3 = st.radio("3. สภาพตัวถังไม่บุบ ไม่มีสิ่งผิดปกติ", ["ใช่", "ไม่ใช่"], key="chk_dry_3")
            q4 = st.radio("4. ซีลและสลักอยู่ครบ ไม่ฉีกขาด", ["ใช่", "ไม่ใช่"], key="chk_dry_4")
            q5 = st.radio("5. ระยะรอบถังไม่มีสิ่งกีดขวาง เข้าใข้งานถังได้สะดวก", ["ใช่", "ไม่ใช่"], key="chk_dry_5")

        elif device_sub_type == "CO2":
            st.write(f"🔍 ประเภทถัง: **{device_sub_type}**")
            q1 = st.radio("1. น้ำหนักถังปกติ (ยกประเมินด้วยมือต้องไม่เบาโหวง)", ["ใช่", "ไม่ใช่"], key="chk_co2_1")
            q2 = st.radio("2. คันบีบและสลักไม่เป็นสนิม ไม่หักงอ", ["ใช่", "ไม่ใช่"], key="chk_co2_2")
            q3 = st.radio("3. หัวฉีดไม่มีน้ำแข็งเกาะ/ไม่อุดตัน)", ["ใช่", "ไม่ใช่"], key="chk_co2_3")
            q4 = st.radio("4. ระยะรอบถังไม่มีสิ่งกีดขวาง เข้าใข้งานถังได้สะดวก", ["ใช่", "ไม่ใช่"], key="chk_co2_4")

    elif device_type == "Fire Alarm":
        st.info("🚨 ตรวจระบบ: Fire Alarm")
        st.write(f"🔍 ประเภทอุปกรณ์: **{device_sub_type}**")
        status = st.radio("สถานะโดยรวม", ["ปกติ", "ไม่ปกติ"])


    # --- ส่วนแนบรูป (บังคับให้แนบเพื่อยืนยันว่าไปจริง) ---
    img_file = st.file_uploader("📸 แนบรูปถ่ายขณะตรวจเช็ค", type=['jpg', 'png', 'jpeg'])
    status = st.radio("สถานะโดยรวม", ["ปกติ", "ไม่ปกติ (ต้องแก้ไข)"])
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
        new_log_entry = [
            now_str,  # คอลัมน์ 1: วันเวลาที่ตรวจ
            device_sub_type,  # คอลัมน์ 3: ประเภทอุปกรณ์ (Type) 💡 เพิ่มตัวนี้เข้ามาแล้วครับ
            selected_device,  # คอลัมน์ 2: รหัสอุปกรณ์ (ID)
            inspector,  # คอลัมน์ 4: ชื่อผู้ตรวจ
            status,  # คอลัมน์ 5: สถานะโดยรวม
            remarks,  # คอลัมน์ 6: หมายเหตุ
            image_link  # คอลัมน์ 7: ลิงก์รูปภาพ
        ]
        log_sheet.append_row(new_log_entry)
        if status == "ไม่ปกติ (ต้องแก้ไข)":
            try:
                    # เปิด Sheet Action_Required
                action_sheet = client.open(sheet_name).worksheet("Action_Required")
                cell = sheet.find(selected_device)
                device_row = sheet.row_values(cell.row)
                device_location = device_row[3] if len(device_row) > 3 else "-"  # ปรับ index ตาม Sheet

                action_entry = [
                    now_str,  # คอลัมน์ 1: วันเวลาที่ตรวจ
                    device_sub_type,  # คอลัมน์ 3: ประเภทอุปกรณ์ (Type) 💡 เพิ่มตัวนี้เข้ามาแล้วครับ
                    selected_device,  # คอลัมน์ 2: รหัสอุปกรณ์ (ID)
                    inspector,  # คอลัมน์ 4: ชื่อผู้ตรวจ
                    status,  # คอลัมน์ 5: สถานะโดยรวม
                    remarks,  # คอลัมน์ 6: หมายเหตุ
                    image_link  # คอลัมน์ 7: ลิงก์รูปภาพ
                ]
                action_sheet.append_row(action_entry)
                st.success("✅ บันทึกข้อมูลเรียบร้อย")
                st.warning(f"⚠️ รายการ {selected_device} ถูกส่งไปยัง 'Action_Required' เพื่อติดตามการแก้ไข")
            except Exception as e:
                    st.warning(f"⚠️ บันทึกลง Inspection_Logs แล้ว แต่ไม่สามารถส่งไป Action_Required: {e}")
        else:
                st.success("✅ บันทึกข้อมูลเรียบร้อย")
            # 3. อัปเดตตารางหลัก (Master List)
                cell = sheet.find(selected_device)
                sheet.update_cell(cell.row, 4, now_str)  # อัปเดตวันที่
                sheet.update_cell(cell.row, 5, status)  # อัปเดตสถานะ
                st.sidebar.success(f"✅ บันทึกข้อมูลและรูปภาพถัง {selected_device} เรียบร้อย!")
                st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ เกิดข้อผิดพลาดในการบันทึก: {e}")

#------------------------------------------------------------------------------------------------------------------
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

#--------------------------------------------------------------------------------------------------------------------
#โฟลวหน้าล็อคอิน

wb = client.open_by_key(st.secrets["sheet_id"])
sheet_emp  = wb.worksheet("employee_list")   # คอลัมน์ A: รหัสพนักงาน
sheet_log  = wb.worksheet("login_log")       # คอลัมน์ A: รหัส, B: วันที่ (YYYY-MM-DD)

# ─── 2. โหลดข้อมูลจาก Sheets (cache ลดโควต้า) ────────────────────
@st.cache_data(ttl=600)
def load_employees():
    return set(sheet_emp.col_values(1))

@st.cache_data(ttl=600)
def load_login_log():
    return sheet_log.get_all_records()  # [{'employee_id':..., 'date':...}, ...]

def append_login_log(emp_id, date_str):
    sheet_log.append_row([emp_id, date_str])

# ─── 3. ฟังก์ชันตรวจล็อกอิน ────────────────────────────────────────
def check_auth():
    from datetime import datetime, date
    today = date.today().isoformat()

    # กรณี session_state ยังเก็บสถานะล็อกอินวันนี้ไว้
    if st.session_state.get("authenticated") and st.session_state.get("last_login") == today:
        return True

    # โหลด log มาเช็คว่ารหัสนี้เคยล็อกอินวันนี้หรือยัง
    for entry in load_login_log():
        if (entry["employee_ID"] == st.session_state.get("emp_id")
                and entry["date"] == today):
            st.session_state["authenticated"] = True
            st.session_state["last_login"]    = today
            return True

    # ยังไม่เคยล็อกอินวันนี้ → แสดงฟอร์มกรอกรหัส
    emp_input = st.text_input("กรอกรหัสพนักงาน", key="emp_input")
    if st.button("ล็อกอิน"):
        if emp_input in load_employees():
            append_login_log(emp_input, today)
            st.session_state["emp_id"]         = emp_input
            st.session_state["authenticated"]  = True
            st.session_state["last_login"]     = today
            st.experimental_rerun()  # รีโหลดหน้าใหม่ ให้กระโดดไปส่วนฟอร์มถัง
        else:
            st.error("รหัสพนักงานไม่ถูกต้อง")
    return False

# ─── 4. เรียกตรวจล็อกอินก่อนเข้าใช้งาน ────────────────────────────
if not check_auth():
    st.stop()  # หยุดแอปไว้ที่หน้าล็อกอิน

# ถ้า authenticated แล้ว จึงมาฝั่งฟอร์มตรวจเช็คถัง
st.header("ฟอร์มตรวจเช็คถังดับเพลิง")
# … วาง st.text_input, st.selectbox ฯลฯ ต่อได้เลย …


