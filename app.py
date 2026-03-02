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
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; }
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

# --- 核心新增：安全图片预处理函数 ---
def optimize_image_for_api(uploaded_file, max_size=(1024, 1024)):
    """将上传的图片转化为 RGB 模式，并等比压缩到安全尺寸，防止 API 卡死"""
    try:
        img = Image.open(uploaded_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        st.error(f"图片处理失败，请更换格式：{str(e)}")
        return None

# --- 5. 核心逻辑入口 ---
if check_auth():
    if st.session_state["current_user"] == "ADMIN":
        with st.sidebar:
            st.header("📈 后台流量监控", anchor=False)
            st.metric("累计生图次数", stats["total"])
            st.table(stats["codes"])
            if st.button("重置统计记录"):
                stats["total"] = 0; stats["codes"] = {}; st.rerun()
            st.divider()

    with st.sidebar:
        st.title("🛠️ 渲染参数 (Imagen 4.0)", anchor=False)
        st.caption("视觉引擎：Google Imagen 4 | 技术支持：观世不笑")
        style_list = {
            '温馨暖调 (Warm)': "Cozy, warm, soft lighting, inviting atmosphere, wood or creamy tones.",
            '清冷高级 (Cool)': "Modern, cool-toned, chic, minimalist, high-end aesthetics.",
            '极简主义 (Minimalist)': "Clean lines, negative space, soft diffuse lighting, minimalist decor.",
            '复古胶片 (Vintage)': "Vintage film aesthetic, nostalgic mood, realistic textures, moody lighting."
        }
        style_name = st.selectbox("选择生图风格滤镜", list(style_list.keys()))
        aspect_ratio_map = {"16:9 (横向)": "16:9", "1:1 (方形)": "1:1", "9:16 (竖向)": "9:16"}
        aspect_ratio = st.selectbox("输出画幅", list(aspect_ratio_map.keys()))
        st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传", anchor=False)
        room_img = st.file_uploader("1. 房间底图 (必需)", type=['png', 'jpg', 'jpeg'])
        if room_img:
            st.image(room_img, caption="✅ 底图已就绪", use_container_width=True)
            
        items_img = st.file_uploader("2. 家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if items_img:
            preview_cols = st.columns(4)
            for idx, f in enumerate(items_img):
                with preview_cols[idx % 4]:
                    st.image(f, use_container_width=True)
                    
        note = st.text_area("3. 补充描述", placeholder="例如：保留原有木地板，将上传的灰色沙发放在窗边。")

    with col2:
        st.subheader("✨ 旗舰视觉生成", anchor=False)
        if st.button("🚀 启动 Imagen 4.0 超写实渲染", type="primary", use_container_width=True):
            if not room_img:
                st.warning("请先上传 1. 房间底图。")
            else:
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # =========================================================
                    # STEP 1: Gemini 视觉解析 (带防卡死图片压缩)
                    # =========================================================
                    with st.spinner("1/2: Gemini 视觉解析中 (已开启提速压缩)..."):
                        available_names = [m.name for m in genai.list_models()]
                        vision_models = ['models/gemini-2.5-pro', 'models/gemini-3.1-pro-preview', 'models/gemini-1.5-pro']
                        selected_vision = next((m for m in vision_models if m in available_names), available_names[0])
                        
                        vision_model = genai.GenerativeModel(selected_vision)
                        
                        # 应用图片预压缩逻辑
                        payload = []
                        optimized_room = optimize_image_for_api(room_img)
                        if optimized_room: payload.append(optimized_room)
                        
                        for f in items_img:
                            optimized_item = optimize_image_for_api(f)
                            if optimized_item: payload.append(optimized_item)
                        
                        prompt_engineer_task = f"""
                        You are an expert interior design prompt engineer for an AI image generator.
                        Analyze the room's architecture, lighting, and the uploaded furniture. 
                        Write a SINGLE, highly detailed, photorealistic text-to-image prompt in ENGLISH.
                        
                        Requirements:
                        1. Describe the interior architecture based on the first image.
                        2. Seamlessly integrate the provided furniture items.
                        3. Style: {style_list[style_name]}.
                        4. User's specific notes: {note if note else "Blend naturally"}.
                        5. Add photographic modifiers (e.g., photorealistic, 8k, ray tracing, architectural photography).
                        
                        ONLY output the final English prompt. No explanation.
                        """
                        payload.append(prompt_engineer_task)
                        vision_response = vision_model.generate_content(payload)
                        generated_prompt = vision_response.text.strip()
                        print(f"✅ 生成的 Prompt: {generated_prompt}")

                    # =========================================================
                    # STEP 2: Imagen 4.0 执行渲染
                    # =========================================================
                    with st.spinner("2/2: Imagen 4.0 正在执行逼真光影渲染... (预计 10-20 秒)"):
                        image_result = genai.generate_images(
                            prompt=generated_prompt,
                            number_of_images=1,
                            model="models/imagen-4.0-generate-001",
                            aspect_ratio=aspect_ratio_map[aspect_ratio]
                        )
                        
                        if image_result and image_result.images:
                            img_data = image_result.images[0].image.image_bytes
                            final_image = Image.open(io.BytesIO(img_data))
                            
                            st.image(final_image, caption=f"✨ Imagen 4.0 渲染完成", use_container_width=True)
                            
                            st.download_button(
                                label="📥 下载超清设计图", 
                                data=img_data, 
                                file_name="luolai_imagen4_design.png", 
                                mime="image/png",
                                use_container_width=True
                            )
                            
                            stats["total"] += 1
                            usr = st.session_state["current_user"]
                            stats["codes"][usr] = stats["codes"].get(usr, 0) + 1
                            st.success("Imagen 超写实渲染成功！")
                            st.balloons()
                            
                            with st.expander("👀 查看底层生图核心指令 (Prompt)"):
                                st.write(generated_prompt)
                        else:
                            st.error("未能生成图像，可能触发了安全拦截，请修改提示词。")
                            
                except Exception as e:
                    st.error(f"渲染链路发生异常：{str(e)}")

# --- 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业授权版 | 罗莱软装官方技术支持</p>", unsafe_allow_html=True)
