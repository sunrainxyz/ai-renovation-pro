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

# --- 2. 深度精修 UI CSS (汉化、避坑、移除锚点图标) ---
st.markdown("""
    <style>
    /* 彻底移除原英文标签，防止重影 */
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span {
        display: none !important;
    }
    /* 汉化并精修拖拽区域提示语 */
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {
        content: "将房间照片或家具图片拖拽至此处";
        font-size: 16px;
        font-weight: bold;
        color: #31333F;
        display: block;
        margin-bottom: 10px;
    }
    
    /* 汉化上传按钮：修改为“选择图片” */
    [data-testid="stFileUploader"] button { font-size: 0px !important; }
    [data-testid="stFileUploader"] button::after {
        content: "选择图片";
        font-size: 14px !important;
        visibility: visible;
        display: block;
    }
    
    /* 全局禁用标题旁的锚点超链接图标 (解决 image_d00257 问题) */
    .stApp a.element-container:hover { display: none !important; }
    
    /* 侧边栏文字颜色加固：确保在白底模式下清晰可见 */
    [data-testid="stSidebar"] [data-testid="stText"], 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: #31333F !important; }

    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 统计逻辑 ---
@st.cache_resource
def get_traffic_stats():
    return {"total": 0, "codes": {}}

stats = get_traffic_stats()

# --- 4. 授权门禁系统 ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        # 设置 anchor=False 禁用标题超链接
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

# --- 5. 核心逻辑入口 ---
if check_auth():
    with st.sidebar:
        st.title("🛠️ 设计参数", anchor=False)
        st.caption("技术支持：观世不笑")
        style_list = {
            '原图风格 (Original)': "Maintain original lighting and layout.",
            '温馨暖调 (Warm)': "Apply cozy, warm, and high-end interior lighting.",
            '清冷高级 (Cool)': "Apply modern, cool, and premium chic aesthetic.",
            '复古胶片 (Vintage)': "Apply nostalgic film vibe with realistic textures.",
            '极简主义 (Minimalist)': "Focus on clean lines and simple lighting."
        }
        style_name = st.selectbox("选择设计风格", list(style_list.keys()))
        res = st.select_slider("选择生成画质", options=["1K", "2K", "4K"], value="2K")
        show_list = st.toggle("📋 同步生成主材清单", value=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传", anchor=False)
        # 1. 房间底图 (带预览)
        room_img = st.file_uploader("1. 房间底图", type=['png', 'jpg', 'jpeg'])
        if room_img:
            st.image(room_img, caption="✅ 房间底图预览", use_container_width=True)
            
        # 2. 家具素材 (带多图预览)
        items_img = st.file_uploader("2. 家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if items_img:
            preview_cols = st.columns(4)
            for idx, f in enumerate(items_img):
                with preview_cols[idx % 4]:
                    st.image(f, use_container_width=True)
                    
        # 3. 补充描述 (业务引导占位符)
        note = st.text_area("3. 补充描述", placeholder="例如：将上传的窗帘替换掉原来的窗帘，并调整室内光影。")

    with col2:
        st.subheader("✨ 渲染预览", anchor=False)
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_img:
                st.warning("请先上传 1. 房间底图。")
            else:
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # 动态探测 2026 最新可用模型
                    target_models = ['models/gemini-1.5-pro', 'models/gemini-1.5-flash']
                    available_names = [m.name for m in genai.list_models()]
                    selected = next((m for m in target_priority if m in available_names), available_names[0])
                    model = genai.GenerativeModel(selected)

                    with st.spinner(f"正在驱动 {selected.split('/')[-1]} 渲染中..."):
                        # 构建多模态载荷
                        payload = [Image.open(room_img)]
                        for f in items_img:
                            payload.append(Image.open(f))
                        
                        # 核心：强化视觉生成指令
                        p_text = f"""
                        TASK: Photorealistic Interior Rendering.
                        INPUT: Image 1 is the room. Other images are furniture items.
                        INSTRUCTION: Seamlessly blend the items into the room.
                        STYLE: {style_list[style_name]}
                        DETAILS: {note if note else "Natural integration."}
                        FORMAT: Output the edited image first, followed by a markdown table of materials if requested.
                        """
                        if show_list: p_text += "\n[MANDATORY: Include Material List Table]"
                        payload.append(p_text)
                        
                        response = model.generate_content(payload)
                        
                        if response.candidates:
                            has_image = False
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.image(part.inline_data.data, caption=f"渲染完成 ({res})", use_container_width=True)
                                    st.download_button("📥 下载设计高清图", part.inline_data.data, "luolai_pro_design.png", "image/png")
                                    has_image = True
                                elif hasattr(part, 'text') and part.text:
                                    st.markdown(part.text)
                            
                            if has_image:
                                stats["total"] += 1
                                usr = st.session_state["current_user"]
                                stats["codes"][usr] = stats["codes"].get(usr, 0) + 1
                                st.success("设计方案渲染成功！")
                                st.balloons()
                            else:
                                st.error("⚠️ AI 仅返回了文字建议，未生成图像。请尝试简化图片背景或在‘补充描述’中明确写下‘生成渲染图’。")
                except Exception as e:
                    st.error(f"渲染中发生错误：{str(e)}")

# --- 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业授权版 | 罗莱软装官方技术支持</p>", unsafe_allow_html=True)
