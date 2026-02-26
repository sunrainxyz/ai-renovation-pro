import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="AI装修模拟器-罗莱软装 Pro", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 深度修复版 UI CSS (解决重影与颜色冲突) ---
st.markdown("""
    <style>
    /* 1. 彻底移除原英文并注入中文，解决重影 */
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {
        content: "将房间照片或家具图片拖拽至此处";
        font-size: 16px;
        font-weight: bold;
        color: #31333F;
        display: block;
        margin-bottom: 10px;
    }
    
    /* 2. 汉化上传按钮 */
    [data-testid="stFileUploader"] button {
        font-size: 0px !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: "从手机相册选择";
        font-size: 14px !important;
        visibility: visible;
        display: block;
    }
    
    /* 3. 汉化底部小字提示 */
    [data-testid="stFileUploaderDropzoneInstructions"] div small {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::after {
        content: "支持 JPG/PNG，单文件上限 200MB";
        font-size: 12px;
        color: #808495;
        display: block;
        margin-top: 5px;
    }

    /* 4. 修复侧边栏文字颜色（解决白底白字看不见的问题） */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] [data-testid="stText"], 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p {
        color: #31333F !important;
    }

    /* 5. 隐藏官方页脚与冗余边框 */
    footer {visibility: hidden;}
    [data-testid="stFileUploader"] {
        border: 1px dashed #ced4da;
        border-radius: 10px;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 流量监控逻辑 (全局缓存) ---
@st.cache_resource
def get_traffic_stats():
    return {"total": 0, "codes": {}}

stats = get_traffic_stats()

# --- 4. 授权系统 ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🏠 AI 装修模拟器 · 罗莱软装专业版")
        access_code = st.text_input("请输入专属授权码：", type="password")
        if st.button("激活系统", use_container_width=True, type="primary"):
            valid_codes = st.secrets.get("ACCESS_CODES", [])
            if access_code in valid_codes or access_code == st.secrets.get("ADMIN_CODE", "GSBX2026"):
                st.session_state["authenticated"] = True
                st.session_state["current_user"] = access_code
                st.rerun()
            else:
                st.error("授权码无效。")
        return False
    return True

# --- 5. 主程序入口 ---
if check_auth():
    # 侧边栏设置
    with st.sidebar:
        st.title("🛠️ 设计参数")
        st.caption("技术支持：观世不笑")
        style_list = {
            '原图风格 (Original)': "Maintain original lighting.",
            '温馨暖调 (Warm)': "Apply cozy golden-hour lighting.",
            '清冷高级 (Cool)': "Apply modern cool-toned aesthetic.",
            '极简主义 (Minimalist)': "Focus on clean lines."
        }
        style_name = st.selectbox("选择设计风格", list(style_list.keys()))
        res = st.select_slider("画质", options=["1K", "2K", "4K"], value="2K")
        show_list = st.toggle("📋 生成主材清单", value=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传")
        room_img = st.file_uploader("1. 房间底图", type=['png', 'jpg', 'jpeg'])
        items_img = st.file_uploader("2. 家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        note = st.text_area("3. 补充描述")

    with col2:
        st.subheader("✨ 渲染预览")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_img:
                st.warning("请上传房间底图。")
            else:
                try:
                    # AI 配置
                    gen
