import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 페이지 설정 및 회사 공식 타이틀 적용
# ==========================================
# page_title 부분에 회사 공식 명칭을 넣으세요.
st.set_page_config(page_title="GA GLOBAL LOGISTICS - 백홀 관리 시스템", page_icon="🚚", layout="wide")

# 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 함수
@st.cache_data(ttl=60)
def load_data():
    try:
        clients = conn.read(worksheet="Clients")
        orders = conn.read(worksheet="Orders")
        trucks = conn.read(worksheet="Trucks")
        return clients, orders, trucks
    except Exception as e:
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

# 사이드바 상단에 공식 타이틀 배치
st.sidebar.markdown(f"## 🏢 GA GLOBAL LOGISTICS") # 여기를 회사 이름으로 수정하세요.
st.sidebar.caption("통합 백홀 판매/배차 관리 시스템")
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
    # 메인 상단에도 공식 타이틀 표시
    st.title("🏢 GA GLOBAL LOGISTICS")
    st.subheader("📊 통합 주문 현황 (Backhaul Aggregation)")
    st.write("실시간 수요를 집계하여 트럭 매칭 준비를 진행합니다.")
    
    if df_orders.empty:
        st.warning("데이터를 불러오는 중이거나 Orders 시트가 비어있습니다.")
        return

    try:
        df_merged = pd.merge(df_orders, df_clients, on="client_id", how="left")
    except Exception:
        st.error("데이터 매칭 오류 (client_id를 확인하세요)")
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
    st.title("🏢 GA GLOBAL LOGISTICS")
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
    st.title("🏢 GA GLOBAL LOGISTICS")
    st.subheader("🚚 트럭 배차 현황 (Backhaul Dispatch)")
    
    days_map = {"화": "NC_SC", "수": "TX", "금": "FL"}
    cols = st.columns(3)
    
    for i, (day, region) in enumerate(days_map.items()):
        with cols[i]:
            st.error(f"### {day}요일 ({region})") if day=="화" else st.warning(f"### {day}요일 ({region})") if day=="수" else st.success(f"### {day}요일 ({region})")
            day_trucks = df_trucks[df_trucks['return_day'] == day]
            
            for _, truck in day_trucks.iterrows():
                is_assigned = truck['assigned'] == 1
                status = "✅ 상차 완료" if is_assigned else "🔲 배차 대기"
                st.markdown(f"**{truck['truck_id']}** ({truck['capacity']} PLT)")
                st.caption(status)
                if not is_assigned:
                    st.button(f"배차 확정", key=f"d_btn_{truck['truck_id']}")

# ==========================================
# 6. 화면 뷰 4: 시스템 도움말
# ==========================================
def view_help():
    st.title("❓ 시스템 관리 및 연동 가이드")
    st.markdown("""
    ### 🏢 공식 타이틀 변경 방법
    코드 상단의 `st.set_page_config`와 사이드바의 `st.sidebar.markdown` 부분에서 회사 명칭을 수정할 수 있습니다.

    ### 🔗 구글 시트 연결 (Secrets 설정)
    1. **Streamlit Settings** -> **Secrets**
    2. 아래 형식으로 입력:
    ```toml
    [connections.gsheets]
    spreadsheet = "[https://docs.google.com/spreadsheets/d/본인_시트_아이디/edit#gid=0](https://docs.google.com/spreadsheets/d/본인_시트_아이디/edit#gid=0)"
    ```
    """)

# 메인 라우팅
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "공동구매 전용 관리":
    view_group_buy()
elif st.session_state.current_menu == "트럭 배차 현황":
    view_truck_dispatch()
elif st.session_state.current_menu == "시스템 도움말":
    view_help()
