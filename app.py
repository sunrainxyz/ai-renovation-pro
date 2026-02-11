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

# --- 3. 核心功能逻辑 ---
if check_auth():
    # 侧边栏：风格与参数 (复刻 geminiService.ts 中的滤镜逻辑)
    with st.sidebar:
        st.title("🛠️ 设计参数")
        st.caption("作者：观世不笑")
        
        # 风格滤镜映射表
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
        st.divider()
        st.info("💡 建议：上传清晰的侧视图或俯视图效果最佳。")

    # 主界面布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ 上传素材")
        room_file = st.file_uploader("1. 上传【底图房间】照片", type=['png', 'jpg', 'jpeg'])
        furniture_files = st.file_uploader("2. 上传【家具/软装】素材（可多选）", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        user_prompt = st.text_area("3. 补充描述", placeholder="例如：将那张沙发放在靠窗位置...")

    with col2:
        st.subheader("✨ 装修预览")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_file:
                st.warning("请先上传底图房间照片。")
            else:
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # 使用您 TS 代码中指定的最新模型
                    # 注意：如果 3-pro 暂不可用，代码会自动尝试 fallback 到 1.5-pro
                    model_name = 'gemini-3-pro-image-preview'
                    try:
                        model = genai.GenerativeModel(model_name)
                    except:
                        model = genai.GenerativeModel('gemini-1.5-pro')

                    with st.spinner("AI 正在解析空间结构并融合素材..."):
                        # 准备多模态数据包
                        input_data = []
                        
                        # 注入底图
                        base_img = Image.open(room_file)
                        input_data.append(base_img)
                        
                        # 注入所有家具素材
                        for f_file in furniture_files:
                            input_data.append(Image.open(f_file))
                        
                        # 构建核心 Prompt (严格复刻 TS 代码逻辑)
                        core_prompt = f"""
                        [STRICT INSTRUCTION: PRESERVE ORIGINAL ROOM LAYOUT]
                        The first image provided is the "Base Room". 
                        The subsequent images are "New Furniture/Decor Items".
                        
                        CORE TASK: Synthesize a new image that looks exactly like the "Base Room" but with the "New Furniture" integrated into it.
                        
                        CONSTRAINTS:
                        1. STRICTLY PRESERVE the architecture: Keep walls, floor, ceiling, windows, and perspective EXACTLY as the first image.
                        2. Naturally integrate furniture with realistic shadows and scale.
                        3. STYLE/FILTER: {filter_prompts[style_name]}
                        
                        User extra note: {user_prompt}
                        """
                        input_data.append(core_prompt)
                        
                        # 获取生成结果
                        response = model.generate_content(input_data)
                        
                        # 展示结果
                        if response.text:
                            st.image(base_img, caption="原始房间结构", use_container_width=True)
                            st.success("🎉 装修方案已生成！")
                            st.markdown(response.text)
                            st.balloons()
                except Exception as e:
                    st.error(f"生成失败：{str(e)}")

# --- 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 品牌授权 | 罗莱软装官方合作伙伴</p>", unsafe_allow_html=True)
