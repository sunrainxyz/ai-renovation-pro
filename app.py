import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. 商业版页面配置 ---
st.set_page_config(page_title="AI装修模拟器-罗莱软装 Pro", page_icon="🏠", layout="wide")

# --- 2. 流量监控核心逻辑 (全局共享) ---
@st.cache_resource
def get_traffic_stats():
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

# --- 4. 核心功能与渲染逻辑 ---
if check_auth():
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
        show_material_list = st.toggle("📋 自动生成主材清单", value=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传")
        room_file = st.file_uploader("1. 上传房间底图", type=['png', 'jpg', 'jpeg'])
        furniture_files = st.file_uploader("2. 上传家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        user_prompt = st.text_area("3. 补充描述")

    with col2:
        st.subheader("✨ 渲染预览")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_file:
                st.warning("请先上传底图房间照片。")
            else:
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # --- 核心：根据您的权限列表进行最优匹配 ---
                    # 优先级：3.0 图像专用 > 2.5 Pro (最强逻辑) > 2.0 Flash (最新稳定)
                    target_models = [
                        'models/gemini-3-pro-image-preview',
                        'models/gemini-2.5-pro',
                        'models/gemini-2.5-flash',
                        'models/gemini-2.0-flash'
                    ]
                    
                    selected_model = None
                    # 自动从您的可用名单中寻找最匹配的
                    available_names = [m.name for m in genai.list_models()]
                    for target in target_models:
                        if target in available_names:
                            selected_model = target
                            break
                    
                    if not selected_model:
                        st.error("无法匹配到可用模型，请联系作者更新模型库。")
                        st.stop()

                    model = genai.GenerativeModel(selected_model)
                    
                    with st.spinner(f"正在使用 {selected_model.split('/')[-1]} 渲染中..."):
                        input_data = []
                        base_img = Image.open(room_file)
                        input_data.append(base_img)
                        for f_file in furniture_files:
                            input_data.append(Image.open(f_file))
                        
                        list_instr = "Include a 'Material List' table." if show_material_list else ""
                        core_prompt = f"""
                        [STRICT INSTRUCTION: PRESERVE ORIGINAL ROOM LAYOUT]
                        Base Room: 1st image. Task: Photorealistically integrate furniture.
                        STYLE: {filter_prompts[style_name]}
                        User request: {user_prompt}
                        {list_instr}
                        """
                        input_data.append(core_prompt)
                        
                        response = model.generate_content(input_data)
                        
                        if response.candidates:
                            has_image = False
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.image(part.inline_data.data, caption=f"渲染完成 ({resolution})", use_container_width=True)
                                    st.download_button("📥 下载设计图", part.inline_data.data, "result.png", "image/png")
                                    has_image = True
                                elif hasattr(part, 'text') and part.text:
                                    st.markdown(part.text)
                            
                            if has_image:
                                stats["total"] += 1
                                user = st.session_state["current_user"]
                                stats["codes"][user] = stats["codes"].get(user, 0) + 1
                                st.success(f"渲染成功！累计服务 {stats['codes'][user]} 次。")
                                st.balloons()
                except Exception as e:
                    st.error(f"渲染错误：{str(e)}")

# --- 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业版 | 罗莱软装官方合作伙伴</p>", unsafe_allow_html=True)
