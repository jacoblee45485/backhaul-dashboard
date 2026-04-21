import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import requests
import re
import urllib.parse
import base64
from datetime import datetime

# Plotly 라이브러리 안전하게 불러오기 (미국 지도 및 차트용)
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
    page_title="GIANT FOODSYSTEM - 통합 백홀 관리 시스템", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (UI 요소들은 각진 스타일 유지)
custom_css = (
    "<style>"
    ".block-container { padding-top: 1.5rem; }"
    ".metric-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 0px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }"
    ".metric-label { font-size: 0.9rem; color: #64748b; font-weight: 600; margin-bottom: 5px; }"
    ".metric-value { font-size: 1.8rem; font-weight: 900; color: #0f172a; }"
    ".status-badge { padding: 2px 10px; border-radius: 0px; font-size: 0.75rem; background-color: #dcfce7; color: #166534; font-weight: bold; }"
    ".warning-box { padding: 15px; border-radius: 0px; background-color: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; margin-bottom: 20px; }"
    ".stButton>button { border-radius: 0px; }"
    ".stTextInput>div>div>input { border-radius: 0px; }"
    ".stSelectbox>div>div>div { border-radius: 0px; }"
    "</style>"
)
st.markdown(custom_css, unsafe_allow_html=True)

def render_official_header():
    # 타이틀 박스의 모서리를 30px로 다시 둥글게 수정
    header_html = (
        '<div style="background-color: #f8fafc; padding: 30px 20px; border-radius: 30px; border: 2px solid #e2e8f0; margin-bottom: 30px; text-align: center;">'
        '<h1 style="margin: 0; font-size: 3.5rem; font-weight: 900; letter-spacing: -2px; line-height: 1.1;">'
        '<span style="color: #E31837;">GIANT</span> <span style="color: #000000;">FOODSYSTEM</span>'
        '</h1>'
        '<p style="font-size: 1.2rem; font-weight: 700; color: #475569; margin: 10px 0 5px 0;">#1 K-food Distributor in USA</p>'
        '<p style="font-size: 0.95rem; font-weight: 500; color: #64748b; margin: 0; line-height: 1.4;">'
        'A nationwide food distributor serving for Korean Restaurants, Deli & Salad Bars since 1986'
        '</p>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# 2. 구글 시트 및 로컬 공급처 데이터 로드
# ==========================================
@st.cache_data(ttl=60)
def load_gsheet_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_orders = conn.read(worksheet="Orders")
        df_trucks = conn.read(worksheet="Trucks")
        
        if not df_orders.empty:
            df_orders.columns = [re.sub(r'[^a-z0-9_]+', '_', str(c).strip().lower()).strip('_') for c in df_orders.columns]
        if not df_trucks.empty:
            df_trucks.columns = [re.sub(r'[^a-z0-9_]+', '_', str(c).strip().lower()).strip('_') for c in df_trucks.columns]
            
        return df_orders, df_trucks, None
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), str(e)

df_orders, df_trucks, error_msg = load_gsheet_data()

@st.cache_data
def get_local_suppliers():
    return {
        "TX": pd.DataFrame([
            {"업체명": "Texas Beef Packers", "도시": "Dallas", "취급품목": "Beef", "상태": "계약 검토중", "lat": 32.7767, "lon": -96.7970},
            {"업체명": "Houston Wholesale Meat", "도시": "Houston", "취급품목": "Beef/Pork", "상태": "컨택 요망", "lat": 29.7604, "lon": -95.3698},
            {"업체명": "Austin Poultry Farms", "도시": "Austin", "취급품목": "Poultry", "상태": "계약 검토중", "lat": 30.2672, "lon": -97.7431},
            {"업체명": "San Antonio Meats", "도시": "San Antonio", "취급품목": "Pork", "상태": "컨택 요망", "lat": 29.4241, "lon": -98.4936}
        ]),
        "FL": pd.DataFrame([
            {"업체명": "Jacksonville Seafood Co.", "도시": "Jacksonville", "취급품목": "Seafood", "상태": "계약 완료", "lat": 30.3322, "lon": -81.6557},
            {"업체명": "Tampa Citrus Farms", "도시": "Tampa", "취급품목": "Citrus/Fruits", "상태": "계약 검토중", "lat": 27.9506, "lon": -82.4572},
            {"업체명": "Miami Ocean Catch", "도시": "Miami", "취급품목": "Seafood", "상태": "컨택 요망", "lat": 25.7617, "lon": -80.1918},
            {"업체명": "Orlando Fresh Greens", "도시": "Orlando", "취급품목": "Vegetables", "상태": "컨택 요망", "lat": 28.5383, "lon": -81.3792}
        ]),
        "GA": pd.DataFrame([
            {"업체명": "Gainesville Poultry", "도시": "Gainesville", "취급품목": "Poultry", "상태": "메인 파트너", "lat": 34.2978, "lon": -83.8240},
            {"업체명": "Albany Peanut Co.", "도시": "Albany", "취급품목": "Agri/Peanuts", "상태": "계약 완료", "lat": 31.5785, "lon": -84.1557},
            {"업체명": "Savannah Seafood", "도시": "Savannah", "취급품목": "Seafood", "상태": "컨택 요망", "lat": 32.0809, "lon": -81.0912},
            {"업체명": "Atlanta Fresh Meats", "도시": "Atlanta", "취급품목": "Beef/Pork", "상태": "메인 파트너", "lat": 33.7490, "lon": -84.3880}
        ]),
        "NJ": pd.DataFrame([
            {"업체명": "Hammonton Blueberry Farms", "도시": "Hammonton", "취급품목": "Fruits", "상태": "계약 검토중", "lat": 39.6364, "lon": -74.8036},
            {"업체명": "Cape May Catch", "도시": "Cape May", "취급품목": "Seafood", "상태": "계약 완료", "lat": 38.9351, "lon": -74.9060},
            {"업체명": "Vineland Produce", "도시": "Vineland", "취급품목": "Vegetables", "상태": "컨택 요망", "lat": 39.4863, "lon": -75.0259},
            {"업체명": "Trenton Meats", "도시": "Trenton", "취급품목": "Meat/Poultry", "상태": "메인 파트너", "lat": 40.2170, "lon": -74.7429}
        ]),
        "GA_W": pd.DataFrame([
            {"업체명": "Macon Food Distributors", "도시": "Macon", "취급품목": "Wholesale", "상태": "판매 협의중", "lat": 32.8407, "lon": -83.6324},
            {"업체명": "Norcross Asian Wholesale", "도시": "Norcross", "취급품목": "Wholesale", "상태": "타겟 고객", "lat": 33.9412, "lon": -84.2135},
            {"업체명": "Buford Farmers Wholesale", "도시": "Buford", "취급품목": "Retail/Wholesale", "상태": "신규 발굴", "lat": 34.1207, "lon": -84.0044}
        ])
    }

# ==========================================
# 3. USDA 실시간 가격 연동 엔진
# ==========================================
@st.cache_data(ttl=3600)
def fetch_usda_market_data(report_id):
    api_key = st.secrets.get("USDA_API_KEY", "J5v4ZF527NWTsrcMJeB7jrXgfgRyPVzd")
    url = f"https://marsapi.ams.usda.gov/services/v1.2/reports/{report_id}/data"
    
    auth_bytes = f"{api_key}:".encode('utf-8')
    encoded_auth = base64.b64encode(auth_bytes).decode('utf-8')
    headers = {"Authorization": f"Basic {encoded_auth}", "Accept": "application/json"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return None, "empty_shell"
            
            df = pd.DataFrame(results)
            price_col = 'avg_price' if 'avg_price' in df.columns else ('price' if 'price' in df.columns else None)
            
            if price_col and price_col in df.columns:
                df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
                filtered_df = df[df[price_col] > 0].dropna(subset=[price_col])
                
                if filtered_df.empty:
                    return None, "empty_shell"
                return filtered_df, "success"
            else:
                return None, "empty_shell"
        return None, f"error_{response.status_code}"
    except Exception as e:
        return None, str(e)

# ==========================================
# 4. 사이드바 구성 (메뉴 순서 변경)
# ==========================================
if 'current_menu' not in st.session_state:
    st.session_
