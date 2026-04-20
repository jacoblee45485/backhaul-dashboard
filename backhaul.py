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
            NJ Headquarters & GA Logistics Hub Optimization
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 강화된 데이터 로드 로직 (안정성 강화)
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
<p style="font-size: 0.8rem; font-weight: 600;">Headquarters: NJ | Hub: GA</p>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

if st.sidebar.button("🔄 데이터 강제 새로고침", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
all_menus = ["통합 주문 현황", "백홀 파트너 매칭", "공급자 파트너 서치", "데이터 통합 관리", "시스템 도움말"]
for menu in all_menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

# --- 공유 섹션 ---
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.markdown("---")
backhaul_share_url = "https://giant-backhaul.streamlit.app" 
qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={backhaul_share_url}"
st.sidebar.image(qr_api_url, caption="시스템 접속 QR", width=150)

# ==========================================
# 4. 화면 뷰 로직
# ==========================================

def render_network_map():
    """
    뉴저지 본사(HQ)와 조지아 물류 허브(Hub)를 중심으로 한 전국 네트워크 시각화 (도시명 제외)
    """
    if not PLOTLY_AVAILABLE:
        st.warning("지도 라이브러리(Plotly)를 사용할 수 없습니다.")
        return

    # 주요 거점 좌표 및 주 단위 역할 설정 (도시 이름 제거)
    hubs = {
        'NJ (Headquarters)': [40.7128, -74.0060],
        'GA (Logistics Hub)': [33.7490, -84.3880],
        'TX (Regional Hub)': [29.7604, -95.3698],
        'FL (Regional Hub)': [25.7617, -80.1918],
        'NC/SC (Regional Hub)': [35.2271, -80.8431]
    }
    
    fig = go.Figure()

    # 조지아 허브에서 각 거점으로 이어지는 경로선 추가 (GA Hub 중심 연결)
    hub_lat, hub_lon = hubs['GA (Logistics Hub)']
    for name, coord in hubs.items():
        if 'GA' not in name:
            fig.add_trace(go.Scattergeo(
                locationmode = 'USA-states',
                lon = [hub_lon, coord[1]],
                lat = [hub_lat, coord[0]],
                mode = 'lines',
                line = dict(width = 2, color = '#E31837' if 'NJ' in name else '#cbd5e1'),
                opacity = 0.6,
                hoverinfo = 'none'
            ))

    # 거점 포인트 및 주 이름 라벨 표시
    lats = [v[0] for v in hubs.values()]
    lons = [v[1] for v in hubs.values()]
    # 텍스트가 굵게 보이도록 HTML 태그 적용
    names = [f"<b>{n}</b>" for n in hubs.keys()]
    
    # 역할별 색상 및 크기 구분
    colors = []
    sizes = []
    for n in hubs.keys():
        if 'Headquarters' in n:
            colors.append('#000000') # 본사: 블랙
            sizes.append(18)
        elif 'Logistics Hub' in n:
            colors.append('#E31837') # 허브: 레드
            sizes.append(16)
        else:
            colors.append('#0F4C81') # 일반 거점: 블루
            sizes.append(12)

    fig.add_trace(go.Scattergeo(
        locationmode = 'USA-states',
        lon = lons,
        lat = lats,
        text = names,
        mode = 'markers+text',
        textposition = "top center",
        # font_weight 제거 및 폰트 설정
        textfont = dict(family="sans serif", size=11, color="#0f172a"),
        marker = dict(
            size = sizes,
            color = colors,
            line = dict(width=2, color='white')
        ),
        name = 'Logistics Hubs'
    ))

    fig.update_layout(
        geo = dict(
            scope = 'usa',
            projection_type = 'albers usa',
            showland = True,
            landcolor = "rgb(250, 250, 250)",
            subunitcolor = "rgb(220, 220, 220)",
            countrycolor = "rgb(217, 217, 217)",
            showlakes = True,
            lakecolor = "rgb(255, 255, 255)"
        ),
        margin = dict(l=0, r=0, t=0, b=0),
        height = 500,
        showlegend = False
    )
    st.plotly_chart(fig, use_container_width=True)

def view_unified_orders():
    render_official_header()
    if error_msg: st.error(error_msg)
    
    # 상단 지표 카드
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">총 오더</div><div class="metric-value">{len(df_orders)}건</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-label">총 물량</div><div class="metric-value">{df_orders["quantity"].sum()} PLT</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-label">운행 트럭</div><div class="metric-value">{len(df_trucks)}대</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-label">허브 매칭률</div><div class="metric-value">72%</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 지도와 리스트 병렬 배치
    c1, c2 = st.columns([1.6, 1])
    with c1:
        st.subheader("🌐 NJ 본사 & GA 허브 네트워크 시스템")
        render_network_map()
    with c2:
        st.subheader("📍 지역별 실시간 수요")
        if df_orders.empty:
            st.info("현재 접수된 주문이 없습니다.")
        else:
            region_sum = df_orders.groupby('region')['quantity'].sum().reset_index()
            st.dataframe(region_sum.rename(columns={'region':'지역', 'quantity':'수량(PLT)'}), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("📦 본사(NJ) 긴급 오더 현황")
            nj_orders = df_orders[df_orders['region'].str.contains('NJ|NY', case=False, na=False)]
            if nj_orders.empty:
                st.caption("진행 중인 본사 직할 오더 없음")
            else:
                st.dataframe(nj_orders[['product', 'quantity']].tail(5), use_container_width=True, hide_index=True)

def view_backhaul_matching():
    render_official_header()
    st.subheader("🤝 조지아(GA) 허브 회항 물량 파트너 매칭")
    st.markdown("타 지역 배송 후 조지아 물류 허브로 돌아올 때 실을 수 있는 'Inbound GA Hub' 화물 정보입니다.")
    
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("### 🏟️ 허브 유입 화물 소스 (Hub Inbound)")
        st.markdown("""
        <div class="supplier-card">
            <span class="match-tag high-priority">TX -> GA Hub</span>
            <b>🥩 하이랜드 미트 (Highland Meats)</b><br>
            - 품목: 텍사스산 냉장 소고기 / <b>조지아 허브 입고용</b>
        </div>
        <div class="supplier-card">
            <span class="match-tag" style="background-color: #000000; color: white;">NJ -> GA Hub</span>
            <b>🏢 NJ 본사 재고 이동 (HQ Internal)</b><br>
            - 품목: 본사 직송 수입 식자재 / <b>허브 보충 재고</b>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("### 📉 물류 최적화 분석")
        st.info("뉴저지 본사의 수입 오더와 조지아 허브의 배송 트럭을 매칭하여 '본사-허브' 간 내부 물류 비용을 제로화하는 것이 목표입니다.")

def view_data_management():
    render_official_header()
    st.subheader("⚙️ 데이터 통합 관리 (Interactive Editor)")
    st.markdown("본사(NJ)와 허브(GA)의 데이터를 앱 내에서 통합 관리합니다.")
    
    m_tab1, m_tab2 = st.tabs(["오더/재고 관리", "허브 배차 수정"])
    
    with m_tab1:
        st.write("📝 **실시간 오더 데이터 편집**")
        edited_orders = st.data_editor(df_orders, use_container_width=True, num_rows="dynamic")
            
    with m_tab2:
        st.write("🚛 **조지아 허브 배차 관리**")
        edited_trucks = st.data_editor(df_trucks, use_container_width=True, num_rows="fixed")
        if st.button("허브 배차 승인"):
            st.toast("조지아 물류센터로 승인 신호가 전송되었습니다.")

def view_supplier_search():
    render_official_header()
    st.subheader("🔍 주요 거점 파트너 정보")
    st.info("HQ: NJ | HUB: GA | Regional Hubs: TX, FL, NC/SC")

def view_help():
    render_official_header()
    st.subheader("🛠️ 시스템 구조 안내")
    st.markdown("""
    - **NJ Headquarters**: 시스템의 컨트롤 타워 및 수입 물량 관리
    - **GA Logistics Hub**: 전국 배송의 중심점 및 백홀 매칭 최적화 지점
    - **Regional Hubs**: 텍사스, 플로리다 등 주요 수요처
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
