import streamlit as st

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(
    page_title="GIANT FOODSYSTEM", 
    page_icon="🚚", 
    layout="wide"
)

# ==========================================
# 2. 메인 화면 타이틀
# ==========================================
st.markdown("""
    <div style="background-color: #f8fafc; padding: 50px; border-radius: 20px; text-align: center; border: 2px solid #e2e8f0; margin-top: 50px;">
        <h1 style="margin: 0; font-size: 4rem; font-weight: 900; letter-spacing: -2px;">
            <span style="color: #E31837;">GIANT</span> <span style="color: #000000;">FOODSYSTEM</span>
        </h1>
        <p style="font-size: 1.5rem; font-weight: 600; color: #475569; margin-top: 20px;">#1 K-food Distributor in USA</p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 사이드바
# ==========================================
st.sidebar.title("🚚 GIANT FOOD")
st.sidebar.markdown("---")
st.sidebar.info("시스템 초기화 상태입니다.")
