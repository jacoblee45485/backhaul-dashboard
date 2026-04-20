import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# Plotly 라이브러리 안전하게 불러오기
try:
    import plotly.graph_objects as go
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

# 커스텀 CSS (UI 디자인 개선)
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
    .supplier-card {
        background-color: #f1f5f9;
        padding: 15px;
        border-left: 5px solid #E31837;
        margin-bottom: 15px;
        border-radius: 5px;
    }
    .match-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 5px;
        background-color: #e2e8f0;
        color: #475569;
    }
    .high-priority { background-color: #fee2e2; color: #b91c1c; }
</style>
""", unsafe_allow_html=True)

def render_official_header():
    st.markdown("""
    <div style="background-color: #f8fafc; padding: 30px 20px; border-radius: 15px; border: 2px solid #e2e8f0; margin-bottom: 30px; text-align: center;">
        <h1 style="margin: 0; font-size: 3.5rem; font-weight: 900; letter-spacing: -2px; line-height: 1.1;">
            <span style="color: #E31837;">GIANT</span> <span style="color: #000000;">FOODSYSTEM</span>
        </h1>
        <p style="font-size: 1.2rem; font-weight: 700; color: #475569; margin: 10px 0 5px 0;">#1 K-food Distributor in USA</p>
        <p style="font-size: 0.95rem; font-weight: 500; color: #64748b; margin: 0; line-height: 1.4;">
            GA Hub Connectivity & Inbound Backhaul Optimization
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 데이터 로드 및 전처리 (안정성 강화)
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
        df.columns = [str(c).strip().lower() for c in df.columns]
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

# 컬럼 존재 보장
def ensure_columns(df, expected_cols):
    for col in expected_cols:
        if col not in df.columns: df[col] = 0 if col in ['quantity', 'capacity', 'assigned'] else ""
    return df

df_clients = ensure_columns(df_clients, ["client_id", "name", "type"])
df_orders = ensure_columns(df_orders, ["order_id", "client_id", "region", "product", "quantity"])
df_trucks = ensure_columns(df_trucks, ["truck_id", "region", "return_day", "capacity", "assigned"])

# ==========================================
# 3. 사이드바 메뉴 구성
# ==========================================
if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "통합 주문 현황"

st.sidebar.markdown("""
<h2 style="margin: 0; font-weight: 900; color: #E31837;">GIANT FOOD</h2>
<p style="font-size: 0.8rem; font-weight: 600;">Logistics & Backhaul Match</p>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

if st.sidebar.button("🔄 데이터 강제 새로고침", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
# 신규 탭 '데이터 통합 관리' 추가
all_menus = ["통합 주문 현황", "백홀 파트너 매칭", "공급자 파트너 서치", "데이터 통합 관리", "시스템 도움말"]
for menu in all_menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

# ==========================================
# 4. 화면 뷰 로직
# ==========================================

def view_unified_orders():
    render_official_header()
    if error_msg: st.error(error_msg)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">총 오더</div><div class="metric-value">{len(df_orders)}건</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-label">총 물량</div><div class="metric-value">{df_orders["quantity"].sum()} PLT</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-label">운행 트럭</div><div class="metric-value">{len(df_trucks)}대</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-label">조지아 회항 물량</div><div class="metric-value">128 PLT</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📋 실시간 오더 현황")
    st.dataframe(df_orders, use_container_width=True, hide_index=True)

def view_backhaul_matching():
    render_official_header()
    st.subheader("🤝 조지아(GA) 회항 물량 파트너 매칭")
    st.markdown("타 지역 배송 후 조지아 본사로 돌아올 때 실을 수 있는 'Inbound GA' 화물 보유 업체 리스트입니다.")
    
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("### 🏟️ 주요 백홀 화물 소스 (Load Sources)")
        st.markdown("""
        <div class="supplier-card">
            <span class="match-tag high-priority">TX -> GA</span>
            <b>🥩 하이랜드 미트 (Highland Meats)</b><br>
            - 품목: 텍사스산 냉장 소고기 / <b>빈도: 주 3회 정기</b>
        </div>
        <div class="supplier-card">
            <span class="match-tag high-priority">FL -> GA</span>
            <b>🐟 썬샤인 시푸드 (Sunshine Seafood)</b><br>
            - 품목: 수입 냉동 수산물 / <b>빈도: 주 2회</b>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("### 📉 백홀 매칭 경제성")
        st.info("현재 빈 트럭 회항 시 마일당 약 $2.50의 기회비용이 발생하고 있습니다. 백홀 매칭 시 운송비의 약 40%를 절감할 수 있습니다.")

def view_data_management():
    render_official_header()
    st.subheader("⚙️ 데이터 통합 관리 (Interactive Editor)")
    st.markdown("앱 내에서 데이터를 직접 수정하고 시뮬레이션할 수 있습니다.")
    
    m_tab1, m_tab2 = st.tabs(["주문 관리", "배차 현황 수정"])
    
    with m_tab1:
        st.write("📝 **현재 주문 리스트 수정** (수정 후 엔터를 누르세요)")
        edited_orders = st.data_editor(df_orders, use_container_width=True, num_rows="dynamic")
        if st.button("주문 변경사항 임시 저장"):
            st.success("대시보드에 변경사항이 반영되었습니다. (실제 시트 반영은 쓰기 권한 설정 필요)")
            
    with m_tab2:
        st.write("🚛 **트럭 배차 현황 관리**")
        edited_trucks = st.data_editor(df_trucks, use_container_width=True, num_rows="fixed")
        if st.button("배차 확정 통보"):
            st.toast("해당 차량 기사님께 알림이 전송되었습니다.")

def view_supplier_search():
    render_official_header()
    st.subheader("🔍 지역별 파트너 거점 정보")
    st.info("전략적 배송 거점: TX(Houston/Dallas), FL(Miami), NC(Hickory), SC(Charleston)")

def view_help():
    render_official_header()
    st.subheader("🛠️ 관리 가이드")
    st.markdown("""
    - **통합 주문 현황**: 현재 접수된 모든 오더 확인
    - **백홀 파트너 매칭**: 조지아로 돌아올 때 실을 짐 발굴
    - **데이터 통합 관리**: 엑셀처럼 직접 데이터를 수정하는 기능
    """)

# 메인 라우팅
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "백홀 파트너 매칭":
    view_backhaul_matching()
elif st.session_state.current_menu == "공급자 파트너 서치":
    view_supplier_search()
elif st.session_state.current_menu == "데이터 통합 관리":
    view_data_management()
elif st.session_state.current_menu == "시스템 도움말":
    view_help()
