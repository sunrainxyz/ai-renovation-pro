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

# --- 2. 界面汉化与 UI 优化 (CSS 注入) ---
st.markdown("""
    <style>
    /* 汉化上传框提示语 "Drag and drop file here" */
    [data-testid="stFileUploaderDropzoneInstructions"] div span {
        visibility: hidden;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] div span::before {
        content: "将房间照片或家具图片拖拽至此处";
        visibility: visible;
        display: block;
    }
    
    /* 汉化上传按钮 "Browse files" */
    [data-testid="stFileUploader"] button {
        visibility: hidden;
        line-height: 0;
    }
    [data-testid="stFileUploader"] button::after {
        content: "从手机相册选择";
        visibility: visible;
        display: block;
        line-height: 2.1;
    }
    
    /* 汉化文件大小限制提示 */
    [data-testid="stFileUploaderDropzoneInstructions"] div small {
        visibility: hidden;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] div small::before {
        content: "单文件上限 200MB (支持 JPG/PNG)";
        visibility: visible;
        display: block;
    }

    /* 隐藏 Streamlit 默认页脚 */
    footer {visibility: hidden;}
    
    /* 调色：侧边栏品牌化 */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 流量监控核心逻辑 (全局共享) ---
@st.cache_resource
def get_traffic_stats():
    # 初始化统计：总请求数、各授权码消耗数
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
        st.info("本系统已开启商业授权保护，请使用专属授权码登录。")
        
        # 居中布局登录框
        col_l, col_m, col_r = st.columns([1, 2, 1])
        with col_m:
            access_code = st.text_input("请输入您的专属授权码：", type="password")
            if st.button("激活系统并开始设计", use_container_width=True, type="primary"):
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
                    st.error("授权码无效，请联系博主【观世不笑】获取。")
        return False
    return True

# --- 5. 核心业务流程 ---
if check_auth():
    # 管理员监控面板
    if st.session_state["current_user"] == "ADMIN":
        with st.sidebar:
            st.header("📈 流量监控后台")
            st.metric("累计生成次数", stats["total"])
            st.write("**授权码消耗排名：**")
            st.table(stats["codes"])
            if st.button("重置统计记录"):
                stats["total"] = 0
                stats["codes"] = {}
                st.rerun()
            st.divider()

    with st.sidebar:
        st.title("🛠️ 设计参数")
        st.caption("技术支持：观世不笑")
        
        # 风格映射
        filter_prompts = {
            '原图风格 (Original)': "Maintain the original lighting and architectural style.",
            '温馨暖调 (Warm)': "Apply a cozy, warm, and inviting home atmosphere.",
            '清冷高级 (Cool)': "Apply a modern, minimalist, cool-toned high-end aesthetic.",
            '复古胶片 (Vintage)': "Use a nostalgic, vintage film aesthetic for interior design.",
            '明亮通透 (Bright)': "Maximize natural light and airy, white-themed spaciousness.",
            '极简主义 (Minimalist)': "Focus on soft textures and clean lines, removing clutter."
        }
        style_name = st.selectbox("选择设计风格", list(filter_prompts.keys()))
        resolution = st.select_slider("输出画质", options=["1K", "2K", "4K"], value="2K")
        show_material_list = st.toggle("📋 同步生成主材清单", value=True)
        st.divider()
        st.markdown("### 💡 使用贴士\n1. 上传一张空房间作为底图\n2. 可上传多张家具图作为素材\n3. AI会自动完成空间融合")

    # 主操作区布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传")
        room_file = st.file_uploader("1. 房间底图 (关键素材)", type=['png', 'jpg', 'jpeg'])
        furniture_files = st.file_uploader("2. 家具/配饰素材 (可选，支持多张)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        user_prompt = st.text_area("3. 设计补充描述", placeholder="例如：保留原有木地板，将墙面换成奶咖色，把沙发放在窗边...")

    with col2:
        st.subheader("✨ 渲染预览")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_file:
                st.warning("请先上传底图照片，AI需要空间坐标进行建模。")
            else:
                try:
                    # API 初始化
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # 动态探测最佳可用模型 (优先使用 3.0 或 2.5 系列)
                    target_models = [
                        'models/gemini-3-pro-image-preview',
                        'models/gemini-2.5-pro',
                        'models/gemini-2.5-flash',
                        'models/gemini-2.0-flash'
                    ]
                    available_names = [m.name for m in genai.list_models()]
                    selected_model = next((m for m in target_models if m in available_names), 'models/gemini-1.5-pro')

                    model = genai.GenerativeModel(selected_model)
                    
                    with st.spinner(f"正在驱动 {selected_model.split('/')[-1]} 进行空间渲染..."):
                        # 构建多模态输入列表
                        input_payload = []
                        input_payload.append(Image.open(room_file))
                        for f in furniture_files:
                            input_payload.append(Image.open(f))
                        
                        # 商业 Prompt 注入
                        list_req = "And generate a 'Main Material List' in a Markdown table." if show_material_list else ""
                        final_prompt = f"""
                        [STRICT INSTRUCTION: PHOTOREALISTIC INTERIOR DESIGN]
                        Image 1 is the base room layout. Following images are reference furniture.
                        ACTION: Seamlessly blend furniture into the room.
                        STYLE: {filter_prompts[style_name]}
                        NOTE: {user_prompt if user_prompt else "Natural and professional integration."}
                        {list_req}
                        """
                        input_payload.append(final_prompt)
                        
                        response = model.generate_content(input_payload)
                        
                        if response.candidates:
                            has_img = False
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.image(part.inline_data.data, caption=f"渲染完成 (预设画质: {resolution})", use_container_width=True)
                                    st.download_button("📥 下载设计高清图", part.inline_data.data, "luolai_design.png", "image/png")
                                    has_img = True
                                elif hasattr(part, 'text') and part.text:
                                    st.markdown(part.text)
                            
                            if has_img:
                                # 成功后计数
                                stats["total"] += 1
                                usr = st.session_state["current_user"]
                                stats["codes"][usr] = stats["codes"].get(usr, 0) + 1
                                st.success(f"设计完成！该授权码已为您的客户累计服务 {stats['codes'][usr]} 次。")
                                st.balloons()
                            else:
                                st.error("AI 仅输出了文字建议，未能成功生成图像。请尝试简化补充描述。")
                except Exception as e:
                    st.error(f"渲染中发生意外：{str(e)}")

# --- 6. 品牌版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #bfbfbf; font-size: 0.8em;'>观世不笑 · 2026 商业授权版 | 罗莱软装官方技术支持</p>", unsafe_allow_html=True)
