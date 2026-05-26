import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import pytz
from datetime import datetime, timedelta
import streamlit as st
import time
import uuid
import extra_streamlit_components as stx
from streamlit_extras.stylable_container import stylable_container


def colored_button(label, color, text_color="white", key=None):
    """
    ฟังก์ชันสร้างปุ่มเปลี่ยนสีแยกรายปุ่ม (เวอร์ชันทางการ)
    """
    btn_key = key if key else f"btn_{label.replace(' ', '_').lower()}"

    with stylable_container(
            key=f"container_{btn_key}",
            css_styles=f"""
            button {{
                background-color: {color} !important;
                color: {text_color} !important;
                border: 1px solid {color} !important;
                border-radius: 8px !important;
                font-weight: bold !important;
            }}
            button * {{
                color: {text_color} !important;
            }}
            button:hover {{
                opacity: 0.85 !important;
                border-color: {color} !important;
            }}
        """,
    ):

        return st.button(label, key=btn_key)
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
#==================================================================================================================
# โซนปรับแต่งสีจ้า (Sidebar)
st.markdown("""
    <style>
    [data-testid="stSidebar"] > div:first-child {
        background-color: #14264d !important; 
    }

    /* บังคับสีขาวเฉพาะ หัวข้อ (h1-h6) และ ป้ายข้อความกำกับ (Labels) เท่านั้น */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4, 
    [data-testid="stSidebar"] h5, [data-testid="stSidebar"] h6,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
        color: #ffffff !important;
    }

    /* ==========================================================
       2. SELECTBOX (เมื่อไม่มีข้อ 1 มาขัดขา สีน้ำเงินเข้มจะทำงานได้ 100%)
       ========================================================== */
    /* ตัวกล่อง Selectbox */
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #f3f6fb !important; /* พื้นหลังกล่อง */
        border: 1px solid #cbd8f2 !important; /* เส้นขอบกล่อง */
    }

    /* บังคับสีตัวอักษรข้างในกล่องหลักเป็นสีน้ำเงินเข้ม */
    [data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #111844 !important;
        -webkit-text-fill-color: #111844 !important;
    }

    /* เปลี่ยนสีไอคอนลูกศรชี้ลง */
    [data-testid="stSidebar"] div[data-baseweb="select"] svg {
        fill: #111844 !important;
    }

    /* ==========================================================
       3. DROPDOWN MENU (หน้าต่างรายการตัวเลือกที่เด้งกางออกมา)
       ========================================================== */
    /* หน้าต่างป๊อปอัปและตัวเลือกแถว */
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] li * {
        background-color: #f3f6fb !important; 
        color: #111844 !important;            
    }

/* ==========================================================
       4. TEXT INPUT / TEXT AREA (ช่องพิมพ์ข้อความใน Sidebar)
       ========================================================== */
    /* ดักจับช่อง st.text_input */
    [data-testid="stSidebar"] [data-testid="stTextInput"] div[data-baseweb="input"] input {
        background-color: #f3f6fb !important; /* สีฟ้าอ่อน */
        color: #111844 !important;            
        -webkit-text-fill-color: #111844 !important; 
    }
    /* ดักจับช่อง st.text_area (จุดที่แก้ไข: เปลี่ยนจากสีครีมเป็นสีฟ้าอ่อน #f3f6fb) */
    [data-testid="stSidebar"] [data-testid="stTextArea"] div[data-baseweb="textarea"] textarea {
        background-color: #f3f6fb !important; /* ปรับเป็นสีฟ้าอ่อนตามที่คุณต้องการ */
        color: #111844 !important;            
        -webkit-text-fill-color: #111844 !important; 
    }
    /* คุมเส้นขอบรอบกล่องพิมพ์ข้อความ (สภาวะปกติ) */
    [data-testid="stSidebar"] [data-testid="stTextInput"] div[data-baseweb="input"],
    [data-testid="stSidebar"] [data-testid="stTextArea"] div[data-baseweb="textarea"] {
        border: 1px solid #cbd8f2 !important; 
        background-color: transparent !important;
    }
    /* สีเส้นขอบตอนกำลังคลิกพิมพ์ (Focus) */
    [data-testid="stSidebar"] [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
    [data-testid="stSidebar"] [data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within {
        border-color: #5b7db1 !important;
        box-shadow: 0 0 0 1px #5b7db1 !important;
    }

    /* ==========================================================
       5. FILE UPLOADER (กล่องอัปโหลดไฟล์)
       ========================================================== */
    /* ตัวกล่องอัปโหลดภาพรวม */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background-color: #f3f6fb !important;
        border: 1px dashed #5b7db1 !important; 
    }
    
    /* สยบทุกตัวอักษรที่เป็นคำอธิบายในกล่องอัปโหลด (รวมถึง 200MB per file...) */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section div,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section div *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color: #111844 !important;
        -webkit-text-fill-color: #111844 !important;
        opacity: 1 !important; /* ป้องกันระบบทำโปร่งใส/ตัวเทา */
    }

    /* ตัวปุ่ม Upload ด้านใน (แยกสไตล์ออกเพื่อให้ปุ่มยังคงเด่น) */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"] {
        background-color: #5b7db1 !important; 
        border: none !important;
    }
    /* ตัวอักษรบนปุ่ม Upload */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"] p,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"] * {
        color: #ffffff !important;                
        -webkit-text-fill-color: #ffffff !important;
    }
    /* เอฟเฟกต์ตอนเอาเมาส์ไปชี้ปุ่ม (Hover) */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #466699 !important; 
    }
    
    /* ==========================================================
       6. MODERN RADIO BUTTONS (ล็อกให้ใหญ่เฉพาะใน Sidebar)
       ========================================================== */
    /* จัดเลย์เอาต์ของกลุ่มตัวเลือกใน Sidebar */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        gap: 16px !important; 
        padding-top: 12px !important;
    }

    /* สไตล์ของแต่ละกล่องใน Sidebar (สถานะปกติ / ยังไม่ถูกเลือก) */
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {
        background-color: rgba(243, 246, 251, 0.08) !important; 
        border: 1px solid rgba(203, 216, 242, 0.2) !important;  
        padding: 20px 24px !important;  /* เพิ่มความกว้างและความสูงเฉพาะใน Sidebar */
        border-radius: 12px !important; 
        width: 100% !important;         
        min-height: 64px !important;    /* บังคับความสูงกล่องใหญ่ใน Sidebar */
        transition: all 0.25s ease !important;                  
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important; 
    }

    /* ซ่อนวงกลมดั้งเดิมใน Sidebar */
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }

    /* ตัวหนังสือในกล่อง Sidebar (สถานะปกติ) */
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] div,
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-size: 16px !important; /* ขนาดกล่องเมนูหลักด้านบน */
        font-weight: 500 !important;
    }

    /* เอฟเฟกต์ตอนเมาส์ชี้ใน Sidebar */
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background-color: rgba(243, 246, 251, 0.15) !important;
        border-color: #5b7db1 !important;
        transform: translateY(-2px) !important; 
    }

    /* เอฟเฟกต์เมื่อกล่องใน Sidebar "ถูกเลือก" */
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background-color: #f3f6fb !important; 
        border: 1px solid #5b7db1 !important;
        box-shadow: 0 6px 16px rgba(17, 24, 68, 0.2) !important; 
    }

    /* ตัวหนังสือในกล่อง Sidebar (สถานะเลือกแล้ว) */
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div,
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span {
        color: #111844 !important;
        -webkit-text-fill-color: #111844 !important;
        font-weight: 600 !important;
    }


    /* ==========================================================
       7. MAIN CONTENT RADIO BUTTONS (เวอร์ชันสมดุล มินิมอล สวยงาม)
       ========================================================== */
    /* คุมพฤติกรรมกลุ่มปุ่มวิทยุหน้าหลัก */
    [data-testid="stMain"] [data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important; 
        gap: 10px !important;              /* ระยะห่างที่กำลังพอดีระหว่างกล่อง ใช่ และ ไม่ใช่ */
        padding-top: 8px !important;
        
        width: 100% !important;
        max-width: 280px !important;       /* 👈 ปรับความกว้างให้มินิมอลพอดีคำ (จากเดิม 400px) */
        margin: 0 !important;              /* จัดชิดซ้ายตามแนวหัวข้อคำถามเพื่อให้อ่านง่าย */
    }

    /* ปรับขนาดกล่อง ใช่ / ไม่ใช่ ทุกข้อให้เท่ากันและสมดุล */
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] {
        background-color: rgba(243, 246, 251, 0.06) !important; /* ปรับพื้นหลังจางลงเล็กน้อยให้ดูคลีน */
        border: 1px solid rgba(203, 216, 242, 0.15) !important;
        border-radius: 10px !important;    /* ปรับความมนให้เข้ากับขนาดกล่องที่เล็กลง */
        
        width: 100% !important;            /* กางเท่ากันทุกกล่องที่ความกว้าง 280px */
        min-height: 42px !important;       /* 👈 ลดความสูงกล่องลงมาให้เรียวสวยงาม ไม่หนาเทอะทะ */
        padding: 0 !important;             /* ล้างค่าพื้นที่ในเพื่อคุมความสูงด้วย min-height ได้นิ่งๆ */
        
        display: flex !important;
        align-items: center !important;
        justify-content: center !important; /* ตัวหนังสืออยู่กึ่งกลางกล่องเป๊ะ */
        transition: all 0.2s ease !important;
        cursor: pointer !important;
        margin: 0 !important;              
    }

    /* ซ่อนวงกลมดั้งเดิม */
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }

    /* ปรับแต่งตัวอักษร ใช่ / ไม่ใช่ ข้างในกล่อง */
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] div,
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] p,
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] span {
        color: rgba(255, 255, 255, 0.85) !important; /* สีขาวนวลสบายตาในสถานะปกติ */
        -webkit-text-fill-color: rgba(255, 255, 255, 0.85) !important;
        font-size: 14px !important;        /* ขนาดตัวอักษรพอดีกับขนาดกล่องใหม่ */
        font-weight: 500 !important;
        margin: 0 !important;
    }

    /* เอฟเฟกต์เมื่อเมาส์ชี้ */
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background-color: rgba(243, 246, 251, 0.12) !important;
        border-color: #5b7db1 !important;
    }

    /* เอฟเฟกต์เมื่อกล่อง "ถูกเลือก" */
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background-color: #f3f6fb !important; /* ไฮไลต์ฟ้าอ่อนสว่าง */
        border: 1px solid #5b7db1 !important;
        box-shadow: 0 4px 10px rgba(17, 24, 68, 0.08) !important;
    }

    /* สีฟอนต์เมื่อกล่อง "ถูกเลือก" */
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div,
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    [data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span {
        color: #111844 !important;            /* ตัวอักษรน้ำเงินเข้มคมชัด */
        -webkit-text-fill-color: #111844 !important;
        font-weight: 600 !important;
    }
""", unsafe_allow_html=True)

#ส่วนที่ 1 ของล็อคอิน======================================================================================================

COOKIE_NAME = "emp_auth_token"
SESSION_EXPIRY_DAYS = 1



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

if "logged_out" not in st.session_state:
    st.session_state["logged_out"] = False

# ตรวจสอบ Auto-login หลังจากที่ Cookie พร้อมใช้งานแล้ว
if st.session_state.get("cookie_ready", False):
    if not st.session_state.get("authenticated", False) and not st.session_state.get("logged_out", False):
        saved_token = get_cookie_safe(COOKIE_NAME)
        if saved_token and saved_token != "None":
            emp_id = verify_token_in_sheet(saved_token)
            if emp_id:
                st.session_state["authenticated"] = True
                st.session_state["emp_id"] = emp_id

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

st.markdown("""
<div style="
    display: flex;
    align-items: center;
    gap: 8px;
    color: #ffffff;
    font-size: 40px;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 10px;
    letter-spacing: 0.3px;
">
    <span>SafePig Safety Inspection System</span>
    <span style="font-size: 32px;">🧯</span>
</div>
""", unsafe_allow_html=True)
# ดึงชื่อแสดงผลแบบปลอดภัย
current_user = st.session_state.get("emp_id")

if "emp_name" not in st.session_state or not st.session_state["emp_name"]:
    if current_user and current_user != "None":
        st.session_state["emp_name"] = get_employee_name_by_id(current_user)
    else:
        st.session_state["emp_name"] = "ผู้ใช้"

# แสดงข้อมูลผู้ใช้

# [เขียนส่วนที่เหลือของกระบวนการควบคุม การดำเนินเรื่องตรวจเช็คถังดับเพลิงและระบบหน้าของคุณด้านล่างนี้ได้เลย]


# ปุ่มควบคุมการออกจากระบบ (Logout Service)
st.markdown("---")
with st.container(border=True):
    col_info, col_profile = st.columns([3, 1])

    with col_info:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fff6dd, #f7e8bc);
            padding: 22px;
            border-radius: 16px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.12);
            border: 1px solid rgba(255,255,255,0.4);
            color: #1f2a44;
            min-height: 180px;
        ">
            <div style="font-size: 24px; font-weight: 700; margin-bottom: 16px; color: #0b3d91;">
                📰 User Profile
            </div>
            <div style="font-size: 20px; line-height: 1.8;">
                <p style="margin: 0;"><strong>ชื่อ:</strong> {st.session_state.get('emp_name', 'ไม่ระบุ')}</p>
                <p style="margin: 0;"><strong>รหัส:</strong> {current_user}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)


        selected_tank = st.session_state.get("selected_tank") or st.query_params.get("tank_id")

    with col_profile:
        # 1. เพิ่มขนาดรูปภาพ (จากเดิม 90 เป็น 120-130 หรือปรับตามชอบ)
        user_image = "FirePig.png"
        st.image(user_image, width=130)

        # 2. ลดขนาดปุ่ม โดยเอา use_container_width=True ออก
        # และเปลี่ยน type="primary" หรือคง secondary ไว้ตามต้องการเพื่อความสวยงาม
        if st.button("🚪 ออกจากระบบ", type="secondary"):
            with st.spinner("กำลังออกจากระบบ..."):
                current_token = get_cookie_safe(COOKIE_NAME)
                if current_token:
                    revoke_token_in_sheet(current_token)

                remove_cookie_safe(COOKIE_NAME)

                for key in list(st.session_state.keys()):
                    if key not in ["cookie_ready", "logged_out"]:
                        del st.session_state[key]

                st.session_state["authenticated"] = False
                st.session_state["logged_out"] = True

                time.sleep(1)
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
    df = df.reset_index(drop=True)
    df.insert(0, "No.", df.index + 1)
    return df

# --- 2. ดึงข้อมูลจาก Google Sheets --------------------------------------------------------------------------------------
sheet_name = "FireExtinguisher_MasterList_2026"
spreadsheet = client.open(sheet_name)
# บรรทัดนี้คือการเปิดแท็บหลัก
sheet = spreadsheet.worksheet("FireExtinguisher_Data")
log_sheet = spreadsheet.worksheet("Inspection_Log")

# --- 3. หน้าตาแอป (UI) และ Tabs ---

st.markdown("""
    <style>
        /* 1. เปลี่ยนสีตัวอักษรแท็บปกติที่ยังไม่ได้กด */
        button[data-baseweb="tab"] p {
            color: #ffffff !important;
            font-weight: 500;
        }
        /* 2. เปลี่ยนสีตัวอักษรแท็บตอนที่เราคลิกเลือกอยู่ (Active Tab) */
        button[aria-selected="true"] p {
            color: #ebeff5 !important;
            font-weight: bold;
        }
        
        /* 3. ปรับสีของเส้นขีดล่าง (เส้นใต้แท็บ) เวลาที่เลือก ให้เป็นสีส้มทอง */
        div[data-testid="stTabs"] [data-baseweb="tab-highlight-bar"] {
            background-color: #FFC570 !important;
            height: 4px !important; /* เพิ่มความหนาของเส้นไฮไลท์ให้ดูโมเดิร์นสปอร์ตขึ้น */
        }
    </style>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📅 รายการตรวจวันนี้", "📋 FireExtinguisher_Data", "🚨 Emergency_Safety_Equipment", "🔧 ติดตามการแก้ไข"])
#ดึงข้อมูลจากชีตมาโชว์
with tab1:
    df = load_sheet_data("Inspection_Log")
    st.markdown("<h3 style='color: #ffffff; font-weight: bold;'>รายการที่ตรวจเช็คแล้ววันนี้</h3>", unsafe_allow_html=True)

    if not df.empty:
        date_col = "Timestamp" if "Timestamp" in df.columns else df.columns[0]
        df_temp = df.copy()

        # 1. แปลงคอลัมน์ Timestamp ให้กลายเป็นวันที่ (ตัดเวลาออก)
        df_temp['parsed_date'] = pd.to_datetime(df_temp[date_col], errors='coerce', dayfirst=True).dt.date

        # ดึงวันที่ปัจจุบันของวันนี้จริงๆ มาเก็บไว้
        thai_tz = pytz.timezone("Asia/Bangkok")
        today_date = datetime.now(thai_tz).date()

        # 💡 ปรับปรุงจุดนี้: เปลี่ยนมากรองข้อมูลเจาะจงเฉพาะ "วันนี้จริงๆ (today_date)" เท่านั้น
        df_today = df_temp[df_temp['parsed_date'] == today_date].copy()

        # ตรวจสอบว่า "วันนี้" มีคนคีย์ข้อมูลเข้ามาหรือยัง
        if not df_today.empty:
            df_today = df_today.drop(columns=['parsed_date'])  # ลบคอลัมน์คำนวณออก

            # 4. จัดการเลขลำดับใหม่เพื่อแสดงผล
            df_display = df_today.reset_index(drop=True)
            df_display.index = df_display.index + 1

            # ถ้าในตารางเดิมมีคอลัมน์ "No." อยู่แล้ว ให้ลบอันเก่าออกแล้วรันใหม่
            if "No." in df_display.columns:
                df_display = df_display.drop(columns=["No."])

            df_display.insert(0, "No.", df_display.index)

            st.success(f"📊 แสดงข้อมูลการตรวจเช็คประจำวันนี้: {today_date}")
            st.dataframe(
                df_display.style.set_properties(**{
                    'background-color': '#cbd8f2',  # บังคับพื้นหลังในตารางให้เป็นสีน้ำเงินเข้มตามธีม
                    'color': '#111844',  # บังคับตัวหนังสือด้านในให้เป็นสีขาวนวล (อ่านง่าย ชัดเจน 100%)
                    'border-color': '#FFFFFF' #เส้นตัดขอบในตารางจางๆ
                }),
                use_container_width=True,
                hide_index=True
            )


        else:
            # 💡 ถ้าเปลี่ยนเป็นวันใหม่แล้วยังไม่มีข้อมูล จะล้างตารางและสลับมาแสดงกล่องสีฟ้านี้ทันที
            st.info(f"📅 วันที่ {today_date} ยังไม่มีข้อมูลการตรวจบันทึกในระบบ")

    else:
        st.info("ยังไม่มีข้อมูลการตรวจบันทึกในแท็บ Log")


with tab2:
    df = load_sheet_data("FireExtinguisher_Data")
    st.markdown("<h3 style='color: #ffffff; font-weight: bold;'>📋 FireExtinguisher_Data</h3>",
                unsafe_allow_html=True)
    try:
        df_tab2 = load_sheet_data("FireExtinguisher_Data")

        if df_tab2.empty:
            st.warning("⚠️ ไม่พบข้อมูล")
        else:
            # ลบคอลัมน์ No. ถ้ามี
            if "No." in df_tab2.columns:
                df_tab2 = df_tab2.drop(columns=["No."])

            # ให้ index เริ่มที่ 1
            df_tab2 = df_tab2.reset_index(drop=True)
            df_tab2.index = df_tab2.index + 1

            df_tab2.insert(0, "No.", df_tab2.index)

            st.dataframe(
                df_tab2.style.set_properties(**{
                    'background-color': '#cbd8f2',  # บังคับพื้นหลังในตารางให้เป็นสีน้ำเงินเข้มตามธีม
                    'color': '#111844',  # บังคับตัวหนังสือด้านในให้เป็นสีขาวนวล (อ่านง่าย ชัดเจน 100%)
                    'border-color': '#FFFFFF' #  # เส้นตัดขอบในตารางจางๆ
                }),
                use_container_width=True,
                hide_index=True
            )

            # แสดงผลลัพธ์ (แนะนำให้ใส่ hide_index=True เพื่อไม่ให้มี index ซ้ำซ้อนโผล่มาซ้ายสุดอีก)
            #st.dataframe(df_tab2, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"❌ {type(e).__name__}: {e}")


with tab3:
    df = load_sheet_data("Emergency_Safety_Equipment")
    st.markdown("<h3 style='color: #ffffff; font-weight: bold;'>🚨 Emergency_Safety_Equipment</h3>",
                unsafe_allow_html=True)
    try:
        df_tab3 = load_sheet_data("Emergency_Safety_Equipment")

        if df_tab3.empty:
            st.warning("⚠️ ไม่พบข้อมูล")
        else:
            # ลบคอลัมน์ No. ถ้ามี
            if "No." in df_tab3.columns:
                df_tab3 = df_tab3.drop(columns=["No."])

            # ให้ index เริ่มที่ 1
            df_tab3 = df_tab3.reset_index(drop=True)
            df_tab3.index = df_tab3.index + 1

            df_tab3.insert(0, "No.", df_tab3.index)

            # แสดงผลลัพธ์ (แนะนำให้ใส่ hide_index=True เพื่อไม่ให้มี index ซ้ำซ้อนโผล่มาซ้ายสุดอีก)
            st.dataframe(
                df_tab3.style.set_properties(**{
                    'background-color': '#cbd8f2',  # บังคับพื้นหลังในตารางให้เป็นสีน้ำเงินเข้มตามธีม
                    'color': '#111844',  # บังคับตัวหนังสือด้านในให้เป็นสีขาวนวล (อ่านง่าย ชัดเจน 100%)
                    'border-color': '#FFFFFF'  # # เส้นตัดขอบในตารางจางๆ
                }),
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(f"❌ {type(e).__name__}: {e}")

with tab4:
    st.markdown("<h3 style='color: #ffffff; font-weight: bold;'>🔧 ติดตามการแก้ไข</h3>",
                unsafe_allow_html=True)
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
                # --- 1. ส่วนหัวข้อ และ ตัวกรองมุมขวา (ใช้ st.popover เพื่อความสะอาดตา) ---
                col_title, col_filter = st.columns([3, 1])
                with col_filter:
                    # สร้างปุ่มกดตัวกรองไว้มุมขวาบน
                    with st.popover("🔍 ตัวกรองข้อมูล", use_container_width=True):
                        selected_inspector = st.selectbox("เลือกคนตรวจ",
                                                          ["ทั้งหมด"] + list(df_need_repair['Inspector'].unique()))
                        selected_id = st.selectbox("เลือก ID อุปกรณ์",
                                                   ["ทั้งหมด"] + list(df_need_repair['ID'].unique()))





                # ทำการกรองข้อมูล
                df_filtered = df_need_repair.copy()
                if selected_inspector != "ทั้งหมด":
                    df_filtered = df_filtered[df_filtered['Inspector'] == selected_inspector]
                if selected_id != "ทั้งหมด":
                    df_filtered = df_filtered[df_filtered['ID'] == selected_id]


                # ตาราง
                if not df_need_repair.empty:
                    st.warning(f"พบ {len(df_need_repair)} รายการ")

                    for col in ["No.", "No"]:
                        if col in df_need_repair.columns:
                            df_need_repair = df_need_repair.drop(columns=[col])

                            # ให้ index เริ่มที่ 1
                    df_need_repair = df_need_repair.reset_index(drop=True)
                    df_need_repair.index = df_need_repair.index + 1

                    df_need_repair.insert(0, "No.", df_need_repair.index)

                    # แสดงผลโดยซ่อน index เดิมเพื่อความสวยงาม
                    st.dataframe(
                        df_need_repair.style.set_properties(**{
                            'background-color': '#cbd8f2',  # บังคับพื้นหลังในตารางให้เป็นสีน้ำเงินเข้มตามธีม
                            'color': '#111844',  # บังคับตัวหนังสือด้านในให้เป็นสีขาวนวล (อ่านง่าย ชัดเจน 100%)
                            'border-color': '#FFFFFF'  # # เส้นตัดขอบในตารางจางๆ
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.success("🎉 ไม่มีรายการที่ต้องแก้ไข")

    except Exception as e:
        st.error(f"❌ Error: {e}")

if colored_button("🔄 อัปเดตข้อมูลล่าสุด", color="#ffe683", text_color="#111844"):
    st.rerun()




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
with st.sidebar:
    st.header("📌 ระบบบันทึกข้อมูล")

    # 1. ปุ่มเปลี่ยนหน้าฟอร์ม (อยู่ใน Sidebar)
    menu_page = st.radio(
        "เลือกประเภทฟอร์ม:",
        ["📝 ฟอร์มบันทึกการตรวจ", "🛠️ ฟอร์มแจ้งการแก้ไข"]
    )
    st.divider()
    # ดึงค่าจาก URL สำหรับระบบ QR Code
    query_params = st.query_params
    url_type = query_params.get("type", "ถังดับเพลิง")
    target_id = query_params.get("tank_id")

    # โฟลวที่ 1: แบบฟอร์มบันทึกการตรวจ (แสดงใน Sidebar เมื่อเลือกเมนูแรก)
    if menu_page == "📝 ฟอร์มบันทึกการตรวจ":
        st.subheader("📋 ฟอร์มบันทึกการตรวจ")

        device_type = st.selectbox(
            "เลือกประเภทอุปกรณ์ที่ต้องการตรวจ",
            ["ถังดับเพลิง", "Emergency Equipment"],
            index=0 if url_type == "ถังดับเพลิง" else 1,
            key="selectbox_device_type_main"
        )

        sheet_name_var = "FireExtinguisher_MasterList_2026"
        @st.cache_data(ttl=600)
        def get_device_options(sheet_name):
            try:
                target_sheet = client.open(sheet_name_var).worksheet(sheet_name)
                rows = target_sheet.get_all_values()
                return [row[1] for row in rows[1:]]
            except:
                return []
        default_index = 0
        is_locked_by_qr = False

        if device_type == "ถังดับเพลิง":
            options = get_device_options("FireExtinguisher_Data")
            id_label = "เลือก/สแกนรหัสถังดับเพลิง"

            if target_id and target_id in options:
                default_index = options.index(target_id)
                is_locked_by_qr = True
                st.success(f"🔒 **ล็อกจาก QR Code**: {target_id}")
            else:
                if target_id:
                    st.error(f"⚠️ รหัสถัง '{target_id}' ไม่ถูกต้อง")
                st.warning("⚠️ **กรุณาสแกน QR Code** ก่อนเริ่มตรวจ")

            if is_locked_by_qr:
                if st.button("🔓 ปลดล็อกและสแกนใหม่"):
                    st.query_params.clear()
                    st.rerun()
        else:
            options = get_device_options("Emergency_Safety_Equipment")
            id_label = "เลือกโซน/รหัส Fire Alarm"

        selected_device = st.selectbox(
            id_label,
            options,
            index=default_index,
            disabled=is_locked_by_qr,
            key=f"select_{device_type}"
        )

        if device_type == "ถังดับเพลิง":
            sheet = client.open(sheet_name).worksheet("FireExtinguisher_Data")
        else:
            sheet = client.open(sheet_name).worksheet("Emergency_Safety_Equipment")

        if selected_device:
            cell_info = sheet.find(selected_device)
            if cell_info is not None:
                device_sub_type = sheet.cell(cell_info.row, 3).value
            else:
                device_sub_type = None
                st.warning(f"⚠️ ไม่พบรหัส {selected_device} ใน Master List")
        else:
            device_sub_type = None
            # --- ตัวฟอร์มตรวจเช็ค (อยู่ใน Sidebar) ---
        with st.form("check_form", clear_on_submit=True):
            default_name = st.session_state.get("emp_name", "")
            inspector = st.text_input("ชื่อผู้ตรวจ", value=default_name, key="inspector_input")

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
                # --- 1. เคส: Emergency Light (ไฟฉุกเฉิน) ---
                if device_sub_type == "Emergency Light":
                    q1 = st.radio("1. ตัวถังเครื่องและดวงโคมสภาพสมบูรณ์ ไม่แตกหัก ไม่มีฝุ่นเกาะ", ["ใช่", "ไม่ใช่"],
                                  key="chk_em_light_1")
                    q2 = st.radio("2. สายไฟและปลั๊กเสียบอยู่ในสภาพดี ไม่หลุดลุ่ยหรือชำรุด", ["ใช่", "ไม่ใช่"],
                                  key="chk_em_light_3")
                    q3 = st.radio("3. ไม่มีสิ่งกีดขวางบดบังตัวโคมไฟฉุกเฉิน", ["ใช่", "ไม่ใช่"], key="chk_em_light_4")
                # --- 2. เคส: Fire Alarm (ระบบแจ้งเหตุเพลิงไหม้) ---
                elif device_sub_type == "Fire alarm":
                    q1 = st.radio(
                        "1. อุปกรณ์แจ้งเหตุด้วยมือ (Manual Station) สภาพสมบูรณ์ หน้ากระจกไม่แตก/ฝาไม่เปิดค้าง",
                        ["ใช่", "ไม่ใช่"], key="chk_fire_alarm_1")
                    q2 = st.radio("2. ไม่มีสิ่งกีดขวางทางเข้าถึงปุ่มกดแจ้งเหตุ หรือบดบังตัวอุปกรณ์", ["ใช่", "ไม่ใช่"],
                                  key="chk_fire_alarm_2")
                    # --- 3. เคส: Emergency Exit (ทางออกฉุกเฉิน / ประตูหนีไฟ) ---
                elif device_sub_type == "Emergency Exit":
                    q1 = st.radio("1. ป้ายบอกทางหนีไฟ (Exit Sign) ติดสว่างชัดเจน ไม่ดับหรือกะพริบ", ["ใช่", "ไม่ใช่"],
                                  key="chk_exit_1")
                    q2 = st.radio("2. บริเวณเส้นทางหนีไฟและหน้าประตู ไม่มีสิ่งของวางกีดขวางแม้แต่ชิ้นเดียว",
                                  ["ใช่", "ไม่ใช่"], key="chk_exit_2")
                    q3 = st.radio("3. ประตูหนีไฟปิดสนิท สภาพสมบูรณ์ ลูกบิด/คานผลัก (Panic Bar) ไม่ชำรุด",
                                  ["ใช่", "ไม่ใช่"], key="chk_exit_3")
                    q4 = st.radio("4. ประตูหนีไฟสามารถผลักเปิดออกได้ง่าย ไม่ถูกล็อกแม่กุญแจจากภายนอก",
                                  ["ใช่", "ไม่ใช่"], key="chk_exit_4")

            # --- ส่วนแนบรูป (บังคับให้แนบเพื่อยืนยันว่าไปจริง) ---------------------------------------------------------------------------
            img_files = st.file_uploader("📸 แนบรูปถ่ายขณะตรวจเช็ค", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
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
                if img_files:  # เปลี่ยนตามชื่อตัวแปรของ st.file_uploader ตัวใหม่
                    image_urls = []

                # วนลูปส่งรูปขึ้น Cloudinary ทีละรูปจนครบ
                    for file in img_files:
                        result = cloudinary.uploader.upload(file)  # ✅ Cloudinary อัปโหลดทีละไฟล์
                        image_urls.append(result["secure_url"])  # เก็บลิงก์ที่ได้ลงลิสต์

                # รวมทุกลิงก์เป็นข้อความเดียว คั่นด้วยคอมม่า (,) เพื่อส่งต่อลงช่องเดิมใน Sheets
                    image_link = ", ".join(image_urls)
                else:
                    image_link = ""

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
                        sheet.update_cell(cell.row, 6, status)

                    # อัปเดตช่อง Last Inspected -> ให้ลงคอลัมน์ F (คอลัมน์ที่ 6)
                        sheet.update_cell(cell.row, 7, now_str)

                    # อัปเดตช่อง ผู้ตรวจ -> ให้ลงคอลัมน์ G (คอลัมน์ที่ 7)
                        sheet.update_cell(cell.row, 8, inspector)
                        st.sidebar.success(f"✅ บันทึกข้อมูลและรูปภาพถัง {selected_device} เรียบร้อย!")
                        st.query_params.clear()
                        st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ เกิดข้อผิดพลาดในการบันทึก: {e}")
    #โฟลวที่ 2 แบบฟอร์มแจ้งการแก้ไข
    elif menu_page == "🛠️ ฟอร์มแจ้งการแก้ไข":
        st.subheader("🛠️ ฟอร์มแจ้งการแก้ไข")

        try:
            repair_log_sheet = client.open(sheet_name).worksheet("Inspection_Log")
            repair_data = repair_log_sheet.get_all_values()

            if len(repair_data) > 1:
                df_repair = pd.DataFrame(repair_data[1:], columns=repair_data[0])
                df_repair['sheet_row_index'] = df_repair.index + 2

                # กรองเฉพาะเคสค้างซ่อม
                df_need_action = df_repair[df_repair['Status'].str.strip() == 'ไม่ปกติ (ต้องแก้ไข)']

                if not df_need_action.empty:
                    df_need_action['picker_label'] = df_need_action['ID'] + " (" + df_need_action['Timestamp'].str[
                        5:16] + ")"

                    # --- ตัวฟอร์มแจ้งซ่อม (อยู่ใน Sidebar) ---
                    with st.form("repair_form"):
                        selected_repair_item = st.selectbox(
                            "เลือกอุปกรณ์ที่แก้ไขแล้ว:",
                            df_need_action['picker_label'].tolist()
                        )

                        repair_details = st.text_area(
                            "รายละเอียดการแก้ไข:",
                            placeholder="เช่น เปลี่ยนถังใหม่ / เติมแรงดันแล้ว"
                        )
                        repairman_name = st.text_input("ชื่อผู้แก้ไข:")

                        submit_repair = st.form_submit_button("💾 ยืนยันแก้ไขสำเร็จ", type="primary")

                    if submit_repair:
                        if not repairman_name or not repair_details:
                            st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
                        else:
                            with st.spinner("กำลังอัปเดตระบบ..."):
                                chosen_row = \
                                df_need_action[df_need_action['picker_label'] == selected_repair_item].iloc[0]
                                target_row_num = int(chosen_row['sheet_row_index'])

                                status_col_num = repair_data[0].index('Status') + 1
                                repair_log_sheet.update_cell(target_row_num, status_col_num, "ดำเนินการแก้ไขแล้ว")

                                if 'Note' in repair_data[0]:
                                    note_col_num = repair_data[0].index('Note') + 1
                                    current_date_str = datetime.now().strftime('%Y-%m-%d')
                                    repair_log_text = f"⚙️ ซ่อมโดย {repairman_name}: {repair_details} ({current_date_str})"
                                    repair_log_sheet.update_cell(target_row_num, note_col_num, repair_log_text)

                                st.success("🎉 อัปเดตสถานะสำเร็จแล้ว!")
                                st.rerun()
                else:
                    st.success("🎉 ไม่มีรายการค้างซ่อมในระบบ")
            else:
                st.info("ไม่มีข้อมูลบันทึกในระบบ")

        except Exception as e:
            st.error(f"❌ ระบบฟอร์มซ่อมแซมขัดข้อง: {e}")


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
        "to": target_ids,
        "messages": [{"type": "text", "text": message}]
    }
        # ส่งข้อมูล
    requests.post(url, headers=headers, json=data)

import pandas as pd
if colored_button("📋 ส่งสรุปข้อมูลประจำเดือน", color="#1791e0", text_color="#ffff"):
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


