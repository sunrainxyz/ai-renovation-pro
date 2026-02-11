import streamlit as st
import google.generativeai as genai

# 页面配置
st.set_page_config(page_title="AI装修模拟器-专业版", page_icon="🏠")

# 1. 登录验证逻辑
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🏠 AI 装修模拟器 · 授权登录")
        access_code = st.text_input("请输入您的专属授权码：", type="password")
        if st.button("激活"):
            if access_code in st.secrets["gsbx2025"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("验证失败，请联系博主获取。")
        return False
    return True

# 2. 验证通过后的功能
if check_auth():
    st.title("🛠️ AI 装修模拟器")
    st.caption("观世不笑 · 出品 | 您的智能设计管家")
    
    # 初始化 API
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro')

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("请描述您的装修需求..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        # 核心人设：装修专家
        system_prompt = "你是一个精通家装预算、空间规划和现代美学的顶级设计师。请给出专业且细致的建议。"
        response = model.generate_content(system_prompt + prompt)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
