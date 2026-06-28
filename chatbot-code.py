# -*- coding: utf-8 -*-
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import ClientError
import PIL.Image
import io
import os
import time

START_ICON_PATH = "start_icon.png"
BOT_ICON_PATH = "bot_icon.png"
assistant_icon = BOT_ICON_PATH if os.path.exists(BOT_ICON_PATH) else "🤖"

st.set_page_config(
    page_title="大崎上島 チャットボット", 
    page_icon=BOT_ICON_PATH, 
    layout="centered",
    initial_sidebar_state="expanded"
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "started" not in st.session_state:
    st.session_state.started = False

if not st.session_state.started:
    css_template = f"""
    <style>
        .welcome-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            width: 100%;
            padding: 4rem 0 0 0;
        }}
        .bubble {{
            position: relative;
            background: #f0f2f6;
            border-radius: 20px;
            padding: 20px 35px;
            margin-bottom: 40px;
            font-size: 1.8rem;
            font-weight: bold;
            color: #31333F;
            box-shadow: 0 6px 12px rgba(0,0,0,0.08);
            display: inline-block;
            max-width: 100%;
        }}
        .bubble:after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            width: 0;
            height: 0;
            border: 35px solid transparent;
            border-top-color: #f0f2f6;
            border-bottom: 0;
            border-left: 0;
            margin-left: -10px;
            margin-bottom: -35px;
        }}
        .inline-chat-input .stChatInput {{
            position: static !important;
            padding: 0 !important;
            width: 100% !important;
            max-width: 700px;
            margin: 0 auto !important;
        }}
        .stChatInput textarea {{
            font-size: 1.3rem !important;
            line-height: 1.6 !important;
            padding: 15px 20px !important;
            border-radius: 15px !important;
        }}
        .stChatInput button {{
            right: 15px !important;
            bottom: 12px !important;
        }}
        .typing-effect {{
            white-space: nowrap;
            overflow: hidden;
            border-right: 3px solid #FF4B4B;
            animation: typing 2.5s steps(20, end), blink .75s step-end infinite;
        }}
        @keyframes typing {{ from {{ width: 0 }} to {{ width: 100% }} }}
        @keyframes blink {{ from, to {{ border-color: transparent }} 50% {{ border-color: #FF4B4B }} }}
    </style>
    """
else:
    css_template = f"""
    <style>
        .stApp {{
            background-image: url("{START_ICON_PATH}");
            background-repeat: no-repeat;
            background-position: center 60%;
            background-size: 550px; 
            background-attachment: fixed;
        }}
        
        @media (prefers-color-scheme: dark) {{
            .main .block-container {{
                background-color: rgba(27, 28, 34, 0.85) !important;
                backdrop-filter: blur(1px);
                border-radius: 20px;
                padding: 3rem;
            }}
            .stChatMessage {{
                background-color: rgba(43, 44, 54, 0.9) !important;
                color: #fafafa !important;
                border-radius: 15px;
                margin-bottom: 10px;
            }}
        }}

        @media (prefers-color-scheme: light) {{
            .main .block-container {{
                background-color: rgba(255, 255, 255, 0.85) !important;
                backdrop-filter: blur(1px);
                border-radius: 20px;
                padding: 3rem;
            }}
            .stChatMessage {{
                background-color: rgba(240, 242, 246, 0.9) !important;
                color: #31333F !important;
                border-radius: 15px;
                margin-bottom: 10px;
            }}
        }}

        .stChatMessage p, .stChatMessage span, .stChatMessage div {{
            color: inherit !important;
        }}

        .stChatMessage img {{
            opacity: 1.0 !important;
            visibility: visible !important;
        }}
    </style>
    """

st.markdown(css_template, unsafe_allow_html=True)


@st.cache_resource
def init_api_and_knowledge():
    txt_path = "knowledge.txt"
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            system_instruction = f.read()
    else:
        system_instruction = "あなたは広島県大崎上島特化型AIです。"
        
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        
    client = genai.Client(api_key=api_key)
    
    return client, system_instruction

client, system_instruction = init_api_and_knowledge()

sidebar_prompt = None

with st.sidebar:
    st.write("### メニュー")
    if st.button("🔄 会話をリセット"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
    
    st.write("---")
    st.write("**👇気になることを質問！**")
    if st.button("⚓ 大崎上島へのアクセスは？", use_container_width=True):
        sidebar_prompt = "大崎上島へのアクセス方法（フェリーなど）について詳しく教えてください。"
    if st.button("🍊 特産品は何がある？", use_container_width=True):
        sidebar_prompt = "大崎上島の有名な特産品やグルメを教えてください。"
    if st.button("🗺️ おすすめの観光スポットは？", use_container_width=True):
        sidebar_prompt = "大崎上島で行くべきおすすめの観光スポットを教えてください。"
    
    st.write("---")
    st.write("**画像管理**")
    uploaded_file = st.file_uploader("写真をアップロードしてください", type=["jpg", "jpeg", "png"])
    
    image = None
    if uploaded_file is not None:
        image_obj = PIL.Image.open(uploaded_file)
        use_image = st.checkbox("この画像をAIに参照させる", value=True)
        if use_image:
            image = image_obj
            st.image(image, caption="現在この画像を参照中", use_container_width=True)
        else:
            st.image(image_obj, caption="現在画像を参照していません", use_container_width=True)
    else:
        st.write("（画像がアップロードされていません）")


if not st.session_state.started and not sidebar_prompt:
    st.markdown('<div class="welcome-container">', unsafe_allow_html=True)
    st.markdown('<div class="bubble"><div class="typing-effect">大崎上島チャットボット!なんでも質問してね!</div></div>', unsafe_allow_html=True)
    
    if os.path.exists(START_ICON_PATH):
        st.image(START_ICON_PATH, width=700) 
    else:
        st.title("🏝️ (start_icon.png が見つかりません)")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="inline-chat-input">', unsafe_allow_html=True)
    init_input = st.chat_input("ここに最初の質問を入力してね！")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if init_input:
        st.session_state.messages.append({"role": "user", "content": init_input})
        st.session_state.started = True
        st.rerun()


else:
    if not st.session_state.started:
        st.session_state.started = True

    st.title("大崎上島チャットボット")
    
    for message in st.session_state.messages:
        icon = assistant_icon if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=icon):
            st.markdown(message["content"])

    if sidebar_prompt:
        st.session_state.messages.append({"role": "user", "content": sidebar_prompt})
        st.rerun()

    placeholder_text = "アップロードした画像について質問" if image else "メッセージを入力"
    chat_input_val = st.chat_input(placeholder_text)
    if chat_input_val:
        st.session_state.messages.append({"role": "user", "content": chat_input_val})
        st.rerun()

    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant", avatar=assistant_icon):
            status_placeholder = st.empty()
            
            def stream_gemini_response():
                formatted_contents = []
                recent_messages = st.session_state.messages[-6:]
                
                for msg in recent_messages:
                    if msg == recent_messages[-1] and msg["role"] == "user" and image is not None:
                        img_byte_arr = io.BytesIO()
                        image_format = image.format if image.format else "PNG"
                        image.save(img_byte_arr, format=image_format)
                        img_bytes = img_byte_arr.getvalue()
                        mime_type = f"image/{image_format.lower()}"
                        if mime_type == "image/jpg":
                            mime_type = "image/jpeg"
                        
                        formatted_contents.append(
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                                    types.Part.from_text(text=msg["content"])
                                ]
                            )
                        )
                    else:
                        role_map = "user" if msg["role"] == "user" else "model"
                        formatted_contents.append(
                            types.Content(
                                role=role_map,
                                parts=[types.Part.from_text(text=msg["content"])]
                            )
                        )

                search_tool = types.Tool(google_search=types.GoogleSearch())
                status_placeholder.markdown("🔍 *インターネット上で情報を検索中...*")

                try:
                    response_stream = client.models.generate_content_stream(
                        model='gemini-2.5-flash',
                        contents=formatted_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            tools=[search_tool],
                            temperature=0.7
                        )
                    )
                    for chunk in response_stream:
                        if chunk.text:
                            status_placeholder.empty()
                            yield chunk.text
                    return 
                    
                except ClientError as e:
                    if e.code == 429:
                        status_placeholder.markdown("📋 *回線混雑のため、内蔵ナレッジベース（knowledge.txt）に切り替えて確認中...*")
                        try:
                            fallback_instruction = (
                                system_instruction + 
                                "\n\n【緊急指示】現在システム制限（クォータ制限）が発生しています。"
                                "Web検索は使わず、あなたの持っている大崎上島ナレッジベース（上記の知識）だけを使って回答してください。"
                                "もし上記の知識の中にユーザーの質問に答えるための明確な情報がない場合は、"
                                "他の言葉を一切付け加えずに、必ず『申し訳ございません。ただいま回答することが困難です。』とだけ返答してください。"
                            )
                            
                            response_stream = client.models.generate_content_stream(
                                model='gemini-2.5-flash',
                                contents=formatted_contents,
                                config=types.GenerateContentConfig(
                                    system_instruction=fallback_instruction,
                                    tools=[], 
                                    temperature=0.1
                                )
                            )
                            for chunk in response_stream:
                                if chunk.text:
                                    status_placeholder.empty()
                                    yield chunk.text
                            return
                        except Exception:
                            status_placeholder.empty()
                            yield "申し訳ございません。ただいま回答することが困難です。"
                            return
                    else:
                        status_placeholder.empty()
                        yield "申し訳ございません。ただいま回答することが困難です。"
                        return

            full_response = st.write_stream(stream_gemini_response())
            status_placeholder.empty()
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()
