from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.ai.assessment.legacy_parser import parse_quiz_from_text
from study_supporter.ai.graph.algorithms import detect_cycles, suggest_learning_path
from study_supporter.application.use_cases.build_learning_path import build_concept_graph
from study_supporter.domain.errors import EvidenceNotFound
from study_supporter.domain.knowledge_graph import ConceptGraph


class LearningSession:
    """Account-bound application facade; never cached process-wide."""

    def __init__(
        self,
        context,
        document,
        chunks,
        answer,
        generator,
        submit,
        progress,
        documents,
        llm,
        mode="auto",
        notice="",
    ):
        self.context, self.document, self.chunks = context, document, tuple(chunks)
        self._answer, self._generator, self._submit = answer, generator, submit
        self._progress, self._documents, self._llm = progress, documents, llm
        self.mode, self.notice = mode, notice
        self.graph = (
            ConceptGraph(**document["concept_graph_json"])
            if document["concept_graph_json"]
            else None
        )
        self.learning_path = (
            []
            if self.graph is None or detect_cycles(self.graph)
            else suggest_learning_path(self.graph)
        )

    def answer(self, question):
        return self._answer.execute(AnswerRequest(self.context, question))

    def generate_quiz(self, request):
        if request.context != self.context:
            raise EvidenceNotFound("Document not found")
        self._documents.get(self.context.user_id, self.document["id"])
        content = "\n\n".join(chunk.text for chunk in self.chunks[:5])
        if not content:
            raise EvidenceNotFound("Document content unavailable")
        if request.topic_description:
            content = f"Hãy tạo {request.num_questions} câu hỏi trắc nghiệm TẬP TRUNG vào chủ đề: {request.topic_label}\nMô tả chủ đề: {request.topic_description}\nDựa trên nội dung tài liệu sau:\n\n{content}"
        else:
            content = f"Hãy tạo {request.num_questions} câu hỏi trắc nghiệm dựa trên nội dung tài liệu sau:\n\n{content}"
        questions = parse_quiz_from_text(
            self._generator.run(content, request.num_questions), request.topic_label
        )
        if not questions:
            raise ValueError("Quiz trả về không hợp lệ. Thử lại với model hoặc nội dung khác.")
        return questions

    def submit_quiz(self, question, selected):
        return self._submit.execute(self.context, self.document["id"], question, selected)

    def progress(self):
        return self._progress.execute(self.context)

    def build_graph(self):
        self._documents.get(self.context.user_id, self.document["id"])
        self.graph = build_concept_graph(
            "\n\n".join(chunk.text for chunk in self.chunks[:5]), self._llm
        )
        self.learning_path = [] if detect_cycles(self.graph) else suggest_learning_path(self.graph)
        if self.graph.nodes:
            self._documents.update(
                self.context.user_id,
                self.document["id"],
                concept_graph_json=self.graph.model_dump(),
            )
        return self.graph, self.learning_path
