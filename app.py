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

# --- 2. 深度精修版 UI CSS (解决文字重影、侧边栏不可见及汉化问题) ---
st.markdown("""
    <style>
    /* 1. 彻底移除原英文标签，解决截图中的重影问题 */
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span {
        display: none !important;
    }
    /* 2. 汉化拖拽区域文字提示 */
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {
        content: "将图片拖拽至此处或点击“选择图片”按钮";
        font-size: 16px;
        font-weight: bold;
        color: #31333F;
        display: block;
        margin-bottom: 10px;
    }
    
    /* 3. 汉化上传按钮：精准修改为“选择图片” */
    [data-testid="stFileUploader"] button {
        font-size: 0px !important;
    }
    [data-testid="stFileUploader"] button::after {
        content: "选择图片";
        font-size: 14px !important;
        visibility: visible;
        display: block;
    }
    
    /* 4. 汉化底部格式提示词 */
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

    /* 5. 强制修正侧边栏颜色对比度 (解决文字“隐身”问题) */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] [data-testid="stText"], 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #31333F !important;
    }

    /* 6. 隐藏官方冗余元素 */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. 流量监控核心逻辑 (全局共享) ---
@st.cache_resource
def get_traffic_stats():
    # 初始化统计数据：总次数与分授权码统计
    return {"total": 0, "codes": {}}

stats = get_traffic_stats()

# --- 4. 授权门禁系统 ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🏠 AI 装修模拟器 · 罗莱软装专业版")
        st.info("本系统由【观世不笑】开发，仅供商业授权客户使用。")
        
        col_l, col_m, col_r = st.columns([1, 2, 1])
        with col_m:
            access_code = st.text_input("请输入您的专属授权码：", type="password")
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

# --- 5. 核心逻辑入口 ---
if check_auth():
    # 管理员监控界面
    if st.session_state["current_user"] == "ADMIN":
        with st.sidebar:
            st.header("📈 后台流量监控")
            st.metric("累计生成次数", stats["total"])
            st.table(stats["codes"])
            if st.button("清空统计数据"):
                stats["total"] = 0; stats["codes"] = {}; st.rerun()
            st.divider()

    with st.sidebar:
        st.title("🛠️ 设计参数")
        st.caption("技术支持：观世不笑")
        style_list = {
            '原图风格 (Original)': "Maintain original lighting.",
            '温馨暖调 (Warm)': "Apply cozy golden-hour lighting.",
            '清冷高级 (Cool)': "Apply modern cool-toned aesthetic.",
            '复古胶片 (Vintage)': "Apply nostalgic film vibe.",
            '极简主义 (Minimalist)': "Focus on clean lines."
        }
        style_name = st.selectbox("4.选择设计风格", list(style_list.keys()))
        res = st.select_slider("选择生成画质", options=["1K", "2K", "4K"], value="2K")
        show_list = st.toggle("📋 同步生成主材清单", value=True)

    # 主操作区布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传")
        # --- 精修修改点：增加 1-2-3 数字序列 ---
        room_img = st.file_uploader("1.房间底图", type=['png', 'jpg', 'jpeg'])
        items_img = st.file_uploader("2.家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        # --- 占位符引导更新 ---
        note = st.text_area("3.补充描述", placeholder="例如：将上传的窗帘替换掉原来的窗帘")

    with col2:
        st.subheader("✨ 渲染预览")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_img:
                st.warning("请先上传1号房间底图。")
            else:
                try:
                    # AI 配置
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # 动态探测最佳模型 (优先使用您权限内的 Pro 系列)
                    target_models = ['models/gemini-3-pro-image-preview', 'models/gemini-2.5-pro', 'models/gemini-2.0-flash']
                    available_names = [m.name for m in genai.list_models()]
                    selected = next((m for m in target_models if m in available_names), 'models/gemini-1.5-pro')
                    
                    model = genai.GenerativeModel(selected)

                    with st.spinner(f"正在驱动 {selected.split('/')[-1]} 渲染中..."):
                        # 准备多模态数据包
                        payload = [Image.open(room_img)]
                        for f in items_img:
                            payload.append(Image.open(f))
                        
                        prompt_text = f"STYLE: {style_list[style_name]}. {note}. "
                        if show_list: prompt_text += "Include a material list table."
                        payload.append(prompt_text)
                        
                        # 调用 AI 执行生成
                        response = model.generate_content(payload)
                        
                        # 渲染输出
                        if response.candidates:
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.image(part.inline_data.data, caption=f"渲染完成 ({res})", use_container_width=True)
                                    st.download_button("📥 下载设计高清图", part.inline_data.data, "luolai_design.png", "image/png")
                                elif hasattr(part, 'text') and part.text:
                                    st.markdown(part.text)
                            
                            # 统计计费逻辑
                            stats["total"] += 1
                            usr = st.session_state["current_user"]
                            stats["codes"][usr] = stats["codes"].get(usr, 0) + 1
                            st.success("设计渲染成功！")
                            st.balloons()
                
                # --- 语法修复：补全缺失的 except 块 ---
                except Exception as e:
                    st.error(f"渲染中发生错误：{str(e)}")

# --- 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业授权版 | 罗莱软装官方技术支持</p>", unsafe_allow_html=True)
