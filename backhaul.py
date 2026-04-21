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

# 커스텀 CSS
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
    .warning-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #fff7ed;
        border: 1px solid #fed7aa;
        color: #9a3412;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 회사 공식 타이틀과 상세 설명이 포함된 헤더
def render_official_header():
    st.markdown("""
    <div style="background-color: #f8fafc; padding: 30px 20px; border-radius: 15px; border: 2px solid #e2e8f0; margin-bottom: 30px; text-align: center;">
        <h1 style="margin: 0; font-size: 3.5rem; font-weight: 900; letter-spacing: -2px; line-height: 1.1;">
            <span style="color: #E31837;">GIANT</span> <span style="color: #000000; font-size: 1.5rem; vertical-align: middle;">FOODSYSTEM</span>
        </h1>
        <p style="font-size: 1.2rem; font-weight: 700; color: #475569; margin: 10px 0 5px 0;">#1 K-food Distributor in USA</p>
        <p style="font-size: 0.95rem; font-weight: 500; color: #64748b; margin: 0; line-height: 1.4;">
            A nationwide food distributor serving for Korean Restaurants, Deli & Salad Bars since 1986
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 구글 시트 데이터 로드
# ==========================================
@st.cache_data(ttl=60)
def load_gsheet_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_orders = conn.read(worksheet="Orders")
        df_trucks = conn.read(worksheet="Trucks")
        
        # 컬럼명을 소문자 및 공백을 언더스코어로 변환 (안전 처리)
        if not df_orders.empty:
            df_orders.columns = [re.sub(r'[^a-z0-9_]+', '_', str(c).strip().lower()).strip('_') for c in df_orders.columns]
        if not df_trucks.empty:
            df_trucks.columns = [re.sub(r'[^a-z0-9_]+', '_', str(c).strip().lower()).strip('_') for c in df_trucks.columns]
            
        return df_orders, df_trucks, None
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), str(e)

df_orders, df_trucks, error_msg = load_gsheet_data()

# ==========================================
# 3. USDA 실시간 가격 연동 엔진 (필터링 강화)
# ==========================================
@st.cache_data(ttl=3600)
def fetch_usda_market_data(report_id):
    # Secrets 최상단에 있는 API 키를 안전하게 불러옵니다.
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
# 4. 사이드바 구성
# ==========================================
if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "통합 주문 현황"

st.sidebar.markdown("""
<h2 style="margin: 0; font-weight: 900; line-height: 1.0;">
    <span style="color: #E31837;">GIANT</span><br>
    <span style="color: #cbd5e1; font-size: 0.95rem; letter-spacing: 1px;">FOODSYSTEM</span>
</h2>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 최신 버전 메뉴 복구
menus = ["통합 주문 현황", "수요자(Customer) 포털", "품목별 시장가 비교", "데이터 통합 관리"]
for menu in menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

st.sidebar.markdown("---")
if st.sidebar.button("🔄 실시간 데이터 업데이트", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🔗 시스템 공유하기")
app_share_url = "https://backhaul-dashboard-giant.streamlit.app" 
qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={app_share_url}"
st.sidebar.image(qr_api_url, caption="스마트폰으로 접속하기", width=150)

# ==========================================
# 5. 메인 화면 뷰 (라우팅)
# ==========================================
def view_unified_dashboard():
    render_official_header()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">총 주문</div><div class="metric-value">{len(df_orders)}건</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-label">운행 트럭</div><div class="metric-value">{len(df_trucks)}대</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-label">GA 허브 상태</div><div class="metric-value">정상</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-label">시스템 연동</div><div class="metric-value">Online</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📊 지역별 물량 요약")
    
    if PLOTLY_AVAILABLE and not df_orders.empty and 'region' in df_orders.columns:
        fig = px.pie(df_orders, names='region', title="지역별 주문 분포", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("데이터를 불러오는 중이거나 지역별 데이터(region 열)가 구글 시트에 없습니다.")

def view_market_comparison():
    render_official_header()
    st.subheader("📈 USDA 실시간 품목 시세 분석")
    
    with st.expander("📌 주요 품목별 Report ID 가이드", expanded=False):
        st.markdown("""
        - **닭고기 (Poultry):** 2752 (National Whole Broiler)
        - **돼지고기 (Pork):** 2498 (National Daily Pork Carcass)
        - **소고기 (Beef):** 2461 (National Weekly Boxed Beef)
        """)

    report_id = st.text_input("조회할 USDA 리포트 번호 (숫자)", value="2498")
    
    if report_id:
        with st.spinner(f"Report {report_id} 데이터를 분석 중..."):
            df_market, status = fetch_usda_market_data(report_id)
            
            if status == "success":
                st.success(f"✅ Report {report_id}에서 유효한 가격 정보를 찾았습니다.")
                price_col = 'avg_price' if 'avg_price' in df_market.columns else 'price'
                if PLOTLY_AVAILABLE:
                    fig = px.bar(df_market.head(15), x=df_market.head(15).index, y=price_col, 
                                 title=f"품목별 평균 단가 ($)", color_discrete_sequence=['#E31837'])
                    st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_market[[price_col]].head(10))
            
            elif status == "empty_shell":
                st.markdown(f"""
                <div class="warning-box">
                    <b>[데이터 경고]</b> 의미 없는 껍데기 데이터(표지)를 자동으로 걸러냈습니다!<br>
                    조회하신 숫자 번호(<b>{report_id}</b>)는 서버에서 정상 응답은 했으나, 실제 가격 정보는 숨겨두었거나 없습니다. 
                    위 목록에서 다른 숫자 ID를 찾아 입력해 보세요!
                </div>
                """, unsafe_allow_html=True)
                st.info("💡 추천: 돼지고기 시세는 **2498** 또는 **2507** 번호를 시도해 보세요.")
            else:
                st.error(f"오류가 발생했습니다: {status}")

if st.session_state.current_menu == "통합 주문 현황":
    view_unified_dashboard()
elif st.session_state.current_menu == "품목별 시장가 비교":
    view_market_comparison()
elif st.session_state.current_menu == "수요자(Customer) 포털":
    render_official_header()
    st.subheader("👤 수요자 포털")
    st.dataframe(df_orders, use_container_width=True)
elif st.session_state.current_menu == "데이터 통합 관리":
    render_official_header()
    st.subheader("⚙️ 데이터 관리")
    st.data_editor(df_orders, use_container_width=True)
