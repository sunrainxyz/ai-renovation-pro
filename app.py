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
        # 风格映射表
        filter_prompts = {
            '原图风格 (Original)': "Maintain the original lighting.",
            '温馨暖调 (Warm)': "Apply a warm, cozy, golden-hour lighting filter.",
            '清冷高级 (Cool)': "Apply a cool, modern, chic color grading.",
            '极简主义 (Minimalist)': "Clean up visual noise, focus on simple aesthetics."
        }
        style_name = st.selectbox("选择装修滤镜", list(filter_prompts.keys()))
        resolution = st.select_slider("生成画质", options=["1K", "2K", "4K"], value="2K")

    # 主界面布局
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
                    # 配置 API
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-pro')

                    with st.spinner("AI 正在高保真渲染中，请稍候..."):
                        # 准备数据包
                        input_data = []
                        base_img = Image.open(room_file)
                        input_data.append(base_img)
                        for f_file in furniture_files:
                            input_data.append(Image.open(f_file))
                        
                        # 核心 Prompt
                        core_prompt = f"""
                        [STRICT INSTRUCTION: PRESERVE ORIGINAL ROOM LAYOUT]
                        The first image is the Base Room. The others are New Furniture.
                        Synthesize a new image integrating furniture naturally.
                        STYLE/FILTER: {filter_prompts[style_name]}
                        User note: {user_prompt if user_prompt else "请将素材自然融入房间。"}
                        """
                        input_data.append(core_prompt)
                        
                        # 执行 AI 生成
                        response = model.generate_content(input_data)
                        
                        # --- 核心：渲染结果展示 (修复处) ---
                        if response.candidates:
                            has_image = False
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.image(part.inline_data.data, caption=f"渲染完成 (画质: {resolution})", use_container_width=True)
                                    st.download_button("📥 下载设计图", part.inline_data.data, "result.png", "image/png")
                                    has_image = True
                                elif hasattr(part, 'text') and part.text:
                                    st.info("📄 AI 设计建议：")
                                    st.markdown(part.text)
                            
                            if has_image:
                                # 仅在成功生成图片后才计费/计数
                                stats["total"] += 1
                                user = st.session_state["current_user"]
                                stats["codes"][user] = stats["codes"].get(user, 0) + 1
                                st.success(f"渲染成功！该授权码本月已累计服务 {stats['codes'][user]} 次。")
                                st.balloons()
                            else:
                                st.error("AI 仅返回了文字，未能生成图片。请检查 Prompt 或素材。")
                except Exception as e:
                    st.error(f"渲染中发生错误：{str(e)}")

# --- 版权底栏 ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>观世不笑 · 流量监控中 | 罗莱软装商业版</p>", unsafe_allow_html=True)
