"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileText,
  Search,
  Upload,
} from "lucide-react";
import { useRef, useState } from "react";
import {
  api,
  documentSchema,
  documentsSchema,
  message,
  progressSchema,
} from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import {
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeading,
} from "@/components/ui";

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: ({ signal }) => api("/documents", documentsSchema, { signal }),
    refetchInterval: (query) =>
      query.state.data?.some((d) => d.status === "processing") ? 5000 : false,
  });
}
const statuses = {
  ready: "Sẵn sàng",
  processing: "Đang xử lý",
  failed: "Xử lý thất bại",
};
export function DocumentItem({
  document,
}: {
  document: Schemas["DocumentDTO"];
}) {
  return (
    <div className="document-item">
      <span className="document-icon">
        <FileText size={24} aria-hidden="true" />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Link href={`/documents/${document.id}`} className="document-title">
          {document.filename}
        </Link>
        <div className="row">
          <small className="muted">
            PDF
            {document.page_count != null
              ? ` · ${document.page_count} trang`
              : ""}
          </small>
          <span className={`badge ${document.status}`}>
            {document.status === "ready" && (
              <CheckCircle2 size={12} aria-hidden="true" />
            )}
            {statuses[document.status]}
          </span>
        </div>
      </div>
      {document.status === "ready" && (
        <Link
          className="button secondary"
          href={`/documents/${document.id}/study`}
          aria-label={`Học ${document.filename}`}
        >
          <ArrowRight size={18} aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}
export function Dashboard() {
  const documents = useDocuments();
  const progress = useQuery({
    queryKey: ["progress"],
    queryFn: ({ signal }) => api("/progress", progressSchema, { signal }),
  });
  if (documents.isPending) return <LoadingState />;
  if (documents.error)
    return (
      <ErrorState
        message={message(documents.error)}
        retry={() => void documents.refetch()}
      />
    );
  const ready = documents.data.filter((d) => d.status === "ready");
  const next = ready[0];
  return (
    <div className="stack">
      <PageHeading
        eyebrow="Không gian học tập"
        title="Hôm nay, bạn muốn học gì?"
      >
        Bắt đầu từ tài liệu của bạn, hiểu sâu hơn qua từng câu hỏi.
      </PageHeading>
      <section className="hero">
        <div className="row between">
          <div>
            <p className="eyebrow">Bước tiếp theo</p>
            <h2>
              {next
                ? "Tiếp tục học từ tài liệu"
                : "Bắt đầu với tài liệu đầu tiên"}
            </h2>
            <p className="muted document-title">
              {next
                ? next.filename
                : "Tải lên một PDF có văn bản để đọc, hỏi AI và luyện tập."}
            </p>
            <Link
              className="button"
              href={next ? `/documents/${next.id}/study` : "/documents"}
            >
              {next ? "Tiếp tục học" : "Thêm tài liệu"}
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
          </div>
          <BookOpen size={72} color="var(--primary)" aria-hidden="true" />
        </div>
      </section>
      <div className="grid-2">
        <section className="card">
          <h2>Tài liệu học tập</h2>
          <div className="metric">{ready.length}</div>
          <p className="muted">Tài liệu đã sẵn sàng để học</p>
          <small>
            {documents.data.filter((d) => d.status === "processing").length}{" "}
            đang xử lý ·{" "}
            {documents.data.filter((d) => d.status === "failed").length} cần
            kiểm tra
          </small>
        </section>
        <section className="card">
          <h2>Luyện tập của bạn</h2>
          {progress.isPending ? (
            <p role="status">Đang tải tiến độ…</p>
          ) : progress.error ? (
            <ErrorState
              message={message(progress.error)}
              retry={() => void progress.refetch()}
            />
          ) : (
            <>
              <div className="metric">{progress.data.total_attempts}</div>
              <p className="muted">
                Câu hỏi đã nộp
                {progress.data.accuracy != null
                  ? ` · ${progress.data.accuracy}% trả lời đúng`
                  : ""}
              </p>
              <Link href="/progress" className="row">
                Xem tiến độ
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </>
          )}
        </section>
      </div>
      <section>
        <div className="row between" style={{ marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>Tài liệu gần đây</h2>
          <Link href="/documents" className="button secondary">
            Xem tất cả
          </Link>
        </div>
        {documents.data.length ? (
          <div className="stack">
            {documents.data.slice(0, 3).map((doc) => (
              <DocumentItem key={doc.id} document={doc} />
            ))}
          </div>
        ) : (
          <EmptyState title="Một khởi đầu mới">
            Tài liệu bạn thêm sẽ xuất hiện tại đây. Chọn “Thêm tài liệu” để bắt
            đầu.
          </EmptyState>
        )}
      </section>
    </div>
  );
}
export function Documents() {
  const documents = useDocuments();
  const cache = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const lock = useRef(false);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.set("file", file);
      return api("/documents", documentSchema, { method: "POST", body: form });
    },
    onSettled: () => {
      void cache.invalidateQueries({ queryKey: ["documents"] });
    },
  });
  async function add(file?: File) {
    if (!file || lock.current) return;
    setError("");
    if (
      !file.name.toLowerCase().endsWith(".pdf") ||
      file.size > 20 * 1024 * 1024 ||
      !file.size
    ) {
      setError("Chọn PDF có dữ liệu, tối đa 20 MB.");
      return;
    }
    lock.current = true;
    try {
      await upload.mutateAsync(file);
    } catch (e) {
      setError(message(e));
    } finally {
      lock.current = false;
      if (input.current) input.current.value = "";
    }
  }
  return (
    <div className="stack">
      <PageHeading eyebrow="Môn học · Thư viện" title="Tài liệu của bạn">
        Mỗi tài liệu là một không gian để đọc, hỏi và luyện tập.
      </PageHeading>
      <section
        className="card empty"
        style={{
          borderStyle: "dashed",
          borderColor: dragging ? "var(--primary)" : "var(--control-border)",
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void add(e.dataTransfer.files[0]);
        }}
      >
        <div className="empty-icon">
          <Upload size={28} aria-hidden="true" />
        </div>
        <h2>Thêm tài liệu học tập</h2>
        <p className="muted">
          Kéo một PDF vào đây hoặc chọn tệp. Tối đa 20 MB, có văn bản.
        </p>
        <input
          ref={input}
          type="file"
          accept=".pdf,application/pdf"
          className="sr-only"
          aria-label="Chọn tài liệu PDF"
          disabled={upload.isPending}
          onChange={(e) => void add(e.target.files?.[0])}
        />
        <Button
          pending={upload.isPending}
          onClick={() => input.current?.click()}
        >
          <Upload size={18} aria-hidden="true" />
          {upload.isPending ? "Đang xử lý tài liệu…" : "Chọn PDF"}
        </Button>
        {upload.isPending && (
          <p role="status" className="muted" style={{ marginTop: 16 }}>
            Đang đọc và lập chỉ mục PDF. Giữ trang mở đến khi hoàn tất.
          </p>
        )}
        {upload.isSuccess && !error && (
          <p role="status" style={{ marginTop: 16 }}>
            Tài liệu đã sẵn sàng để học.
          </p>
        )}
      </section>
      {error && <ErrorState message={error} />}
      <label className="field">
        <span className="row">
          <Search size={18} aria-hidden="true" />
          Tìm tài liệu
        </span>
        <input
          className="input"
          placeholder="Tìm theo tên tài liệu…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </label>
      {documents.isPending ? (
        <LoadingState />
      ) : documents.error ? (
        <ErrorState
          message={message(documents.error)}
          retry={() => void documents.refetch()}
        />
      ) : documents.data.length ? (
        <div className="stack">
          {documents.data
            .filter((doc) =>
              doc.filename
                .toLocaleLowerCase("vi")
                .includes(filter.toLocaleLowerCase("vi")),
            )
            .map((doc) => (
              <DocumentItem key={doc.id} document={doc} />
            ))}
          {documents.data.every(
            (doc) =>
              !doc.filename
                .toLocaleLowerCase("vi")
                .includes(filter.toLocaleLowerCase("vi")),
          ) && (
            <EmptyState title="Không tìm thấy tài liệu">
              Thử tên khác hoặc xóa nội dung tìm kiếm.
            </EmptyState>
          )}
        </div>
      ) : (
        <EmptyState title="Thư viện đang chờ bạn">
          Thêm tài liệu đầu tiên để bắt đầu. PDF scan cần OCR trước khi tải lên.
        </EmptyState>
      )}
      <p className="muted">
        Nếu xử lý thất bại hoặc kết nối bị ngắt, tải lại thư viện và chọn lại
        cùng PDF để thử lại.
      </p>
    </div>
  );
}
