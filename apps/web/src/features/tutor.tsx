"use client";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { BookOpen, MessageCircle, Send, Sparkles, X } from "lucide-react";
import { useRef, useState } from "react";
import { z } from "zod";
import { api, answerSchema, citationSchema, documentSchema, message, post, readerSchema } from "@/lib/api/client";
import { useMode } from "@/features/settings";
import { Button, EmptyState, ErrorState, LoadingState } from "@/components/ui";

type Answer = z.infer<typeof answerSchema>;
type Citation = z.infer<typeof citationSchema>;
export function pageLabel(start: number | null, end: number | null) { return start == null ? "" : end != null && end !== start ? ` · trang ${start}–${end}` : ` · trang ${start}`; }
export function Tutor({ documentId }: { documentId: number }) {
  const document = useQuery({ queryKey: ["document", documentId], queryFn: ({ signal }) => api(`/documents/${documentId}`, documentSchema, { signal }) });
  const reader = useQuery({ queryKey: ["reader", documentId], queryFn: ({ signal }) => api(`/documents/${documentId}/reader`, readerSchema, { signal }), enabled: document.data?.status === "ready" });
  const [pane, setPane] = useState<"both" | "read" | "chat">("both");
  const [draft, setDraft] = useState(""); const [turns, setTurns] = useState<{ question: string; response: Answer }[]>([]);
  const [citation, setCitation] = useState<Citation | null>(null); const [note, setNote] = useState("");
  const mode = useMode(); const lock = useRef(false);
  const ask = useMutation({ mutationFn: (question: string) => post(`/documents/${documentId}/chat`, answerSchema, { question, mode }), onSuccess: (response, question) => { setTurns(turns => [...turns, { question, response }]); setDraft(""); } });
  const saveNote = useMutation({ mutationFn: () => post(`/documents/${documentId}/notes`, z.object({ message: z.string() }), { note }), onSuccess: () => setNote("") });
  async function send(event: React.FormEvent) { event.preventDefault(); if (!draft.trim() || lock.current) return; lock.current = true; try { await ask.mutateAsync(draft.trim()); } catch { /* Preserve draft on failure. */ } finally { lock.current = false; } }
  if (document.isPending) return <LoadingState />;
  if (document.error) return <ErrorState message={message(document.error)} retry={() => void document.refetch()} />;
  if (document.data.status !== "ready") return <EmptyState title="Tài liệu chưa sẵn sàng" action={<Link href="/documents" className="button">Về thư viện</Link>}>Kiểm tra trạng thái hoặc chọn lại PDF để thử xử lý.</EmptyState>;
  return <div className="stack">
    <div className="row between"><div><Link href={`/documents/${documentId}`} className="muted">← Tài liệu của bạn</Link><h1 className="document-title" style={{ fontSize: 24, marginTop: 12 }}>{document.data.filename}</h1></div><Link className="button secondary" href="/practice">Luyện tập</Link></div>
    <div className="row pane-controls" aria-label="Chế độ học"><Button className={pane === "read" ? "" : "secondary"} aria-pressed={pane === "read"} onClick={() => setPane("read")}><BookOpen size={18} aria-hidden="true" />Đọc</Button><Button className={pane === "chat" ? "" : "secondary"} aria-pressed={pane === "chat"} onClick={() => setPane("chat")}><MessageCircle size={18} aria-hidden="true" />Hỏi AI</Button><Button className="secondary desktop-only" aria-pressed={pane === "both"} onClick={() => setPane("both")}>Đọc & hỏi</Button></div>
    <div className={`study-grid pane-${pane}`}>
      <section className="card reader-pane" aria-label="Đọc tài liệu"><h2>Đọc tài liệu</h2><p className="muted">Văn bản đã lập chỉ mục từ PDF. Số trang theo nguồn gốc.</p>{reader.isPending ? <LoadingState /> : reader.error ? <ErrorState message={message(reader.error)} retry={() => void reader.refetch()} /> : reader.data.length ? <div className="reader-content">{reader.data.map(chunk => <article key={chunk.chunk_id} id={`chunk-${chunk.chunk_id}`} tabIndex={-1} className="reader-chunk"><small className="eyebrow">{chunk.page_start == null ? "Đoạn tài liệu" : `Trang ${chunk.page_start}${chunk.page_end != null && chunk.page_end !== chunk.page_start ? `–${chunk.page_end}` : ""}`}</small><p className="pre-wrap">{chunk.text}</p></article>)}</div> : <EmptyState title="Chưa có nội dung đọc">Thử tải lại hoặc kiểm tra việc xử lý PDF.</EmptyState>}</section>
      <section className="card tutor-pane" aria-label="Trợ giảng AI"><div className="row"><span className="brand-mark"><Sparkles size={20} aria-hidden="true" /></span><div><h2 style={{ margin: 0 }}>Học cùng AI</h2><small className="muted">Hỏi từ nội dung tài liệu của bạn</small></div></div>
        <div className="chat-history">{turns.length === 0 && <div className="chat-welcome"><p className="eyebrow">Một câu hỏi, một bước hiểu</p><h3>Bạn đang muốn làm rõ điều gì?</h3><p className="muted">Hỏi về khái niệm, cách áp dụng hoặc đoạn bạn vừa đọc. Nguồn trích dẫn sẽ xuất hiện cùng câu trả lời.</p></div>}{turns.map((turn, index) => <div className="chat-turn" key={index}><div className="chat-question pre-wrap">{turn.question}</div><div className="chat-answer"><p className="pre-wrap">{turn.response.answer}</p>{turn.response.citations.length > 0 && <div><p className="muted" style={{ fontSize: 13 }}>Nguồn từ tài liệu</p><div className="stack" style={{ gap: 8 }}>{turn.response.citations.map((source, i) => <button key={`${source.chunk_id}-${i}`} className="citation-chip" onClick={() => setCitation(source)}><BookOpen size={16} aria-hidden="true" />{source.source}{pageLabel(source.page_start, source.page_end)}</button>)}</div></div>}</div></div>)}</div>
        {ask.isPending && <p role="status" className="muted">Đang tìm bằng chứng và soạn câu trả lời…</p>}{ask.error && <ErrorState message={message(ask.error)} />}
        <form className="stack chat-composer" onSubmit={send}><label className="field">Câu hỏi của bạn<textarea className="input" placeholder="Hỏi về đoạn bạn vừa đọc…" maxLength={4000} required value={draft} onChange={e => setDraft(e.target.value)} disabled={ask.isPending} /></label><Button type="submit" pending={ask.isPending} disabled={!draft.trim()}><Send size={18} aria-hidden="true" />Gửi câu hỏi</Button></form>
        <details className="notes"><summary>Ghi chú của tôi</summary><div className="stack" style={{ marginTop: 16 }}><label className="field">Nội dung ghi chú<textarea className="input" maxLength={4000} value={note} onChange={e => setNote(e.target.value)} /></label>{saveNote.error && <ErrorState message={message(saveNote.error)} />}{saveNote.isSuccess && <p role="status">Đã lưu ghi chú.</p>}<Button className="secondary" disabled={!note.trim()} pending={saveNote.isPending} onClick={() => saveNote.mutate()}>Lưu ghi chú</Button></div></details>
      </section>
    </div>
    <Dialog.Root open={citation !== null} onOpenChange={open => { if (!open) setCitation(null); }}><Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="dialog-content"><Dialog.Title style={{ paddingRight: 44 }}>Nguồn trích dẫn</Dialog.Title><Dialog.Description>{citation?.source}{citation && pageLabel(citation.page_start, citation.page_end)}</Dialog.Description><Dialog.Close className="button secondary dialog-close" aria-label="Đóng nguồn"><X size={18} aria-hidden="true" /></Dialog.Close><p className="pre-wrap" style={{ marginTop: 24 }}>{citation?.text}</p><Button className="secondary" disabled={!reader.data?.some(c => c.chunk_id === citation?.chunk_id)} onClick={() => { const key = citation?.chunk_id; setPane("read"); setCitation(null); setTimeout(() => { const target = window.document.getElementById(`chunk-${key}`); target?.scrollIntoView({ block: "center" }); target?.focus({ preventScroll: true }); }, 50); }}>Đọc đoạn trong tài liệu</Button></Dialog.Content></Dialog.Portal></Dialog.Root>
  </div>;
}
