import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import re

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
            NJ Headquarters & GA Logistics Hub Optimization
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 데이터 로드 로직 (정규식 기반 컬럼 매칭)
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
        new_cols = []
        for col in df.columns:
            clean_col = str(col).strip().lower()
            clean_col = re.sub(r'[^a-z0-9_]+', '_', clean_col).strip('_')
            new_cols.append(clean_col)
        df.columns = new_cols
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
# 3. 사이드바 및 공유 기능 (QR & Link)
# ==========================================
if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "통합 주문 현황"

st.sidebar.markdown("""
<h2 style="margin: 0; font-weight: 900; color: #E31837;">GIANT FOOD</h2>
<p style="font-size: 0.8rem; font-weight: 600;">HQ: NJ | Hub: GA</p>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 메뉴 버튼들
all_menus = ["통합 주문 현황", "수요자(Customer) 포털", "백홀 파트너(단순물류이송)", "공급자 파트너 서치", "데이터 통합 관리", "시스템 도움말"]
for menu in all_menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

st.sidebar.markdown("---")
if st.sidebar.button("🔄 데이터 새로고침", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# --- 공유 섹션 (QR 코드 및 링크) ---
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.markdown("### 🔗 시스템 공유하기")

# [중요] 실제 배포된 URL로 수정하세요.
app_url = "https://giant-backhaul.streamlit.app" 
qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={app_url}"

st.sidebar.image(qr_url, caption="QR 코드를 스캔하여 접속", width=150)
st.sidebar.markdown(f"**접속 링크:**")
st.sidebar.code(app_url, language=None)
st.sidebar.caption("위 링크를 복사하여 담당자에게 전달하세요.")

# ==========================================
# 4. 시각화 및 화면 로직
# ==========================================
def render_network_map():
    if not PLOTLY_AVAILABLE:
        st.warning("지도 라이브러리 미설치")
        return
    hubs = {
        'NJ (Headquarters)': [40.7128, -74.0060],
        'GA (Logistics Hub)': [33.7490, -84.3880],
        'TX (Regional Hub)': [29.7604, -95.3698],
        'FL (Regional Hub)': [25.7617, -80.1918],
        'NC/SC (Regional Hub)': [35.2271, -80.8431]
    }
    fig = go.Figure()
    hub_lat, hub_lon = hubs['GA (Logistics Hub)']
    
    for name, coord in hubs.items():
        if 'GA' not in name:
            line_color = '#E31837' if 'NJ' in name else '#94a3b8' 
            fig.add_trace(go.Scattergeo(locationmode='USA-states', lon=[hub_lon, coord[1]], lat=[hub_lat, coord[0]], mode='lines', line=dict(width=1.2, color=line_color), opacity=0.7))
    
    processed_names = [f"<b>{n.split(' (')[0]}</b><br><span style='font-size: 10px; color: #475569;'>{n.split(' (')[1].replace(')', '')}</span>" for n in hubs.keys()]
    colors = ['#000000' if 'Headquarters' in n else '#E31837' if 'Hub' in n else '#0F4C81' for n in hubs.keys()]
    
    fig.add_trace(go.Scattergeo(locationmode='USA-states', lon=[v[1] for v in hubs.values()], lat=[v[0] for v in hubs.values()], text=processed_names, mode='markers+text', textposition="top center", textfont=dict(size=14), marker=dict(size=14, color=colors, line=dict(width=2, color='white'))))
    fig.update_layout(geo=dict(scope='usa', projection_type='albers usa', showland=True, landcolor="#f8fafc", subunitcolor="#cbd5e1"), margin=dict(l=0, r=0, t=0, b=0), height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def view_unified_orders():
    render_official_header()
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">총 오더</div><div class="metric-value">{len(df_orders)}건</div></div>', unsafe_allow_html=True)
    with col2: 
        box = df_orders["quantity_box"].sum()
        plt = df_orders["quantity_pallet"].sum()
        st.markdown(f'<div class="metric-card"><div class="metric-label">물량 (Box / PLT)</div><div class="metric-value">{int(box)} / {int(plt)}</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-label">운행 트럭</div><div class="metric-value">{len(df_trucks)}대</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-label">매칭 지수</div><div class="metric-value">Active</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    c1, c2 = st.columns([1.6, 1])
    with c1: render_network_map()
    with c2: 
        st.subheader("📍 지역별 수요 (PLT)")
        if not df_orders.empty:
            summary = df_orders.groupby('region')['quantity_pallet'].sum().reset_index()
            st.dataframe(summary, use_container_width=True, hide_index=True)

def view_customer_portal():
    render_official_header()
    st.subheader("👤 수요자(Customer) 포털")
    st.info("고객사별 공동구매 참여 및 배송 상태를 확인합니다.")
    tab1, tab2 = st.tabs(["주문 추적", "공동구매(Group Buy)"])
    with tab1:
        st.dataframe(df_orders, use_container_width=True)
    with tab2:
        st.success("대량 공동구매 건: CJ 비비고 만두 (진행률 85%)")

def view_backhaul_matching():
    render_official_header()
    st.subheader("🤝 백홀 파트너(단순물류이송)")
    st.markdown("""
    <div class="supplier-card"><b>🥩 Highland Meats (TX)</b><br>조지아 허브행 냉장 소고기 이송 가능</div>
    <div class="supplier-card"><b>🏢 NJ HQ Internal</b><br>본사 -> 조지아 허브 재고 보충 물량</div>
    """, unsafe_allow_html=True)

def view_data_management():
    render_official_header()
    st.subheader("⚙️ 데이터 통합 관리")
    st.data_editor(df_orders, use_container_width=True, num_rows="dynamic")

def view_supplier_search():
    render_official_header()
    st.subheader("🔍 주요 거점 파트너 정보")
    st.info("NJ(HQ), GA(Hub), TX, FL, NC/SC 지역별 파트너 리스트")

# 메인 라우팅
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "수요자(Customer) 포털":
    view_customer_portal()
elif st.session_state.current_menu == "백홀 파트너(단순물류이송)":
    view_backhaul_matching()
elif st.session_state.current_menu == "공급자 파트너 서치":
    view_supplier_search()
elif st.session_state.current_menu == "데이터 통합 관리":
    view_data_management()
elif st.session_state.current_menu == "시스템 도움말":
    st.write("도움말 정보")
