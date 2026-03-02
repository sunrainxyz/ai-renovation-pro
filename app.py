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

# --- 2. UI 深度精修 (汉化、移除锚点、侧边栏修复) ---
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
    /* 汉化上传按钮 */
    [data-testid="stFileUploader"] button { font-size: 0px !important; }
    [data-testid="stFileUploader"] button::after {
        content: "选择图片";
        font-size: 14px !important;
        visibility: visible;
        display: block;
    }
    /* 彻底隐藏标题旁的锚点超链接图标 */
    .stApp a.element-container:hover { display: none !important; }
    
    /* 侧边栏文字颜色修正 */
    [data-testid="stSidebar"] [data-testid="stText"], 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p { color: #31333F !important; }
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 统计逻辑 (全局缓存) ---
@st.cache_resource
def get_traffic_stats():
    return {"total": 0, "codes": {}}

stats = get_traffic_stats()

# --- 4. 授权门禁系统 ---
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
                if access_code in valid_codes or access_code == st.secrets.get("ADMIN_CODE", "GSBX2026"):
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = access_code
                    st.rerun()
                else:
                    st.error("授权码无效。")
        return False
    return True

# --- 5. 主程序逻辑 ---
if check_auth():
    with st.sidebar:
        st.title("🛠️ 设计参数", anchor=False)
        st.caption("技术支持：观世不笑")
        style_list = {'原图风格': "Original lighting.", '温馨暖调': "Warm lighting.", '清冷高级': "Cool modern."}
        style_name = st.selectbox("选择设计风格", list(style_list.keys()))
        res = st.select_slider("选择生成画质", options=["1K", "2K", "4K"], value="2K")
        show_list = st.toggle("📋 同步生成主材清单", value=True)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🖼️ 素材上传", anchor=False)
        # 1. 房间底图 + 即时预览
        room_img = st.file_uploader("1. 房间底图", type=['png', 'jpg', 'jpeg'])
        if room_img:
            st.image(room_img, caption="✅ 底图预览已就绪", use_container_width=True)
            
        # 2. 家具素材 + 多图预览
        items_img = st.file_uploader("2. 家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if items_img:
            cols = st.columns(4)
            for idx, f in enumerate(items_img):
                with cols[idx % 4]:
                    st.image(f, use_container_width=True)
                    
        # 3. 补充描述 + 业务占位符
        note = st.text_area("3. 补充描述", placeholder="例如：将上传的窗帘替换掉原来的窗帘")

    with col2:
        st.subheader("✨ 渲染预览", anchor=False)
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_img:
                st.warning("请先上传底图。")
            else:
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # --- 动态模型选择：解决 404 报错 ---
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    target_priority = [
                        'models/gemini-2.0-flash', # 优先使用 2.0 极速版
                        'models/gemini-1.5-pro',
                        'models/gemini-1.5-flash'  # 最稳健的备选
                    ]
                    selected_model = next((m for m in target_priority if m in available_models), available_models[0])
                    
                    model = genai.GenerativeModel(selected_model)
                    
                    with st.spinner(f"正在驱动 {selected_model.split('/')[-1]} 进行空间建模..."):
                        payload = [Image.open(room_img)]
                        for f in items_img: payload.append(Image.open(f))
                        payload.append(f"STYLE: {style_list[style_name]}. {note}.")
                        
                        response = model.generate_content(payload)
                        if response.candidates:
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.image(part.inline_data.data, use_container_width=True)
                                    st.download_button("📥 下载设计图", part.inline_data.data, "luolai_design.png", "image/png")
                                elif hasattr(part, 'text') and part.text:
                                    st.markdown(part.text)
                            stats["total"] += 1
                            usr = st.session_state["current_user"]
                            stats["codes"][usr] = stats["codes"].get(usr, 0) + 1
                            st.success("设计完成！")
                            st.balloons()
                except Exception as e:
                    st.error(f"渲染中发生错误：{str(e)}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业授权版 | 罗莱软装官方技术支持</p>", unsafe_allow_html=True)
