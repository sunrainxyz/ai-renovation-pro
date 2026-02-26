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

# --- 2. 深度精修版 UI CSS ---
st.markdown("""
    <style>
    /* 彻底移除原英文标签，防止重影 */
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span {
        display: none !important;
    }
    /* 汉化并精修拖拽区域提示语 */
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {
        content: "将图片拖拽至此处或点击“选择图片”按钮";
        font-size: 16px;
        font-weight: bold;
        color: #31333F;
        display: block;
        margin-bottom: 10px;
    }
    
    /* 汉化上传按钮：修改为“选择图片” */
    [data-testid="stFileUploader"] button {
        font-size: 0px !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: "选择图片";
        font-size: 14px !important;
        visibility: visible;
        display: block;
    }
    
    /* 汉化底部格式提示词 */
    [data-testid="stFileUploaderDropzoneInstructions"] div small {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::after {
        content: "支持 JPG/PNG/JPEG，单文件上限 200MB";
        font-size: 12px;
        color: #808495;
        display: block;
        margin-top: 5px;
    }

    /* 侧边栏文字颜色修正 */
    [data-testid="stSidebar"] [data-testid="stText"], 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p {
        color: #31333F !important;
    }

    /* 隐藏所有标题旁边的锚点链接图标 (全局方案) */
    .stApp a.element-container:hover {
        display: none !important;
    }

    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心统计逻辑 ---
@st.cache_resource
def get_traffic_stats():
    return {"total": 0, "codes": {}}

stats = get_traffic_stats()

# --- 4. 授权门禁 ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🏠 AI 装修模拟器 · 罗莱软装专业版", anchor=False)
        st.info("本系统已开启商业授权保护，请输入专属授权码激活。")
        
        col_l, col_m, col_r = st.columns([1, 2, 1])
        with col_m:
            access_code = st.text_input("请输入授权码：", type="password")
            if st.button("激活系统", use_container_width=True, type="primary"):
                valid_codes = st.secrets.get("ACCESS_CODES", [])
                admin_code = st.secrets.get("ADMIN_CODE", "GSBX2026") 
                if access_code in valid_codes or access_code == admin_code:
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = access_code
                    st.rerun()
                else:
                    st.error("授权码无效。")
        return False
    return True

# --- 5. 主程序 ---
if check_auth():
    if st.session_state["current_user"] == "ADMIN":
        with st.sidebar:
            st.header("📈 后台流量监控", anchor=False)
            st.metric("累计生成次数", stats["total"])
            st.table(stats["codes"])
            if st.button("重置统计"):
                stats["total"] = 0; stats["codes"] = {}; st.rerun()
            st.divider()

    with st.sidebar:
        st.title("🛠️ 设计参数", anchor=False)
        st.caption("技术支持：观世不笑")
        style_list = {
            '原图风格 (Original)': "Maintain original lighting.",
            '温馨暖调 (Warm)': "Apply cozy golden-hour lighting.",
            '清冷高级 (Cool)': "Apply modern cool-toned aesthetic.",
            '复古胶片 (Vintage)': "Apply nostalgic film vibe.",
            '极简主义 (Minimalist)': "Focus on clean lines."
        }
        style_name = st.selectbox("选择设计风格", list(style_list.keys()))
        res = st.select_slider("选择生成画质", options=["1K", "2K", "4K"], value="2K")
        show_list = st.toggle("📋 同步生成主材清单", value=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        # 注意：此处 anchor=False 彻底去除了超链接图标
        st.subheader("🖼️ 素材上传", anchor=False)
        room_img = st.file_uploader("1.房间底图", type=['png', 'jpg', 'jpeg'])
        items_img = st.file_uploader("2.家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        note = st.text_area("3.补充描述", placeholder="例如：将上传的窗帘替换掉原来的窗帘")

    with col2:
        st.subheader("✨ 渲染预览", anchor=False)
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_img:
                st.warning("请上传1号房间底图。")
            else:
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    with st.spinner("AI 渲染中..."):
                        payload = [Image.open(room_img)]
                        for f in items_img: payload.append(Image.open(f))
                        payload.append(f"STYLE: {style_list[style_name]}. {note}.")
                        response = model.generate_content(payload)
                        if response.candidates:
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.image(part.inline_data.data, use_container_width=True)
                                    st.download_button("📥 下载设计图", part.inline_data.data, "design.png", "image/png")
                                elif hasattr(part, 'text') and part.text:
                                    st.markdown(part.text)
                            stats["total"] += 1
                            usr = st.session_state["current_user"]
                            stats["codes"][usr] = stats["codes"].get(usr, 0) + 1
                            st.success("设计渲染成功！")
                            st.balloons()
                except Exception as e:
                    st.error(f"渲染中发生错误：{str(e)}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业授权版 | 罗莱软装官方技术支持</p>", unsafe_allow_html=True)
