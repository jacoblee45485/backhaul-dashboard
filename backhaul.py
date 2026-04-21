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

# 커스텀 CSS (모든 모서리를 부드럽게 라운딩 처리)
custom_css = (
    "<style>"
    ".block-container { padding-top: 1.5rem; }"
    ".metric-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 15px; padding: 15px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }"
    ".metric-label { font-size: 0.9rem; color: #64748b; font-weight: 600; margin-bottom: 5px; }"
    ".metric-value { font-size: 1.8rem; font-weight: 900; color: #0f172a; }"
    ".status-badge { padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; background-color: #dcfce7; color: #166534; font-weight: bold; }"
    ".warning-box { padding: 15px; border-radius: 12px; background-color: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; margin-bottom: 20px; }"
    ".stButton>button { border-radius: 10px; font-weight: 600; }"
    ".stTextInput>div>div>input { border-radius: 10px; }"
    ".stSelectbox>div>div>div { border-radius: 10px; }"
    ".stSlider>div { padding-bottom: 10px; }"
    "div[data-baseweb='tab-list'] { gap: 10px; }"
    "button[data-baseweb='tab'] { border-radius: 10px 10px 0px 0px; }"
    "</style>"
)
st.markdown(custom_css, unsafe_allow_html=True)

def render_official_header():
    # 타이틀 박스의 네 모서리를 25px로 부드럽게 라운딩
    header_html = (
        '<div style="background-color: #f8fafc; padding: 30px 20px; border-radius: 25px; border: 2px solid #e2e8f0; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">'
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
# 4. 사이드바 구성 (메뉴 순서 및 라운딩 디자인)
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

menus = [
    "통합 주문 현황", 
    "B2B 백홀 화물 운송 (3PL)", 
    "시장가 비교 & 수익성 분석", 
    "로컬 파트너 검색", 
    "데이터 통합 관리"
]

for menu in menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

st.sidebar.markdown("---")
if st.sidebar.button("🔄 실시간 데이터 업데이트", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

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
            {"품목": "Peanuts (땅콩)", "카테고리": "Agri", "비교지역": "GA", "GA_기준단가": 1.20, "Relat_Local": 1.15}, 
        ]
        
        df_analysis = pd.DataFrame(analysis_data)
        df_analysis["타지역_현지단가"] = df_analysis.apply(lambda x: x.get("Relat_Local", x.get("타지역_현지단가")), axis=1)
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
            st.dataframe(df_analysis[["품목", "비교지역", "GA_기준단가", "타지역_현지단가", "단가차이(%)", "시스템 판정"]].style.map(highlight_status, subset=['시스템 판정']), use_container_width=True, hide_index=True)
            
        with col2:
            st.markdown(f"**🔥 백홀 타겟 확정 품목 (차익 {target_margin}% 이상)**")
            if not df_target_only.empty:
                for idx, row in df_target_only.iterrows():
                    st.success(f"{row['비교지역']} - {row['품목']}\n(마진: {row['단가차이(%)']}%)")
            else:
                st.warning("조건을 만족하는 타겟 아이템이 없습니다.")

        if not df_target_only.empty:
            st.markdown("---")
            st.subheader("🔗 타겟 품목 지역별 로컬 공급처 매칭")
            st.caption("수익성이 확인된 타겟 품목을 조달할 수 있는 현지 파트너 목록입니다.")
            
            target_regions = df_target_only['비교지역'].unique()
            suppliers_db = get_local_suppliers()
            
            matched_tabs = st.tabs([f"📍 {region} 지역 조달처" for region in target_regions if region in suppliers_db])
            
            tab_idx = 0
            for region in target_regions:
                if region in suppliers_db:
                    with matched_tabs[tab_idx]:
                        reg_df = suppliers_db[region]
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
                            else:
                                st.warning("⚠️ Plotly 라이브러리 설치 필요.")
                    tab_idx += 1

def view_3pl_freight():
    render_official_header()
    st.subheader("🚛 B2B 백홀 화물 운송 의뢰 & 수익 분석 (3PL)")
    st.markdown("아웃바운드(프론트홀) 배송을 마치고 **조지아(GA) 메인 허브로 귀환하는 백홀 트럭**의 여유 공간을 활용합니다.")
    
    tab1, tab2 = st.tabs(["📝 운송 의뢰 및 실시간 매칭", "📊 백홀 운송 실적 및 수익성 분석"])
    
    with tab1:
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.markdown("#### 📝 백홀 운송 의뢰서 작성")
            with st.form("freight_form"):
                sender = st.selectbox("의뢰 업체 (화주)", ["Macon Food Distributors (GA)", "Norcross Asian Wholesale (GA)", "Texas Beef Packers (TX)", "기타 업체"])
                origin = st.selectbox("상차지 (Origin)", ["TX (Texas)", "FL (Florida)", "NJ (New Jersey)", "NC (North Carolina)", "기타"])
                destination = st.selectbox("하차지 (Destination)", ["GA (Georgia Main Hub)"])
                item_desc = st.text_input("화물 내용 (품목 무관)", placeholder="예: 상온 공산품, 포장 자재 등")
                pallets = st.number_input("물량 (Pallets)", min_value=1, max_value=22, value=1)
                date = st.date_input("희망 상차일")
                submitted = st.form_submit_button("백홀 운송 의뢰 접수")
                if submitted:
                    st.success(f"✅ {sender}님의 운송 의뢰({pallets} PLT)가 접수되었습니다.")
                    
        with col2:
            st.markdown("#### 🚚 실시간 귀환 트럭 적재 공간 시각화")
            st.info("GA로 돌아오는 트럭의 빈 공간 현황 (최대 22 PLT)")
            
            backhaul_trucks = [
                {"id": "TRK-901", "origin": "TX (Dallas)", "dest": "GA", "sched": "내일 오전", "used": 10, "avail": 12, "status": "매칭 가능"},
                {"id": "TRK-905", "origin": "FL (Miami)", "dest": "GA", "sched": "오늘 오후", "used": 0, "avail": 22, "status": "완전 공차"},
                {"id": "TRK-912", "origin": "NJ (Trenton)", "dest": "GA", "sched": "모레", "used": 18, "avail": 4, "status": "공간 협소"}
            ]
            
            for truck in backhaul_trucks:
                row1_html = ""
                row2_html = ""
                for i in range(11): 
                    idx1 = i * 2      
                    idx2 = i * 2 + 1  
                    if idx1 < truck["used"]:
                        row1_html += '<div style="width: 24px; height: 24px; background-color: #94a3b8; border-radius: 4px; flex-shrink: 0;">&nbsp;</div>'
                    else:
                        row1_html += '<div style="width: 24px; height: 24px; background-color: #dcfce7; border-radius: 4px; border: 2px solid #22c55e; box-sizing: border-box; flex-shrink: 0;">&nbsp;</div>'
                    if idx2 < truck["used"]:
                        row2_html += '<div style="width: 24px; height: 24px; background-color: #94a3b8; border-radius: 4px; flex-shrink: 0;">&nbsp;</div>'
                    else:
                        row2_html += '<div style="width: 24px; height: 24px; background-color: #dcfce7; border-radius: 4px; border: 2px solid #22c55e; box-sizing: border-box; flex-shrink: 0;">&nbsp;</div>'
    
                truck_html = f"""<div style="border: 1px solid #e2e8f0; border-radius: 15px; padding: 15px; margin-bottom: 15px; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
<strong style="font-size: 1.1em; color: #0f172a;">🚛 {truck['id']}</strong>
<span style="background-color: #f1f5f9; color: #334155; padding: 3px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold;">{truck['status']}</span>
</div>
<div style="color: #475569; font-size: 0.85em; margin-bottom: 12px;">
📍 <b>{truck['origin']}</b> ➡️ GA Hub | 🕒 {truck['sched']}
</div>
<div style="font-size: 0.85em; color: #334155; margin-bottom: 6px; display: flex; justify-content: space-between;">
<span>적재 현황 (사용: {truck['used']} / <b>잔여: {truck['avail']} PLT</b>)</span>
</div>
<div style="display: flex; align-items: center; background-color: #f8fafc; padding: 12px; border-radius: 12px; border: 1px solid #e2e8f0; overflow-x: auto;">
<div style="background-color: #cbd5e1; color: #334155; padding: 8px 4px; border-radius: 8px; font-size: 0.6rem; font-weight: bold; margin-right: 12px; text-align: center; min-width: 40px;">안쪽</div>
<div style="display: flex; flex-direction: column; gap: 5px; flex-shrink: 0;">
<div style="display: flex; flex-direction: row; gap: 5px;">{row1_html}</div>
<div style="display: flex; flex-direction: row; gap: 5px;">{row2_html}</div>
</div>
<div style="margin-left: auto; padding-left: 12px; color: #64748b; font-size: 0.6rem; font-weight: bold; text-align: center; border-left: 2px dashed #cbd5e1; min-width: 40px;">뒷문</div>
</div>
</div>"""
                st.markdown(truck_html, unsafe_allow_html=True)

    with tab2:
        st.markdown("#### 💰 백홀 화물 운송 수익성 분석")
        price_per_pallet = st.slider("💰 팔렛(Pallet)당 평균 운송 단가 설정 ($)", min_value=20, max_value=300, value=120, step=5)
        profit_data = [
            {"운송일자": "2026-04-15", "트럭ID": "TRK-881", "출발지": "TX", "물량(PLT)": 22, "한계비용($)": 350},
            {"운송일자": "2026-04-17", "트럭ID": "TRK-885", "출발지": "FL", "물량(PLT)": 18, "한계비용($)": 200},
            {"운송일자": "2026-04-19", "트럭ID": "TRK-890", "출발지": "NJ", "물량(PLT)": 20, "한계비용($)": 400},
        ]
        df_p = pd.DataFrame(profit_data)
        df_p["운송매출($)"] = df_p["물량(PLT)"] * price_per_pallet
        df_p["순이익($)"] = df_p["운송매출($)"] - df_p["한계비용($)"]
        df_p["이익률(%)"] = (df_p["순이익($)"] / df_p["운송매출($)"] * 100).round(1)
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="metric-card"><div class="metric-label">누적 백홀 매출</div><div class="metric-value">${df_p["운송매출($)"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><div class="metric-label">누적 순이익</div><div class="metric-value" style="color:#16a34a;">${df_p["순이익($)"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><div class="metric-label">평균 이익률</div><div class="metric-value" style="color:#2563eb;">{df_p["이익률(%)"].mean():.1f}%</div></div>', unsafe_allow_html=True)
        
        st.dataframe(df_p.style.map(lambda x: 'color: #16a34a; font-weight: bold;' if isinstance(x, (int, float)) and x > 0 else '', subset=["순이익($)", "이익률(%)"]), use_container_width=True, hide_index=True)

def view_local_partners():
    render_official_header()
    st.subheader("🤝 로컬 파트너 발굴 (전체 검색)")
    suppliers_db = get_local_suppliers()
    tabs = st.tabs(["🥩 텍사스 (TX)", "🍊 플로리다 (FL)", "🍑 조지아 (GA)", "🍎 뉴저지 (NJ)"])
    for i, region in enumerate(["TX", "FL", "GA", "NJ"]):
        with tabs[i]:
            c1, c2 = st.columns([1, 1.5])
            with c1: st.dataframe(suppliers_db[region][["업체명", "도시", "취급품목", "상태"]], use_container_width=True, hide_index=True)
            with c2:
                if PLOTLY_AVAILABLE:
                    fig = px.scatter_geo(suppliers_db[region], lat='lat', lon='lon', text='업체명', scope='usa', title=f"{region} 공급처 지도")
                    fig.update_geos(fitbounds="locations")
                    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300)
                    st.plotly_chart(fig, use_container_width=True)

# 라우팅
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_dashboard()
elif st.session_state.current_menu == "B2B 백홀 화물 운송 (3PL)":
    view_3pl_freight()
elif st.session_state.current_menu == "시장가 비교 & 수익성 분석":
    view_market_comparison()
elif st.session_state.current_menu == "로컬 파트너 검색":
    view_local_partners()
elif st.session_state.current_menu == "데이터 통합 관리":
    render_official_header()
    st.data_editor(df_orders, use_container_width=True)
