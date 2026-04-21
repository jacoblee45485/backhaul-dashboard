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

# 전역에서 재사용 가능한 로컬 파트너 데이터 생성
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

menus = ["통합 주문 현황", "시장가 비교 & 수익성 분석", "로컬 파트너 검색", "데이터 통합 관리"]
for menu in menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

st.sidebar.markdown("---")
if st.sidebar.button("🔄 실시간 데이터 업데이트", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# QR 코드 및 공유 링크 섹션 (고정된 URL)
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 시스템 공유하기")
st.sidebar.caption("아래 QR코드를 스캔하여 모바일로 접속하세요.")

fixed_app_url = "https://backhaul-dashboard-f8gdhjdyappm23kcj6hli87.streamlit.app/"
encoded_url = urllib.parse.quote(fixed_app_url)
qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={encoded_url}"

st.sidebar.image(qr_api_url, caption="스마트폰으로 스캔하세요", width=150)
st.sidebar.code(fixed_app_url, language=None)

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
    
    tab1, tab2 = st.tabs(["🎯 백홀 타겟 아이템 분석 (10% 룰 적용)", "📈 USDA 실시간 API 원본 조회"])
    
    with tab1:
        st.subheader("💡 지역별 단가 비교 및 백홀 타겟 아이템 선정")
        st.markdown("조지아(GA) 본사의 조달가 대비 **단가 차이가 10% 이상 저렴한** 타 지역 품목만 자동으로 타겟 아이템(Target)으로 분류하며, 차이가 미미한 품목은 검토 대상에서 제외(Exclude)합니다.")
        
        target_margin = st.slider("목표 마진율(%) 기준 설정", min_value=5, max_value=20, value=10, step=1)
        
        analysis_data = [
            {"품목": "Beef Ribeye (소고기 립아이)", "카테고리": "Meat", "비교지역": "TX", "GA_기준단가": 8.50, "타지역_현지단가": 7.10},
            {"품목": "Pork Belly (삼겹살)", "카테고리": "Meat", "비교지역": "TX", "GA_기준단가": 4.10, "타지역_현지단가": 3.90}, 
            {"품목": "Citrus (오렌지/자몽)", "카테고리": "Fruits", "비교지역": "FL", "GA_기준단가": 24.00, "타지역_현지단가": 18.50}, 
            {"품목": "Fresh Shrimp (생물 새우)", "카테고리": "Seafood", "비교지역": "FL", "GA_기준단가": 12.50, "타지역_현지단가": 9.80}, 
            {"품목": "Blueberry (블루베리)", "카테고리": "Fruits", "비교지역": "NJ", "GA_기준단가": 32.00, "타지역_현지단가": 26.50}, 
            {"품목": "Peanuts (땅콩)", "카테고리": "Agri", "비교지역": "GA", "GA_기준단가": 1.20, "타지역_현지단가": 1.15}, 
        ]
        
        df_analysis = pd.DataFrame(analysis_data)
        df_analysis["단가차이(%)"] = ((df_analysis["GA_기준단가"] - df_analysis["타지역_현지단가"]) / df_analysis["GA_기준단가"] * 100).round(1)
        
        def judge_target(margin):
            if margin >= target_margin: return "🎯 타겟 아이템"
            else: return "❌ 검토 제외"
                
        df_analysis["시스템 판정"] = df_analysis["단가차이(%)"].apply(judge_target)
        df_analysis = df_analysis.sort_values(by="단가차이(%)", ascending=False).reset_index(drop=True)
        df_target_only = df_analysis[df_analysis["단가차이(%)"] >= target_margin]
        
        col1, col2 = st.columns([1.5, 1])
        with col1:
            def highlight_status(val):
                if "타겟" in val: return 'color: #166534; background-color: #dcfce7; font-weight: bold'
                elif "제외" in val: return 'color: #64748b; background-color: #f1f5f9'
                return ''
            st.dataframe(df_analysis.style.map(highlight_status, subset=['시스템 판정']), use_container_width=True, hide_index=True)
            
        with col2:
            st.markdown(f"**🔥 백홀 타겟 확정 품목 (차익 {target_margin}% 이상)**")
            if not df_target_only.empty:
                for idx, row in df_target_only.iterrows():
                    st.success(f"{row['비교지역']} - {row['품목']}\n(마진: {row['단가차이(%)']}%)")
            else:
                st.warning("조건을 만족하는 타겟 아이템이 없습니다.")

        # ==========================================
        # 🔥 신규 기능: 타겟 아이템 기반 로컬 파트너 자동 매칭
        # ==========================================
        if not df_target_only.empty:
            st.markdown("---")
            st.subheader("🔗 타겟 품목 지역별 로컬 공급처 매칭")
            st.caption("수익성이 확인된 타겟 품목을 조달할 수 있는 현지 파트너 목록입니다.")
            
            # 타겟으로 선정된 고유 지역 추출 (예: TX, FL, NJ)
            target_regions = df_target_only['비교지역'].unique()
            suppliers_db = get_local_suppliers()
            
            # 매칭된 지역들의 탭 생성
            matched_tabs = st.tabs([f"📍 {region} 지역 조달처" for region in target_regions if region in suppliers_db])
            
            tab_idx = 0
            for region in target_regions:
                if region in suppliers_db:
                    with matched_tabs[tab_idx]:
                        reg_df = suppliers_db[region]
                        
                        # 해당 지역에서 타겟으로 선정된 품목 리스트 요약
                        matched_items = df_target_only[df_target_only['비교지역'] == region]['품목'].tolist()
                        st.markdown(f"**조달 목표:** {', '.join(matched_items)}")
                        
                        c_list, c_map = st.columns([1.2, 1])
                        with c_list:
                            st.dataframe(reg_df[["업체명", "도시", "취급품목", "상태"]], hide_index=True, use_container_width=True)
                        with c_map:
                            if PLOTLY_AVAILABLE:
                                fig = px.scatter_geo(reg_df, lat='lat', lon='lon', text='업체명', color='취급품목', scope='usa')
                                fig.update_geos(fitbounds="locations")
                                fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
                                st.plotly_chart(fig, use_container_width=True)
                    tab_idx += 1


    with tab2:
        st.markdown("USDA MARS API를 통해 특정 리포트의 실시간 가공되지 않은 원본 시세를 조회합니다.")
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
                        fig = px.bar(df_market.head(15), x=df_market.head(15).index, y=price_col, title=f"품목별 평균 단가 ($)", color_discrete_sequence=['#E31837'])
                        st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df_market[[price_col]].head(10))
                elif status == "empty_shell":
                    st.markdown(f"""
                    <div class="warning-box">
                        <b>[데이터 경고]</b> 의미 없는 껍데기 데이터(표지)를 자동으로 걸러냈습니다!<br>
                        조회하신 숫자 번호(<b>{report_id}</b>)는 실제 가격 정보가 없습니다. 다른 ID를 입력해 보세요!
                    </div>
                    """, unsafe_allow_html=True)

def view_local_partners():
    render_official_header()
    st.subheader("🤝 로컬 파트너 발굴 (전체 검색)")
    st.markdown("배송 후 GA 허브로 돌아오는 트럭의 공차율을 줄이기 위한 전체 산지 조달 및 지역 내 잠재 판매처 발굴 지도입니다.")
    
    suppliers_db = get_local_suppliers()
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🥩 텍사스 (TX 육류)", 
        "🍊 플로리다 (FL 농·수산물)", 
        "🍑 조지아 (GA 농·축산물)", 
        "🍎 뉴저지 (NJ 농·수산물)",
        "🏢 조지아 홀세일 (잠재 판매처)"
    ])
    
    with tab1:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.dataframe(suppliers_db["TX"][["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
        with c2:
            if PLOTLY_AVAILABLE:
                fig1 = px.scatter_geo(suppliers_db["TX"], lat='lat', lon='lon', text='업체명', color='취급품목', scope='usa', title="Texas Local Meat Suppliers Map", color_discrete_sequence=['#E31837', '#0F4C81', '#166534'])
                fig1.update_geos(fitbounds="locations")
                st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        c3, c4 = st.columns([1, 1.5])
        with c3:
            st.dataframe(suppliers_db["FL"][["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
        with c4:
            if PLOTLY_AVAILABLE:
                fig2 = px.scatter_geo(suppliers_db["FL"], lat='lat', lon='lon', text='업체명', color='취급품목', scope='usa', title="Florida Agri/Seafood Suppliers Map", color_discrete_sequence=['#0EA5E9', '#F59E0B', '#10B981'])
                fig2.update_geos(fitbounds="locations")
                st.plotly_chart(fig2, use_container_width=True)
                
    with tab3:
        c5, c6 = st.columns([1, 1.5])
        with c5:
            st.dataframe(suppliers_db["GA"][["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
        with c6:
            if PLOTLY_AVAILABLE:
                fig3 = px.scatter_geo(suppliers_db["GA"], lat='lat', lon='lon', text='업체명', color='취급품목', scope='usa', title="Georgia Agri/Livestock Suppliers Map", color_discrete_sequence=['#F59E0B', '#E31837', '#0EA5E9', '#10B981'])
                fig3.update_geos(fitbounds="locations")
                st.plotly_chart(fig3, use_container_width=True)
                
    with tab4:
        c7, c8 = st.columns([1, 1.5])
        with c7:
            st.dataframe(suppliers_db["NJ"][["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
        with c8:
            if PLOTLY_AVAILABLE:
                fig4 = px.scatter_geo(suppliers_db["NJ"], lat='lat', lon='lon', text='업체명', color='취급품목', scope='usa', title="New Jersey Agri/Seafood Suppliers Map", color_discrete_sequence=['#10B981', '#0EA5E9', '#F59E0B', '#E31837'])
                fig4.update_geos(fitbounds="locations")
                st.plotly_chart(fig4, use_container_width=True)

    with tab5:
        c9, c10 = st.columns([1, 1.5])
        with c9:
            st.dataframe(suppliers_db["GA_W"][["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
            st.info("💡 **세일즈 포인트:** 조지아 로컬 홀세일러들은 자사 백홀 네트워크를 통해 확보한 원물을 대량으로 공급할 수 있는 핵심 잠재 B2B 판매처입니다.")
        with c10:
            if PLOTLY_AVAILABLE:
                fig5 = px.scatter_geo(suppliers_db["GA_W"], lat='lat', lon='lon', text='업체명', color='취급품목', scope='usa', title="Georgia Wholesale Customers (B2B) Map", color_discrete_sequence=['#8B5CF6', '#EC4899'])
                fig5.update_geos(fitbounds="locations")
                st.plotly_chart(fig5, use_container_width=True)

if st.session_state.current_menu == "통합 주문 현황":
    view_unified_dashboard()
elif st.session_state.current_menu == "시장가 비교 & 수익성 분석":
    view_market_comparison()
elif st.session_state.current_menu == "로컬 파트너 검색":
    view_local_partners()
elif st.session_state.current_menu == "데이터 통합 관리":
    render_official_header()
    st.subheader("⚙️ 데이터 관리")
    st.data_editor(df_orders, use_container_width=True)
