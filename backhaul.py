import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import re
import requests
import base64
from datetime import datetime

# Plotly 라이브러리 안전하게 불러오기
try:
    import plotly.graph_objects as go
    import plotly.express as px
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

# 커스텀 CSS
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
    .status-badge {
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        background-color: #dcfce7;
        color: #166534;
        font-weight: bold;
    }
    .debug-box {
        background-color: #fef2f2;
        border: 1px solid #fee2e2;
        padding: 15px;
        border-radius: 10px;
        color: #991b1b;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.85rem;
        margin: 10px 0;
    }
    .sim-warning {
        background-color: #fffbeb;
        border-left: 5px solid #f59e0b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

def render_official_header():
    st.markdown("""
    <div style="background-color: #f8fafc; padding: 30px 20px; border-radius: 15px; border: 2px solid #e2e8f0; margin-bottom: 30px; text-align: center;">
        <h1 style="margin: 0; font-size: 3.5rem; font-weight: 900; letter-spacing: -2px; line-height: 1.1;">
            <span style="color: #E31837;">GIANT</span> <span style="color: #000000; font-size: 1.5rem; vertical-align: middle;">FOODSYSTEM</span>
        </h1>
        <p style="font-size: 1.2rem; font-weight: 700; color: #475569; margin: 10px 0 5px 0;">#1 K-food Distributor in USA</p>
        <p style="font-size: 0.95rem; font-weight: 500; color: #64748b; margin: 0; line-height: 1.4;">
            NJ Headquarters & GA Logistics Hub Optimization
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. USDA MyMarketNews API 실시간 연동 엔진 (검색기 추가)
# ==========================================

@st.cache_data(ttl=3600)
def fetch_all_usda_reports():
    """
    USDA 서버에 존재하는 '전체 리포트 목록'을 가져옵니다.
    사용자가 올바른 숫자 ID를 찾을 수 있도록 도와주는 검색기능입니다.
    """
    api_key = st.secrets.get("USDA_API_KEY", "J5v4ZF527NWTsrcMJeB7jrXgfgRyPVzd")
    auth_bytes = f"{api_key}:".encode('utf-8')
    encoded_auth = base64.b64encode(auth_bytes).decode('utf-8')
    headers = {"Authorization": f"Basic {encoded_auth}", "Accept": "application/json"}
    
    url = "https://marsapi.ams.usda.gov/services/v1.2/reports"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            # data 구조가 보통 [{"report_id": 1234, "report_title": "..."}, ...] 형태이거나
            # {"results": [...]} 형태입니다.
            if isinstance(data, list):
                return pd.DataFrame(data)
            elif isinstance(data, dict) and "results" in data:
                return pd.DataFrame(data["results"])
    except Exception as e:
        pass
    return pd.DataFrame()

def fetch_usda_api_data(manual_id=None):
    """
    특정 리포트 ID의 상세 가격 데이터를 가져옵니다.
    """
    api_key = st.secrets.get("USDA_API_KEY", "J5v4ZF527NWTsrcMJeB7jrXgfgRyPVzd")
    
    demo_prices = [
        {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.52},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.15},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉장', '부위': '통닭(Whole)', '가격': 1.40},
        {'품목': '🍗 닭고기(Poultry)', '지역': 'TX', '상태': '냉동', '부위': '통닭(Whole)', '가격': 1.08},
        {'품목': '🥩 소고기(Beef)', '지역': 'TX', '상태': '냉장', '부위': '립아이(Ribeye)', '가격': 8.70},
        {'품목': '🥩 돼지고기(Pork)', '지역': 'GA (Hub)', '상태': '냉동', '부위': '무기후지 삼겹살(Mugifuji)', '가격': 4.90},
        {'품목': '🦐 새우(Shrimp)', '지역': 'FL', '상태': '냉동', '부위': '블랙타이거(Black Tiger)', '가격': 6.40},
    ]

    if not api_key:
        return pd.DataFrame(demo_prices), "API 키 미설정", {"error": "API 키가 없습니다."}, "", "error"

    # 영문 ID 입력 시 차단 및 안내
    if manual_id and not manual_id.isdigit():
        return pd.DataFrame(demo_prices), "영문 ID 입력 오류 (숫자로 입력해주세요)", {"error": "API 요청 주소에는 영문(Slug ID)이 아닌 '숫자' 리포트 ID만 입력해야 합니다."}, "", "error"

    target_id = manual_id if manual_id else "2461"
    
    # 🚨 경로 최적화 (오직 Data / Results만 집중 타격)
    data_urls = [
        f"https://marsapi.ams.usda.gov/services/v1.2/reports/{target_id}/data",
        f"https://marsapi.ams.usda.gov/services/v1.2/reports/{target_id}/results"
    ]
    meta_urls = [
        f"https://marsapi.ams.usda.gov/services/v1.2/reports/{target_id}"
    ]
    
    auth_bytes = f"{api_key}:".encode('utf-8')
    encoded_auth = base64.b64encode(auth_bytes).decode('utf-8')
    headers = {"Authorization": f"Basic {encoded_auth}", "Accept": "application/json"}
    
    debug_log = []
    raw_json_data = None
    success_url = ""
    status_type = "error"
    
    # 1. 진짜 알맹이(Data/Results) 집중 탐색
    for url in data_urls:
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                temp_json = res.json()
                
                # 스마트 엑스레이 검사: 알맹이 여부 확인
                is_real_data = False
                if isinstance(temp_json, dict) and "results" in temp_json and len(temp_json["results"]) > 0:
                    sample_keys = str(temp_json["results"][0].keys()).lower()
                    if any(keyword in sample_keys for keyword in ['price', 'value', 'cost', 'item', 'weight', 'volume', 'cut', 'yield']):
                        is_real_data = True
                
                if is_real_data:
                    raw_json_data = temp_json
                    success_url = url
                    status_type = "success_data"
                    debug_log.append(f"✅ [알맹이 발견] URL: {url} (Status: 200)")
                    break 
                else:
                    raw_json_data = temp_json
                    success_url = url
                    status_type = "success_meta"
                    debug_log.append(f"⚠️ [껍데기만 수신] URL: {url} (Status: 200)")
            else:
                debug_log.append(f"❌ [접속 실패] URL: {url} | 상태코드: {res.status_code} | 응답원문: {res.text[:150]}")
        except Exception as e:
            debug_log.append(f"❌ [시스템 에러] URL: {url} | 예외: {str(e)}")
            
    # 2. 알맹이를 못 찾았을 경우 껍데기(표지) 확인
    if status_type == "error":
        for url in meta_urls:
            try:
                res = requests.get(url, headers=headers, timeout=12)
                if res.status_code == 200:
                    raw_json_data = res.json()
                    success_url = url
                    status_type = "success_meta"
                    break
                else:
                    debug_log.append(f"❌ [표지조차 없음] URL: {url} | 상태코드: {res.status_code}")
            except Exception as e:
                pass

    st.session_state['api_debug_details'] = debug_log
    
    if status_type == "success_data":
        return pd.DataFrame(demo_prices), "API 데이터 연동 성공", raw_json_data, success_url, status_type
    elif status_type == "success_meta":
        return pd.DataFrame(demo_prices), "알맹이(Data) 없음 - 표지(Meta)만 수신됨", raw_json_data, success_url, status_type
    else:
        return pd.DataFrame(demo_prices), "통신 실패 - 해당 번호의 리포트가 존재하지 않습니다.", None, "", status_type

# ==========================================
# 3. 데이터 로드 로직 (구글 시트 연동)
# ==========================================
@st.cache_data(ttl=60)
def fetch_gsheet_data(sheet_url, worksheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url, worksheet=worksheet_name)
    except Exception:
        return pd.DataFrame()
    
    if not df.empty:
        df.columns = [re.sub(r'[^a-z0-9_]+', '_', str(col).strip().lower()).strip('_') for col in df.columns]
    return df

def load_all_data():
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "URL 미설정"
    return fetch_gsheet_data(sheet_url, "Clients"), fetch_gsheet_data(sheet_url, "Orders"), fetch_gsheet_data(sheet_url, "Trucks"), None

df_clients, df_orders, df_trucks, error_msg = load_all_data()

def ensure_columns(df, expected_cols):
    for col in expected_cols:
        if col not in df.columns: 
            df[col] = 0 if 'quantity' in col or col in ['capacity', 'assigned'] else ""
    return df

df_orders = ensure_columns(df_orders, ["order_id", "client_id", "region", "product", "quantity_box", "quantity_pallet"])
df_trucks = ensure_columns(df_trucks, ["truck_id", "region", "return_day", "capacity", "assigned"])

# ==========================================
# 4. 사이드바 구성
# ==========================================
if 'current_menu' not in st.session_state:
    st.session_state.current_menu = "품목별 시장가 비교"

st.sidebar.markdown("""
<h2 style="margin: 0; font-weight: 900; line-height: 1.0;">
    <span style="color: #E31837;">GIANT</span><br>
    <span style="color: #cbd5e1; font-size: 0.95rem; letter-spacing: 1px;">FOODSYSTEM</span>
</h2>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

for menu in ["통합 주문 현황", "수요자(Customer) 포털", "백홀 파트너(단순물류이송)", "지역별 공급자 파트너", "품목별 시장가 비교", "데이터 통합 관리"]:
    if st.sidebar.button(menu, key=f"sidebar_{menu}", use_container_width=True):
        st.session_state.current_menu = menu

st.sidebar.markdown("---")
use_live_api = st.sidebar.toggle("🛰️ API 통신 테스트 모드", value=True)

# ==========================================
# 5. 화면 뷰 로직
# ==========================================
def view_market_price_comparison():
    render_official_header()
    
    st.subheader("📊 주요 식자재 백홀 차익 분석 시스템")
    
    st.markdown("""
    <div class="sim-warning">
        <b>🚨 시스템 검증을 위한 시뮬레이션 모드 가동 중</b><br>
        아래 출력되는 차트와 분석 내용은 UI 구성을 위해 채워진 가짜(Mock-up) 데이터입니다. 실제 USDA API에서 알맹이(가격) 데이터를 추출하려면 통신에 성공한 진짜 리포트를 찾아야 합니다.
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🛠️ 데이터 매핑을 위한 리포트 번호 발굴 도구 (여기를 펼쳐주세요!)", expanded=True):
        st.markdown("""
        **🚨 영문 Slug ID 오류 원인 파악 완료:** USDA API는 호출 주소에 영문(`lm_xb403`)이 아닌 **숫자로 된 고유 Report ID**만 허용합니다!
        더 이상 번호를 찍어 맞출 필요 없이, 아래의 **[전체 리포트 목록 불러오기]**를 통해 현재 USDA 서버에 등록된 수백 개의 진짜 숫자 번호를 직접 검색해 보세요.
        """)
        
        # 1. 전체 리포트 검색기 버튼
        if st.button("🔍 1. 현재 살아있는 USDA 전체 리포트 목록 불러오기", type="primary"):
            with st.spinner("USDA 서버에서 전체 리포트 메뉴판을 가져오고 있습니다..."):
                df_reports = fetch_all_usda_reports()
                if not df_reports.empty:
                    st.success(f"✅ 총 {len(df_reports)}개의 리포트 목록을 성공적으로 불러왔습니다!")
                    # 사용자가 보기 편하게 필수 컬럼만 필터링
                    display_cols = [c for c in ['report_id', 'report_title', 'slug_name', 'market_type'] if c in df_reports.columns]
                    st.dataframe(df_reports[display_cols], height=300, use_container_width=True)
                    st.info("👆 위 표의 우측 상단 '돋보기 아이콘'을 누르고 `Beef`, `Pork`, `Broiler` 등을 검색하여, 좌측의 **`report_id` (숫자)**를 찾아주세요!")
                else:
                    st.error("전체 리포트 목록을 불러오지 못했습니다. API 키 문제이거나 서버 응답 지연입니다.")
        
        st.markdown("---")
        
        # 2. 숫자 ID 입력 및 테스트
        st.markdown("**🔍 2. 위에서 찾은 숫자 ID(Report ID)로 알맹이 데이터 추출 테스트**")
        col_id, col_btn = st.columns([3, 1])
        # 기본값으로 가장 확률이 높은 소고기 관련 숫자 ID(2461: National Daily Boxed Beef Cuts)를 배치
        manual_report_id = col_id.text_input("통신 테스트용 '숫자' Report ID 입력 (예: 2461, 3208 등)", value="2461")
        if col_btn.button("진짜 데이터 찾기 테스트", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
    df_price, update_status, raw_json, success_url, status_type = fetch_usda_api_data(manual_report_id)

    # 상태에 따른 색상 및 메시지 처리
    if status_type == "success_data":
        st.markdown(f"**통신 결과:** <span style='color:#166534; font-weight:bold; font-size:1.2em;'>✅ {update_status}</span>", unsafe_allow_html=True)
    elif status_type == "success_meta":
        st.markdown(f"**통신 결과:** <span style='color:#f59e0b; font-weight:bold; font-size:1.2em;'>⚠️ {update_status}</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"**통신 결과:** <span style='color:#dc2626; font-weight:bold; font-size:1.2em;'>❌ {update_status}</span>", unsafe_allow_html=True)

    if use_live_api:
        st.markdown("### 💻 수신된 실제 Raw Data (알맹이 판별기)")
        
        if status_type == "success_meta":
            st.error(f"🚨 **[경고] 의미 없는 껍데기 데이터(표지)를 자동으로 걸러냈습니다!**\n\n조회하신 숫자 번호({manual_report_id})는 서버에서 정상 응답은 했으나, 실제 가격 정보는 숨겨두었거나 없습니다. 위 목록에서 다른 숫자 ID를 찾아 입력해 보세요!")
            if raw_json: st.json(raw_json)
            
        elif status_type == "success_data":
            st.success(f"🎯 **[빙고!] 스마트 엑스레이가 완벽한 알맹이(가격) 데이터를 찾아냈습니다!**\n\n출처: `{success_url}`\n\n아래 표의 영문 컬럼명(`Price`, `Item_Desc`, `Cut` 등)을 자세히 보세요. 이제 이 진짜 데이터를 가지고 파싱 코드를 짜면 시뮬레이션 데이터를 완벽히 교체할 수 있습니다.")
            
            if isinstance(raw_json, dict) and "results" in raw_json:
                real_df = pd.DataFrame(raw_json["results"])
                st.markdown(f"#### 🔍 진짜 데이터 미리보기 (총 {len(real_df)}건의 세부 시세 발견)")
                st.dataframe(real_df, height=400)
                st.markdown("**👇 이 리포트에서 사용할 수 있는 진짜 영문 Key(컬럼명) 목록:**")
                st.code(", ".join(real_df.columns))
            else:
                st.json(raw_json)
                
        elif status_type == "error":
            st.error("해당 번호의 리포트가 USDA 서버에 존재하지 않거나 막혀있습니다. 숫자 ID가 맞는지 확인해 주세요.")
            with st.expander("서버 오류 로그 상세 보기", expanded=False):
                for log in st.session_state.get('api_debug_details', []): st.text(log)

    st.markdown("---")
    st.subheader("🛠️ 아래는 시뮬레이션용 차트 (데이터 교체 전 임시 화면입니다)")
    
    # 시뮬레이션 차트
    if not df_price.empty and PLOTLY_AVAILABLE:
        fig = px.bar(df_price.head(10), x='지역', y='가격', color='상태', title="[가짜 데이터] UI 테스트용 임시 차트")
        st.plotly_chart(fig, use_container_width=True)

if st.session_state.current_menu == "품목별 시장가 비교":
    view_market_price_comparison()
else:
    st.info("좌측 메뉴에서 [품목별 시장가 비교]를 선택해 주세요.")
