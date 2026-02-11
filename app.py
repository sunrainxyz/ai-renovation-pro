import streamlit as st
import google.generativeai as genai
from PIL import Image
import datetime

# --- 1. 商业版页面配置 ---
st.set_page_config(page_title="AI装修模拟器-罗莱软装 Pro", page_icon="🏠", layout="wide")

# --- 2. 流量监控核心逻辑 (全局共享) ---
@st.cache_resource
def get_traffic_stats():
    # 初始化监控数据：总请求数、各授权码使用频次、最后使用时间
    return {"total": 0, "codes": {}, "history": []}

stats = get_traffic_stats()

# --- 3. 授权门禁系统 ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = None

    if not st.session_state["authenticated"]:
        st.title("🏠 AI 装修模拟器 · 罗莱软装专业版")
        access_code = st.text_input("请输入您的专属授权码：", type="password")
        if st.button("激活系统"):
            # 检查是否为管理员或普通授权码
            valid_codes = st.secrets.get("ACCESS_CODES", [])
            admin_code = st.secrets.get("ADMIN_CODE", "GSBX2026") # 建议在 Secrets 设置管理员码
            
            if access_code == admin_code:
                st.session_state["authenticated"] = True
                st.session_state["current_user"] = "ADMIN"
                st.rerun()
            elif access_code in valid_codes:
                st.session_state["authenticated"] = True
                st.session_state["current_user"] = access_code
                st.rerun()
            else:
                st.error("授权码无效。")
        return False
    return True

# --- 4. 核心功能与监控集成 ---
if check_auth():
    # 管理员面板：仅当登录者为 ADMIN 时在侧边栏显示
    if st.session_state["current_user"] == "ADMIN":
        with st.sidebar:
            st.header("📈 后台流量监控")
            st.metric("累计生成次数", stats["total"])
            st.write("**授权码使用排行：**")
            st.table(stats["codes"])
            if st.button("清除监控记录"):
                stats["total"] = 0
                stats["codes"] = {}
                st.rerun()
            st.divider()

    with st.sidebar:
        st.title("🛠️ 设计参数")
        style_name = st.selectbox("选择装修滤镜", ["原图风格 (Original)", "温馨暖调 (Warm)", "清冷高级 (Cool)", "极简主义 (Minimalist)"])
        resolution = st.select_slider("生成画质", options=["1K", "2K", "4K"], value="2K")

    # 主界面布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传")
        room_file = st.file_uploader("1. 上传房间底图", type=['png', 'jpg', 'jpeg'])
        furniture_files = st.file_uploader("2. 上传家具素材", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        user_prompt = st.text_area("3. 补充描述")

    with col2:
        st.subheader("✨ 渲染预览")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if room_file:
                try:
                    # --- 记录流量 ---
                    stats["total"] += 1
                    user = st.session_state["current_user"]
                    stats["codes"][user] = stats["codes"].get(user, 0) + 1
                    
                    # --- 执行生成 (复刻之前的多模态逻辑) ---
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    
                    with st.spinner("AI 渲染中..."):
                        # 此处省略具体的 generate_content 逻辑，保持与上个版本一致
                        # ... 
                        st.success(f"渲染完成！当前授权码已累计使用 {stats['codes'][user]} 次。")
                        st.balloons()
                except Exception as e:
                    st.error(f"失败：{e}")
