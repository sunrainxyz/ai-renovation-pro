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

# --- 2. 深度精修 UI CSS ---
st.markdown("""
    <style>
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span { display: none !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {
        content: "将房间照片或家具图片拖拽至此处";
        font-size: 16px; font-weight: bold; color: #31333F; display: block; margin-bottom: 10px;
    }
    [data-testid="stFileUploader"] button { font-size: 0px !important; }
    [data-testid="stFileUploader"] button::after {
        content: "选择图片"; font-size: 14px !important; visibility: visible; display: block;
    }
    .stApp a.element-container:hover { display: none !important; }
    [data-testid="stSidebar"] [data-testid="stText"], 
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #31333F !important; }
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

# --- 5. 核心逻辑入口 ---
if check_auth():
    with st.sidebar:
        st.title("🛠️ 设计参数", anchor=False)
        st.caption("技术支持：观世不笑")
        style_list = {
            '温馨暖调 (Warm)': "温馨、柔和，偏向原木风或奶油风。",
            '清冷高级 (Cool)': "现代简约，偏向黑白灰或极简高定风。",
            '原图风格 (Original)': "保持原图的空间光影与硬装结构。"
        }
        style_name = st.selectbox("选择设计风格", list(style_list.keys()))
        show_list = st.toggle("📋 生成主材与采购清单", value=True)
        st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传", anchor=False)
        room_img = st.file_uploader("1. 房间底图 (必需)", type=['png', 'jpg', 'jpeg'])
        if room_img:
            st.image(room_img, caption="✅ 房间底图预览", use_container_width=True)
            
        items_img = st.file_uploader("2. 家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if items_img:
            preview_cols = st.columns(4)
            for idx, f in enumerate(items_img):
                with preview_cols[idx % 4]:
                    st.image(f, use_container_width=True)
                    
        note = st.text_area("3. 补充描述", placeholder="例如：请分析将这些家具放入房间后，空间色彩是否协调？")

    with col2:
        st.subheader("✨ AI 方案分析结果", anchor=False)
        if st.button("开始生成专业软装报告", type="primary", use_container_width=True):
            if not room_img:
                st.warning("请先上传 1. 房间底图。")
            else:
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # --- 核心修复：精准匹配您的超前 API 权限 ---
                    available_names = [m.name for m in genai.list_models()]
                    target_priority = [
                        'models/gemini-3.1-pro-preview', 
                        'models/gemini-2.5-pro', 
                        'models/gemini-2.5-flash'
                    ]
                    
                    # 绝对兜底机制，即使找不到优先模型，也抓取账号里的第一个可用模型
                    selected = next((m for m in target_priority if m in available_names), available_names[0])
                    model = genai.GenerativeModel(selected)

                    with st.spinner(f"正在驱动旗舰级 {selected.split('/')[-1]} 进行空间解析..."):
                        payload = [Image.open(room_img)]
                        for f in items_img:
                            payload.append(Image.open(f))
                        
                        p_text = f"""
                        作为一名顶级的室内软装设计师，请仔细观察我提供的第一张房间底图，以及后续的家具素材图。
                        客户要求的设计风格是：{style_list[style_name]}。
                        客户补充描述：{note if note else "无"}。
                        
                        请输出一份专业的软装诊断报告，包含：
                        1. 空间与光影分析
                        2. 家具融合度评价（这些家具放进去是否合适，为什么？）
                        3. 色彩搭配建议
                        """
                        if show_list: 
                            p_text += "\n4. **主材采购清单**（请务必使用 Markdown 表格形式列出图中涉及的家具和材质建议）。"
                            
                        payload.append(p_text)
                        response = model.generate_content(payload)
                        
                        if response.candidates:
                            st.markdown(response.text)
                            stats["total"] += 1
                            usr = st.session_state["current_user"]
                            stats["codes"][usr] = stats["codes"].get(usr, 0) + 1
                            st.success("诊断报告已生成！")
                            st.balloons()
                except Exception as e:
                    st.error(f"分析中发生错误：{str(e)}")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业授权版 | 罗莱软装官方技术支持</p>", unsafe_allow_html=True)
