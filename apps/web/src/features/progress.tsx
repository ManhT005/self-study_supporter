"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, message, progressSchema } from "@/lib/api/client";
import { EmptyState, ErrorState, LoadingState, PageHeading } from "@/components/ui";
export function Progress() {
  const query = useQuery({ queryKey: ["progress"], queryFn: ({ signal }) => api("/progress", progressSchema, { signal }) });
  if (query.isPending) return <LoadingState />;
  if (query.error) return <ErrorState message={message(query.error)} retry={() => void query.refetch()} />;
  const progress = query.data;
  return <div className="stack"><PageHeading eyebrow="Nhìn lại hành trình" title="Tiến độ học tập">Theo dõi câu hỏi đã làm và kết quả luyện tập của bạn.</PageHeading>{progress.total_attempts ? <><div className="grid-2"><section className="card"><h2>Câu hỏi đã nộp</h2><div className="metric">{progress.total_attempts}</div><p className="muted">{progress.correct} câu đúng · {progress.total_attempts - progress.correct} câu cần ôn</p></section><section className="card"><h2>Tỉ lệ trả lời đúng</h2><div className="metric">{progress.accuracy}%</div><p className="muted">Tỉ lệ trên các câu đã nộp, chưa phải mức độ thành thạo.</p></section></div><section className="card"><h2>Chủ đề đã luyện</h2><ul>{progress.topics.map(topic => <li key={topic}>{topic}</li>)}</ul><Link className="button" href="/practice">Tiếp tục luyện tập</Link></section></> : <EmptyState title="Tiến bộ bắt đầu từ lần luyện đầu tiên" action={<Link className="button" href="/practice">Bắt đầu luyện tập</Link>}>Hoàn thành câu hỏi đầu tiên để xem kết quả tại đây.</EmptyState>}</div>;
}
