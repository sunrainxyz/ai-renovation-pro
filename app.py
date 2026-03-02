import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import requests
import base64

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

# --- 3. 统计与持久化状态初始化 ---
@st.cache_resource
def get_traffic_stats():
    return {"total": 0, "codes": {}}

stats = get_traffic_stats()

if "result_image" not in st.session_state:
    st.session_state["result_image"] = None
if "result_prompt" not in st.session_state:
    st.session_state["result_prompt"] = None

# --- 核心组件：沉浸式大图弹窗 ---
@st.dialog("🔍 超清细节预览", width="large")
def show_zoomed_image(image_bytes):
    final_image = Image.open(io.BytesIO(image_bytes))
    st.image(final_image, use_container_width=True)

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

# --- 核心函数 A：安全图片预处理 ---
def optimize_image_for_api(uploaded_file, max_size=(1024, 1024)):
    try:
        img = Image.open(uploaded_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        st.error(f"图片处理失败：{str(e)}")
        return None

# --- 核心函数 B：智能计算原图画幅 ---
def get_closest_aspect_ratio(image_file):
    try:
        img = Image.open(image_file)
        w, h = img.size
        ratio = w / h
        
        supported_ratios = {
            "1:1": 1.0, "4:3": 4/3, "3:4": 3/4, "16:9": 16/9, "9:16": 9/16
        }
        closest_ratio_key = min(supported_ratios.items(), key=lambda x: abs(x[1] - ratio))[0]
        return closest_ratio_key
    except Exception:
        return "1:1" 

# --- 5. 主程序入口 ---
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
            '✨ 保持原图 (Original)': "Maintain the original lighting, color palette, and architectural style of the base image exactly.",
            '温馨暖调 (Warm)': "Cozy, warm, soft lighting, inviting atmosphere, wood or creamy tones.",
            '清冷高级 (Cool)': "Modern, cool-toned, chic, minimalist, high-end aesthetics.",
            '极简主义 (Minimalist)': "Clean lines, negative space, soft diffuse lighting, minimalist decor.",
            '复古胶片 (Vintage)': "Vintage film aesthetic, nostalgic mood, realistic textures, moody lighting."
        }
        style_name = st.selectbox("选择生图风格滤镜", list(style_list.keys()))
        
        aspect_ratio_map = {
            "✨ 智能匹配原图比例": "auto", "16:9 (标准横向)": "16:9", "4:3 (中画幅横向)": "4:3",
            "1:1 (正方形)": "1:1", "3:4 (中画幅竖向)": "3:4", "9:16 (手机竖屏)": "9:16"
        }
        aspect_ratio = st.selectbox("输出画幅", list(aspect_ratio_map.keys()))
        
        st.divider()
        enable_ref = st.toggle("🎯 启用几何特征强控 (文本级精准还原)", value=True, help="开启后，AI将深度解析素材轮廓与色彩，强制锁定 Imagen 绘画结构。")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 素材上传", anchor=False)
        room_img = st.file_uploader("1.房间底图 (必需)", type=['png', 'jpg', 'jpeg'])
        if room_img:
            st.image(room_img, caption="✅ 底图已就绪", use_container_width=True)
            
        items_img = st.file_uploader("2.家具素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if items_img:
            preview_cols = st.columns(4)
            for idx, f in enumerate(items_img):
                with preview_cols[idx % 4]:
                    st.image(f, use_container_width=True)
                    
        note = st.text_area(
            "3.补充描述", 
            value="请将我上传的窗帘素材安装并替换掉房间原有的窗帘，注意保持布料的垂坠感与室内光影的自然和谐。"
        )

    with col2:
        st.subheader("✨ AI装修模拟", anchor=False)
        
        if st.button("🚀 启动 Imagen 4.0 超写实渲染", type="primary", use_container_width=True):
            if not room_img:
                st.warning("请先上传 1. 房间底图。")
            else:
                st.session_state["result_image"] = None
                
                try:
                    api_key = st.secrets["GEMINI_API_KEY"]
                    genai.configure(api_key=api_key)
                    
                    final_ratio = aspect_ratio_map[aspect_ratio]
                    if final_ratio == "auto":
                        final_ratio = get_closest_aspect_ratio(room_img)
                        st.toast(f"📐 自动匹配生图比例为：{final_ratio}")
                    
                    with st.spinner("1/2: Gemini 正在进行结构特征提取与解析..."):
                        available_names = [m.name for m in genai.list_models()]
                        vision_models = ['models/gemini-2.5-pro', 'models/gemini-3.1-pro-preview', 'models/gemini-1.5-pro']
                        selected_vision = next((m for m in vision_models if m in available_names), available_names[0])
                        vision_model = genai.GenerativeModel(selected_vision)
                        
                        payload = []
                        optimized_room = optimize_image_for_api(room_img)
                        if optimized_room: payload.append(optimized_room)
                        
                        for f in items_img:
                            optimized_item = optimize_image_for_api(f)
                            if optimized_item: payload.append(optimized_item)
                        
                        # --- 核心进化：解剖级视觉特征提取 ---
                        prompt_engineer_task = f"""
                        You are a highly analytical interior design prompt engineer for the Imagen 4.0 generator.
                        Analyze the room's architecture and the uploaded furniture. 
                        Write a SINGLE, highly detailed, photorealistic text-to-image prompt in ENGLISH.
                        
                        Requirements:
                        1. Environment: Describe the interior architecture based on the first image.
                        2. Style: {style_list[style_name]}.
                        3. Task: {note if note else "Seamlessly integrate the items."}
                        """
                        
                        if enable_ref and items_img:
                            prompt_engineer_task += """
                            [ABSOLUTE REPLICATION PROTOCOL]: You must act as a precise visual scanner for the uploaded furniture/curtain.
                            You MUST extract and explicitly state in the prompt:
                            - The EXACT color palette (mention approximate hex codes or specific color names like 'Navy Blue #000080').
                            - The EXACT material and texture (e.g., 'heavy matte velvet', 'translucent linen', 'shiny silk').
                            - The EXACT pattern, fabric folds, hanging style (e.g., 'grommet top', 'pinch pleat'), and hardware.
                            FORCE the image generator to replicate this exact physical item. Do not invent any new design for the added item.
                            """
                        else:
                            prompt_engineer_task += "\n4. Seamlessly integrate the provided furniture items."
                            
                        prompt_engineer_task += "\nONLY output the final English prompt. NO explanatory text."
                        
                        payload.append(prompt_engineer_task)
                        vision_response = vision_model.generate_content(payload)
                        generated_prompt = vision_response.text.strip()

                    with st.spinner(f"2/2: Imagen 4.0 纯文本直驱渲染中..."):
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={api_key}"
                        
                        payload_data = {
                            "instances": [{"prompt": generated_prompt}],
                            "parameters": {"sampleCount": 1, "aspectRatio": final_ratio}
                        }
                        
                        resp = requests.post(url, json=payload_data)
                        
                        if resp.status_code == 200:
                            result_json = resp.json()
                            if "predictions" in result_json and len(result_json["predictions"]) > 0:
                                b64_image = result_json["predictions"][0]["bytesBase64Encoded"]
                                img_data = base64.b64decode(b64_image)
                                
                                st.session_state["result_image"] = img_data
                                st.session_state["result_prompt"] = generated_prompt
                                
                                stats["total"] += 1
                                usr = st.session_state["current_user"]
                                stats["codes"][usr] = stats["codes"].get(usr, 0) + 1
                                st.success("Imagen 渲染成功！")
                                st.balloons()
                            else:
                                st.error("API 返回成功，但未包含图像数据。")
                        else:
                            st.error(f"Imagen API 调用失败：HTTP {resp.status_code} - {resp.text}")
                            
                except Exception as e:
                    st.error(f"渲染链路发生异常：{str(e)}")

        if st.session_state.get("result_image"):
            final_image = Image.open(io.BytesIO(st.session_state["result_image"]))
            st.image(final_image, caption="✨ Imagen 4.0 渲染完成", use_container_width=True)
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                st.download_button(
                    label="📥 下载超清设计图", 
                    data=st.session_state["result_image"], 
                    file_name="luolai_imagen4_design.png", 
                    mime="image/png",
                    use_container_width=True
                )
            with btn_col2:
                if st.button("🔍 放大查看细节", use_container_width=True):
                    show_zoomed_image(st.session_state["result_image"])
            
            with st.expander("👀 查看底层特征强控指令 (Prompt)"):
                st.write(st.session_state["result_prompt"])

# --- 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 2026 商业授权版 | 罗莱软装官方技术支持</p>", unsafe_allow_html=True)
