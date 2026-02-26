import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. 商业版页面配置 ---
st.set_page_config(
    page_title="AI装修模拟器-罗莱软装 Pro", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 深度修复版 UI CSS (解决重影与颜色冲突) ---
st.markdown("""
    <style>
    /* 1. 汉化上传组件并修复重影 */
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {
        content: "将房间照片或家具图片拖拽至此处";
        font-size: 16px;
        font-weight: bold;
        color: #31333F;
        display: block;
        margin-bottom: 5px;
    }
    
    /* 2. 汉化上传按钮 */
    [data-testid="stFileUploader"] button {
        font-size: 0px !important;
        padding: 10px 20px !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: "从手机相册选择";
        font-size: 14px !important;
        visibility: visible;
        display: block;
    }
    
    /* 3. 汉化文件限制说明 */
    [data-testid="stFileUploaderDropzoneInstructions"] div small {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::after {
        content: "支持 JPG/PNG，单文件上限 200MB";
        font-size: 12px;
        color: #808495;
        display: block;
    }

    /* 4. 修复侧边栏颜色（解决文字不可见问题） */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E6E9EF;
    }
    [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #31333F !important;
    }

    /* 5. 隐藏 Streamlit 官方水印 */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 流量监控核心逻辑 ---
@st.cache_resource
def get_traffic_stats():
    return {"total": 0, "codes": {}}

stats = get_traffic_stats()

# --- 4. 授权门禁系统 ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = None

    if not st.session_state["authenticated"]:
        st.title("🏠 AI 装修模拟器 · 罗莱软装专业版")
        st.info("本系统已开启商业授权保护，请输入专属授权码登录。")
        
        col_l, col_m, col_r = st.columns([1, 2, 1])
        with col_m:
            access_code = st.text_input("请输入授权码：", type="password")
            if st.button("激活系统", use_container_width=True, type="primary"):
                valid_codes = st.secrets.get("ACCESS_CODES", [])
                admin_code = st.secrets.get("ADMIN_CODE", "GSBX2026") 
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

# --- 5. 核心逻辑 ---
if check_auth():
    if st.session_state["current_user"] == "ADMIN":
        with st.sidebar:
            st.header("📈 流量监控后台")
            st.metric("累计生成次数", stats["total"])
            st.write("**授权码消耗：**")
            st.table(stats["codes"])
            if st.button("重置统计"):
                stats["total"] = 0
                stats["codes"] = {}
                st.rerun()
            st.divider()

    with st.sidebar:
        st.title("🛠️ 设计参数")
        st.caption("技术支持：观世不笑")
        filter_prompts = {
            '原图风格 (Original)': "Maintain original lighting.",
            '温馨暖调 (Warm)': "Apply cozy golden-hour lighting.",
            '清冷高级 (Cool)': "Apply modern cool-toned aesthetic.",
            '极简主义 (Minimalist)': "Focus on clean lines and soft lighting."
        }
        style_name = st.selectbox("选择设计风格", list(filter_prompts.keys()))
        resolution = st.select_slider("输出画画质", options=["1K", "2K", "4K"], value="2K")
        show_material_list = st.toggle("📋 同步生成主材清单", value=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传")
        room_file = st.file_uploader("1. 房间底图", type=['png', 'jpg', 'jpeg'])
        furniture_files = st.file_uploader("2. 家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        user_prompt = st.text_area("3. 补充描述")

    with col2:
        st.subheader("✨ 渲染预览")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_file:
                st.warning("请先上传底图。")
            else:
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # 使用您权限内最强的模型列表
                    target_models = [
                        'models/gemini-3-pro-image-preview',
                        'models/gemini-2.5-pro',
                        'models/gemini-2.0-flash'
                    ]
                    available_names = [m.name for m in genai.list_models()]
                    selected_model = next((m for m in target_models if m in available_names), 'models/gemini-1.5-pro')

                    model = genai.GenerativeModel(selected_model)
                    
                    with st.spinner(f"正在驱动 {selected_model.split('/')[-1]} 渲染..."):
                        input_payload = [Image.open(room_file)]
                        for f in furniture_files:
                            input_payload.append(Image.open(f))
