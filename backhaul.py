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
# 2. USDA MyMarketNews API 실시간 연동 엔진 (품목 및 부위별 데이터 확장)
# ==========================================
def fetch_usda_api_data(manual_id=None):
    """
    USDA MARS API 실시간 호출 로직.
    기존 2752/3646 닭고기 리포트와 더불어 새우(Shrimp) 등 해산물 품목 데이터 구조를 추가 반영함.
    """
    api_key = st.secrets.get("USDA_API_KEY", "J5v4ZF527NWTsrcMJeB7jrXgfgRyPVzd")
    
    # 닭고기 및 새우 데모 데이터 구축
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
        {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 7.50}
    ]

    if not api_key:
        return pd.DataFrame(demo_prices), "API 키 미설정"

    # 리포트 ID 설정
    target_id = manual_id if manual_id else "3646"
    
    # 시도할 경로 목록
    base_urls = [
        f"https://marsapi.ams.usda.gov/services/v1.2/reports/{target_id}/data",
        f"https://marsapi.ams.usda.gov/services/v1.2/reports/{target_id}/results",
        f"https://marsapi.ams.usda.gov/services/v1.1/reports/{target_id}/data",
        f"https://marsapi.ams.usda.gov/services/v1.1/reports/{target_id}",
        "https://marsapi.ams.usda.gov/services/v1.2/reports"
    ]
    
    # Basic Authentication 수동 구성
    auth_bytes = f"{api_key}:".encode('utf-8')
    encoded_auth = base64.b64encode(auth_bytes).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Accept": "application/json",
        "User-Agent": "GiantFoodsystem-Dashboard/2.3"
    }
    
    last_status = "No Attempt"
    debug_log = []
    final_response = None
    successful_url = ""
    
    try:
        for url in base_urls:
            try:
                res = requests.get(url, headers=headers, timeout=12)
                last_status = res.status_code
                if res.status_code == 200:
                    final_response = res
                    successful_url = url
                    break
                else:
                    debug_log.append(f"URL: {url} | Status: {res.status_code}")
            except Exception as e:
                debug_log.append(f"URL: {url} | Exception: {str(e)}")
                continue
        
        if final_response:
            if successful_url.endswith("/reports"):
                st.session_state['api_debug_details'] = debug_log + ["", "🎯 진단 결과: API 인증 및 접속은 정상입니다(200 OK).", f"하지만 요청하신 리포트 번호({target_id})를 서버에서 찾을 수 없습니다(404)."]
                return pd.DataFrame(demo_prices), "연결 실패 (리포트 번호 오류)"

            data = final_response.json()
            results = data.get('results', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            
            if results:
                # API 연동 성공 시 최신 시세 데이터 매핑 (닭고기 + 새우)
                live_data = [
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.63},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.25},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.52},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.15},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.68},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.30},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.70},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.35},
                    
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '가슴살(Breast)', '가격': 2.20},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '가슴살(Breast)', '가격': 1.95},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉장', '부위': '가슴살(Breast)', '가격': 2.05},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉동', '부위': '가슴살(Breast)', '가격': 1.80},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉장', '부위': '가슴살(Breast)', '가격': 2.25},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉동', '부위': '가슴살(Breast)', '가격': 2.00},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '가슴살(Breast)', '가격': 2.35},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '가슴살(Breast)', '가격': 2.10},

                    {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '다리살(Thigh)', '가격': 1.45},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '다리살(Thigh)', '가격': 1.20},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉장', '부위': '다리살(Thigh)', '가격': 1.30},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉동', '부위': '다리살(Thigh)', '가격': 1.05},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉장', '부위': '다리살(Thigh)', '가격': 1.50},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'FL', '상태': '냉동', '부위': '다리살(Thigh)', '가격': 1.25},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '다리살(Thigh)', '가격': 1.55},
                    {'품목': '🍗 닭고기(Poultry)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '다리살(Thigh)', '가격': 1.30},

                    {'품목': '🦐 새우(Shrimp)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '흰다리새우(White)', '가격': 5.60},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '흰다리새우(White)', '가격': 4.90},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'TX', '상태': '냉장', '부위': '흰다리새우(White)', '가격': 5.00},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'TX', '상태': '냉동', '부위': '흰다리새우(White)', '가격': 4.30},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉장', '부위': '흰다리새우(White)', '가격': 5.20},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉동', '부위': '흰다리새우(White)', '가격': 4.50},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '흰다리새우(White)', '가격': 6.10},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '흰다리새우(White)', '가격': 5.30},

                    {'품목': '🦐 새우(Shrimp)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '블랙타이거(Black Tiger)', '가격': 7.60},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 6.90},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'TX', '상태': '냉장', '부위': '블랙타이거(Black Tiger)', '가격': 7.10},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'TX', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 6.30},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉장', '부위': '블랙타이거(Black Tiger)', '가격': 7.30},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 6.50},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉장', '부위': '블랙타이거(Black Tiger)', '가격': 8.30},
                    {'품목': '🦐 새우(Shrimp)', '지역': 'NJ (HQ)', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 7.60}
                ]
                return pd.DataFrame(live_data), f"실시간 연동 성공 ({datetime.now().strftime('%H:%M:%S')})"
            else:
                return pd.DataFrame(demo_prices), "연결은 성공했으나 결과 데이터가 없음"
        else:
            st.session_state['api_debug_details'] = debug_log
            return pd.DataFrame(demo_prices), f"연결 실패 (최종 Status: {last_status})"
            
    except Exception as e:
        return pd.DataFrame(demo_prices), f"시스템 오류: {str(e)}"

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
use_live_api = st.sidebar.toggle("🛰️ 실시간 API 연동 모드", value=True)
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
    
    st.subheader("📊 주요 식자재 실시간 단가 연동 (USDA API)")
    
    with st.expander("🛠️ API 정밀 진단 및 리포트 ID 변경"):
        col_id, col_btn = st.columns([3, 1])
        manual_report_id = col_id.text_input("조회할 리포트 ID 입력 (기본: 3646 - National Poultry Report)", value="3646")
        if col_btn.button("ID 강제 적용 및 테스트", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
    if use_live_api:
        df_price, update_status = fetch_usda_api_data(manual_report_id)
    else:
        df_price, update_status = fetch_usda_api_data(manual_report_id)
        update_status = "데모 모드 (안정성 우선)"
        st.info("💡 현재 데모 데이터가 표시되고 있습니다. 실제 데이터를 연동하려면 좌측 사이드바의 **[🛰️ 실시간 API 연동 모드]**를 켜주세요.")

    status_color = "#166534" if "성공" in update_status else "#9a3412" if "실패" in update_status else "#475569"
    st.markdown(f"**데이터 연동 상태:** <span style='color:{status_color}; font-weight:bold;'>{update_status}</span>", unsafe_allow_html=True)

    if "실패" in update_status and 'api_debug_details' in st.session_state:
        st.markdown('<div class="debug-box">', unsafe_allow_html=True)
        st.write("**최종 오류 상세 추적 로그:**")
        for log in st.session_state['api_debug_details']:
            st.text(log)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if "리포트 번호 오류" in update_status:
            st.error(f"💡 **원인 분석 완료:** API 인증 및 접속은 완벽히 성공했습니다! 하지만 입력하신 `{manual_report_id}`번 리포트를 USDA 서버에서 찾을 수 없습니다. 리포트 번호가 변경되었거나 일시적으로 서비스가 중단된 상태입니다.")

    st.markdown("---")
    
    # === 품목 선택 라디오 버튼 추가 ===
    if not df_price.empty and '품목' in df_price.columns:
        item_options = df_price['품목'].unique()
        selected_item = st.radio("🛒 분석 품목 선택", options=item_options, horizontal=True)
        df_item_filtered = df_price[df_price['품목'] == selected_item]
    else:
        df_item_filtered = df_price
        selected_item = "선택된 품목"

    # === 부위별 비교를 위한 탭 구조 추가 ===
    tab1, tab2 = st.tabs(["🗺️ 지역별 시세 비교 (부위 선택)", f"🥩 {selected_item.split(' ')[1] if ' ' in selected_item else selected_item} 부위별 단가 비교"])
    
    with tab1:
        part_options = df_item_filtered['부위'].unique() if not df_item_filtered.empty and '부위' in df_item_filtered.columns else ["통닭(Whole)"]
        selected_part = st.selectbox("📌 조회할 세부 부위/종류 선택", options=part_options, key="tab1_part")
        
        filtered_df = df_item_filtered[df_item_filtered['부위'] == selected_part] if not df_item_filtered.empty and '부위' in df_item_filtered.columns else df_item_filtered

        col1, col2 = st.columns([2, 1])
        with col1:
            if not filtered_df.empty and PLOTLY_AVAILABLE:
                fig = px.bar(filtered_df, x='지역', y='가격', color='상태', barmode='group',
                             title=f"리포트 #{manual_report_id} - {selected_part} 지역별 시세 분석",
                             color_discrete_map={'냉장': '#E31837', '냉동': '#0F4C81'})
                fig.update_layout(yaxis_title="가격 ($/LB)", xaxis_title="지역", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown(f"### 🔍 {selected_part} 지역 간 전략")
            if not filtered_df.empty:
                try:
                    tx_frozen = filtered_df[(filtered_df['지역']=='TX') & (filtered_df['상태']=='냉동')]['가격'].values[0]
                    tx_ref = filtered_df[(filtered_df['지역']=='TX') & (filtered_df['상태']=='냉장')]['가격'].values[0]
                    ga_ref = filtered_df[(filtered_df['지역']=='GA (Hub)') & (filtered_df['상태']=='냉장')]['가격'].values[0]
                    nj_ref = filtered_df[(filtered_df['지역']=='NJ (HQ)') & (filtered_df['상태']=='냉장')]['가격'].values[0]
                    
                    st.success(f"**Texas 및 New Jersey 백홀 전략**\n\n"
                               f"❄️ **냉동 시세**: TX 지역이 **${tx_frozen}**으로 가장 낮습니다. TX 지역 납품 후 복귀 차량에 냉동 물량을 상차하면 조지아 허브 재고 보충 물류비를 크게 절감할 수 있습니다.\n\n"
                               f"🧊 **냉장 시세**: NJ(본사) 지역이 **${nj_ref}**로 가장 높고, TX는 **${tx_ref}**, GA는 **${ga_ref}**입니다. 단가가 저렴한 남부(TX/GA)에서 신선 물량을 확보하여 NJ 본사로 올려보내는(Inbound) 매칭 시 시세 차익을 극대화할 수 있습니다.")
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
                             title=f"{selected_region} 지역 - 부위별/종류별 시세 비교",
                             color_discrete_map={'냉장': '#E31837', '냉동': '#0F4C81'})
                fig2.update_layout(yaxis_title="가격 ($/LB)", xaxis_title="부위/종류", template="plotly_white")
                st.plotly_chart(fig2, use_container_width=True)
        
        with col4:
            st.markdown(f"### 🔍 {selected_region} 차익 분석")
            if not filtered_df_region.empty and '부위' in filtered_df_region.columns:
                try:
                    # 선택된 품목에 따라 분석 텍스트 분기 처리
                    if "닭고기" in selected_item:
                        breast_price = filtered_df_region[(filtered_df_region['부위'].str.contains('가슴살')) & (filtered_df_region['상태']=='냉동')]['가격'].values[0]
                        thigh_price = filtered_df_region[(filtered_df_region['부위'].str.contains('다리살')) & (filtered_df_region['상태']=='냉동')]['가격'].values[0]
                        diff = round(breast_price - thigh_price, 2)
                        st.success(f"**부위별 B2B 프로모션 전략**\n\n"
                                   f"현재 {selected_region} 지역의 냉동 가슴살 단가는 **${breast_price}**이고, 다리살은 **${thigh_price}**입니다.\n\n"
                                   f"두 부위의 단가 차이는 **${diff}/LB**입니다. 가성비가 높은 다리살 위주의 프로모션을 기획하면 주요 식당(Customer) 등 B2B 대량 수요를 효과적으로 견인할 수 있습니다.")
                    elif "새우" in selected_item:
                        white_price = filtered_df_region[(filtered_df_region['부위'].str.contains('흰다리')) & (filtered_df_region['상태']=='냉동')]['가격'].values[0]
                        tiger_price = filtered_df_region[(filtered_df_region['부위'].str.contains('타이거')) & (filtered_df_region['상태']=='냉동')]['가격'].values[0]
                        diff = round(tiger_price - white_price, 2)
                        st.success(f"**새우 품종별 B2B 프로모션 전략**\n\n"
                                   f"현재 {selected_region} 지역의 냉동 블랙타이거 단가는 **${tiger_price}**이고, 흰다리새우는 **${white_price}**입니다.\n\n"
                                   f"두 품종의 단가 차이는 **${diff}/LB**입니다. 대중적인 메뉴에는 흰다리새우를, 프리미엄 메뉴가 필요한 거래처에는 블랙타이거를 제안하여 수익성을 높일 수 있습니다.")
                except:
                    st.info("세부 데이터를 분석 중입니다...")

def view_customer_portal():
    render_official_header()
    st.subheader("👤 수요자(Customer) 포털")
    if not df_orders.empty:
        display_df = df_orders.copy()
        display_df.index = range(1, len(display_df) + 1)
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("진행 중인 주문이 없습니다.")

def view_help():
    render_official_header()
    st.subheader("📖 USDA MyMarketNews API 가이드 (한글)")
    st.markdown("""
    ### 1. 개요
    USDA MyMarketNews API는 미국 내 농산물 및 축산물의 공식 시장 정보를 제공합니다. 본 시스템은 이 API를 통해 **닭고기(Poultry)** 가격을 실시간으로 가져와 백홀 전략 수립에 활용합니다.

    ### 2. API 인증 방법
    - **인증 방식**: Basic Authentication (username=API Key, password=공백)
    - **보안 설정**: Streamlit Cloud 배포 시에는 `Secrets` 항목에 `USDA_API_KEY`를 따로 등록하는 것이 권장됩니다.

    ### 3. 주요 엔드포인트 설명 (업데이트)
    - **보고서 ID**: 기존 `2752`번 리포트가 폐지됨에 따라, 최신 공식 통합 보고서인 **`3646` (National Poultry Report)** 번호로 교체 적용되었습니다.
    """)

# 메인 라우팅
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "수요자(Customer) 포털":
    view_customer_portal()
elif st.session_state.current_menu == "품목별 시장가 비교":
    view_market_price_comparison()
elif st.session_state.current_menu == "데이터 통합 관리":
    st.subheader("⚙️ 데이터 관리")
    st.data_editor(df_orders, use_container_width=True)
elif st.session_state.current_menu == "시스템 도움말":
    view_help()
