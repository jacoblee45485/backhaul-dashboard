import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 페이지 설정 및 회사 공식 스타일 적용
# ==========================================
st.set_page_config(
    page_title="GIANT FOODSYSTEM - 백홀 관리 시스템", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# [스타일] 트럭 대시보드에서 사용하던 CSS 스타일 이식
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .logo-container {
        background-color: #f8fafc; 
        padding: 20px; 
        border-radius: 12px; 
        text-align: center; 
        border: 1px solid #e2e8f0; 
        margin-bottom: 25px;
    }
    .logo-text-giant { color: #E31837; font-weight: 900; }
    .logo-text-food { color: #000000; font-weight: 900; }
    .tagline { font-size: 1.08rem; font-weight: 600; color: #475569; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# 공용 로고 렌더링 함수
def render_official_logo():
    st.markdown("""
    <div class="logo-container">
        <h1 style="margin: 0; font-size: 3.2rem; font-weight: 900; letter-spacing: -1px;">
            <span class="logo-text-giant">GIANT</span> <span class="logo-text-food">FOODSYSTEM</span>
        </h1>
        <p class="tagline">#1 K-food Distributor in USA</p>
    </div>
    """, unsafe_allow_html=True)

# 구글 시트 연결 설정
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("라이브러리 연결 오류가 발생했습니다. GitHub의 requirements.txt 설정을 확인해주세요.")

# 데이터 불러오기 함수 (캐시 적용)
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
if df_clients.empty:
    df_clients = pd.DataFrame(columns=["client_id", "name", "type"])
if df_orders.empty:
    df_orders = pd.DataFrame(columns=["order_id", "client_id", "region", "product", "quantity"])
if df_trucks.empty:
    df_trucks = pd.DataFrame(columns=["truck_id", "region", "return_day", "capacity", "assigned"])

# 메뉴 상태 관리
if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "통합 주문 현황"
if 'pinned_menus' not in st.session_state:
    st.session_state.pinned_menus = ["통합 주문 현황"]

# ==========================================
# 2. 사이드바 (공식 타이틀 및 메뉴)
# ==========================================
def toggle_pin(menu_name):
    if menu_name in st.session_state.pinned_menus:
        st.session_state.pinned_menus.remove(menu_name)
    else:
        st.session_state.pinned_menus.append(menu_name)

def change_menu(menu_name):
    st.session_state.current_menu = menu_name

all_menus = ["통합 주문 현황", "공동구매 전용 관리", "트럭 배차 현황", "시스템 도움말"]

# 사이드바 상단 타이틀
st.sidebar.markdown("""
<h2 style="margin: 0; font-weight: 900;">
    <span style="color: #E31837;">GIANT</span> <span style="color: #000000;">FOOD</span>
</h2>
<p style="font-size: 0.85rem; color: #64748b; font-weight: 600;">Backhaul Management System</p>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 고정된 메뉴
st.sidebar.subheader("📌 바로가기")
for menu in all_menus:
    if menu in st.session_state.pinned_menus:
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(menu, key=f"pinned_{menu}", use_container_width=True):
                change_menu(menu)
        with col2:
            st.button("⭐", key=f"unpin_{menu}", on_click=toggle_pin, args=(menu,))

st.sidebar.markdown("---")

# 전체 메뉴
st.sidebar.subheader("📂 전체 메뉴")
for menu in all_menus:
    if menu not in st.session_state.pinned_menus:
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(menu, key=f"all_{menu}", use_container_width=True):
                change_menu(menu)
        with col2:
            st.button("☆", key=f"pin_{menu}", on_click=toggle_pin, args=(menu,))

# ==========================================
# 3. 화면 뷰 1: 통합 주문 현황
# ==========================================
def view_unified_orders():
    render_official_logo()
    st.subheader("📊 통합 주문 현황 (Backhaul Aggregation)")
    st.write("실시간 수요를 집계하여 트럭 매칭 준비를 진행합니다.")
    
    if df_orders.empty:
        st.warning("데이터를 불러오는 중이거나 구글 시트 연결 설정이 필요합니다. '시스템 도움말' 메뉴를 확인하세요.")
        return

    try:
        df_merged = pd.merge(df_orders, df_clients, on="client_id", how="left")
    except Exception:
        st.error("데이터 매칭 오류 (구글 시트의 client_id 열을 확인하세요)")
        return
    
    regions = ["TX", "FL", "NC_SC"]
    for region in regions:
        with st.expander(f"📍 {region} 지역 수요 상세", expanded=True):
            region_data = df_merged[df_merged['region'] == region]
            if region_data.empty:
                st.write("현재 접수된 주문이 없습니다.")
                continue
                
            products = region_data['product'].unique()
            for product in products:
                prod_data = region_data[region_data['product'] == product]
                w_qty = prod_data[prod_data['type'] == 'Wholesale']['quantity'].sum()
                gb_qty = prod_data[prod_data['type'] == 'GroupBuy']['quantity'].sum()
                
                st.info(f"**{product}**: 총 {w_qty + gb_qty} 파렛트 (Wholesale: {w_qty} / GroupBuy: {gb_qty})")
                st.table(prod_data[['name', 'type', 'quantity']])

# ==========================================
# 4. 화면 뷰 2: 공동구매 전용 관리
# ==========================================
def view_group_buy():
    render_official_logo()
    st.subheader("🤝 공동구매 전용 관리")
    
    df_merged = pd.merge(df_orders, df_clients, on="client_id", how="left")
    gb_data = df_merged[df_merged['type'] == 'GroupBuy']
    
    if gb_data.empty:
        st.info("현재 진행 중인 공동구매가 없습니다.")
        return

    deals = gb_data.groupby(['region', 'product'])['quantity'].sum().reset_index()
    TARGET = 20 
    
    cols = st.columns(2)
    for i, (_, row) in enumerate(deals.iterrows()):
        with cols[i % 2]:
            st.markdown(f"#### {row['region']} - {row['product']}")
            progress = min(row['quantity'] / TARGET, 1.0)
            st.progress(progress)
            st.write(f"모집: {row['quantity']} / {TARGET} 파렛트 ({int(progress*100)}%)")

# ==========================================
# 5. 화면 뷰 3: 트럭 배차 현황
# ==========================================
def view_truck_dispatch():
    render_official_logo()
    st.subheader("🚚 트럭 배차 현황 (Backhaul Dispatch)")
    
    days_map = {"화": "NC_SC", "수": "TX", "금": "FL"}
    cols = st.columns(3)
    
    for i, (day, region) in enumerate(days_map.items()):
        with cols[i]:
            if day == "화": st.error(f"### {day}요일 ({region})")
            elif day == "수": st.warning(f"### {day}요일 ({region})")
            else: st.success(f"### {day}요일 ({region})")
            
            day_trucks = df_trucks[df_trucks['return_day'] == day]
            
            for _, truck in day_trucks.iterrows():
                try:
                    is_assigned = int(truck['assigned']) == 1
                except:
                    is_assigned = False
                status = "✅ 상차 완료" if is_assigned else "🔲 배차 대기"
                st.markdown(f"**{truck['truck_id']}** ({truck['capacity']} PLT)")
                st.caption(status)
                if not is_assigned:
                    st.button(f"배차 확정", key=f"d_btn_{truck['truck_id']}")

# ==========================================
# 6. 화면 뷰 4: 시스템 도움말
# ==========================================
def view_help():
    render_official_logo()
    st.subheader("❓ 시스템 관리 및 연동 가이드")
    
    st.info("### 🔗 구글 시트 연결 (Secrets 설정)")
    st.markdown("""
    1. **Streamlit Cloud Dashboard** -> **Settings** -> **Secrets** 클릭
    2. 아래 내용을 입력 (URL은 본인 시트 주소로 교체):
    ```toml
    [connections.gsheets]
    spreadsheet = "[https://docs.google.com/spreadsheets/d/본인_시트_아이디/edit#gid=0](https://docs.google.com/spreadsheets/d/본인_시트_아이디/edit#gid=0)"
    ```
    3. **파일명 확인:** GitHub의 설정 파일 이름이 반드시 `requirements.txt`여야 라이브러리가 설치됩니다.
    """)

# 메인 라우팅 (Routing)
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "공동구매 전용 관리":
    view_group_buy()
elif st.session_state.current_menu == "트럭 배차 현황":
    view_truck_dispatch()
elif st.session_state.current_menu == "시스템 도움말":
    view_help()
