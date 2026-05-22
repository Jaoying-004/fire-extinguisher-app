import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import pytz
from datetime import datetime, timedelta
from streamlit_cookies_controller import CookieController
import streamlit as st
import time
import uuid
import extra_streamlit_components as stx

# ตั้งค่าเวลาไทยไว้ใช้ทั้งแอป
tz = pytz.timezone('Asia/Bangkok')
def get_now():
    return datetime.now(tz)
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

#ส่วนที่ 1 ของล็อคอิน======================================================================================================

COOKIE_NAME = "emp_auth_token"
SESSION_EXPIRY_DAYS = 1

# ✅ สร้าง Cookie Manager และรอให้พร้อม
@st.cache_resource
def get_cookie_manager():
    """
    สร้าง CookieManager instance แบบ Singleton
    ใช้ cache_resource เพื่อให้ instance เดียวกันตลอด session
    """
    return stx.CookieManager()

# เรียกใช้ครั้งเดียว
cookie_manager = stx.CookieManager()

# ✅ เพิ่มการตรวจสอบว่า Cookie Manager พร้อมใช้งานแล้วหรือยัง
if "cookie_ready" not in st.session_state:
    st.session_state["cookie_ready"] = False

# รอให้ CookieManager พร้อม (สำคัญมาก!)
if not st.session_state["cookie_ready"]:
    try:
        # ลองเรียก get_all() เพื่อ trigger initialization
        _ = cookie_manager.get_all()

        # รอ JavaScript execute เสร็จ
        time.sleep(0.8)

        st.session_state["cookie_ready"] = True

        # ✅ เก็บ query params ไว้ก่อน rerun
        if st.query_params:
            st.session_state["saved_query_params"] = dict(st.query_params)

        st.rerun()
    except Exception as e:
        st.warning(f"⏳ กำลังเตรียม Cookie Manager... ({e})")
        time.sleep(0.5)
        st.rerun()

# ✅ กู้คืน query params หลัง rerun
if "saved_query_params" in st.session_state:
    for key, value in st.session_state["saved_query_params"].items():
        if key not in st.query_params:
            st.query_params[key] = value
    # ลบออกหลังใช้แล้ว
    del st.session_state["saved_query_params"]


def get_cookie_safe(name):
    """อ่าน Cookie อย่างปลอดภัย"""
    if not st.session_state.get("cookie_ready", False):
        return None

    try:
        all_cookies = cookie_manager.get_all()
        if all_cookies and isinstance(all_cookies, dict):
            return all_cookies.get(name)
    except Exception as e:
        # st.warning(f"⚠️ ไม่สามารถอ่าน cookie: {e}")
        pass
    return None


def set_cookie_safe(name, value, expiry_days=1):
    """บันทึก Cookie"""
    if not st.session_state.get("cookie_ready", False):
        st.error("❌ Cookie Manager ยังไม่พร้อม")
        return False

    try:
        cookie_manager.set(
            name,
            value,
            expires_at=datetime.now() + timedelta(days=expiry_days)
        )

        time.sleep(0.5)

        # ตรวจสอบว่าบันทึกสำเร็จ
        saved_value = cookie_manager.get(name)
        if saved_value == value:
            return True
        else:
            st.warning("⚠️ Cookie อาจยังไม่ถูกบันทึก")
            return False

    except Exception as e:
        st.error(f"❌ ไม่สามารถบันทึก Cookie: {e}")
        return False


def remove_cookie_safe(name):
    """ลบ Cookie"""
    if not st.session_state.get("cookie_ready", False):
        return False

    try:
        cookie_manager.delete(name)
        time.sleep(0.3)
        return True
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถลบ cookie: {e}")
    return False

#-----------------------------------------------------------------------------------------------------------------
# ส่วนที่ 2: การเชื่อมต่อแผ่นงานและฐานข้อมูล Google Sheet (Database Connection)
@st.cache_resource
def get_workbook(_client):
    """
    เปิด Google Sheets Workbook และ cache ไว้เพื่อประสิทธิภาพ

    Reference: Streamlit Caching Mechanism
    https://docs.streamlit.io/library/advanced-features/caching
    """
    try:
        return _client.open_by_key(st.secrets["sheet_id"])
    except Exception as e:
        st.error(f"❌ ไม่สามารถเข้าถึง Google Sheet: {e}")
        st.stop()


@st.cache_resource
def get_worksheet(_wb, sheet_name: str):
    """
    เปิด Worksheet ตามชื่อและ cache ไว้

    Args:
        _wb: Workbook object
        sheet_name (str): ชื่อของ worksheet

    Returns:
        gspread.Worksheet: worksheet object
    """
    try:
        return _wb.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ ไม่พบชีตชื่อ '{sheet_name}' ในไฟล์ Google Sheets")
        st.stop()
# เชื่อมต่อกับ Worksheets
try:
    wb = get_workbook(client)
    sheet_emp = get_worksheet(wb, "employee_list")      # คอลัมน์: emp_id | emp_name
    sheet_log = get_worksheet(wb, "login_log")          # คอลัมน์: emp_id | timestamp
    sheet_sessions = get_worksheet(wb, "Auth_Sessions") # คอลัมน์: emp_id | token | expires_at
except Exception as e:
    st.error(f"❌ เกิดข้อผิดพลาดในการโหลดชีต: {e}")
    st.stop()

#ส่วนที่ 3 =========================================================================================================
@st.cache_data(ttl=600)  # Cache 10 นาที
def load_employees():
    """
    โหลดรายชื่อรหัสพนักงานทั้งหมดจาก Google Sheets

    Returns:
        set: เซตของรหัสพนักงานที่ใช้งานได้
    """
    try:
        values = sheet_emp.col_values(1)  # คอลัมน์ A
        # ทำความสะอาดข้อมูล: เอาช่องว่างออกและข้าม header
        cleaned = [str(v).strip() for v in values[1:] if str(v).strip()]
        return set(cleaned)
    except Exception as e:
        st.error(f"❌ ไม่สามารถโหลดข้อมูลพนักงาน: {e}")
        return set()


@st.cache_data(ttl=600)
def get_employee_name_by_id(emp_id):
    """
    ค้นหาชื่อพนักงานจากรหัสพนักงาน

    Args:
        emp_id (str): รหัสพนักงาน

    Returns:
        str: ชื่อพนักงาน หรือ "" ถ้าไม่พบ
    """
    try:
        all_emp_ids = sheet_emp.col_values(1)  # คอลัมน์ A: รหัส
        all_names = sheet_emp.col_values(2)  # คอลัมน์ B: ชื่อ

        # ทำความสะอาดข้อมูล
        cleaned_ids = [str(x).strip() for x in all_emp_ids]
        target_id = str(emp_id).strip()

        if target_id in cleaned_ids:
            index = cleaned_ids.index(target_id)
            if index < len(all_names):
                return all_names[index]
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถดึงชื่อพนักงาน: {e}")

    return ""  # คืนค่าว่างถ้าไม่พบ


def save_session_to_sheet(emp_id, token, expires_at):
    """
    บันทึก Session Token ลง Google Sheets

    Args:
        emp_id (str): รหัสพนักงาน
        token (str): Token ที่สร้างขึ้น (UUID)
        expires_at (str): วันเวลาหมดอายุ (format: YYYY-MM-DD HH:MM:SS)
    """
    try:
        sheet_sessions.append_row([emp_id, token, expires_at])
    except Exception as e:
        st.error(f"❌ ไม่สามารถบันทึก session: {e}")


def verify_token_in_sheet(token):
    """ตรวจสอบความถูกต้องและอายุของ Token"""
    try:
        cell = sheet_sessions.find(token)

        if cell:
            row_data = sheet_sessions.row_values(cell.row)

            if len(row_data) >= 3:
                emp_id = row_data[0]
                expires_str = row_data[2]
                expires_at = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")

                if datetime.now() < expires_at:
                    return emp_id
                else:
                    # Token หมดอายุ - ลบออก
                    sheet_sessions.delete_rows(cell.row)
    except Exception as e:
        st.warning(f"⚠️ เกิดข้อผิดพลาดในการตรวจสอบ token: {e}")

    return None


def revoke_token_in_sheet(token):
    """
    เพิกถอน Token โดยการลบออกจาก Google Sheets

    Args:
        token (str): Token ที่ต้องการเพิกถอน
    """
    try:
        cell = sheet_sessions.find(token)
        if cell:
            sheet_sessions.delete_rows(cell.row)
    except Exception:
        pass  # ไม่แสดง error เพราะอาจเป็นกรณีที่ token ถูกลบไปแล้ว

# ส่วนที่ 4: การจัดกระบวนการทำงานและตรวจสอบสิทธิ์อัตโนมัติ (Execution Flow)

# เริ่มต้น session state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# ตรวจสอบ Auto-login หลังจากที่ Cookie พร้อมใช้งานแล้ว
if st.session_state.get("cookie_ready", False):
    if not st.session_state.get("authenticated", False):

        # อ่าน Cookie
        saved_token = get_cookie_safe(COOKIE_NAME)

        if saved_token and saved_token != "None":
            # ตรวจสอบ Token
            emp_id = verify_token_in_sheet(saved_token)

            if emp_id:
                # ✅ Login สำเร็จ
                st.session_state["authenticated"] = True
                st.session_state["emp_id"] = emp_id
                st.session_state["last_login"] = datetime.now().date().isoformat()

                # แสดงข้อความ
                st.success(f"✅ ยินดีต้อนรับกลับ {get_employee_name_by_id(emp_id)}")

                # ✅ สำคัญ: ไม่ rerun ถ้ามี query params (เพื่อไม่ให้หายไป)
                if not st.query_params:
                    time.sleep(0.5)
                    st.rerun()
            else:
                # Token หมดอายุ
                remove_cookie_safe(COOKIE_NAME)

if not st.session_state.get("authenticated"):
    st.title("🚒 ระบบตรวจเช็คอุปกรณ์ดับเพลิง")
    st.subheader("กรุณาเข้าสู่ระบบ")

    # ✅ แสดง query params ถ้ามี
    tank_id = st.query_params.get("tank_id")
    if tank_id:
        st.info(f"📍 คุณกำลังจะตรวจสอบถัง: **{tank_id}**")
        st.warning("⚠️ กรุณาเข้าสู่ระบบก่อนดำเนินการต่อ")

    # แสดงสถานะ Cookie
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.session_state.get("cookie_ready"):
            st.success("🟢 ระบบพร้อม")
        else:
            st.warning("🟡 กำลังโหลด...")

    emp_input = st.text_input(
        "รหัสพนักงาน",
        key="emp_input",
        placeholder="กรอกรหัสพนักงาน",
        max_chars=20
    ).strip()

    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        login_button = st.button("🔐 เข้าสู่ระบบ", type="primary", use_container_width=True)

    if login_button:
        if not emp_input:
            st.error("❌ กรุณากรอกรหัสพนักงาน")

        elif emp_input in load_employees():
            with st.spinner("กำลังตรวจสอบข้อมูล..."):
                # สร้าง Token
                new_token = str(uuid.uuid4())
                expiry_date = (
                        datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)
                ).strftime("%Y-%m-%d %H:%M:%S")

                # 1. บันทึก Session
                save_session_to_sheet(emp_input, new_token, expiry_date)

                # 2. บันทึก Login Log
                try:
                    sheet_log.append_row([
                        emp_input,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ])
                except Exception:
                    pass

                # 3. บันทึก Cookie
                cookie_saved = set_cookie_safe(
                    COOKIE_NAME,
                    new_token,
                    expiry_days=SESSION_EXPIRY_DAYS
                )

                if cookie_saved:
                    # อัปเดต Session State
                    st.session_state["authenticated"] = True
                    st.session_state["emp_id"] = emp_input
                    st.session_state["last_login"] = datetime.now().date().isoformat()

                    # ✅ เก็บ tank_id ไว้ใน session_state (ถ้ามี)
                    if tank_id:
                        st.session_state["selected_tank"] = tank_id

                    st.success("✅ เข้าสู่ระบบสำเร็จ!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ ไม่สามารถบันทึก Session ได้")
        else:
            st.error("❌ ไม่พบรหัสพนักงานในระบบ")

    with st.expander("ℹ️ ข้อมูลการใช้งาน"):
        st.markdown("""
        **คำแนะนำ:**
        - ใช้รหัสพนักงานที่ได้รับจากแผนก HR
        - ระบบจะจดจำการเข้าสู่ระบบไว้ 1 วัน

        **ความปลอดภัย:**
        - Session หมดอายุอัตโนมัติภายใน 24 ชั่วโมง
        """)

    st.stop()

# ส่วนที่ 5: ฟังก์ชันควบคุมและควบคุมระบบแสดงผล หน้าจอหลัก / หน้าจอล็อกอิน==========================================================

st.title("ยินดีต้อนรับเข้าใช้งานหน้าการตรวจเช็คตรวจสอบระบบ 🚒")
# ดึงชื่อแสดงผลแบบปลอดภัย
current_user = st.session_state.get("emp_id")

if "emp_name" not in st.session_state or not st.session_state["emp_name"]:
    if current_user and current_user != "None":
        st.session_state["emp_name"] = get_employee_name_by_id(current_user)
    else:
        st.session_state["emp_name"] = "ผู้ใช้"

# แสดงข้อมูลผู้ใช้
st.markdown(f"""
<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
    <h3 style='margin: 0;'>👤 ข้อมูลผู้ใช้งาน</h3>
    <p style='margin: 5px 0;'><strong>ชื่อ:</strong> {st.session_state.get('emp_name', 'ไม่ระบุ')}</p>
    <p style='margin: 5px 0;'><strong>รหัส:</strong> {current_user}</p>
    <p style='margin: 5px 0;'><strong>Login:</strong> {st.session_state.get('last_login', '-')}</p>
</div>
""", unsafe_allow_html=True)

selected_tank = st.session_state.get("selected_tank") or st.query_params.get("tank_id")
# [เขียนส่วนที่เหลือของกระบวนการควบคุม การดำเนินเรื่องตรวจเช็คถังดับเพลิงและระบบหน้าของคุณด้านล่างนี้ได้เลย]


# ปุ่มควบคุมการออกจากระบบ (Logout Service)
st.markdown("---")

col1, col2, col3 = st.columns([4, 1, 1])

with col3:
    if st.button("🚪 ออกจากระบบ", type="secondary", use_container_width=True):
        with st.spinner("กำลังออกจากระบบ..."):
            # ลบ Cookie
            remove_cookie_safe(COOKIE_NAME)

            # ลบ Session จาก Sheets
            current_token = get_cookie_safe(COOKIE_NAME)
            if current_token:
                revoke_token_in_sheet(current_token)

            # ล้าง Session State
            for key in list(st.session_state.keys()):
                if key != "cookie_ready":  # เก็บ cookie_ready ไว้
                    del st.session_state[key]

            st.session_state["authenticated"] = False

            st.success("✅ ออกจากระบบสำเร็จ")
            time.sleep(0.8)
            st.rerun()

#จบส่วนล็อคอิน==========================================================================================================

#------------------------------กำหนดลิมิตของข้อมูล-------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_sheet_data(worksheet_name):
    ws = spreadsheet.worksheet(worksheet_name)
    rows = ws.get_all_values()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df.loc[:, df.columns != ""]
    return df

# --- 2. ดึงข้อมูลจาก Google Sheets --------------------------------------------------------------------------------------
sheet_name = "FireExtinguisher_MasterList_2026"
spreadsheet = client.open(sheet_name)
# บรรทัดนี้คือการเปิดแท็บหลัก
sheet = spreadsheet.worksheet("FireExtinguisher_Data")
log_sheet = spreadsheet.worksheet("Inspection_Log")

# --- 3. หน้าตาแอป (UI) และ Tabs ---
st.title("🔥 FireExtinguisher")
tab1, tab2, tab3, tab4 = st.tabs(["📅 รายการตรวจวันนี้", "📋 FireExtinguisher_Data", "🚨 Emergency_Safety_Equipment", "🔧 ติดตามการแก้ไข"])
#ดึงข้อมูลจากชีตมาโชว์
with tab1:
    df = load_sheet_data("Inspection_Log")
    st.subheader("รายการที่ตรวจเช็คแล้ววันนี้")

    if not df.empty:
        today_str = datetime.now().strftime("%Y-%m-%d")
        first_col = df.columns[0]

        df_today = df[df[first_col].astype(str).str.startswith(today_str, na=False)]

        if not df_today.empty:
            st.dataframe(df_today, use_container_width=True)
        else:
            st.info(f"📌 ยังไม่มีข้อมูลการตรวจบันทึกในวันนี้ {today_str}")
    else:
        st.info("ยังไม่มีข้อมูลการตรวจบันทึกในแท็บ Log")


with tab2:
    df = load_sheet_data("FireExtinguisher_Data")
    st.subheader("📋 FireExtinguisher_Data")
    try:
        df_tab2 = load_sheet_data("FireExtinguisher_Data")

        if df_tab2.empty:
            st.warning("⚠️ ไม่พบข้อมูล")
        else:
            st.dataframe(df_tab2, use_container_width=True)

    except Exception as e:
        st.error(f"❌ {type(e).__name__}: {e}")


with tab3:
    df = load_sheet_data("Emergency_Safety_Equipment")
    st.subheader("🚨 Emergency_Safety_Equipment")
    try:
        df_tab3 = load_sheet_data("Emergency_Safety_Equipment")

        if df_tab3.empty:
            st.warning("⚠️ ไม่พบข้อมูล")
        else:
            st.dataframe(df_tab3, use_container_width=True)

    except Exception as e:
        st.error(f"❌ {type(e).__name__}: {e}")

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

# --- 4. ส่วนของแบบฟอร์มการตรวจเช็ค (เพิ่มต่อท้าย) ---------------------------------------------------------------------------
st.sidebar.header("📝 แบบฟอร์มบันทึกการตรวจ")
# ฟอร์มกรอกข้อมูล
# 1. เลือกประเภทอุปกรณ์ (ถังดับเพลิง / Fire Alarm)
# ==========================================
# รองรับการรับค่าประเภทอุปกรณ์จาก URL (ถ้ามี) เช่น ?type=fire_extinguisher&id=0F01
query_params = st.query_params
url_type = query_params.get("type", "ถังดับเพลิง") # ค่าเริ่มต้นถ้าไม่มีคือถังดับเพลิง

device_type = st.sidebar.selectbox(
    "เลือกประเภทอุปกรณ์ที่ต้องการตรวจ",
    ["ถังดับเพลิง", "Emergency Equipment"],
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

#--------------------------------------------------------------------------------------------------------------------
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
    cell_info = sheet.find(selected_device) #5555555555

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
    default_name = st.session_state.get("emp_name", "")
    inspector = st.text_input(
        "ชื่อผู้ตรวจ",
        value=default_name,  # 👈 ดึงข้อมูลชื่อจากชีตเติมให้โดยอัตโนมัติ
        key="inspector_input",  # 👈 ปรับเป็น True หากป้องกันไม่ให้แก้ไขสิทธิ์ชื่อ หรือเว้นไว้เพื่อให้ผู้เขียนแก้ต่อได้
    )

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

    elif device_type == "Emergency Equipment":
        st.info("🚨 ตรวจระบบ: Emergency Equipment")
        st.write(f"🔍 ประเภทอุปกรณ์: **{device_sub_type}**")
        status = st.radio("สถานะโดยรวม", ["ปกติ", "ไม่ปกติ"])

    # --- ส่วนแนบรูป (บังคับให้แนบเพื่อยืนยันว่าไปจริง) ---------------------------------------------------------------------------
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
                if cell is not None:
                    # 💡 ปรับเลขคอลัมน์ใหม่ให้ตรงตามหน้าแผ่นงานจริงเป๊ะๆ ครับ
                    # อัปเดตช่อง Status -> ให้ลงคอลัมน์ E (คอลัมน์ที่ 5)
                    sheet.update_cell(cell.row, 5, status)

                    # อัปเดตช่อง Last Inspected -> ให้ลงคอลัมน์ F (คอลัมน์ที่ 6)
                    sheet.update_cell(cell.row, 6, now_str)

                    # อัปเดตช่อง ผู้ตรวจ -> ให้ลงคอลัมน์ G (คอลัมน์ที่ 7)
                    sheet.update_cell(cell.row, 7, inspector)
                    st.sidebar.success(f"✅ บันทึกข้อมูลและรูปภาพถัง {selected_device} เรียบร้อย!")
                    st.query_params.clear()
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


