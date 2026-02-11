import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. 商业版页面配置 ---
st.set_page_config(page_title="AI装修模拟器-罗莱软装 Pro", page_icon="🏠", layout="wide")

# --- 2. 流量监控核心逻辑 (全局共享) ---
@st.cache_resource
def get_traffic_stats():
    # 初始化监控数据：总请求数、各授权码使用频次
    return {"total": 0, "codes": {}}

stats = get_traffic_stats()

# --- 3. 授权门禁系统 ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = None

    if not st.session_state["authenticated"]:
        st.title("🏠 AI 装修模拟器 · 罗莱软装专业版")
        st.info("本系统由【观世不笑】开发，仅供商业授权客户使用。")
        access_code = st.text_input("请输入您的专属授权码：", type="password")
        if st.button("激活系统"):
            # 从 Secrets 获取配置
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
                st.error("授权码无效，请联系博主获取。")
        return False
    return True

# --- 4. 核心功能与渲染逻辑 ---
if check_auth():
    # 管理员面板：仅当登录者为 ADMIN 时显示
    if st.session_state["current_user"] == "ADMIN":
        with st.sidebar:
            st.header("📈 后台流量监控")
            st.metric("累计生成总次数", stats["total"])
            st.write("**授权码消耗统计：**")
            st.table(stats["codes"])
            if st.button("重置统计数据"):
                stats["total"] = 0
                stats["codes"] = {}
                st.rerun()
            st.divider()

    with st.sidebar:
        st.title("🛠️ 设计参数")
        st.caption("作者：观世不笑")
        
        # 复刻专业滤镜逻辑
        filter_prompts = {
            '原图风格 (Original)': "Maintain the original lighting and color grading of the room.",
            '温馨暖调 (Warm)': "Apply a warm, cozy, golden-hour lighting filter. Make the atmosphere inviting.",
            '清冷高级 (Cool)': "Apply a cool, modern, chic color grading with bluish/neutral tones.",
            '复古胶片 (Vintage)': "Apply a vintage film look, slightly desaturated with a nostalgic vibe.",
            '明亮通透 (Bright)': "Maximize natural light, make the room look airy, bright, and spacious.",
            '赛博朋克 (Cyberpunk)': "Apply dramatic neon lighting (pink/blue) for a cyberpunk aesthetic.",
            '极简主义 (Minimalist)': "Clean up the visual noise, focus on soft, even lighting and simple aesthetics."
        }
        style_name = st.selectbox("选择装修滤镜", list(filter_prompts.keys()))
        resolution = st.select_slider("生成画质", options=["1K", "2K", "4K"], value="2K")
        
        # 主材清单开关
        show_material_list = st.toggle("📋 自动生成主材清单", value=True, help="AI 将同步列出装修所需的核心材料建议")
        st.divider()
        st.info("💡 建议：上传清晰、无遮挡的底图房间照片效果最佳。")

    # 主界面布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传")
        room_file = st.file_uploader("1. 上传房间底图 (Base Room)", type=['png', 'jpg', 'jpeg'])
        furniture_files = st.file_uploader("2. 上传家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        user_prompt = st.text_area("3. 补充描述", placeholder="例如：保留地板颜色，更换现代简约风沙发...")

    with col2:
        st.subheader("✨ 渲染预览与清单")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_file:
                st.warning("请先上传底图房间照片。")
            else:
                try:
                    # 1. 配置 API
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # --- 核心修复：动态探测可用模型 ---
                    with st.spinner("正在连接 AI 设计引擎..."):
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        # 优先级排序：Pro-Latest > Pro > Flash
                        target_models = [
                            'models/gemini-1.5-pro-latest', 
                            'models/gemini-1.5-pro', 
                            'models/gemini-1.5-flash-latest',
                            'models/gemini-1.5-flash'
                        ]
                        
                        selected_model_name = None
                        for target in target_models:
                            if target in available_models:
                                selected_model_name = target
                                break
                        
                        if not selected_model_name:
                            st.error(f"⚠️ 权限不足：您的 API Key 无法访问所需的模型。当前可用：{available_models}")
                            st.stop()
                        
                        model = genai.GenerativeModel(selected_model_name)

                    with st.spinner(f"正在使用 {selected_model_name.split('/')[-1]} 深度解析中..."):
                        # 准备多模态数据包
                        input_data = []
                        base_img = Image.open(room_file)
                        input_data.append(base_img)
                        for f_file in furniture_files:
                            input_data.append(Image.open(f_file))
                        
                        # 集成主材清单指令
                        list_instruction = ""
                        if show_material_list:
                            list_instruction = """
                            Additionally, please provide a 'Main Material List' in a Markdown table format. 
                            Include columns: 序号, 项目名称, 推荐材质/规格, 选购建议。
                            """

                        # 核心 Prompt (严格复刻 TS 指令逻辑)
                        core_prompt = f"""
                        [STRICT INSTRUCTION: PRESERVE ORIGINAL ROOM LAYOUT]
                        The first image provided is the "Base Room". 
                        The subsequent {len(furniture_files)} images are "New Furniture/Decor Items".
                        
                        CORE TASK: Synthesize a new image that looks exactly like the "Base Room" but with the "New Furniture" integrated into it.
                        
                        CONSTRAINTS:
                        1. STRICTLY PRESERVE the architecture: Keep walls, floor, ceiling, windows, and perspective EXACTLY as the first image.
                        2. Naturally integrate furniture with realistic shadows, scale, and perspective.
                        3. STYLE/FILTER: {filter_prompts[style_name]}
                        4. Resolution target: {resolution}
                        
                        User extra note: {user_prompt if user_prompt else "请将素材自然融入房间。"}
                        {list_instruction}
                        """
                        input_data.append(core_prompt)
                        
                        # 执行生成
                        response = model.generate_content(input_data)
                        
                        # 展示结果
                        if response.candidates:
                            has_output = False
                            for part in response.candidates[0].content.parts:
                                # 处理图片
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.image(part.inline_data.data, caption=f"渲染完成 ({resolution})", use_container_width=True)
                                    st.download_button("📥 下载设计图", part.inline_data.data, "renovation_design.png", "image/png")
                                    has_output = True
                                # 处理文字（及清单表格）
                                elif hasattr(part, 'text') and part.text:
                                    st.info("📄 AI 设计师建议与主材清单：")
                                    st.markdown(part.text)
                                    has_output = True
                            
                            if has_output:
                                # 流量计费
                                stats["total"] += 1
                                current_user = st.session_state["current_user"]
                                stats["codes"][current_user] = stats["codes"].get(current_user, 0) + 1
                                st.success(f"渲染成功！已为您累计服务 {stats['codes'][current_user]} 次。")
                                st.balloons()
                            else:
                                st.error("AI 未能返回有效内容，请检查素材或重试。")
                                
                except Exception as e:
                    if "404" in str(e):
                        st.error("⚠️ 模型路径冲突：已尝试自动修复。请刷新页面重试，或检查 API Key 权限。")
                    else:
                        st.error(f"渲染错误：{str(e)}")

# --- 5. 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业版 | 罗莱软装主材清单系统</p>", unsafe_allow_html=True)
