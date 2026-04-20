import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 페이지 설정 및 초기화 (Page Config & Init)
# ==========================================
st.set_page_config(page_title="통합 백홀 판매 시스템", page_icon="🚚", layout="wide")

# 구글 시트 연결 설정 (st-gsheets-connection 사용)
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 함수 (캐시 적용으로 성능 최적화)
@st.cache_data(ttl=60) # 60초 동안 데이터 유지 후 갱신
def load_data():
    try:
        # 각 워크시트에서 데이터 읽기
        clients = conn.read(worksheet="Clients")
        orders = conn.read(worksheet="Orders")
        trucks = conn.read(worksheet="Trucks")
        return clients, orders, trucks
    except Exception as e:
        # 시트가 없거나 연결 오류 시 빈 데이터프레임 반환
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# 데이터 로드 실행
df_clients, df_orders, df_trucks = load_data()

# 데이터 유효성 검사 및 기본 컬럼 보장
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
# 2. 사이드바 로직 (Sidebar & Pin Feature)
# ==========================================
def toggle_pin(menu_name):
    if menu_name in st.session_state.pinned_menus:
        st.session_state.pinned_menus.remove(menu_name)
    else:
        st.session_state.pinned_menus.append(menu_name)

def change_menu(menu_name):
    st.session_state.current_menu = menu_name

all_menus = ["통합 주문 현황", "공동구매 전용 관리", "트럭 배차 현황", "시스템 도움말"]

st.sidebar.title("🚚 Backhaul Hub")
st.sidebar.markdown("---")

# 고정된 메뉴 (Pinned Menus)
st.sidebar.subheader("📌 고정된 메뉴")
for menu in all_menus:
    if menu in st.session_state.pinned_menus:
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(menu, key=f"pinned_{menu}", use_container_width=True):
                change_menu(menu)
        with col2:
            st.button("⭐", key=f"unpin_{menu}", on_click=toggle_pin, args=(menu,))

st.sidebar.markdown("---")

# 전체 메뉴 (All Menus)
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
# 3. 화면 뷰 1: 통합 주문 현황 (수요 집계)
# ==========================================
def view_unified_orders():
    st.title("📊 통합 주문 현황 (수요 집계)")
    st.write("구글 시트의 주문 데이터를 기반으로 실시간 수요를 집계합니다.")
    
    if df_orders.empty:
        st.warning("Orders 시트에 데이터가 없습니다. 구글 시트를 확인해 주세요.")
        return

    # 데이터 병합 (Orders + Clients)
    try:
        df_merged = pd.merge(df_orders, df_clients, on="client_id", how="left")
    except KeyError:
        st.error("데이터 컬럼명이 일치하지 않습니다. (client_id 확인 필요)")
        return
    
    # 지역별 섹션 생성
    regions = ["TX", "FL", "NC_SC"]
    for region in regions:
        with st.expander(f"📍 {region} 지역 수요 상세", expanded=True):
            region_data = df_merged[df_merged['region'] == region]
            if region_data.empty:
                st.write("해당 지역의 주문이 없습니다.")
                continue
                
            products = region_data['product'].unique()
            for product in products:
                prod_data = region_data[region_data['product'] == product]
                w_qty = prod_data[prod_data['type'] == 'Wholesale']['quantity'].sum()
                gb_qty = prod_data[prod_data['type'] == 'GroupBuy']['quantity'].sum()
                total_qty = w_qty + gb_qty
                
                st.info(f"**{product}**: 총 {total_qty} 파렛트 (홀세일: {w_qty} / 공동구매: {gb_qty})")
                st.table(prod_data[['name', 'type', 'quantity']].rename(
                    columns={'name': '판매처명', 'type': '구분', 'quantity': '수량'}
                ))

# ==========================================
# 4. 화면 뷰 2: 공동구매 전용 관리 (Progress Bar)
# ==========================================
def view_group_buy():
    st.title("🤝 공동구매 전용 관리")
    st.write("공동구매 멤버들의 주문 합계가 트럭 목표치(20파렛트)에 도달했는지 확인합니다.")
    
    if df_orders.empty:
        st.info("진행 중인 공동구매 오더가 없습니다.")
        return

    df_merged = pd.merge(df_orders, df_clients, on="client_id", how="left")
    gb_data = df_merged[df_merged['type'] == 'GroupBuy']
    
    if gb_data.empty:
        st.info("공동구매 멤버의 주문이 아직 없습니다.")
        return

    deals = gb_data.groupby(['region', 'product'])['quantity'].sum().reset_index()
    TARGET_CAPACITY = 20 # 트럭 한 대분 기준
    
    cols = st.columns(2)
    for i, (_, row) in enumerate(deals.iterrows()):
        with cols[i % 2]:
            st.subheader(f"🏷️ {row['region']} {row['product']}")
            progress_val = min(row['quantity'] / TARGET_CAPACITY, 1.0)
            st.progress(progress_val)
            st.write(f"모집 현황: **{row['quantity']}** / {TARGET_CAPACITY} 파렛트 ({int(progress_val * 100)}%)")
            
            # 해당 딜 참여 멤버 리스트
            details = gb_data[(gb_data['region'] == row['region']) & (gb_data['product'] == row['product'])]
            st.caption(f"참여 업체: {', '.join(details['name'].tolist())}")

# ==========================================
# 5. 화면 뷰 3: 트럭 배차 현황 (Backhaul Matching)
# ==========================================
def view_truck_dispatch():
    st.title("🚚 트럭 배차 현황 (백홀 매칭)")
    st.write("조지아로 복귀하는 트럭 스케줄에 집계된 수요를 매칭합니다.")
    
    if df_trucks.empty:
        st.warning("Trucks 시트에 트럭 데이터가 없습니다.")
        return

    days_map = {"화": "NC_SC", "수": "TX", "금": "FL"}
    cols = st.columns(3)
    
    for i, (day, region) in enumerate(days_map.items()):
        with cols[i]:
            st.markdown(f"### {day}요일 복귀 ({region})")
            day_trucks = df_trucks[df_trucks['return_day'] == day]
            
            if day_trucks.empty:
                st.caption("해당 요일 운행 트럭 없음")
                continue
                
            for _, truck in day_trucks.iterrows():
                # 배차 상태에 따른 카드 디자인
                is_assigned = truck['assigned'] == 1
                color = "green" if is_assigned else "red"
                status_text = "상차 완료" if is_assigned else "빈 차 (배차 필요)"
                
                with st.container():
                    st.markdown(f"""
                    <div style="border:1px solid {color}; border-radius:10px; padding:15px; margin-bottom:10px;">
                        <h4 style="margin:0;">{truck['truck_id']}</h4>
                        <p style="margin:0; font-size:14px;">상태: <span style="color:{color}; font-weight:bold;">{status_text}</span></p>
                        <p style="margin:0; font-size:12px;">가용 용량: {truck['capacity']} 파렛트</p>
                    </div>
                    """, unsafe_allow_name=True)
                    
                    if not is_assigned:
                        if st.button(f"{truck['truck_id']} 배차 확정", key=f"btn_{truck['truck_id']}"):
                            st.success(f"{truck['truck_id']} 배차 처리됨 (구글 시트 업데이트 기능 연동 예정)")

# ==========================================
# 6. 화면 뷰 4: 시스템 도움말 (Help & Secrets)
# ==========================================
def view_help():
    st.title("❓ 시스템 도움말 및 연동 가이드")
    st.markdown("""
    ### 🔗 구글 스프레드시트 실시간 연동 방법
    본 앱은 구글 시트의 데이터를 직접 읽어옵니다. 아래 단계를 따라 설정을 완료하세요.

    **1. 구글 시트 공유 설정**
    - 구글 시트 우측 상단 **[공유]** 클릭
    - '링크가 있는 모든 사용자'가 **'편집자'** 권한을 갖도록 변경

    **2. Streamlit Secrets 설정**
    - [Streamlit Cloud](https://share.streamlit.io/) 대시보드 접속
    - 본인 앱 우측의 `...` 아이콘 -> **Settings** 클릭
    - 좌측 메뉴에서 **Secrets** 선택
    - 아래 내용을 복사해서 붙여넣으세요 (URL은 본인 시트 주소로 수정):
    ```toml
    [connections.gsheets]
    spreadsheet = "[https://docs.google.com/spreadsheets/d/본인_시트_아이디/edit#gid=0](https://docs.google.com/spreadsheets/d/본인_시트_아이디/edit#gid=0)"
    ```
    - **Save** 버튼 클릭

    **3. 파일 및 브랜치 설정**
    - **Main file path:** `backhaul.py` (현재 대표님의 파일 이름)
    - **Branch:** `main`
    """)

# ==========================================
# 7. 메인 라우팅 (Main Routing)
# ==========================================
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "공동구매 전용 관리":
    view_group_buy()
elif st.session_state.current_menu == "트럭 배차 현황":
    view_truck_dispatch()
elif st.session_state.current_menu == "시스템 도움말":
    view_help()
