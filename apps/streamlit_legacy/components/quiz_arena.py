# ui/components/quiz_arena.py
import streamlit as st

from study_supporter.application.contracts.learning import QuizRequest
from apps.streamlit_legacy.components.sidebar import _rebuild_orchestrator_with_new_llm


def _switch_quiz_model_to_ollama():
    st.session_state.model_choice = "ollama"
    _rebuild_orchestrator_with_new_llm()


def _get_quiz_history() -> list:
    file_id = st.session_state.get("last_uploaded_file_id") or "no_doc"
    history_dict = st.session_state.setdefault("quiz_history", {})
    if file_id not in history_dict:
        history_dict[file_id] = []
    return history_dict[file_id]


def _add_quiz_to_history(quiz: list):
    history = _get_quiz_history()
    history.append(quiz)


def _get_available_topics() -> list[dict]:
    """Trích xuất các chủ đề khả dụng từ concept graph."""
    graph = st.session_state.get("concept_graph")
    if not graph:
        return []

    nodes = graph.nodes if hasattr(graph, "nodes") else graph.get("nodes", [])

    topics = []
    for n in nodes:
        if isinstance(n, dict):
            topics.append(
                {
                    "id": n.get("id", ""),
                    "label": n.get("label", ""),
                    "description": n.get("description", ""),
                }
            )
        else:
            topics.append(
                {
                    "id": getattr(n, "id", ""),
                    "label": getattr(n, "label", ""),
                    "description": getattr(n, "description", ""),
                }
            )
    return topics


def render_quiz_arena():
    if st.session_state.orchestrator is None:
        st.caption("Upload tài liệu trước để bắt đầu làm quiz.")
        return

    st.markdown(
        "<div style='margin-bottom:0.6rem; color:#475569;'>Tạo một bộ quiz nhanh và nhận phản hồi tức thì.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Lịch sử Quiz")
    history = _get_quiz_history()

    if history:
        past_quiz_options = [f"Quiz {i + 1} ({len(q)} câu hỏi)" for i, q in enumerate(history)]
        hist_cols = st.columns([2, 1])
        with hist_cols[0]:
            selected_past_idx = st.selectbox(
                "Chọn quiz cũ:",
                range(len(past_quiz_options)),
                format_func=lambda x: past_quiz_options[x],
                key="select_past_quiz",
            )
        with hist_cols[1]:
            st.write("")  # spacer
            st.write("")
            if st.button("📥 Tải lại quiz", use_container_width=True, key="load_past_quiz_btn"):
                st.session_state.current_quiz = history[selected_past_idx]
                st.session_state.current_quiz_index = 0
                st.session_state.quiz_submitted = False
                st.session_state.quiz_feedback = None
                st.session_state.quiz_results = []
                st.session_state.quiz_finished = False
                st.rerun()
    else:
        st.caption("Chưa có quiz nào được tạo trong phiên này.")

    st.markdown("---")
    st.markdown("### Tạo Quiz Mới")

    topics = _get_available_topics()
    topic_options = [{"id": "all", "label": "📚 Toàn bộ tài liệu", "description": ""}] + topics

    cols = st.columns([2, 1, 1])
    with cols[0]:
        selected_topic_idx = st.selectbox(
            "Chọn chủ đề:",
            range(len(topic_options)),
            format_func=lambda x: topic_options[x]["label"],
            key="quiz_topic",
        )
    with cols[1]:
        num_questions = st.selectbox(
            "Số lượng câu hỏi:", [1, 5, 10, 15], index=0, key="quiz_num_questions"
        )
    with cols[2]:
        st.write("")
        st.write("")
        create_btn = st.button("🎲 Tạo quiz", use_container_width=True, key="create_quiz_btn")

    if create_btn:
        parsed_quiz = None
        selected_topic = topic_options[selected_topic_idx]
        with st.spinner("Đang tạo quiz..."):
            request = QuizRequest(
                st.session_state.document_session.context,
                num_questions,
                selected_topic["label"],
                selected_topic["description"],
            )
            try:
                parsed_quiz = st.session_state.document_session.generate_quiz(request)
            except (ValueError, RuntimeError):
                if st.session_state.model_choice != "ollama":
                    st.warning("Quiz trả về không hợp lệ, thử lại với Ollama local...")
                    _switch_quiz_model_to_ollama()
                    try:
                        parsed_quiz = st.session_state.document_session.generate_quiz(request)
                    except (ValueError, RuntimeError):
                        pass
        if parsed_quiz:
            _add_quiz_to_history(parsed_quiz)
            st.session_state.current_quiz = parsed_quiz
            st.session_state.current_quiz_index = 0
            st.session_state.quiz_submitted = False
            st.session_state.quiz_feedback = None
            st.session_state.quiz_results = []
            st.session_state.quiz_finished = False
            st.rerun()
        else:
            st.error("Không parse được quiz từ Agent, thử lại nhé.")
            st.session_state.current_quiz = None
            st.session_state.current_quiz_index = 0
            st.session_state.quiz_submitted = False
            st.session_state.quiz_feedback = None
            st.session_state.quiz_results = []
            st.session_state.quiz_finished = False

    quiz = st.session_state.get("current_quiz")
    if quiz:
        if st.session_state.get("quiz_finished", False):
            # Show summary
            score = sum(st.session_state.quiz_results)
            total = len(quiz)
            percentage = int((score / total) * 100) if total > 0 else 0

            st.markdown(
                f"""
            <div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:1.5rem; margin-top:1rem; text-align:center;'>
                <h3 style='margin-top:0;'>🏆 Kết quả Quiz</h3>
                <hr style='border-color:#e2e8f0; margin:1rem 0;'/>
                <div style='font-size:3rem; font-weight:bold; color:{"#10b981" if percentage >= 80 else "#f59e0b" if percentage >= 50 else "#ef4444"};'>{percentage}%</div>
                <div style='font-size:1.1rem; margin-bottom:1.5rem;'>Bạn đã trả lời đúng <strong>{score}/{total}</strong> câu.</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Làm lại", use_container_width=True):
                    st.session_state.current_quiz_index = 0
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_feedback = None
                    st.session_state.quiz_results = []
                    st.session_state.quiz_finished = False
                    st.rerun()
            with col2:
                if st.button("🎲 Trở về tạo quiz mới", use_container_width=True):
                    st.session_state.current_quiz = None
                    st.session_state.current_quiz_index = 0
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_feedback = None
                    st.session_state.quiz_results = []
                    st.session_state.quiz_finished = False
                    st.rerun()

        else:
            index = st.session_state.get("current_quiz_index", 0)
            question = quiz[index]
            total_questions = len(quiz)

            # Progress bar
            progress = (index) / total_questions
            st.markdown(
                f"<div style='color:#475569; font-size:0.9rem; margin-bottom:0.2rem;'>Tiến trình: <strong>{index + 1}/{total_questions}</strong></div>",
                unsafe_allow_html=True,
            )
            st.progress(progress)

            st.markdown(
                f"""
                <div style='background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:1.2rem; margin-top:1rem;'>
                    <div style='display:inline-block; background:#e0f2fe; color:#0369a1; padding:0.2rem 0.6rem; border-radius:999px; font-size:0.8rem; font-weight:500; margin-bottom:0.8rem;'>
                        🏷️ Chủ đề: {question.get("topic", "Chủ đề chung")}
                    </div>
                    <div style='font-size:1.1rem; font-weight:600; color:#0f172a; margin-bottom:1rem;'>
                        Câu {index + 1}: {question["question"]}
                    </div>
                """,
                unsafe_allow_html=True,
            )

            choice = st.radio(
                "Chọn đáp án:",
                options=question["options"],
                key=f"quiz_choice_{index}",
                label_visibility="collapsed",
            )

            st.markdown("</div>", unsafe_allow_html=True)

            if not st.session_state.get("quiz_submitted"):
                if st.button("✅ Nộp bài", use_container_width=True, key=f"submit_quiz_{index}"):
                    selected_index = question["options"].index(choice)
                    grade = st.session_state.document_session.submit_quiz(question, selected_index)
                    is_correct = grade.is_correct
                    explanation = grade.explanation

                    st.session_state.quiz_submitted = True
                    st.session_state.quiz_feedback = {
                        "is_correct": is_correct,
                        "explanation": explanation,
                        "correct_answer": question["options"][question["correct_index"]],
                    }
                    st.session_state.quiz_results.append(is_correct)
                    st.rerun()

            if st.session_state.get("quiz_submitted"):
                feedback = st.session_state.get("quiz_feedback", {})
                if feedback.get("is_correct"):
                    st.success(f"**Chính xác!** {feedback.get('explanation', '')}")
                else:
                    st.error(
                        f"**Chưa đúng.** Đáp án đúng: **{feedback.get('correct_answer')}**.\n\n{feedback.get('explanation', '')}"
                    )

                if index + 1 < len(quiz):
                    if st.button(
                        "➡️ Câu tiếp theo",
                        use_container_width=True,
                        key=f"next_quiz_{index}",
                    ):
                        st.session_state.current_quiz_index = index + 1
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_feedback = None
                        st.rerun()
                else:
                    if st.button("🏁 Hoàn thành", use_container_width=True, key="finish_quiz"):
                        st.session_state.quiz_finished = True
                        st.rerun()
