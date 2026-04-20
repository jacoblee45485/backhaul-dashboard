import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import re
import requests
import base64
from datetime import datetime

# Plotly 라이브러리 안전하게 불러오기
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ==========================================
# 1. 페이지 설정 및 회사 공식 스타일 적용
# ==========================================
st.set_page_config(
    page_title="GIANT FOODSYSTEM - 백홀 관리 시스템", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (브랜드 아이덴티티: GIANT 레드 강조, UI 최적화)
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-label { font-size: 0.9rem; color: #64748b; font-weight: 600; margin-bottom: 5px; }
    .metric-value { font-size: 1.8rem; font-weight: 900; color: #0f172a; }
    .status-badge {
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        background-color: #dcfce7;
        color: #166534;
        font-weight: bold;
    }
    .debug-box {
        background-color: #fef2f2;
        border: 1px solid #fee2e2;
        padding: 15px;
        border-radius: 10px;
        color: #991b1b;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.85rem;
        margin: 10px 0;
    }
    .sim-warning {
        background-color: #fffbeb;
        border-left: 5px solid #f59e0b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

def render_official_header():
    st.markdown("""
    <div style="background-color: #f8fafc; padding: 30px 20px; border-radius: 15px; border: 2px solid #e2e8f0; margin-bottom: 30px; text-align: center;">
        <h1 style="margin: 0; font-size: 3.5rem; font-weight: 900; letter-spacing: -2px; line-height: 1.1;">
            <span style="color: #E31837;">GIANT</span> <span style="color: #000000; font-size: 1.5rem; vertical-align: middle;">FOODSYSTEM</span>
        </h1>
        <p style="font-size: 1.2rem; font-weight: 700; color: #475569; margin: 10px 0 5px 0;">#1 K-food Distributor in USA</p>
        <p style="font-size: 0.95rem; font-weight: 500; color: #64748b; margin: 0; line-height: 1.4;">
            NJ Headquarters & GA Logistics Hub Optimization
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. USDA MyMarketNews API 실시간 연동 엔진
# ==========================================
def fetch_usda_api_data(manual_id=None):
    """
    USDA MARS API 실시간 호출 로직.
    개발 및 매핑을 위해 Raw JSON 데이터와 성공한 URL을 함께 반환.
    """
    api_key = st.secrets.get("USDA_API_KEY", "J5v4ZF527NWTsrcMJeB7jrXgfgRyPVzd")
    
    # 시스템 로직 검증용 시뮬레이션 데이터 구축
    demo_prices = [
        # --- 닭고기(Poultry) ---
        {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.52},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.15},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.40},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.08},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.58},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.22},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.65},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.30},
        
        {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '가슴살(Breast)', '가격': 2.10},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '가슴살(Breast)', '가격': 1.85},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉장', '부위': '가슴살(Breast)', '가격': 1.95},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉동', '부위': '가슴살(Breast)', '가격': 1.70},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉장', '부위': '가슴살(Breast)', '가격': 2.15},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉동', '부위': '가슴살(Breast)', '가격': 1.90},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '가슴살(Breast)', '가격': 2.25},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '가슴살(Breast)', '가격': 2.00},

        {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '다리살(Thigh)', '가격': 1.35},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '다리살(Thigh)', '가격': 1.10},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉장', '부위': '다리살(Thigh)', '가격': 1.20},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉동', '부위': '다리살(Thigh)', '가격': 0.95},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉장', '부위': '다리살(Thigh)', '가격': 1.40},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉동', '부위': '다리살(Thigh)', '가격': 1.15},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '다리살(Thigh)', '가격': 1.50},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '다리살(Thigh)', '가격': 1.25},

        # --- 새우(Shrimp) ---
        {'품목': '🦐 새우(Shrimp)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '흰다리새우(White)', '가격': 5.50},
        {'품목': '🦐 새우(Shrimp)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '흰다리새우(White)', '가격': 4.80},
        {'품목': '🦐 새우(Shrimp)', '지역': 'TX', '상태': '냉장', '부위': '흰다리새우(White)', '가격': 4.90},
        {'품목': '🦐 새우(Shrimp)', '지역': 'TX', '상태': '냉동', '부위': '흰다리새우(White)', '가격': 4.20},
        {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉장', '부위': '흰다리새우(White)', '가격': 5.10},
        {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉동', '부위': '흰다리새우(White)', '가격': 4.40},
        {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '흰다리새우(White)', '가격': 6.00},
        {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '흰다리새우(White)', '가격': 5.20},

        {'품목': '🦐 새우(Shrimp)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '블랙타이거(Black Tiger)', '가격': 7.50},
        {'품목': '🦐 새우(Shrimp)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 6.80},
        {'품목': '🦐 새우(Shrimp)', '지역': 'TX', '상태': '냉장', '부위': '블랙타이거(Black Tiger)', '가격': 7.00},
        {'품목': '🦐 새우(Shrimp)', '지역': 'TX', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 6.20},
        {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉장', '부위': '블랙타이거(Black Tiger)', '가격': 7.20},
        {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 6.40},
        {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '블랙타이거(Black Tiger)', '가격': 8.20},
        {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 7.50},

        # --- 돼지고기(Pork) 일반 및 프리미엄 무기후지 ---
        {'품목': '🥩 돼지고기(Pork)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 5.80},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 4.90},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'TX', '상태': '냉장', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 5.50},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'TX', '상태': '냉동', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 4.60},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'FL', '상태': '냉장', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 5.90},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'FL', '상태': '냉동', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 5.00},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 6.50},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 5.50},
        
        {'품목': '🥩 돼지고기(Pork)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '일반 삼겹살(Belly)', '가격': 3.50},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '일반 삼겹살(Belly)', '가격': 2.80},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'TX', '상태': '냉장', '부위': '일반 삼겹살(Belly)', '가격': 3.30},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'TX', '상태': '냉동', '부위': '일반 삼겹살(Belly)', '가격': 2.60},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'FL', '상태': '냉장', '부위': '일반 삼겹살(Belly)', '가격': 3.60},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'FL', '상태': '냉동', '부위': '일반 삼겹살(Belly)', '가격': 2.90},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '일반 삼겹살(Belly)', '가격': 3.90},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '일반 삼겹살(Belly)', '가격': 3.20},

        {'품목': '🥩 돼지고기(Pork)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '목살(Collar)', '가격': 2.80},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '목살(Collar)', '가격': 2.20},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'TX', '상태': '냉장', '부위': '목살(Collar)', '가격': 2.60},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'TX', '상태': '냉동', '부위': '목살(Collar)', '가격': 2.00},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'FL', '상태': '냉장', '부위': '목살(Collar)', '가격': 2.90},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'FL', '상태': '냉동', '부위': '목살(Collar)', '가격': 2.30},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '목살(Collar)', '가격': 3.20},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '목살(Collar)', '가격': 2.60},

        # --- 소고기(Beef) ---
        {'품목': '🥩 소고기(Beef)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '브리스킷(Brisket)', '가격': 4.50},
        {'품목': '🥩 소고기(Beef)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '브리스킷(Brisket)', '가격': 3.80},
        {'품목': '🥩 소고기(Beef)', '지역': 'TX', '상태': '냉장', '부위': '브리스킷(Brisket)', '가격': 4.10},
        {'품목': '🥩 소고기(Beef)', '지역': 'TX', '상태': '냉동', '부위': '브리스킷(Brisket)', '가격': 3.40},
        {'품목': '🥩 소고기(Beef)', '지역': 'FL', '상태': '냉장', '부위': '브리스킷(Brisket)', '가격': 4.60},
        {'품목': '🥩 소고기(Beef)', '지역': 'FL', '상태': '냉동', '부위': '브리스킷(Brisket)', '가격': 3.90},
        {'품목': '🥩 소고기(Beef)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '브리스킷(Brisket)', '가격': 4.90},
        {'품목': '🥩 소고기(Beef)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '브리스킷(Brisket)', '가격': 4.20},

        {'품목': '🥩 소고기(Beef)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '립아이(Ribeye)', '가격': 9.20},
        {'품목': '🥩 소고기(Beef)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '립아이(Ribeye)', '가격': 8.50},
        {'품목': '🥩 소고기(Beef)', '지역': 'TX', '상태': '냉장', '부위': '립아이(Ribeye)', '가격': 8.70},
        {'품목': '🥩 소고기(Beef)', '지역': 'TX', '상태': '냉동', '부위': '립아이(Ribeye)', '가격': 8.00},
        {'품목': '🥩 소고기(Beef)', '지역': 'FL', '상태': '냉장', '부위': '립아이(Ribeye)', '가격': 9.40},
        {'품목': '🥩 소고기(Beef)', '지역': 'FL', '상태': '냉동', '부위': '립아이(Ribeye)', '가격': 8.70},
        {'품목': '🥩 소고기(Beef)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '립아이(Ribeye)', '가격': 10.10},
        {'품목': '🥩 소고기(Beef)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '립아이(Ribeye)', '가격': 9.40}
    ]

    if not api_key:
        return pd.DataFrame(demo_prices), "API 키 미설정", {"error": "API 키가 없습니다."}, ""

    target_id = manual_id if manual_id else "3646"
    
    # URL 시도 순서 (데이터 최우선)
    base_urls = [
        f"https://marsapi.ams.usda.gov/services/v1.2/reports/{target_id}/data",
        f"https://marsapi.ams.usda.gov/services/v1.2/reports/{target_id}/results",
        f"https://marsapi.ams.usda.gov/services/v1.1/reports/{target_id}/data",
        f"https://marsapi.ams.usda.gov/services/v1.1/reports/{target_id}",
        "https://marsapi.ams.usda.gov/services/v1.2/reports"
    ]
    
    auth_bytes = f"{api_key}:".encode('utf-8')
    encoded_auth = base64.b64encode(auth_bytes).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Accept": "application/json",
        "User-Agent": "GiantFoodsystem-Dashboard/3.2"
    }
    
    last_status = "No Attempt"
    debug_log = []
    final_response = None
    successful_url = ""
    raw_json_data = {"status": "통신 실패", "message": "유효한 응답 데이터를 받지 못했습니다."}
    
    try:
        # 1. API 통신 시도
        for url in base_urls:
            try:
                res = requests.get(url, headers=headers, timeout=12)
                last_status = res.status_code
                
                try:
                    raw_json_data = res.json()
                except:
                    raw_json_data = {"status_code": last_status, "raw_response_text": res.text[:2000]}
                
                if res.status_code == 200:
                    final_response = res
                    successful_url = url
                    break
                else:
                    debug_log.append(f"URL: {url} | Status: {res.status_code}")
            except Exception as e:
                debug_log.append(f"URL: {url} | Exception: {str(e)}")
                raw_json_data = {"error": str(e)}
                continue
        
        # 2. 통신 결과 확인
        if final_response:
            status_msg = "API 통신 성공 (시뮬레이션 모드 가동 중)"
            return pd.DataFrame(demo_prices), status_msg, raw_json_data, successful_url
        else:
            st.session_state['api_debug_details'] = debug_log
            return pd.DataFrame(demo_prices), f"통신 실패 (Status: {last_status}) - 시뮬레이션 가동", raw_json_data, ""
            
    except Exception as e:
        return pd.DataFrame(demo_prices), f"시스템 오류 - 시뮬레이션 가동", {"error_message": str(e)}, ""

# ==========================================
# 3. 데이터 로드 로직 (구글 시트 연동)
# ==========================================
@st.cache_data(ttl=60)
def fetch_gsheet_data(sheet_url, worksheet_name):
    df = pd.DataFrame()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url, worksheet=worksheet_name)
    except Exception:
        try:
            if "/d/" in sheet_url:
                sheet_id = sheet_url.split("/d/")[1].split("/")[0]
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(worksheet_name)}"
                df = pd.read_csv(csv_url)
        except: return pd.DataFrame()
    
    if not df.empty:
        df.columns = [re.sub(r'[^a-z0-9_]+', '_', str(col).strip().lower()).strip('_') for col in df.columns]
    return df

def load_all_data():
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "URL 미설정"
    clients = fetch_gsheet_data(sheet_url, "Clients")
    orders = fetch_gsheet_data(sheet_url, "Orders")
    trucks = fetch_gsheet_data(sheet_url, "Trucks")
    return clients, orders, trucks, None

df_clients, df_orders, df_trucks, error_msg = load_all_data()

def ensure_columns(df, expected_cols):
    for col in expected_cols:
        if col not in df.columns: 
            df[col] = 0 if 'quantity' in col or col in ['capacity', 'assigned'] else ""
    return df

df_clients = ensure_columns(df_clients, ["client_id", "name", "type"])
df_orders = ensure_columns(df_orders, ["order_id", "client_id", "region", "product", "quantity_box", "quantity_pallet"])
df_trucks = ensure_columns(df_trucks, ["truck_id", "region", "return_day", "capacity", "assigned"])

# ==========================================
# 4. 사이드바 구성
# ==========================================
if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "통합 주문 현황"

st.sidebar.markdown("""
<h2 style="margin: 0; font-weight: 900; line-height: 1.0;">
    <span style="color: #E31837;">GIANT</span><br>
    <span style="color: #cbd5e1; font-size: 0.95rem; letter-spacing: 1px;">FOODSYSTEM</span>
</h2>
<p style="font-size: 0.8rem; font-weight: 600; color: #64748b; margin-top: 8px;">HQ: NJ | Hub: GA</p>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

all_menus = ["통합 주문 현황", "수요자(Customer) 포털", "백홀 파트너(단순물류이송)", "지역별 공급자 파트너", "품목별 시장가 비교", "데이터 통합 관리", "시스템 도움말"]
for menu in all_menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

st.sidebar.markdown("---")
use_live_api = st.sidebar.toggle("🛰️ API 통신 테스트 모드", value=True)
st.sidebar.markdown("---")

app_url = "https://giant-backhaul.streamlit.app" 
qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={app_url}"
st.sidebar.image(qr_url, caption="시스템 접속 QR", width=150)
st.sidebar.code(app_url, language=None)

# ==========================================
# 5. 화면 뷰 로직
# ==========================================

def render_network_map():
    if not PLOTLY_AVAILABLE: return
    hubs = {'NJ (HQ)': [40.7128, -74.0060], 'GA (Hub)': [33.7490, -84.3880], 'TX': [29.7604, -95.3698], 'FL': [25.7617, -80.1918], 'NC/SC': [35.2271, -80.8431]}
    fig = go.Figure()
    for n, c in hubs.items():
        if 'GA' not in n:
            fig.add_trace(go.Scattergeo(locationmode='USA-states', lon=[-84.3880, c[1]], lat=[33.7490, c[0]], mode='lines', line=dict(width=1.2, color='#94a3b8'), opacity=0.7))
    names = [f"<b>{n}</b>" for n in hubs.keys()]
    fig.add_trace(go.Scattergeo(locationmode='USA-states', lon=[v[1] for v in hubs.values()], lat=[v[0] for v in hubs.values()], text=names, mode='markers+text', textposition="top center", textfont=dict(size=14), marker=dict(size=14, color=['#000000', '#E31837', '#0F4C81', '#0F4C81', '#0F4C81'], line=dict(width=2, color='white'))))
    fig.update_layout(geo=dict(scope='usa', projection_type='albers usa', showland=True, landcolor="#f8fafc", subunitcolor="#cbd5e1"), margin=dict(l=0, r=0, t=0, b=0), height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def view_unified_orders():
    render_official_header()
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">총 오더</div><div class="metric-value">{len(df_orders)}건</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-label">물량 (Box / PLT)</div><div class="metric-value">{int(df_orders["quantity_box"].sum())} / {int(df_orders["quantity_pallet"].sum())}</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-label">운행 트럭</div><div class="metric-value">{len(df_trucks)}대</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-label">허브 매칭률</div><div class="metric-value">Active</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    render_network_map()

def view_market_price_comparison():
    render_official_header()
    
    st.subheader("📊 주요 식자재 백홀 차익 분석 시스템")
    
    # 강력한 시뮬레이션 모드 경고 배너
    st.markdown("""
    <div class="sim-warning">
        <b>🚨 시스템 검증을 위한 시뮬레이션 모드 가동 중</b><br>
        현재 화면의 모든 단가 및 분석 내용은 <b>백홀 매칭 로직과 UI 설계를 테스트하기 위해 구성된 가상의 데이터</b>입니다. 실제 USDA API에서 품목별(소고기, 돼지고기, 닭고기 등) 정확한 단가를 추출하려면, 품목별 고유 리포트 번호 발굴 및 개별 JSON 파싱(추출) 코드 개발이 선행되어야 합니다.
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🛠️ API 통신 테스트 및 리포트 ID 설정 (개발자용)"):
        col_id, col_btn = st.columns([3, 1])
        manual_report_id = col_id.text_input("통신 테스트용 리포트 ID 입력 (기본: 3646)", value="3646")
        
        st.markdown("🔗 **[USDA MyMarketNews 포털 바로가기](https://mymarketnews.ams.usda.gov/)** (여기서 검색하여 리포트 번호나 Slug ID를 찾으세요!)")
        
        if col_btn.button("API 통신 테스트", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
    if use_live_api:
        df_price, update_status, raw_json, success_url = fetch_usda_api_data(manual_report_id)
    else:
        df_price, update_status, raw_json, success_url = fetch_usda_api_data(manual_report_id)
        update_status = "오프라인 시뮬레이션 모드"

    status_color = "#f59e0b" # 오렌지색으로 변경 (시뮬레이션 강조)
    st.markdown(f"**현재 상태:** <span style='color:{status_color}; font-weight:bold;'>{update_status}</span>", unsafe_allow_html=True)

    if "실패" in update_status and 'api_debug_details' in st.session_state:
        st.markdown('<div class="debug-box">', unsafe_allow_html=True)
        st.write("**API 통신 오류 로그:**")
        for log in st.session_state['api_debug_details']:
            st.text(log)
        st.markdown('</div>', unsafe_allow_html=True)
        
    # 개발자를 위한 실제 RAW JSON 뷰어
    if use_live_api:
        st.markdown("### 💻 실제 리포트 Raw Data 분석기")
        
        if success_url:
            st.write(f"✅ **응답 출처 URL:** `{success_url}`")
            
            # URL 끝자리에 따른 상태 판별 로직 추가
            if success_url.endswith(str(manual_report_id)):
                st.error("🚨 **[주의] 현재 '보고서 표지(Metadata)' 정보만 수신되었습니다!** 🚨\n\n대표님께서 찾으신 `office_name`, `report_title` 등의 단어들은 가격 정보가 아니라 이 보고서의 표지(껍데기) 정보입니다. USDA 서버가 실제 가격이 들어있는 `/data` 경로를 막아두었거나, 해당 번호의 보고서에는 API 가격 데이터가 제공되지 않습니다.")
            elif "/data" in success_url or "/results" in success_url:
                st.success("🎯 **[성공] 실제 '가격 상세 데이터(Data)' 경로 접근에 성공했습니다!** 아래 표에서 가격(Price)이나 아이템(Item) 관련 영문 키워드를 찾아주세요.")

        # results 키 내부의 리스트를 추출하여 DataFrame 형태로 깔끔하게 표시
        if isinstance(raw_json, dict) and "results" in raw_json and isinstance(raw_json["results"], list) and len(raw_json["results"]) > 0:
            real_df = pd.DataFrame(raw_json["results"])
            
            st.markdown(f"#### 🔍 수신된 데이터 구조 미리보기 (총 {len(real_df)}개 항목)")
            st.dataframe(real_df, height=300)
            
            # 파싱을 위해 사용 가능한 컬럼명 나열
            st.markdown("**👇 현재 데이터에 포함된 전체 영어 단어(Key) 목록:**")
            st.code(", ".join(real_df.columns))
            
            if success_url.endswith(str(manual_report_id)):
                st.markdown("*이 단어들 중에 가격(Price) 관련 단어가 없다면, 이 보고서 번호로는 실시간 시세 연동이 불가능합니다. 포털 사이트에서 다른 번호나 Slug ID를 찾아 넣어보세요!*")
        else:
            # results 배열이 없거나 다른 형태일 때 원본 JSON 표시
            st.json(raw_json)

    st.markdown("---")
    
    # === 품목 검색 및 필터링 기능 ===
    col_search, _ = st.columns([1, 1])
    search_query = col_search.text_input("🔍 특정 품목/부위 검색 (예: 삼겹살, 립아이)", "")
    
    if search_query:
        df_item_filtered = df_price[df_price['부위'].str.contains(search_query, case=False, na=False) | df_price['품목'].str.contains(search_query, case=False, na=False)]
        selected_item_display = f"'{search_query}' 검색 결과"
        if df_item_filtered.empty:
            st.warning(f"'{search_query}'에 대한 검색 결과가 없습니다. 전체 데이터를 표시합니다.")
            df_item_filtered = df_price
            selected_item_display = "전체 데이터"
    else:
        if not df_price.empty and '품목' in df_price.columns:
            item_options = df_price['품목'].unique()
            selected_item = st.radio("🛒 분석 품목 카테고리 선택", options=item_options, horizontal=True)
            df_item_filtered = df_price[df_price['품목'] == selected_item]
            selected_item_display = selected_item.split(' ')[1] if ' ' in selected_item else selected_item
        else:
            df_item_filtered = df_price
            selected_item_display = "선택된 품목"

    tab1, tab2 = st.tabs(["🗺️ 지역별 시세 비교 (부위 선택)", f"🥩 {selected_item_display} 세부 단가 비교"])
    
    with tab1:
        part_options = df_item_filtered['부위'].unique() if not df_item_filtered.empty and '부위' in df_item_filtered.columns else ["통닭(Whole)"]
        selected_part = st.selectbox("📌 조회할 세부 부위/종류 선택", options=part_options, key="tab1_part")

        filtered_df = df_item_filtered[df_item_filtered['부위'] == selected_part] if not df_item_filtered.empty and '부위' in df_item_filtered.columns else df_item_filtered

        col1, col2 = st.columns([2, 1])
        with col1:
            if not filtered_df.empty and PLOTLY_AVAILABLE:
                fig = px.bar(filtered_df, x='지역', y='가격', color='상태', barmode='group',
                             title=f"[시뮬레이션] {selected_part} 지역별 시세",
                             color_discrete_map={'냉장': '#E31837', '냉동': '#0F4C81'})
                fig.update_layout(yaxis_title="가격 ($/LB)", xaxis_title="지역", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown(f"### 🔍 {selected_part} 가상 맞춤형 전략")
            if not filtered_df.empty:
                try:
                    tx_frozen = filtered_df[(filtered_df['지역']=='TX') & (filtered_df['상태']=='냉동')]['가격'].values[0]
                    tx_ref = filtered_df[(filtered_df['지역']=='TX') & (filtered_df['상태']=='냉장')]['가격'].values[0]
                    ga_ref = filtered_df[(filtered_df['지역']=='GA (Hub)') & (filtered_df['상태']=='냉장')]['가격'].values[0]
                    nj_ref = filtered_df[(filtered_df['지역']=='NJ (HQ)') & (filtered_df['상태']=='냉장')]['가격'].values[0]
                    
                    if "무기후지" in selected_part:
                        st.success(f"**프리미엄 K-BBQ 타겟 전략 (예시)**\n\n"
                                   f"❄️ **냉동 시세**: TX 지역이 **${tx_frozen}** 수준으로 낮게 형성됩니다. 고단가 품목은 물류비가 싼 남부에서 할당량을 확보 후 비축하는 전략이 유효합니다.\n\n"
                                   f"🧊 **냉장 시세**: NJ 본사 지역(**${nj_ref}**)과 남부 지역의 단가 차이가 존재합니다. 최고급 냉장육을 선호하는 프랜차이즈 직납 물량으로 매칭 시 수익 극대화가 예상됩니다.")
                    else:
                        st.success(f"**거점 간 백홀 차익 전략 (예시)**\n\n"
                                   f"❄️ **냉동 시세**: TX 지역이 **${tx_frozen}**으로 가장 낮습니다. TX 지역 납품 후 복귀 차량에 냉동 물량을 상차하면 조지아 허브 재고 보충 물류비를 크게 절감할 수 있습니다.\n\n"
                                   f"🧊 **냉장 시세**: NJ(본사) 지역이 **${nj_ref}**로 가장 높습니다. 단가가 저렴한 남부(TX/GA)에서 신선 물량을 확보하여 NJ 본사로 올려보내는(Inbound) 매칭을 고려하세요.")
                except Exception as e:
                    st.info("데이터를 분석 중입니다...")
                    
    with tab2:
        region_options = df_item_filtered['지역'].unique() if not df_item_filtered.empty and '지역' in df_item_filtered.columns else ["GA (Hub)"]
        selected_region = st.selectbox("📌 조회할 기준 지역 선택", options=region_options, key="tab2_region")
        
        filtered_df_region = df_item_filtered[df_item_filtered['지역'] == selected_region] if not df_item_filtered.empty and '지역' in df_item_filtered.columns else df_item_filtered

        col3, col4 = st.columns([2, 1])
        with col3:
            if not filtered_df_region.empty and PLOTLY_AVAILABLE:
                fig2 = px.bar(filtered_df_region, x='부위', y='가격', color='상태', barmode='group',
                             title=f"[시뮬레이션] {selected_region} 지역 - 부위/종류별 비교",
                             color_discrete_map={'냉장': '#E31837', '냉동': '#0F4C81'})
                fig2.update_layout(yaxis_title="가격 ($/LB)", xaxis_title="부위/종류", template="plotly_white")
                st.plotly_chart(fig2, use_container_width=True)
        
        with col4:
            st.markdown(f"### 🔍 {selected_region} 가상 차익 분석")
            if not filtered_df_region.empty and '부위' in filtered_df_region.columns:
                try:
                    analyze_item = selected_item if not search_query else search_query

                    if "닭고기" in analyze_item:
                        breast_price = filtered_df_region[(filtered_df_region['부위'].str.contains('가슴살')) & (filtered_df_region['상태']=='냉동')]['가격'].values[0]
                        thigh_price = filtered_df_region[(filtered_df_region['부위'].str.contains('다리살')) & (filtered_df_region['상태']=='냉동')]['가격'].values[0]
                        diff = round(breast_price - thigh_price, 2)
                        st.success(f"**부위별 프로모션 기획 (예시)**\n\n"
                                   f"현재 {selected_region} 지역의 냉동 가슴살 단가는 **${breast_price}**, 다리살은 **${thigh_price}**입니다. (차이: **${diff}/LB**)\n\n"
                                   f"가성비가 높은 다리살 위주의 프로모션을 기획하면 B2B 대량 수요를 견인할 수 있습니다.")
                    elif "새우" in analyze_item:
                        white_price = filtered_df_region[(filtered_df_region['
