from dataclasses import asdict
from threading import BoundedSemaphore

from fastapi import APIRouter, Depends, Request, UploadFile
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from apps.api.app.quizzes import Quizzes
from apps.api.app.schemas import (
    ChatRequest,
    ChatResponse,
    CitationDTO,
    DocumentDTO,
    GradeDTO,
    MessageDTO,
    ModeRequest,
    NoteRequest,
    PathDTO,
    ProgressDTO,
    QuizDTO,
    QuizQuestionDTO,
    QuizSetup,
    QuizSubmit,
    ReaderChunk,
)
from study_supporter.ai.graph.algorithms import detect_cycles
from study_supporter.application.contracts.learning import IngestDocumentRequest, QuizRequest
from study_supporter.application.use_cases.learning import GetProgressUseCase, SubmitQuizUseCase
from study_supporter.domain.assessment import QuizQuestion
from study_supporter.domain.errors import EvidenceNotFound
from study_supporter.domain.upload_validation import MAX_PDF_BYTES, validate_pdf_upload


def install_learning(app, principal):
    router = APIRouter(prefix="/api/v1")
    upload_slot = BoundedSemaphore(1)
    # Provider/model calls are bounded independently of lightweight read/auth requests.
    ai_slots = BoundedSemaphore(2)
    app.state.quizzes = Quizzes()

    def dto(document):
        return DocumentDTO(**{k: document[k] for k in DocumentDTO.model_fields})

    def owned(request, user, document_id):
        return request.app.state.factory.documents.get(user.context, document_id)

    def session(request, user, document_id, mode="auto"):
        document = owned(request, user, document_id)
        if document["status"] != "ready":
            raise HTTPException(
                409, "Tài liệu chưa sẵn sàng để học. Kiểm tra trạng thái trong thư viện."
            )
        result = request.app.state.factory.open_document(user.context, document_id, mode)
        if result is None:
            raise EvidenceNotFound("Document content unavailable")
        return result

    def call_ai(callback):
        if not ai_slots.acquire(blocking=False):
            raise HTTPException(429, "AI đang bận. Vui lòng thử lại sau.")
        try:
            return callback()
        finally:
            ai_slots.release()

    @router.get("/documents", response_model=list[DocumentDTO])
    def documents(request: Request, user=Depends(principal)):
        return [dto(doc) for doc in request.app.state.factory.documents.list(user.context)]

    @router.get("/documents/{document_id}", response_model=DocumentDTO)
    def document(document_id: int, request: Request, user=Depends(principal)):
        return dto(owned(request, user, document_id))

    @router.post("/documents", response_model=DocumentDTO, status_code=201)
    async def upload(request: Request, file: UploadFile, user=Depends(principal)):
        try:
            content = await file.read(MAX_PDF_BYTES + 1)
            filename = (file.filename or "document.pdf").replace("\\", "/").split("/")[-1][:255]
            validate_pdf_upload(filename, file.content_type, content)
            if not upload_slot.acquire(blocking=False):
                raise HTTPException(429, "Một tài liệu đang được xử lý. Vui lòng thử lại sau.")
            try:
                result = await run_in_threadpool(
                    request.app.state.factory.ingestion.execute,
                    IngestDocumentRequest(user.context, filename, content, file.content_type),
                )
                return dto(owned(request, user, result.document_id))
            finally:
                upload_slot.release()
        finally:
            await file.close()

    @router.get("/documents/{document_id}/reader", response_model=list[ReaderChunk])
    def reader(document_id: int, request: Request, user=Depends(principal)):
        document = owned(request, user, document_id)
        if document["status"] != "ready":
            raise HTTPException(409, "Tài liệu chưa sẵn sàng.")
        chunks = request.app.state.factory.vector_store(document).load_all_chunks()
        return [
            ReaderChunk(
                chunk_id=c.chunk_id, text=c.text, page_start=c.page_start, page_end=c.page_end
            )
            for c in sorted(chunks, key=lambda c: (c.page_start or 0, c.chunk_id))
        ]

    @router.post("/documents/{document_id}/chat", response_model=ChatResponse)
    def chat(document_id: int, body: ChatRequest, request: Request, user=Depends(principal)):
        def answer():
            study = session(request, user, document_id, body.mode)
            result = study.answer(body.question)
            return ChatResponse(
                answer=result.answer,
                citations=[CitationDTO(**asdict(e)) for e in result.evidences],
                trace_id=result.trace_id,
            )

        return call_ai(answer)

    @router.post("/documents/{document_id}/quizzes", response_model=QuizDTO)
    def generate(document_id: int, body: QuizSetup, request: Request, user=Depends(principal)):
        def quiz():
            study = session(request, user, document_id, body.mode)
            try:
                questions = study.generate_quiz(
                    QuizRequest(study.context, body.num_questions, body.topic)
                )
                public = []
                for q in questions:
                    validated = QuizQuestion(
                        question=q["question"],
                        options=q["options"],
                        correct_answer_index=q["correct_index"],
                        explanation=q.get("explanation", ""),
                    )
                    public.append(
                        QuizQuestionDTO(
                            question=validated.question,
                            options=validated.options,
                            topic=q.get("topic", body.topic),
                        )
                    )
            except ValueError:
                raise HTTPException(
                    503, "AI chưa tạo được câu hỏi hợp lệ. Vui lòng thử lại."
                ) from None
            key = app.state.quizzes.create(user.session_key, document_id, questions)
            return QuizDTO(quiz_id=key, questions=public)

        return call_ai(quiz)

    @router.post("/documents/{document_id}/quizzes/{quiz_id}/attempts", response_model=GradeDTO)
    def submit(
        document_id: int, quiz_id: str, body: QuizSubmit, request: Request, user=Depends(principal)
    ):
        owned(request, user, document_id)
        entry = app.state.quizzes.get(quiz_id, user.session_key, document_id)
        if body.question_index >= len(entry.questions):
            raise HTTPException(422, "Câu hỏi không hợp lệ.")
        with entry.lock:
            previous = entry.grades.get(body.question_index)
            if previous:
                selected, grade = previous
                if selected != body.selected_index:
                    raise HTTPException(409, "Câu hỏi đã được nộp với đáp án khác.")
                return grade
            factory = request.app.state.factory
            grade = SubmitQuizUseCase(
                factory.document_repository, factory.progress_repository
            ).execute(
                user.context, document_id, entry.questions[body.question_index], body.selected_index
            )
            result = GradeDTO(**asdict(grade))
            entry.grades[body.question_index] = (body.selected_index, result)
            return result

    @router.get("/progress", response_model=ProgressDTO)
    def progress(request: Request, user=Depends(principal)):
        return GetProgressUseCase(request.app.state.factory.progress_repository).execute(
            user.context
        )

    @router.get("/documents/{document_id}/learning-path", response_model=PathDTO)
    def path(document_id: int, request: Request, user=Depends(principal)):
        from study_supporter.domain.knowledge_graph import ConceptGraph
        from study_supporter.ai.graph.algorithms import suggest_learning_path

        document = owned(request, user, document_id)
        graph = (
            ConceptGraph(**document["concept_graph_json"])
            if document["concept_graph_json"]
            else None
        )
        cycle = bool(graph and detect_cycles(graph))
        return PathDTO(
            concepts=[] if graph is None or cycle else suggest_learning_path(graph), has_cycle=cycle
        )

    @router.post("/documents/{document_id}/learning-path", response_model=PathDTO)
    def build_path(document_id: int, body: ModeRequest, request: Request, user=Depends(principal)):
        def build():
            graph, concepts = session(request, user, document_id, body.mode).build_graph()
            return PathDTO(concepts=concepts, has_cycle=bool(detect_cycles(graph)))

        return call_ai(build)

    @router.post("/documents/{document_id}/notes", response_model=MessageDTO, status_code=201)
    def note(document_id: int, body: NoteRequest, request: Request, user=Depends(principal)):
        if not body.note.strip():
            raise HTTPException(422, "Ghi chú không được để trống.")
        call_ai(lambda: session(request, user, document_id).save_note(body.note.strip()))
        return MessageDTO(message="Đã lưu ghi chú.")

    app.include_router(router)
