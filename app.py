import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. 商业版页面配置 ---
st.set_page_config(page_title="AI装修模拟器-罗莱软装 Pro", page_icon="??", layout="wide")

# --- 2. 授权门禁系统 ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("?? AI 装修模拟器 · 罗莱软装专业版")
        st.info("本系统由【观世不笑】开发，仅供商业授权客户使用。")
        # 确保此处从 Secrets 读取 ACCESS_CODES
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
    # 侧边栏：风格与参数 (严格复刻 geminiService.ts 逻辑)
    with st.sidebar:
        st.title("??? 设计参数")
        st.caption("作者：观世不笑")
        
        # 风格滤镜映射表 (英文指令确保 AI 理解更精准)
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
        resolution = st.select_slider("生成画质 (Resolution)", options=["1K", "2K", "4K"], value="2K")
        st.divider()
        st.info("?? 建议：上传清晰、无遮挡的底图房间照片效果最佳。")

    # 主界面布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("??? 素材上传区")
        room_file = st.file_uploader("1. 上传【底图房间】(Base Room)", type=['png', 'jpg', 'jpeg'])
        furniture_files = st.file_uploader("2. 上传【家具/软装】素材 (多选)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        user_prompt = st.text_area("3. 补充描述 (可选)", placeholder="例如：将这把椅子放在窗户右侧...")

    with col2:
        st.subheader("? 装修预览区")
        if st.button("开始 Pro 级高保真渲染", type="primary", use_container_width=True):
            if not room_file:
                st.warning("请先上传底图房间照片。")
            else:
                try:
                    # 配置 API
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # 尝试调用最新预览模型，若失败则回退至 1.5-pro
                    try:
                        model = genai.GenerativeModel('gemini-3-pro-image-preview')
                    except:
                        model = genai.GenerativeModel('gemini-1.5-pro')

                    with st.spinner("AI 正在解析空间结构并融合素材..."):
                        # 准备多模态数据包
                        input_data = []
                        
                        # 1. 注入房间底图 (第一张为 Base Room)
                        base_img = Image.open(room_file)
                        input_data.append(base_img)
                        
                        # 2. 注入家具图片
                        for f_file in furniture_files:
                            input_data.append(Image.open(f_file))
                        
                        # 3. 注入复刻自 TS 的严格指令
                        core_prompt = f"""
                        [STRICT INSTRUCTION: PRESERVE ORIGINAL ROOM LAYOUT]
                        The first image provided is the "Base Room". 
                        The subsequent {len(furniture_files)} images are "New Furniture/Decor Items".
                        
                        CORE TASK: 
                        Synthesize a new image that looks exactly like the "Base Room" but with the "New Furniture" integrated into it.
                        
                        CONSTRAINTS:
                        1. STRICTLY PRESERVE the architecture: Keep walls, floor, ceiling, windows, and perspective EXACTLY as the first image. Do not remodel the room.
                        2. Naturally integrate furniture with realistic shadows, scale, and perspective.
                        3. STYLE/FILTER: {filter_prompts[style_name]}
                        
                        User extra note: {user_prompt if user_prompt else "请将素材自然融入房间。"}
                        """
                        input_data.append(core_prompt)
                        
                        # 执行生成
                        response = model.generate_content(input_data)
                        
                        # 修复逻辑：遍历 parts 处理多模态结果
                        if response.candidates:
                            has_output = False
                            for part in response.candidates[0].content.parts:
                                # 处理生成的图片
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.success("?? 最终装修效果图已生成！")
                                    st.image(part.inline_data.data, caption=f"渲染画质: {resolution}", use_container_width=True)
                                    # 提供下载按钮
                                    st.download_button(
                                        label="?? 下载高清设计图",
                                        data=part.inline_data.data,
                                        file_name="renovation_design.png",
                                        mime="image/png"
                                    )
                                    has_output = True
                                
                                # 处理生成的文字说明
                                elif hasattr(part, 'text') and part.text:
                                    st.info("?? AI 设计建议：")
                                    st.markdown(part.text)
                                    has_output = True
                            
                            if has_output:
                                st.balloons()
                            else:
                                st.error("AI 未返回有效内容，请检查素材后重试。")
                                
                except Exception as e:
                    # 捕获详细错误，方便调试
                    st.error(f"生成失败：{str(e)}")
                    if "inline_data" in str(e):
                        st.info("提示：请确保您的 API Key 拥有 Multimodal (多模态) 生成权限。")

# --- 4. 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 品牌授权 | 罗莱软装官方合作伙伴</p>", unsafe_allow_html=True)
