# ui/components/quiz_arena.py
import streamlit as st
import re


def render_quiz_arena():
    if st.session_state.orchestrator is None:
        st.caption("Upload tài liệu trước để bắt đầu làm quiz.")
        return

    if st.button("🎲 Tạo câu hỏi trắc nghiệm mới"):
        with st.spinner("Đang tạo câu hỏi..."):
            question_with_context = (
                f"[user_id của học sinh: {st.session_state.user_id}] "
                f"Hãy tạo 1 câu hỏi trắc nghiệm về nội dung tài liệu đã học."
            )
            state = st.session_state.orchestrator.run(question_with_context)

        parsed_quiz = _parse_quiz_from_text(state.final_answer)
        if parsed_quiz:
            st.session_state.current_quiz = parsed_quiz
        else:
            st.error("Không parse được câu hỏi từ Agent, thử lại nhé.")
            st.session_state.current_quiz = None

    quiz = st.session_state.get("current_quiz")
    if quiz:
        st.write(f"**{quiz['question']}**")
        choice = st.radio("Chọn đáp án:", options=quiz["options"], key="quiz_choice")

        if st.button("✅ Nộp bài"):
            selected_index = quiz["options"].index(choice)
            is_correct = selected_index == quiz["correct_index"]

            if is_correct:
                st.success(f"Chính xác! {quiz.get('explanation', '')}")
            else:
                correct_answer = quiz["options"][quiz["correct_index"]]
                st.error(f"Chưa đúng. Đáp án đúng: {correct_answer}. {quiz.get('explanation', '')}")

            st.session_state.progress_db.record_attempt(
                user_id=st.session_state.user_id,
                topic=quiz.get("topic", "Chủ đề chung"),
                question=quiz["question"],
                is_correct=is_correct,
            )
            st.session_state.current_quiz = None  # xóa để không nộp lại câu cũ


def _parse_quiz_from_text(text: str) -> dict | None:
    """
    Parse quiz từ Final Answer dạng text tự do của Agent (không có structured
    output ở bước này, vì Final Answer là text tổng hợp cuối cùng của LLM,
    không phải Observation gốc từ GenerateQuizTool). Dùng regex đơn giản,
    chấp nhận là "best effort" — có thể fail nếu Agent không theo đúng
    format phổ biến (câu hỏi + 4 đáp án A-D).
    """
    question_match = re.search(r"^(.*?\?)", text, re.DOTALL)
    options = re.findall(r"[A-D]\.\s*(.+?)(?:\n|$)", text)

    if not question_match or len(options) < 2:
        return None

    correct_index = 0
    for i, opt in enumerate(options):
        if "đúng" in opt.lower() or "correct" in opt.lower():
            correct_index = i
            break

    return {
        "question": question_match.group(1).strip(),
        "options": [re.sub(r"\(.*?đúng.*?\)", "", opt, flags=re.IGNORECASE).strip() for opt in options],
        "correct_index": correct_index,
        "topic": "Chủ đề chung",
    }