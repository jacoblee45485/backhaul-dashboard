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
        
        if not df_orders.empty:
            df_orders.columns = [re.sub(r'[^a-z0-9_]+', '_', str(c).strip().lower()).strip('_') for c in df_orders.columns]
        if not df_trucks.empty:
            df_trucks.columns = [re.sub(r'[^a-z0-9_]+', '_', str(c).strip().lower()).strip('_') for c in df_trucks.columns]
            
        return df_orders, df_trucks, None
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), str(e)

df_orders, df_trucks, error_msg = load_gsheet_data()

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

menus = ["통합 주문 현황", "품목별 시장가 비교", "로컬 파트너 검색", "데이터 통합 관리"]
for menu in menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

st.sidebar.markdown("---")
if st.sidebar.button("🔄 실시간 데이터 업데이트", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

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

def view_market_comparison():
    render_official_header()
    st.subheader("📈 USDA 실시간 품목 시세 분석")
    report_id = st.text_input("조회할 USDA 리포트 번호 (숫자)", value="2498")
    
    if report_id:
        with st.spinner(f"Report {report_id} 데이터를 분석 중..."):
            df_market, status = fetch_usda_market_data(report_id)
            if status == "success":
                st.success(f"✅ Report {report_id}에서 유효한 가격 정보를 찾았습니다.")
                price_col = 'avg_price' if 'avg_price' in df_market.columns else 'price'
                if PLOTLY_AVAILABLE:
                    fig = px.bar(df_market.head(15), x=df_market.head(15).index, y=price_col, title=f"품목별 평균 단가 ($)", color_discrete_sequence=['#E31837'])
                    st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_market[[price_col]].head(10))
            elif status == "empty_shell":
                st.warning("데이터는 존재하나 유효한 가격 정보가 없습니다.")

def view_local_partners():
    render_official_header()
    st.subheader("🤝 로컬 파트너 발굴 (Backhaul Sourcing)")
    st.markdown("배송 후 GA 허브로 돌아오는 트럭의 공차율을 줄이기 위한 지역 파트너 및 산지 발굴 지도입니다.")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🥩 텍사스 (TX 육류)", "🍊 플로리다 (FL 농·수산물)", "🍑 조지아 (GA 농·축산물 & 홀세일)", "🍎 뉴저지 (NJ 농·수산물)"])
    
    with tab1:
        # 텍사스 로컬 육류 공급처 데모 데이터
        tx_suppliers = pd.DataFrame([
            {"업체명": "Texas Beef Packers", "도시": "Dallas", "취급품목": "Beef", "상태": "계약 검토중", "lat": 32.7767, "lon": -96.7970},
            {"업체명": "Houston Wholesale Meat", "도시": "Houston", "취급품목": "Beef/Pork", "상태": "컨택 요망", "lat": 29.7604, "lon": -95.3698},
            {"업체명": "Austin Poultry Farms", "도시": "Austin", "취급품목": "Poultry", "상태": "계약 검토중", "lat": 30.2672, "lon": -97.7431},
            {"업체명": "San Antonio Meats", "도시": "San Antonio", "취급품목": "Pork", "상태": "컨택 요망", "lat": 29.4241, "lon": -98.4936}
        ])
        
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.dataframe(tx_suppliers[["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
            st.info("💡 **팁:** 구글 시트 'Suppliers' 탭을 통해 USDA 육류가공업체 데이터를 연동하면 더욱 촘촘한 배차망을 구축할 수 있습니다.")
        with c2:
            if PLOTLY_AVAILABLE:
                fig1 = px.scatter_geo(tx_suppliers, lat='lat', lon='lon', text='업체명', color='취급품목',
                                     scope='usa', title="Texas Local Meat Suppliers Map",
                                     color_discrete_sequence=['#E31837', '#0F4C81', '#166534'])
                fig1.update_geos(fitbounds="locations")
                st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        # 플로리다 농/수산물 공급처 데모 데이터
        fl_suppliers = pd.DataFrame([
            {"업체명": "Jacksonville Seafood Co.", "도시": "Jacksonville", "취급품목": "Seafood", "상태": "계약 완료", "lat": 30.3322, "lon": -81.6557},
            {"업체명": "Tampa Citrus Farms", "도시": "Tampa", "취급품목": "Citrus/Fruits", "상태": "계약 검토중", "lat": 27.9506, "lon": -82.4572},
            {"업체명": "Miami Ocean Catch", "도시": "Miami", "취급품목": "Seafood", "상태": "컨택 요망", "lat": 25.7617, "lon": -80.1918},
            {"업체명": "Orlando Fresh Greens", "도시": "Orlando", "취급품목": "Vegetables", "상태": "컨택 요망", "lat": 28.5383, "lon": -81.3792}
        ])
        
        c3, c4 = st.columns([1, 1.5])
        with c3:
            st.dataframe(fl_suppliers[["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
            st.info("💡 **팁:** 플로리다는 오렌지/자몽 등 감귤류 농장과 해안가 수산물(새우, 생선류) 소싱이 백홀 최적화에 유리합니다.")
        with c4:
            if PLOTLY_AVAILABLE:
                fig2 = px.scatter_geo(fl_suppliers, lat='lat', lon='lon', text='업체명', color='취급품목',
                                     scope='usa', title="Florida Agri/Seafood Suppliers Map",
                                     color_discrete_sequence=['#0EA5E9', '#F59E0B', '#10B981'])
                fig2.update_geos(fitbounds="locations")
                st.plotly_chart(fig2, use_container_width=True)
                
    with tab3:
        # 조지아 농/축산물 및 홀세일러 공급처 데모 데이터
        ga_suppliers = pd.DataFrame([
            {"업체명": "Gainesville Poultry", "도시": "Gainesville", "취급품목": "Poultry", "상태": "메인 파트너", "lat": 34.2978, "lon": -83.8240},
            {"업체명": "Albany Peanut Co.", "도시": "Albany", "취급품목": "Agri/Peanuts", "상태": "계약 완료", "lat": 31.5785, "lon": -84.1557},
            {"업체명": "Savannah Seafood", "도시": "Savannah", "취급품목": "Seafood", "상태": "컨택 요망", "lat": 32.0809, "lon": -81.0912},
            {"업체명": "Atlanta Fresh Meats", "도시": "Atlanta", "취급품목": "Beef/Pork", "상태": "메인 파트너", "lat": 33.7490, "lon": -84.3880},
            {"업체명": "Macon Food Distributors", "도시": "Macon", "취급품목": "Wholesale", "상태": "계약 검토중", "lat": 32.8407, "lon": -83.6324},
            {"업체명": "Norcross Asian Wholesale", "도시": "Norcross", "취급품목": "Wholesale", "상태": "컨택 요망", "lat": 33.9412, "lon": -84.2135}
        ])
        
        c5, c6 = st.columns([1, 1.5])
        with c5:
            st.dataframe(ga_suppliers[["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
            st.info("💡 **팁:** 조지아(GA)는 물류 메인 허브이면서 동시에 가금류(Poultry), 주요 농작물, 그리고 대형 식자재 홀세일러(Wholesale)가 밀집해 있습니다.")
        with c6:
            if PLOTLY_AVAILABLE:
                fig3 = px.scatter_geo(ga_suppliers, lat='lat', lon='lon', text='업체명', color='취급품목',
                                     scope='usa', title="Georgia Agri/Livestock & Wholesale Map",
                                     color_discrete_sequence=['#F59E0B', '#E31837', '#0EA5E9', '#8B5CF6', '#10B981'])
                fig3.update_geos(fitbounds="locations")
                st.plotly_chart(fig3, use_container_width=True)
                
    with tab4:
        # 뉴저지 농/수산물 공급처 데모 데이터
        nj_suppliers = pd.DataFrame([
            {"업체명": "Hammonton Blueberry Farms", "도시": "Hammonton", "취급품목": "Fruits", "상태": "계약 검토중", "lat": 39.6364, "lon": -74.8036},
            {"업체명": "Cape May Catch", "도시": "Cape May", "취급품목": "Seafood", "상태": "계약 완료", "lat": 38.9351, "lon": -74.9060},
            {"업체명": "Vineland Produce", "도시": "Vineland", "취급품목": "Vegetables", "상태": "컨택 요망", "lat": 39.4863, "lon": -75.0259},
            {"업체명": "Trenton Meats", "도시": "Trenton", "취급품목": "Meat/Poultry", "상태": "메인 파트너", "lat": 40.2170, "lon": -74.7429}
        ])
        
        c7, c8 = st.columns([1, 1.5])
        with c7:
            st.dataframe(nj_suppliers[["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
            st.info("💡 **팁:** 뉴저지(NJ) 허브 인근 지역은 블루베리, 토마토 등의 신선 농산물과 해안 지역의 수산물 백홀 최적화에 이상적입니다.")
        with c8:
            if PLOTLY_AVAILABLE:
                fig4 = px.scatter_geo(nj_suppliers, lat='lat', lon='lon', text='업체명', color='취급품목',
                                     scope='usa', title="New Jersey Agri/Seafood Suppliers Map",
                                     color_discrete_sequence=['#10B981', '#0EA5E9', '#F59E0B', '#E31837'])
                fig4.update_geos(fitbounds="locations")
                st.plotly_chart(fig4, use_container_width=True)


if st.session_state.current_menu == "통합 주문 현황":
    view_unified_dashboard()
elif st.session_state.current_menu == "품목별 시장가 비교":
    view_market_comparison()
elif st.session_state.current_menu == "로컬 파트너 검색":
    view_local_partners()
elif st.session_state.current_menu == "데이터 통합 관리":
    render_official_header()
    st.subheader("⚙️ 데이터 관리")
    st.data_editor(df_orders, use_container_width=True)
