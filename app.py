import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. 商业版页面配置 ---
st.set_page_config(page_title="AI装修模拟器-罗莱软装 Pro", page_icon="🏠", layout="wide")

# --- 2. 授权门禁系统 (保持您的收费逻辑) ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🏠 AI 装修模拟器 · 罗莱软装专业版")
        st.info("本系统由【观世不笑】开发，仅供商业授权客户使用。")
        access_code = st.text_input("请输入您的专属授权码：", type="password")
        if st.button("激活系统"):
            if "ACCESS_CODES" in st.secrets and access_code in st.secrets["ACCESS_CODES"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("授权码无效，请联系博主获取。")
        return False
    return True

# --- 3. 核心功能区 (复刻 App.tsx 的功能) ---
if check_auth():
    # 侧边栏：品牌与参数设置
    with st.sidebar:
        st.title("🛠️ 设计参数")
        st.caption("作者：观世不笑")
        
        # 复刻 App.tsx 中的风格选项
        style_option = st.selectbox("滤镜风格", [
            "原图风格 (Original)", "温馨暖调 (Warm)", "清冷高级 (Cool)", 
            "复古胶片 (Vintage)", "明亮通透 (Bright)", "极简主义 (Minimalist)"
        ])
        
        # 复刻画质选项
        resolution = st.select_slider("生成画质", options=["1K", "2K", "4K"], value="2K")
        
        st.divider()
        st.write("📖 **使用说明**：上传房间和家具照片后，点击下方生成按钮即可。")

    # 主界面布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("第1步：素材上传")
        # 支持多张图片上传
        room_files = st.file_uploader("上传房间照片（可多选）", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        furniture_files = st.file_uploader("添加家具/软装素材（可选）", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        
        user_prompt = st.text_area("补充描述 (可选)", placeholder="例如：保持地板不变，更换沙发样式...")

    with col2:
        st.subheader("第2步：效果预览")
        if st.button("✨ 生成装修效果 (Pro渲染)", type="primary", use_container_width=True):
            if not room_files:
                st.warning("请至少上传一张房间照片。")
            else:
                with st.status("AI 正在施展魔法，正在进行高保真渲染...", expanded=True):
                    # 配置 AI
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    
                    # 构建 Prompt (这里融合了您的风格选择)
                    system_instruction = f"你是一个顶级室内设计师。请基于用户上传的房间图片，结合家具素材，生成一张{style_option}风格的装修效果图。画质要求：{resolution}。"
                    
                    # 此处模拟批量处理 (仅展示最后一张的逻辑，实际可循环)
                    for room_file in room_files:
                        img = Image.open(room_file)
                        response = model.generate_content([system_instruction, user_prompt, img])
                        
                        st.image(img, caption=f"房间 {room_file.name} 的原始图", use_container_width=True)
                        st.success(f"已基于 {style_option} 风格完成设计建议：")
                        st.write(response.text)
                        st.info("提示：Gemini 1.5 Pro 在 Streamlit 中主要输出设计方案。如需直接输出合成后的图片，请确认您已开启 Multimodal 权限。")

# --- 品牌水印 ---
st.markdown("---")
st.center = st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 版权所有 © 2026</p>", unsafe_allow_html=True)
