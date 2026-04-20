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

# 커스텀 CSS (메트릭 카드 및 레이아웃 스타일)
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
    .stAlert { margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

def render_official_header():
    st.markdown("""
    <div style="background-color: #f8fafc; padding: 40px 20px; border-radius: 15px; border: 2px solid #e2e8f0; margin-bottom: 30px; text-align: center;">
        <h1 style="margin: 0; font-size: 4rem; font-weight: 900; letter-spacing: -2px; line-height: 1.1;">
            <span style="color: #E31837;">GIANT</span> <span style="color: #000000;">FOODSYSTEM</span>
        </h1>
        <p style="font-size: 1.4rem; font-weight: 700; color: #475569; margin: 15px 0 5px 0;">#1 K-food Distributor in USA</p>
        <p style="font-size: 1.1rem; font-weight: 500; color: #64748b; margin: 0; line-height: 1.4;">
            A nationwide food distributor serving for Korean Restaurants,<br>
            Deli & Salad Bars since 1986
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 강화된 데이터 로드 로직 (400 에러 방지)
# ==========================================

@st.cache_data(ttl=60)
def fetch_gsheet_data(sheet_url, worksheet_name):
    """
    구글 시트 라이브러리가 실패할 경우를 대비한 하이브리드 로더
    """
    try:
        # 방식 1: 전용 커넥션 시도
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(spreadsheet=sheet_url, worksheet=worksheet_name)
    except Exception as e:
        # 방식 2: Pandas를 이용한 직접 CSV 내보내기 링크 시도 (400 에러 우회용)
        try:
            # 주소에서 ID 추출
            if "/d/" in sheet_url:
                sheet_id = sheet_url.split("/d/")[1].split("/")[0]
                # 탭 이름으로 CSV 다운로드 링크 생성
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(worksheet_name)}"
                return pd.read_csv(csv_url)
            else:
                raise ValueError("올바르지 않은 시트 주소 형식입니다.")
        except Exception as e2:
            st.error(f"'{worksheet_name}' 탭을 읽어오지 못했습니다. (에러: {e2})")
            return pd.DataFrame()

def load_all_data():
    # Secrets에서 주소 가져오기
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "Secrets에 'spreadsheet' 주소가 설정되지 않았습니다."

    clients = fetch_gsheet_data(sheet_url, "Clients")
    orders = fetch_gsheet_data(sheet_url, "Orders")
    trucks = fetch_gsheet_data(sheet_url, "Trucks")
    
    if clients.empty and orders.empty and trucks.empty:
        return clients, orders, trucks, "모든 데이터를 불러오는 데 실패했습니다. 시트 권한과 탭 이름을 확인하세요."
    
    return clients, orders, trucks, None

df_clients, df_orders, df_trucks, error_msg = load_all_data()

# 데이터 기본 구조 보장 (에러 시에도 앱이 깨지지 않게 방어)
if df_clients.empty: df_clients = pd.DataFrame(columns=["client_id", "name", "type"])
if df_orders.empty: df_orders = pd.DataFrame(columns=["order_id", "client_id", "region", "product", "quantity"])
if df_trucks.empty: df_trucks = pd.DataFrame(columns=["truck_id", "region", "return_day", "capacity", "assigned"])

# ==========================================
# 3. 사이드바 및 레이아웃
# ==========================================
if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "통합 주문 현황"

st.sidebar.markdown("""
<h2 style="margin: 0; font-weight: 900;">
    <span style="color: #E31837;">GIANT</span> <span style="color: #000000;">FOOD</span>
</h2>
<p style="font-size: 0.85rem; color: #64748b; font-weight: 600;">Backhaul Management System</p>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

if st.sidebar.button("🔄 실시간 데이터 업데이트", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
all_menus = ["통합 주문 현황", "공동구매 전용 관리", "트럭 배차 현황", "시스템 도움말"]
for menu in all_menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

# --- 공유 섹션 ---
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.markdown("---")
backhaul_share_url = "https://giant-backhaul.streamlit.app" 
qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={backhaul_share_url}"
st.sidebar.image(qr_api_url, caption="시스템 접속 QR", width=150)
st.sidebar.caption("본 주소는 대표님의 실제 배포 URL로 변경해 주세요.")

# ==========================================
# 4. 화면 뷰 로직
# ==========================================

def render_network_map():
    if not PLOTLY_AVAILABLE:
        st.warning("지도 라이브러리 사용 불가")
        return
    hubs = {'GA (Main)': [33.7490, -84.3880], 'NJ (Hub)': [40.7128, -74.0060], 'TX': [29.7604, -95.3698], 'FL': [25.7617, -80.1918]}
    fig = go.Figure(go.Scattergeo(locationmode='USA-states', lat=[v[0] for v in hubs.values()], lon=[v[1] for v in hubs.values()], text=list(hubs.keys()), mode='markers+text', marker=dict(size=12, color='#E31837')))
    fig.update_layout(geo=dict(scope='usa'), margin=dict(l=0, r=0, t=0, b=0), height=350)
    st.plotly_chart(fig, use_container_width=True)

def view_unified_orders():
    render_official_header()
    if error_msg:
        st.error(f"연결 상태 확인 필요: {error_msg}")
        st.info("💡 해결 방법: 구글 시트 우측 상단 '공유' -> '링크가 있는 모든 사용자'로 설정을 꼭 확인해 주세요.")
    
    # 지표 요약
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">총 주문</div><div class="metric-value">{len(df_orders)}건</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-label">총 물량</div><div class="metric-value">{df_orders["quantity"].sum() if not df_orders.empty else 0} PLT</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-label">대기 차량</div><div class="metric-value">{len(df_trucks)}대</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-label">네트워크 상태</div><div class="metric-value">Active</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.subheader("🌐 Logistics Network")
        render_network_map()
    with c2:
        st.subheader("📋 실시간 오더 현황")
        if df_orders.empty:
            st.warning("연결된 주문 데이터가 없습니다.")
        else:
            st.dataframe(df_orders[['client_id', 'product', 'quantity']], use_container_width=True, hide_index=True)

def view_help():
    render_official_header()
    st.subheader("🛠️ 연결 문제 해결 가이드 (HTTP 400 대응)")
    st.markdown("""
    ### 1. 구글 시트 공유 설정 확인 (필수)
    구글 시트 우측 상단 **[공유]** 버튼을 누른 후, 하단의 일반 액세스를 반드시 **'링크가 있는 모든 사용자'**로 변경해야 합니다. **'제한됨'** 상태이면 어떤 주소를 넣어도 400 에러가 발생합니다.
    
    ### 2. Secrets 주소 다시 확인
    아래 주소 형식을 권장합니다:
    ```text
    [https://docs.google.com/spreadsheets/d/15MPyXcHcv93E4f1qeswewTWfDensVDp2EZxLHwOLvAU/edit](https://docs.google.com/spreadsheets/d/15MPyXcHcv93E4f1qeswewTWfDensVDp2EZxLHwOLvAU/edit)
    ```
    
    ### 3. 탭 이름 일치 확인
    구글 시트 하단 탭 이름이 아래와 정확히 일치하는지 확인하세요 (대소문자 구분):
    - **Clients**
    - **Orders**
    - **Trucks**
    """)

# 라우팅
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "시스템 도움말":
    view_help()
else:
    st.title(st.session_state.current_menu)
    st.info("데이터 연결 후 상세 내용이 활성화됩니다.")
