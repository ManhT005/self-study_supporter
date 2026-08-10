# ui/components/quiz_arena.py
import streamlit as st
import re

from src.llm.ollama_client import OllamaClient


def _switch_quiz_model_to_ollama():
    st.session_state.model_choice = "ollama"
    new_llm = OllamaClient(model="qwen2.5:1.5b")
    if st.session_state.get("orchestrator") is not None:
        st.session_state.orchestrator.llm = new_llm
        for tool in st.session_state.orchestrator.tools.values():
            if hasattr(tool, "llm"):
                tool.llm = new_llm


def _get_quiz_history() -> list:
    file_id = st.session_state.get("last_uploaded_file_id") or "no_doc"
    history_dict = st.session_state.setdefault("quiz_history", {})
    if file_id not in history_dict:
        history_dict[file_id] = []
    return history_dict[file_id]


def _add_quiz_to_history(quiz: list):
    history = _get_quiz_history()
    history.append(quiz)


def render_quiz_arena():
    if st.session_state.orchestrator is None:
        st.caption("Upload tài liệu trước để bắt đầu làm quiz.")
        return

    st.markdown("<div style='margin-bottom:0.6rem; color:#475569;'>Tạo một bộ quiz nhanh và nhận phản hồi tức thì.</div>", unsafe_allow_html=True)

    st.markdown("### Lịch sử Quiz")
    history = _get_quiz_history()
    
    if history:
        past_quiz_options = [f"Quiz {i+1} ({len(q)} câu hỏi)" for i, q in enumerate(history)]
        hist_cols = st.columns([2, 1])
        with hist_cols[0]:
            selected_past_idx = st.selectbox("Chọn quiz cũ:", range(len(past_quiz_options)), format_func=lambda x: past_quiz_options[x], key="select_past_quiz")
        with hist_cols[1]:
            st.write("") # spacer
            st.write("")
            if st.button("📥 Tải lại quiz", use_container_width=True, key="load_past_quiz_btn"):
                st.session_state.current_quiz = history[selected_past_idx]
                st.session_state.current_quiz_index = 0
                st.session_state.quiz_submitted = False
                st.session_state.quiz_feedback = None
                st.session_state.quiz_results = []
                st.rerun()
    else:
        st.caption("Chưa có quiz nào được tạo trong phiên này.")

    st.markdown("---")
    st.markdown("### Tạo Quiz Mới")

    cols = st.columns([2, 1])
    with cols[0]:
        num_questions = st.selectbox("Số lượng câu hỏi:", [1, 5, 10, 15], index=0, key="quiz_num_questions")
    with cols[1]:
        st.write("")
        st.write("")
        create_btn = st.button("🎲 Tạo quiz", use_container_width=True, key="create_quiz_btn")

    if create_btn:
        with st.spinner("Đang tạo quiz..."):
            document_chunks = st.session_state.get("graph_source_chunks") or []
            document_text = "\n\n".join(chunk.text for chunk in document_chunks if getattr(chunk, "text", ""))
            if not document_text:
                document_text = st.session_state.get("uploaded_document_text") or ""
            if not document_text:
                document_text = "Nội dung tài liệu chưa có sẵn trong phiên làm việc."

            topic_content = (
                f"[user_id của học sinh: {st.session_state.user_id}] "
                f"Hãy tạo {num_questions} câu hỏi trắc nghiệm dựa trên nội dung tài liệu sau:\n\n{document_text}"
            )
            quiz_text = None
            generator = None
            if st.session_state.get("orchestrator") is not None:
                generator = st.session_state.orchestrator.tools.get("generate_quiz")

            try:
                if generator is not None:
                    quiz_text = generator.run(topic_content, num_questions=num_questions)
                else:
                    state = st.session_state.orchestrator.run(topic_content)
                    quiz_text = state.final_answer
            except RuntimeError as e:
                if "quota" in str(e).lower():
                    st.warning("⚠️ Gemini hết quota, chuyển sang Ollama local để tạo quiz.")
                    _switch_quiz_model_to_ollama()
                    generator = st.session_state.orchestrator.tools.get("generate_quiz")
                    if generator is not None:
                        quiz_text = generator.run(topic_content, num_questions=num_questions)
                    else:
                        state = st.session_state.orchestrator.run(topic_content)
                        quiz_text = state.final_answer
                else:
                    raise

        parsed_quiz = _parse_quiz_from_text(quiz_text)
        if not parsed_quiz and st.session_state.model_choice != "ollama":
            st.warning("Quiz trả về không parse được, thử lại với Ollama local...")
            _switch_quiz_model_to_ollama()
            generator = st.session_state.orchestrator.tools.get("generate_quiz")
            if generator is not None:
                quiz_text = generator.run(topic_content, num_questions=num_questions)
            else:
                state = st.session_state.orchestrator.run(topic_content)
                quiz_text = state.final_answer
            parsed_quiz = _parse_quiz_from_text(quiz_text)

        if parsed_quiz:
            _add_quiz_to_history(parsed_quiz)
            st.session_state.current_quiz = parsed_quiz
            st.session_state.current_quiz_index = 0
            st.session_state.quiz_submitted = False
            st.session_state.quiz_feedback = None
            st.session_state.quiz_results = []
            st.rerun()
        else:
            st.error("Không parse được quiz từ Agent, thử lại nhé.")
            st.session_state.current_quiz = None
            st.session_state.current_quiz_index = 0
            st.session_state.quiz_submitted = False
            st.session_state.quiz_feedback = None
            st.session_state.quiz_results = []

    quiz = st.session_state.get("current_quiz")
    if quiz:
        index = st.session_state.get("current_quiz_index", 0)
        question = quiz[index]

        st.markdown(
            f"<div style='background:#f8fafc; border:1px solid #e2e8f0; border-radius:14px; padding:0.9rem; margin-top:0.6rem;'><strong>Câu {index + 1}/{len(quiz)}: {question['question']}</strong></div>",
            unsafe_allow_html=True,
        )
        choice = st.radio("Chọn đáp án:", options=question["options"], key=f"quiz_choice_{index}")

        if st.button("✅ Nộp bài", use_container_width=True, key=f"submit_quiz_{index}"):
            selected_index = question["options"].index(choice)
            is_correct = selected_index == question["correct_index"]
            explanation = question.get("explanation", "")

            if is_correct:
                st.success(f"Chính xác! {explanation}")
            else:
                correct_answer = question["options"][question["correct_index"]]
                st.error(f"Chưa đúng. Đáp án đúng: {correct_answer}. {explanation}")

            if hasattr(st.session_state, "progress_db") and st.session_state.progress_db is not None:
                st.session_state.progress_db.record_attempt(
                    user_id=st.session_state.user_id,
                    topic=question.get("topic", "Chủ đề chung"),
                    question=question["question"],
                    is_correct=is_correct,
                )

            st.session_state.quiz_submitted = True
            st.session_state.quiz_feedback = {
                "is_correct": is_correct,
                "explanation": explanation,
                "correct_answer": question["options"][question["correct_index"]],
            }
            st.session_state.quiz_results.append(is_correct)

        if st.session_state.get("quiz_submitted"):
            feedback = st.session_state.get("quiz_feedback", {})
            if feedback.get("is_correct"):
                st.success(f"Chính xác! {feedback.get('explanation', '')}")
            else:
                st.error(f"Chưa đúng. Đáp án đúng: {feedback.get('correct_answer')}. {feedback.get('explanation', '')}")

            if index + 1 < len(quiz):
                if st.button("➡️ Câu tiếp theo", use_container_width=True, key=f"next_quiz_{index}"):
                    st.session_state.current_quiz_index = index + 1
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_feedback = None
            else:
                if st.button("Hoàn thành", use_container_width=True, key="finish_quiz"):
                    score = sum(st.session_state.quiz_results)
                    st.info(f"Bạn đã trả lời đúng {score}/{len(quiz)} câu.")
                    st.session_state.current_quiz = None
                    st.session_state.current_quiz_index = 0
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_feedback = None
                    st.session_state.quiz_results = []


def _parse_quiz_from_text(text: str) -> list[dict] | None:
    """Parse quiz từ output của Agent thành danh sách câu hỏi."""
    blocks = re.findall(r"^Câu\s*\d+:\s*(.*?)(?=^Câu\s*\d+:|\Z)", text, flags=re.MULTILINE | re.DOTALL)
    if not blocks:
        return None

    questions = []
    for block in blocks:
        block = block.strip()

        # Tách "Giải thích:" ra TRƯỚC khi tìm option — nếu không, đáp án cuối
        # cùng (D) sẽ nuốt luôn cả phần giải thích vào trong text của nó, vì
        # lookahead của regex option chỉ dừng khi gặp đáp án A-D tiếp theo
        # hoặc hết chuỗi, mà dòng "Giải thích:" không khớp cả 2 điều kiện đó.
        explanation_match = re.search(r"^\s*Giải thích:\s*(.+)", block, flags=re.MULTILINE | re.DOTALL)
        if explanation_match:
            options_zone = block[: explanation_match.start()]
            explanation = explanation_match.group(1).strip()
        else:
            options_zone = block
            explanation = ""

        question_match = re.search(r"^(.*?\?)", options_zone.strip(), re.DOTALL)
        options = re.findall(
            r"^\s*[A-D]\.\s*(.+?)(?=\n\s*[A-D]\.\s*|\Z)",
            options_zone,
            flags=re.MULTILINE | re.DOTALL,
        )

        if not question_match or len(options) < 2:
            return None

        cleaned_options = [re.sub(r"\(.*?đáp án đúng.*?\)", "", opt, flags=re.IGNORECASE).strip() for opt in options]
        correct_index = 0
        for i, opt in enumerate(options):
            if "đáp án đúng" in opt.lower() or "correct" in opt.lower():
                correct_index = i
                break

        questions.append(
            {
                "question": question_match.group(1).strip(),
                "options": cleaned_options,
                "correct_index": correct_index,
                "explanation": explanation,
                "topic": "Chủ đề chung",
            }
        )

    return questions