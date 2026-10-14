"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import {
  api,
  documentSchema,
  message,
  pathSchema,
  post,
} from "@/lib/api/client";
import { useMode } from "@/features/settings";
import { Button, ErrorState, LoadingState, PageHeading } from "@/components/ui";
export function DocumentDetail({ documentId }: { documentId: number }) {
  const mode = useMode();
  const cache = useQueryClient();
  const document = useQuery({
    queryKey: ["document", documentId],
    queryFn: ({ signal }) =>
      api(`/documents/${documentId}`, documentSchema, { signal }),
    refetchInterval: (query) =>
      query.state.data?.status === "processing" ? 5000 : false,
  });
  const path = useQuery({
    queryKey: ["path", documentId],
    queryFn: ({ signal }) =>
      api(`/documents/${documentId}/learning-path`, pathSchema, { signal }),
    enabled: document.data?.status === "ready",
  });
  const build = useMutation({
    mutationFn: () =>
      post(`/documents/${documentId}/learning-path`, pathSchema, { mode }),
    onSuccess: (data) => cache.setQueryData(["path", documentId], data),
  });
  if (document.isPending) return <LoadingState />;
  if (document.error)
    return (
      <ErrorState
        message={message(document.error)}
        retry={() => void document.refetch()}
      />
    );
  return (
    <div className="stack">
      <Link href="/documents" className="muted">
        ← Thư viện tài liệu
      </Link>
      <PageHeading title={document.data.filename}>
        PDF · {document.data.page_count ?? "—"} trang
      </PageHeading>
      {document.data.status === "ready" ? (
        <Link
          className="button"
          style={{ justifySelf: "start" }}
          href={`/documents/${documentId}/study`}
        >
          Học cùng AI
          <ArrowRight size={18} aria-hidden="true" />
        </Link>
      ) : (
        <ErrorState
          message={
            document.data.status === "failed"
              ? "Xử lý thất bại. Chọn lại cùng PDF trong thư viện để thử lại."
              : "Tài liệu đang được xử lý. Vui lòng đợi."
          }
        />
      )}
      <section className="card">
        <h2>Lộ trình từ tài liệu</h2>
        <p className="muted">
          Thứ tự khái niệm theo quan hệ tiên quyết từ tài liệu. Bạn có thể điều
          chỉnh cách học theo mục tiêu riêng.
        </p>
        {path.isPending && document.data.status === "ready" ? (
          <LoadingState />
        ) : path.error ? (
          <ErrorState
            message={message(path.error)}
            retry={() => void path.refetch()}
          />
        ) : path.data?.has_cycle ? (
          <p role="status">
            Quan hệ khái niệm có vòng lặp, chưa thể xếp thứ tự. Bạn vẫn có thể
            đọc và hỏi từ tài liệu.
          </p>
        ) : path.data?.concepts.length ? (
          <ol>
            {path.data.concepts.map((concept) => (
              <li key={concept}>{concept}</li>
            ))}
          </ol>
        ) : (
          <p className="muted">Chưa có lộ trình cho tài liệu này.</p>
        )}
        {build.error && <ErrorState message={message(build.error)} />}
        <Button
          className="secondary"
          pending={build.isPending}
          disabled={document.data.status !== "ready"}
          onClick={() => build.mutate()}
        >
          {path.data?.concepts.length ? "Tạo lại lộ trình" : "Tạo lộ trình"}
        </Button>
      </section>
    </div>
  );
}
