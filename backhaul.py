import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Plotly 라이브러리 안전하게 불러오기 (미국 지도 시각화용)
# Plotly ñanduti rembipyahu ñongatu porã
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ==========================================
# 1. 페이지 설정 및 회사 공식 스타일 적용
# ==========================================
# 1. Tenda mohenda ha mba'apohára reko
st.set_page_config(
    page_title="GIANT FOODSYSTEM - 백홀 관리 시스템", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (메트릭 카드 및 레이아웃 스타일)
# CSS teete (Mba'e rechaukaha ha tenda mohenda)
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
</style>
""", unsafe_allow_html=True)

# 회사 공식 타이틀과 상세 설명이 포함된 헤더 렌더링 함수
# Akã guasu rembiapo (Giant Foodsystem mba'e rechaukaha)
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

# 구글 시트 연결 설정
# Google kuatiañe'ẽ ñembojoaju
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("라이브러리 연결 오류가 발생했습니다. GitHub의 requirements.txt 설정을 확인해주세요.")

# 데이터 불러오기 함수 (캐시 적용)
# Marandu mbyaty rembiapo (Cache ndive)
@st.cache_data(ttl=60)
def load_data():
    try:
        clients = conn.read(worksheet="Clients")
        orders = conn.read(worksheet="Orders")
        trucks = conn.read(worksheet="Trucks")
        return clients, orders, trucks
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_clients, df_orders, df_trucks = load_data()

# 데이터 기본 구조 보장
# Marandu reko ñemohenda
if df_clients.empty:
    df_clients = pd.DataFrame(columns=["client_id", "name", "type"])
if df_orders.empty:
    df_orders = pd.DataFrame(columns=["order_id", "client_id", "region", "product", "quantity"])
if df_trucks.empty:
    df_trucks = pd.DataFrame(columns=["truck_id", "region", "return_day", "capacity", "assigned"])

# 메뉴 상태 관리
# Tembipuru ñangareko
if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "통합 주문 현황"

# ==========================================
# 2. 시각화 요소: 미국 네트워크 지도 (Plotly)
# ==========================================
# 2. EE.UU. mapa rechaukaha (Plotly)
def render_network_map():
    if not PLOTLY_AVAILABLE:
        st.warning("지도 라이브러리(Plotly)가 설치되지 않았습니다. 도움말 메뉴를 확인하여 라이브러리를 설치하세요.")
        return

    hubs = {
        'GA (Main)': [33.7490, -84.3880],
        'NJ (Hub)': [40.7128, -74.0060],
        'TX (Region)': [29.7604, -95.3698],
        'FL (Region)': [25.7617, -80.1918],
        'NC/SC (Region)': [35.2271, -80.8431]
    }
    
    fig = go.Figure()

    for name, coord in hubs.items():
        if name != 'GA (Main)':
            fig.add_trace(go.Scattergeo(
                locationmode = 'USA-states',
                lon = [hubs['GA (Main)'][1], coord[1]],
                lat = [hubs['GA (Main)'][0], coord[0]],
                mode = 'markers+lines',
                line = dict(width = 2, color = '#cbd5e1'),
                opacity = 0.6,
                hoverinfo = 'none'
            ))

    lats = [v[0] for v in hubs.values()]
    lons = [v[1] for v in hubs.values()]
    names = list(hubs.keys())
    colors = ['#E31837' if 'GA' in n or 'NJ' in n else '#0F4C81' for n in names]
    sizes = [15 if 'GA' in n or 'NJ' in n else 10 for n in names]

    fig.add_trace(go.Scattergeo(
        locationmode = 'USA-states',
        lon = lons,
        lat = lats,
        text = names,
        mode = 'markers+text',
        textposition = "top center",
        marker = dict(size = sizes, color = colors, line = dict(width=2, color='white')),
        name = 'Logistics Hubs'
    ))

    fig.update_layout(
        geo = dict(
            scope = 'usa',
            projection_type = 'albers usa',
            showland = True,
            landcolor = "rgb(250, 250, 250)",
            subunitcolor = "rgb(217, 217, 217)",
            countrycolor = "rgb(217, 217, 217)",
        ),
        margin = dict(l=0, r=0, t=0, b=0),
        height = 380,
        showlegend = False
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 3. 사이드바 구성
# ==========================================
# 3. Yke pegua ñemohenda
st.sidebar.markdown("""
<h2 style="margin: 0; font-weight: 900;">
    <span style="color: #E31837;">GIANT</span> <span style="color: #000000;">FOOD</span>
</h2>
<p style="font-size: 0.85rem; color: #64748b; font-weight: 600;">Backhaul Management System</p>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

all_menus = ["통합 주문 현황", "공동구매 전용 관리", "트럭 배차 현황", "시스템 도움말"]
for menu in all_menus:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

# --- [사이드바 하단 공유 섹션] ---
# Yke pegua pehẽngue (QR ha link)
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 시스템 공유하기")

# [중요] 배포 완료 후 브라우저 주소창의 실제 URL로 이 부분을 바꿔주세요!
# Tenda mohenda URL tee
backhaul_share_url = "https://backhaul-dashboard-f8gdhjdyappm23kcj6hli87.streamlit.app/" 

# QR 코드 생성 (QR Server API 사용)
qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={backhaul_share_url}"

st.sidebar.image(qr_api_url, caption="QR 코드를 스캔하세요", use_column_width=False, width=150)
st.sidebar.markdown(f"**[접속 링크 복사]**")
st.sidebar.code(backhaul_share_url, language=None)
st.sidebar.caption("⚠️ 접속 오류 시 '시스템 도움말'을 확인하세요.")


# ==========================================
# 4. 화면 뷰 1: 통합 주문 현황
# ==========================================
# 4. Tenda rechaukaha 1: Marandu mbyaty
def view_unified_orders():
    render_official_header()
    
    total_orders = len(df_orders)
    total_pallets = df_orders['quantity'].sum() if not df_orders.empty else 0
    pending_trucks = len(df_trucks[df_trucks['assigned'] == 0])
    match_rate = int((1 - pending_trucks/max(len(df_trucks),1))*100)
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">총 주문 건수</div><div class="metric-value">{total_orders}건</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">전체 수요 용량</div><div class="metric-value">{total_pallets} PLT</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">배차 대기 트럭</div><div class="metric-value">{pending_trucks}대</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">백홀 매칭률</div><div class="metric-value">{match_rate}%</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    
    col_map, col_list = st.columns([1.6, 1])
    with col_map:
        st.subheader("🌐 Logistics Network (GA - NJ Hub)")
        render_network_map()
    with col_list:
        st.subheader("📍 지역별 수요 집계")
        if df_orders.empty:
            st.info("접수된 주문 데이터가 아직 없습니다.")
        else:
            df_merged = pd.merge(df_orders, df_clients, on="client_id", how="left")
            summary = df_merged.groupby('region')['quantity'].sum().reset_index()
            st.dataframe(summary.rename(columns={'region':'지역', 'quantity':'총 수량(PLT)'}), use_container_width=True, hide_index=True)

    st.markdown("---")
    regions = ["TX", "FL", "NC_SC"]
    for region in regions:
        with st.expander(f"📦 {region} 지역 상세 오더 리스트", expanded=(region=="TX")):
            if not df_orders.empty:
                df_merged = pd.merge(df_orders, df_clients, on="client_id", how="left")
                region_data = df_merged[df_merged['region'] == region]
                if region_data.empty:
                    st.write("진행 중인 오더 없음")
                else:
                    st.table(region_data[['name', 'product', 'quantity']].rename(columns={'name':'업체명', 'product':'품목', 'quantity':'수량'}))
            else:
                st.write("데이터 없음")

# ==========================================
# 5. 화면 뷰 2: 공동구매 전용 관리
# ==========================================
# 5. Tenda rechaukaha 2: Ñemumu Joaju
def view_group_buy():
    render_official_header()
    st.subheader("🤝 공동구매 전용 관리 (Group Buy Progress)")
    
    if df_orders.empty:
        st.info("진행 중인 주문이 없습니다.")
        return

    df_merged = pd.merge(df_orders, df_clients, on="client_id", how="left")
    gb_data = df_merged[df_merged['type'] == 'GroupBuy']
    
    if gb_data.empty:
        st.info("현재 진행 중인 공동구매가 없습니다.")
        return

    deals = gb_data.groupby(['region', 'product'])['quantity'].sum().reset_index()
    TARGET_CAPACITY = 20
    
    cols = st.columns(2)
    for i, (_, row) in enumerate(deals.iterrows()):
        with cols[i % 2]:
            st.markdown(f"#### {row['region']} - {row['product']}")
            progress = min(row['quantity'] / TARGET_CAPACITY, 1.0)
            st.progress(progress)
            st.write(f"모집 현황: **{row['quantity']}** / {TARGET_CAPACITY} PLT ({int(progress*100)}%)")

# ==========================================
# 6. 화면 뷰 3: 트럭 배차 현황
# ==========================================
# 6. Tenda rechaukaha 3: Camion ñemohenda
def view_truck_dispatch():
    render_official_header()
    st.subheader("🚚 트럭 배차 현황 (Backhaul Dispatch)")
    
    days_map = {"화": "NC_SC", "수": "TX", "금": "FL"}
    cols = st.columns(3)
    
    for i, (day, region) in enumerate(days_map.items()):
        with cols[i]:
            if day == "화": st.error(f"### {day}요일 ({region})")
            elif day == "수": st.warning(f"### {day}요일 ({region})")
            else: st.success(f"### {day}요일 ({region})")
            
            day_trucks = df_trucks[df_trucks['return_day'] == day]
            if day_trucks.empty:
                st.caption("해당 요일 운행 트럭 정보 없음")
            else:
                for _, truck in day_trucks.iterrows():
                    try: is_assigned = int(truck['assigned']) == 1
                    except: is_assigned = False
                    
                    status = "✅ 상차 완료" if is_assigned else "🔲 배차 대기"
                    st.markdown(f"**{truck['truck_id']}** ({truck['capacity']} PLT)")
                    st.caption(status)
                    if not is_assigned:
                        st.button(f"{truck['truck_id']} 배차 확정", key=f"d_btn_{truck['truck_id']}")

# ==========================================
# 7. 화면 뷰 4: 배포 가이드 및 도움말 (Help & Deployment)
# ==========================================
# 7. Pytyvõ ha Ñemohenda tape
def view_help():
    render_official_header()
    st.subheader("❓ 큐알코드 접속 오류 해결 방법")
    
    st.error("### 🚫 'You do not have access' 오류 발생 시")
    st.markdown("""
    1. **앱 공개 범위 확인:** Streamlit Cloud 대시보드에서 해당 앱의 설정(Settings) 중 **'App sharing'**이 **Public**으로 되어 있는지 확인하세요.
    2. **URL 일치 여부:** 현재 브라우저 주소창에 떠 있는 주소를 복사하여 코드의 `backhaul_share_url` 변수에 정확히 붙여넣어야 합니다. 
       (현재 설정된 `giant-backhaul.streamlit.app`은 예시 주소이므로 본인의 주소로 바꿔야 합니다.)
    3. **저장(Commit) 필수:** 코드를 수정한 후 GitHub에서 반드시 **Commit**을 눌러야 실제 앱에 반영됩니다.
    """)
    
    st.info("### 🔗 구글 시트 연결 (Secrets)")
    st.markdown("""
    1. **Streamlit Settings** -> **Secrets** 클릭
    2. 아래 형식으로 입력 (URL은 본인 시트 주소로 교체):
    ```toml
    [connections.gsheets]
    spreadsheet = "[https://docs.google.com/spreadsheets/d/본인_시트_아이디/edit#gid=0](https://docs.google.com/spreadsheets/d/본인_시트_아이디/edit#gid=0)"
    ```
    """)

# 메인 라우팅
# Tape mohenda tee
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "공동구매 전용 관리":
    view_group_buy()
elif st.session_state.current_menu == "트럭 배차 현황":
    view_truck_dispatch()
elif st.session_state.current_menu == "시스템 도움말":
    view_help()
