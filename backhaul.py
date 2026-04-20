import streamlit as st
import pandas as pd

# ==========================================
# 1. 페이지 설정 및 초기화 (Page Config & Init)
# ==========================================
st.set_page_config(page_title="통합 백홀 판매 시스템", page_icon="🚚", layout="wide")

# 가상 데이터 초기화 (세션 상태에 저장하여 새로고침해도 유지됨)
if 'data_initialized' not in st.session_state:
    # 1) 판매처 데이터 (홀세일러 vs 공동구매)
    st.session_state.clients = pd.DataFrame([
        {"client_id": "C01", "name": "메트로셰프", "type": "Wholesale"},
        {"client_id": "C02", "name": "메가마트", "type": "Wholesale"},
        {"client_id": "C03", "name": "A식당(조지아)", "type": "GroupBuy"},
        {"client_id": "C04", "name": "B마트(애틀랜타)", "type": "GroupBuy"},
        {"client_id": "C05", "name": "C식당(둘루스)", "type": "GroupBuy"},
    ])
    
    # 2) 주문 데이터
    st.session_state.orders = pd.DataFrame([
        {"order_id": "O01", "client_id": "C01", "region": "TX", "product": "소고기", "quantity": 10},
        {"order_id": "O02", "client_id": "C03", "region": "TX", "product": "소고기", "quantity": 4},
        {"order_id": "O03", "client_id": "C04", "region": "TX", "product": "소고기", "quantity": 6},
        {"order_id": "O04", "client_id": "C02", "region": "FL", "product": "냉동새우", "quantity": 15},
        {"order_id": "O05", "client_id": "C05", "region": "FL", "product": "냉동새우", "quantity": 3},
        {"order_id": "O06", "client_id": "C02", "region": "NC_SC", "product": "돼지고기", "quantity": 12},
    ])
    
    # 3) 복귀 트럭 데이터 (용량 기준: 20 파렛트)
    st.session_state.trucks = pd.DataFrame([
        {"truck_id": "TRK-101", "region": "NC_SC", "return_day": "화", "capacity": 20, "assigned": 0},
        {"truck_id": "TRK-102", "region": "TX", "return_day": "수", "capacity": 20, "assigned": 0},
        {"truck_id": "TRK-103", "region": "FL", "return_day": "금", "capacity": 20, "assigned": 0},
    ])
    
    # 4) 메뉴 핀 고정 상태
    st.session_state.pinned_menus = ["통합 주문 현황"] # 기본 고정 메뉴
    st.session_state.current_menu = "통합 주문 현황"
    
    st.session_state.data_initialized = True

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

all_menus = ["통합 주문 현황", "공동구매 전용 관리", "트럭 배차 현황"]

st.sidebar.title("🚚 Backhaul Hub")
st.sidebar.markdown("---")

# 고정된 메뉴 먼저 출력
st.sidebar.subheader("📌 고정된 메뉴")
for menu in all_menus:
    if menu in st.session_state.pinned_menus:
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(menu, key=f"btn_{menu}", use_container_width=True):
                change_menu(menu)
        with col2:
            st.button("⭐", key=f"pin_{menu}", on_click=toggle_pin, args=(menu,))

st.sidebar.markdown("---")

# 고정되지 않은 메뉴 출력
st.sidebar.subheader("📂 전체 메뉴")
for menu in all_menus:
    if menu not in st.session_state.pinned_menus:
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(menu, key=f"btn_{menu}", use_container_width=True):
                change_menu(menu)
        with col2:
            st.button("☆", key=f"pin_{menu}", on_click=toggle_pin, args=(menu,))

# ==========================================
# 3. 화면 뷰 1: 통합 주문 현황 (Demand Aggregation)
# ==========================================
def view_unified_orders():
    st.title("📊 통합 주문 현황 (수요 집계)")
    st.write("홀세일러와 공동구매 멤버의 주문을 합산하여 지역별 필요 물량을 확인합니다.")
    
    # 데이터 병합 (주문 + 판매처 정보)
    df_merged = pd.merge(st.session_state.orders, st.session_state.clients, on="client_id")
    
    # 지역별/품목별 집계 로직
    regions = df_merged['region'].unique()
    for region in regions:
        st.subheader(f"📍 {region} 지역 수요")
        region_data = df_merged[df_merged['region'] == region]
        products = region_data['product'].unique()
        
        for product in products:
            prod_data = region_data[region_data['product'] == product]
            
            # 수량 합산
            wholesale_qty = prod_data[prod_data['type'] == 'Wholesale']['quantity'].sum()
            gb_qty = prod_data[prod_data['type'] == 'GroupBuy']['quantity'].sum()
            total_qty = wholesale_qty + gb_qty
            
            # 메트릭 카드로 표시
            st.info(f"**총 필요 물량: {product} {total_qty} 파렛트** \n(홀세일: {wholesale_qty} + 공동구매: {gb_qty})")
            
            # 상세 주문 내역 표
            st.dataframe(prod_data[['name', 'type', 'quantity']].rename(
                columns={'name': '판매처명', 'type': '분류', 'quantity': '주문수량(파렛트)'}
            ), use_container_width=True)

# ==========================================
# 4. 화면 뷰 2: 공동구매 전용 관리 (Group Buy View)
# ==========================================
def view_group_buy():
    st.title("🤝 공동구매 전용 관리")
    st.write("공동구매 멤버들의 주문 진행 상황을 관리합니다.")
    
    df_merged = pd.merge(st.session_state.orders, st.session_state.clients, on="client_id")
    gb_data = df_merged[df_merged['type'] == 'GroupBuy']
    
    # 딜(Deal)별 진행률 바 구현
    deals = gb_data.groupby(['region', 'product'])['quantity'].sum().reset_index()
    
    # 가상의 트럭 1대 분량 목표 (20파렛트 기준)
    TARGET_CAPACITY = 20
    
    col1, col2 = st.columns(2)
    
    for idx, row in deals.iterrows():
        region = row['region']
        product = row['product']
        current_qty = row['quantity']
        
        # UI 배치를 위해 컬럼 번갈아가며 출력
        target_col = col1 if idx % 2 == 0 else col2
        
        with target_col:
            st.markdown(f"### {region} 특가 딜: {product}")
            
            # 진행률 계산 (최대 100%)
            progress_ratio = min(current_qty / TARGET_CAPACITY, 1.0)
            st.progress(progress_ratio)
            
            st.write(f"**현재 확보량:** {current_qty} 파렛트 / **목표:** {TARGET_CAPACITY} 파렛트")
            
            # 참여 멤버 리스트
            members = gb_data[(gb_data['region'] == region) & (gb_data['product'] == product)]
            with st.expander("참여 업체 상세보기"):
                st.dataframe(members[['name', 'quantity']].rename(
                    columns={'name': '업체명', 'quantity': '수량'}
                ), hide_index=True)

# ==========================================
# 5. 화면 뷰 3: 트럭 배차 현황 (Backhaul Matching)
# ==========================================
def view_truck_dispatch():
    st.title("🚚 트럭 배차 현황 (백홀 매칭)")
    st.write("요일별로 조지아로 복귀하는 트럭에 통합 수요를 할당합니다.")
    
    # 요일별 컬럼 생성
    col_nc, col_tx, col_fl = st.columns(3)
    
    # NC/SC 라인 (화요일)
    with col_nc:
        st.error("### 화요일 복귀 \n **(NC/SC 라인)**")
        trucks_nc = st.session_state.trucks[st.session_state.trucks['region'] == 'NC_SC']
        for _, truck in trucks_nc.iterrows():
            st.markdown(f"**{truck['truck_id']}** (용량: {truck['capacity']} 파렛트)")
            # 할당 시뮬레이션
            st.selectbox("적재할 물량 선택", ["대기 중", "NC_SC 돼지고기 (12 파렛트)"], key=f"sel_{truck['truck_id']}")
            st.button("배차 확정", key=f"btn_assign_{truck['truck_id']}", use_container_width=True)
            st.markdown("---")
            
    # TX 라인 (수요일)
    with col_tx:
        st.warning("### 수요일 복귀 \n **(TX 라인)**")
        trucks_tx = st.session_state.trucks[st.session_state.trucks['region'] == 'TX']
        for _, truck in trucks_tx.iterrows():
            st.markdown(f"**{truck['truck_id']}** (용량: {truck['capacity']} 파렛트)")
            st.selectbox("적재할 물량 선택", ["대기 중", "TX 소고기 통합물량 (20 파렛트)"], key=f"sel_{truck['truck_id']}")
            st.button("배차 확정", key=f"btn_assign_{truck['truck_id']}", use_container_width=True)
            st.markdown("---")

    # FL 라인 (금요일)
    with col_fl:
        st.success("### 금요일 복귀 \n **(FL 라인)**")
        trucks_fl = st.session_state.trucks[st.session_state.trucks['region'] == 'FL']
        for _, truck in trucks_fl.iterrows():
            st.markdown(f"**{truck['truck_id']}** (용량: {truck['capacity']} 파렛트)")
            st.selectbox("적재할 물량 선택", ["대기 중", "FL 냉동새우 통합물량 (18 파렛트)"], key=f"sel_{truck['truck_id']}")
            st.button("배차 확정", key=f"btn_assign_{truck['truck_id']}", use_container_width=True)
            st.markdown("---")

# ==========================================
# 6. 메인 라우팅 (Main Routing)
# ==========================================
if st.session_state.current_menu == "통합 주문 현황":
    view_unified_orders()
elif st.session_state.current_menu == "공동구매 전용 관리":
    view_group_buy()
elif st.session_state.current_menu == "트럭 배차 현황":
    view_truck_dispatch()