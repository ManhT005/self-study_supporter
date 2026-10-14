"use client";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CircleX } from "lucide-react";
import { useRef, useState } from "react";
import { z } from "zod";
import { gradeSchema, message, post, quizSchema } from "@/lib/api/client";
import { useDocuments } from "@/features/documents";
import { useMode } from "@/features/settings";
import {
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeading,
} from "@/components/ui";
type Quiz = z.infer<typeof quizSchema>;
type Grade = z.infer<typeof gradeSchema>;
export function Quiz() {
  const documents = useDocuments();
  const mode = useMode();
  const cache = useQueryClient();
  const lock = useRef(false);
  const [documentId, setDocumentId] = useState("");
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(5);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [activeId, setActiveId] = useState(0);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [finished, setFinished] = useState(false);
  const ready = documents.data?.filter((d) => d.status === "ready") ?? [];
  const chosen = documentId || String(ready[0]?.id ?? "");
  const generate = useMutation({
    mutationFn: () =>
      post(`/documents/${chosen}/quizzes`, quizSchema, {
        num_questions: count,
        topic: topic.trim() || "Chủ đề chung",
        mode,
      }),
    onSuccess: (data) => {
      setQuiz(data);
      setActiveId(Number(chosen));
      setIndex(0);
      setSelected(null);
      setGrades([]);
      setFinished(false);
    },
  });
  const submit = useMutation({
    mutationFn: () =>
      post(
        `/documents/${activeId}/quizzes/${quiz?.quiz_id}/attempts`,
        gradeSchema,
        { question_index: index, selected_index: selected },
      ),
    onSuccess: (grade) => {
      setGrades((values) => [...values, grade]);
      void cache.invalidateQueries({ queryKey: ["progress"] });
    },
  });
  async function start(event: React.FormEvent) {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true;
    try {
      await generate.mutateAsync();
    } catch {
      /* Render error below. */
    } finally {
      lock.current = false;
    }
  }
  async function answer() {
    if (lock.current || selected == null || grades[index]) return;
    lock.current = true;
    try {
      await submit.mutateAsync();
    } catch {
      /* Preserve selection for safe retry. */
    } finally {
      lock.current = false;
    }
  }
  if (documents.isPending) return <LoadingState />;
  if (documents.error)
    return (
      <ErrorState
        message={message(documents.error)}
        retry={() => void documents.refetch()}
      />
    );
  if (!ready.length)
    return (
      <EmptyState
        title="Thêm tài liệu trước khi luyện tập"
        action={
          <Link className="button" href="/documents">
            Thêm tài liệu
          </Link>
        }
      >
        AI sẽ tạo câu hỏi từ nội dung tài liệu đã sẵn sàng của bạn.
      </EmptyState>
    );
  if (!quiz)
    return (
      <div className="stack">
        <PageHeading
          eyebrow="Hiểu đến đâu, luyện đến đó"
          title="Luyện tập từ tài liệu"
        >
          Một câu hỏi mỗi bước, giải thích sau khi nộp.
        </PageHeading>
        <form className="card stack quiz-card" onSubmit={start}>
          <label className="field">
            Tài liệu
            <select
              className="input"
              value={chosen}
              onChange={(e) => setDocumentId(e.target.value)}
              disabled={generate.isPending}
            >
              {ready.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Chủ đề (tùy chọn)
            <input
              className="input"
              value={topic}
              maxLength={200}
              placeholder="Ví dụ: khái niệm ở chương 1"
              onChange={(e) => setTopic(e.target.value)}
              disabled={generate.isPending}
            />
          </label>
          <label className="field">
            Số câu hỏi
            <select
              className="input"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              disabled={generate.isPending}
            >
              {[1, 3, 5, 10, 15].map((n) => (
                <option key={n} value={n}>
                  {n} câu
                </option>
              ))}
            </select>
          </label>
          {generate.error && <ErrorState message={message(generate.error)} />}
          <Button pending={generate.isPending} type="submit">
            Tạo bài luyện tập
          </Button>
          {generate.isPending && (
            <p role="status">Đang tạo câu hỏi từ tài liệu…</p>
          )}
        </form>
      </div>
    );
  if (finished)
    return (
      <div className="stack">
        <PageHeading
          eyebrow="Một bước tiến mới"
          title="Bạn đã hoàn thành bài luyện"
        />
        <section className="card quiz-card">
          <div className="empty-icon">
            <CheckCircle2 size={28} aria-hidden="true" />
          </div>
          <h2>
            {grades.filter((g) => g.is_correct).length}/{quiz.questions.length}{" "}
            câu đúng
          </h2>
          <p className="muted">
            Kết quả từng câu đã được lưu vào tiến độ tài khoản.
          </p>
          <Link className="button" href="/progress">
            Xem tiến độ
          </Link>
          <div style={{ marginTop: 16 }}>
            <Button
              className="secondary"
              onClick={() => {
                setQuiz(null);
                generate.reset();
                submit.reset();
              }}
            >
              Luyện bài khác
            </Button>
          </div>
        </section>
      </div>
    );
  const question = quiz.questions[index];
  const grade = grades[index];
  return (
    <div className="stack">
      <PageHeading
        eyebrow="Luyện tập"
        title={`Câu ${index + 1} / ${quiz.questions.length}`}
      />
      <section className="card quiz-card stack">
        <progress
          className="quiz-progress"
          max={quiz.questions.length}
          value={index + (grade ? 1 : 0)}
          aria-label="Tiến độ bài luyện"
        />
        <fieldset className="quiz-options">
          <legend>
            <h2>{question.question}</h2>
          </legend>
          {question.options.map((option, i) => (
            <label
              className={`quiz-option ${selected === i ? "selected" : ""} ${grade && grade.correct_index === i ? "correct" : ""}`}
              key={i}
            >
              <input
                type="radio"
                name="answer"
                value={i}
                checked={selected === i}
                disabled={!!grade || submit.isPending}
                onChange={() => setSelected(i)}
              />
              <span className="option-letter" aria-hidden="true">
                {String.fromCharCode(65 + i)}
              </span>
              <span>{option}</span>
              {grade && grade.correct_index === i && (
                <span className="badge ready">Đáp án đúng</span>
              )}
            </label>
          ))}
        </fieldset>
        {submit.error && <ErrorState message={message(submit.error)} />}
        {grade ? (
          <>
            <div className="feedback" role="status">
              <div className="row">
                {grade.is_correct ? (
                  <CheckCircle2 aria-hidden="true" />
                ) : (
                  <CircleX aria-hidden="true" />
                )}
                <strong>
                  {grade.is_correct ? "Chính xác!" : "Cần ôn lại khái niệm này"}
                </strong>
              </div>
              <p>
                Đáp án đúng: {String.fromCharCode(65 + grade.correct_index)}
              </p>
              {grade.explanation && (
                <p className="pre-wrap">{grade.explanation}</p>
              )}
              <Link
                href={`/documents/${activeId}/study`}
                className="button secondary"
              >
                Đọc lại tài liệu
              </Link>
            </div>
            <Button
              onClick={() => {
                if (index + 1 === quiz.questions.length) setFinished(true);
                else {
                  setIndex(index + 1);
                  setSelected(null);
                  submit.reset();
                }
              }}
            >
              {index + 1 === quiz.questions.length
                ? "Xem kết quả"
                : "Câu tiếp theo"}
            </Button>
          </>
        ) : (
          <Button
            pending={submit.isPending}
            disabled={selected == null}
            onClick={() => void answer()}
          >
            Nộp đáp án
          </Button>
        )}
      </section>
      <p className="muted">
        Bài quiz chưa hoàn tất chỉ được giữ trong phiên hiện tại.
      </p>
    </div>
  );
}
