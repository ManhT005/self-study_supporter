"use client";
import { useSyncExternalStore } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { api, message } from "@/lib/api/client";
import { Button, ErrorState, PageHeading } from "@/components/ui";
export type Mode = "auto" | "gemini" | "ollama";
function subscribe(callback: () => void) { window.addEventListener("storage", callback); window.addEventListener("study-preferences", callback); return () => { window.removeEventListener("storage", callback); window.removeEventListener("study-preferences", callback); }; }
function snapshot(): Mode { const value = localStorage.getItem("study-mode"); return value === "gemini" || value === "ollama" ? value : "auto"; }
export function useMode() { return useSyncExternalStore(subscribe, snapshot, () => "auto" as Mode); }
export function setMode(value: Mode) { localStorage.setItem("study-mode", value); window.dispatchEvent(new Event("study-preferences")); }
export function Settings() {
  const mode = useMode(); const cache = useQueryClient(); const router = useRouter();
  const logout = useMutation({ mutationFn: () => api("/auth/logout", z.undefined(), { method: "POST" }), onSuccess: async () => { await cache.cancelQueries(); cache.clear(); router.replace("/login"); } });
  return <div className="stack"><PageHeading eyebrow="Theo cách của bạn" title="Cài đặt">Tùy chọn cho những buổi học tiếp theo.</PageHeading><section className="card stack"><h2>Trợ giảng AI</h2><label className="field">Chế độ model<select className="input" value={mode} onChange={e => setMode(e.target.value as Mode)}><option value="auto">Tự động</option><option value="gemini">Gemini</option><option value="ollama">Ollama · Local</option></select></label><p className="muted">Model cần được quản trị viên cấu hình. Lựa chọn này áp dụng cho câu hỏi và bài luyện tập mới.</p></section><section className="card"><h2>Riêng tư và phiên học</h2><p className="muted">Tài liệu và kết quả luyện tập chỉ được truy cập bằng tài khoản của bạn. Phiên đăng nhập và bài quiz chưa hoàn tất sẽ hết hạn khi dịch vụ khởi động lại.</p>{logout.error && <ErrorState message={message(logout.error)} />}<Button className="secondary" pending={logout.isPending} onClick={() => logout.mutate()}>Đăng xuất</Button></section></div>;
}
