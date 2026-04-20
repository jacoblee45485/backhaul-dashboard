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
    .info-card {
        background-color: #f8fafc;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }
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
# 2. 강화된 데이터 로드 로직
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
all_menus = [
    "통합 주문 현황", 
    "수요자(Customer) 포털", 
    "백홀 파트너(단순물류이송)", 
    "공급자 파트너 서치", 
    "데이터 통합 관리", 
    "시스템 도움말"
]
for menu in all_menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

# ==========================================
# 4. 화면 뷰 로직
# ==========================================

def render_network_map():
    """
    뉴저지 본사(HQ)와 조지아 물류 허브(Hub)를 중심으로 한 전국 네트워크 시각화
    가독성을 위해 선 두께를 가늘게 조정하고 라벨 폰트 크기 최적화
    """
    if not PLOTLY_AVAILABLE:
        st.warning("지도 라이브러리 사용 불가")
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
    
    # 연결선 렌더링 (가늘고 세련되게 수정: width 3.5 -> 1.2)
    for name, coord in hubs.items():
        if 'GA' not in name:
            line_color = '#E31837' if 'NJ' in name else '#94a3b8' 
            fig.add_trace(go.Scattergeo(
                locationmode='USA-states', 
                lon=[hub_lon, coord[1]], 
                lat=[hub_lat, coord[0]], 
                mode='lines', 
                line=dict(width=1.2, color=line_color), 
                opacity=0.7
            ))
    
    # 거점 라벨링 (지역명은 크게, 역할 설명은 작게 분리)
    processed_names = []
    for n in hubs.keys():
        state_name = n.split(' (')[0]
        role_name = n.split(' (')[1].replace(')', '')
        processed_names.append(f"<b>{state_name}</b><br><span style='font-size: 10px; color: #475569;'>{role_name}</span>")
    
    colors = ['#000000' if 'Headquarters' in n else '#E31837' if 'Hub' in n else '#0F4C81' for n in hubs.keys()]
    
    fig.add_trace(go.Scattergeo(
        locationmode='USA-states', 
        lon=[v[1] for v in hubs.values()], 
        lat=[v[0] for v in hubs.values()], 
        text=processed_names, 
        mode='markers+text', 
        textposition="top center", 
        textfont=dict(size=14, color="#0f172a"),
        marker=dict(
            size=14, 
            color=colors, 
            line=dict(width=2, color='white')
        )
    ))
    
    fig.update_layout(
        geo=dict(
            scope='usa', 
            projection_type='albers usa',
            showland=True,
            landcolor="#f8fafc",
            subunitcolor="#cbd5e1" 
        ), 
        margin=dict(l=0, r=0, t=0, b=0), 
        height=500, 
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

def view_unified_orders():
    render_official_header()
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-label">총 오더</div><div class="metric-value">{len(df_orders)}건</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-label">총 물량</div><div class="metric-value">{df_orders["quantity"].sum()} PLT</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-label">운행 트럭</div><div class="metric-value">{len(df_trucks)}대</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-label">허브 매칭률</div><div class="metric-value">72%</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    c1, c2 = st.columns([1.6, 1])
    with c1:
        st.subheader("🌐 NJ 본사 & GA 허브 네트워크")
        render_network_map()
    with c2:
        st.subheader("📍 지역별 실시간 수요")
        region_sum = df_orders.groupby('region')['quantity'].sum().reset_index()
        st.dataframe(region_sum, use_container_width=True, hide_index=True)

def view_customer_portal():
    render_official_header()
    st.subheader("👤 수요자(Customer) 포털")
    st.markdown("고객사별 주문 상태 및 공동구매 참여 현황을 관리합니다.")

    # 고객 요약 지표
    c1, c2, c3 = st.columns(3)
    with c1:
        active_customers = df_clients[df_clients['type'] != 'Backhaul_Partner'].shape[0]
        st.markdown(f'<div class="metric-card"><div class="metric-label">활성 고객사</div><div class="metric-value">{active_customers}개</div></div>', unsafe_allow_html=True)
    with c2:
        pending_orders = df_orders.shape[0]
        st.markdown(f'<div class="metric-card"><div class="metric-label">진행 중인 주문</div><div class="metric-value">{pending_orders}건</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">평균 배송 리드타임</div><div class="metric-value">2.4일</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 주문 추적", "🤝 공동구매(Group Buy) 현황"])
    
    with tab1:
        st.write("### 🔍 고객사별 주문 조회")
        search_term = st.text_input("고객사 이름 또는 ID 입력")
        if not df_orders.empty and not df_clients.empty:
            merged = pd.merge(df_orders, df_clients, on='client_id', how='left')
            if search_term:
                merged = merged[merged['name'].str.contains(search_term, case=False, na=False)]
            st.dataframe(merged[['order_id', 'name', 'product', 'quantity', 'region']], use_container_width=True, hide_index=True)
        else:
            st.info("조회할 주문 데이터가 없습니다.")

    with tab2:
        st.write("### 📢 공동구매 진행 상태")
        st.info("최소 주문 수량(MOQ) 충족 시 조지아 허브에서 일괄 발송됩니다.")
        
        gb_items = [
            {"품목": "CJ 비비고 만두 (Pallet)", "지역": "TX", "참여도": 0.85, "잔여": "3 PLT"},
            {"품목": "신라면 컵 (Bulk)", "지역": "FL", "참여도": 0.40, "잔여": "12 PLT"},
            {"품목": "청정원 고추장", "지역": "NC", "참여도": 1.0, "잔여": "완료"}
        ]
        
        for item in gb_items:
            with st.expander(f"{item['품목']} ({item['지역']})"):
                st.write(f"현재 모집 상태: **{int(item['참여도']*100)}%**")
                st.progress(item['참여도'])
                if item['잔여'] == "완료":
                    st.success("🎉 공동구매 확정! 조지아 허브에서 배차 대기 중")
                else:
                    st.warning(f"💡 {item['잔여']}만 더 모이면 최저가 운송이 가능합니다.")

def view_backhaul_matching():
    render_official_header()
    st.subheader("🤝 조지아(GA) 허브 회항 물량 파트너(단순물류이송)")
    st.markdown("타 지역 배송 후 조지아 물류 허브로 돌아올 때 실을 수 있는 'Inbound GA Hub' 화물 정보입니다.")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("### 🏟️ 허브 유입 화물 소스")
        st.markdown("""
        <div class="supplier-card"><span class="match-tag high-priority">TX -> GA Hub</span><b>🥩 하이랜드 미트</b><br>- 텍사스산 냉장 소고기 / 조지아 허브 입고용</div>
        <div class="supplier-card"><span class="match-tag" style="background-color: #000000; color: white;">NJ -> GA Hub</span><b>🏢 NJ 본사 재고 이동</b><br>- 본사 직송 수입 식자재 / 허브 보충 재고</div>
        """, unsafe_allow_html=True)
    with col_b:
        st.info("뉴저지 본사의 수입 오더와 조지아 허브의 배송 트럭을 매칭하여 내부 물류 비용을 제로화합니다.")

def view_data_management():
    render_official_header()
    st.subheader("⚙️ 데이터 통합 관리")
    st.data_editor(df_orders, use_container_width=True, num_rows="dynamic")

def view_supplier_search():
    render_official_header()
    st.subheader("🔍 주요 거점 파트너 정보")
    st.info("HQ: NJ | HUB: GA | Regional Hubs: TX, FL, NC/SC")

def view_help():
    render_official_header()
    st.subheader("🛠️ 시스템 구조")
    st.markdown("- **수요자 포털**: 고객사들의 주문 추적 및 공동구매 혜택 관리\n- **GA Hub**: 전국 배송 및 백홀 매칭의 중심")

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
    view_help()
