import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv

# 환경변수에서 API 키 불러오기
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")  # 또는 gemini-1.5-pro / flash

# 엑셀에서 선생님 데이터 불러오기
@st.cache_data
def load_teacher_json():
    df = pd.read_excel("ㄳㅎ.xlsx")
    teacher_list = []
    for _, row in df.iterrows():
        name = str(row.get("선생님 성함", "")).strip()
        subject = str(row.get("키워드", "")).strip()
        location = str(row.get("위치", "")).strip()
        purpose = str(row.get("목적", "")).strip()
        classnumber = str(row.get("들어가시는 수업 반", "")).strip()
        if name:
            teacher_list.append({
                "이름": name,
                "과목": subject or "정보 없음",
                "위치": location or "정보 없음",
                "설명": purpose or "정보 없음",
                "수업 반": classnumber or "정보 없음"
            })
    return teacher_list

teacher_knowledge = load_teacher_json()

# 대화 이력을 자연어로 정리
def format_history(messages):
    formatted = ""
    for m in messages:
        if m["role"] == "user":
            formatted += f'사용자가 이렇게 말했어: "{m["content"]}"\n'
        else:
            formatted += f'AI가 이렇게 응답했어: "{m["content"]}"\n'
    return formatted.strip()

# 프롬프트 생성 함수
def build_prompt(messages, teacher_data):
    history = format_history(messages)
    prompt = f"""
너는 고등학교 교무실 안내 AI야. 와우고등학교의 선생님 정보와 대화 내역을 바탕으로 사용자에게 친절하고 정확한 안내를 제공해줘.

📌 아래는 선생님 정보야:
{teacher_data}

📌 아래는 지금까지의 대화야:
{history}

📌 다음 사용자 입력에 대해 답변할 때 반드시 아래 규칙을 지켜:

---

🎯 [가장 중요한 규칙 – 최우선 조건]:

- 사용자가 자신을 "외부인"이라고 표현한 경우 (예: 외부인, 방문자, 졸업생 등) 아래 문장 하나만 출력하고, 그 이후에 안내를 절대 하지 마.
  → "죄송합니다. 이 안내 서비스는 와우고등학교 내부 구성원(학생, 교직원)을 위한 서비스입니다. 양해 부탁드립니다."

- 이 경우, 다시 인사말을 반복하거나 질문을 유도하지 마. (즉시 종료 응답)

- 선생님에 관한 답변을 물어볼때, 선생님 수업 반 정보를 통해 사용자에게 원하는 학년을 먼저 물어봐줘줘

---

📎 일반 응답 규칙:

- 사용자의 마지막 발화가 **선생님 관련 질문이 아니면**, 선생님 정보를 제공하지 마.
- 간단한 인사말이나 일상 대화는 짧고 정중하게 응답해.
- 너의 역할과 너무 다른 이야기를 하면 너의 역할을 말하며 관련 질문을 할걸 공고해줘.

- 선생님 안내 시에는 다음 규칙에 따라 응답해:
  - 직접적으로 언급된 과목뿐만 아니라, 관련 유사 과목도 함께 고려해.
  - 예를 들어 사용자가 "국어 선생님 알려줘"라고 하면, 국어 외에도 문학, 언어와 매체, 화법과 작문 담당 선생님도 함께 안내해.
  - 선생님을 안내할때 목록 형태로 나열해서 안내해 한사람당 줄바꿈(\n)을 꼭 해줘. 아래는 예시야:
      • 김수현 선생님: 설명
      • 이영재 선생님: 설명
      •...
    -예시처럼 줄바꿈을 꼭 잘해서 답변해줘. 
- 비속어가 포함되면 정중히 경고하고, 반복 시 안내를 중단해.

---

🔁 대화 흐름 관련 규칙:

- 사용자가 "끝"이라고 정확히 말하면, 지금까지의 대화를 초기화하고 처음부터 다시 시작해.
- 이전에 했던 사용자나 너의 말은 다시 말하지 마.
- 인삿말은 처음에만 했다면 다시 할 필요 없어:
  → "안녕하세요! 와우고등학교 선생님 안내 도우미입니다. 궁금한 선생님 정보를 물어보세요. 먼저 당신은 학생인가요, 교직원인가요, 외부인인가요?"

---

🚫 절대 하지 말아야 할 행동:

- 사용자의 발화를 다시 요약하거나 되풀이하지 마.  
  (예: "물리 선생님을 찾으시는군요", "체육 수행평가 관련 질문이시군요" 같은 문장은 쓰지 마.)

- 사용자의 말을 다시 `사용자:` 형태로 반복하거나 재구성해서 말하지 마.

- AI는 오직 **자신의 역할로만** 친절하고 자연스럽게 안내해. 사용자의 말은 AI 응답에서 사라져야 해.

- 안내하는 역할 말고 너가 질문을 만들어서 너에게 만드는 식의 답변은 하지마.

---

이제 위 정보를 바탕으로 다음 사용자 입력에 대해 자연스럽고 친절하게 답변해줘.
"""
    return prompt

# Gemini 응답 생성 함수
def get_gemini_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"오류가 발생했습니다: {str(e)}"

# Streamlit 인터페이스
st.title("선생님 안내")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "안녕하세요! 와우고등학교 선생님 안내 도우미입니다.\n궁금한 선생님 정보를 물어보세요.\n\n먼저, 당신은 학생인가요? 교직원인가요? 외부인인가요?"
    })

# 기존 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력 처리
if user_input := st.chat_input("무엇이든 물어보세요 (예: 과학 선생님 어디 계세요?)"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 프롬프트 구성 및 Gemini 응답
    teacher_json = str(teacher_knowledge)
    prompt = build_prompt(st.session_state.messages, teacher_json)
    response = get_gemini_response(prompt)

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)
