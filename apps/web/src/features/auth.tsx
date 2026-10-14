"use client";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { z } from "zod";
import {
  GraduationCap,
  LogOut,
  ShieldCheck,
  BookOpen,
  Sparkles,
} from "lucide-react";
import { api, ApiError, identitySchema, message, post } from "@/lib/api/client";
import { Button, ErrorState, LoadingState } from "@/components/ui";
import { NavigationShell } from "@/components/navigation";

export function AuthForm({
  register = false,
  expired = false,
}: {
  register?: boolean;
  expired?: boolean;
}) {
  const router = useRouter();
  const cache = useQueryClient();
  const lock = useRef(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const mutation = useMutation({
    mutationFn: () =>
      post(register ? "/auth/register" : "/auth/login", identitySchema, {
        username,
        password,
      }),
  });
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true;
    setError("");
    try {
      const user = await mutation.mutateAsync();
      if (register) {
        setSuccess(true);
        setPassword("");
      } else {
        cache.clear();
        cache.setQueryData(["identity"], user);
        router.replace("/dashboard");
      }
    } catch (e) {
      setError(message(e));
    } finally {
      lock.current = false;
    }
  }
  return (
    <div className="auth-page">
      <aside className="auth-story">
        <div className="brand">
          <span className="brand-mark">
            <GraduationCap aria-hidden="true" />
          </span>
          Self Study Supporter
        </div>
        <div>
          <p className="eyebrow" style={{ color: "#93c5fd" }}>
            Mỗi ngày, hiểu thêm một chút
          </p>
          <h1 style={{ fontSize: 44 }}>
            Tài liệu của bạn.
            <br />
            Hành trình của bạn.
          </h1>
          <p>
            Đọc có mục tiêu, hỏi có dẫn chứng và luyện tập để biết mình đã hiểu
            đến đâu.
          </p>
          <div className="stack">
            <div className="row">
              <BookOpen aria-hidden="true" />
              Một không gian cho tài liệu học tập
            </div>
            <div className="row">
              <Sparkles aria-hidden="true" />
              Trợ giảng AI gắn với nguồn của bạn
            </div>
            <div className="row">
              <ShieldCheck aria-hidden="true" />
              Tài liệu riêng theo tài khoản
            </div>
          </div>
        </div>
        <small>Học chủ động. Tiến bộ từng bước.</small>
      </aside>
      <main className="auth-form">
        <p className="eyebrow">Self Study Supporter</p>
        <h1>{register ? "Bắt đầu hành trình học" : "Chào mừng trở lại"}</h1>
        {expired && (
          <p role="status">
            Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.
          </p>
        )}
        <p className="muted">
          {register
            ? "Tạo tài khoản để học từ tài liệu của bạn."
            : "Đăng nhập để tiếp tục buổi học của bạn."}
        </p>
        {success ? (
          <div className="stack">
            <p role="status">Tài khoản đã được tạo. Bạn có thể đăng nhập.</p>
            <Link className="button" href="/login">
              Đăng nhập
            </Link>
          </div>
        ) : (
          <form onSubmit={submit} className="stack">
            <label className="field">
              Tên đăng nhập
              <input
                className="input"
                name="username"
                autoComplete="username"
                minLength={3}
                maxLength={80}
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label className="field">
              Mật khẩu
              <input
                className="input"
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                minLength={6}
                maxLength={72}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {error && <ErrorState message={error} />}
            <Button type="submit" pending={mutation.isPending}>
              {register ? "Tạo tài khoản" : "Đăng nhập"}
            </Button>
            <p className="muted">
              {register ? "Đã có tài khoản? " : "Chưa có tài khoản? "}
              <Link href={register ? "/login" : "/register"}>
                {register ? "Đăng nhập" : "Tạo tài khoản"}
              </Link>
            </p>
          </form>
        )}
      </main>
    </div>
  );
}
export function AuthenticatedWorkspace({ children }: { children: ReactNode }) {
  const router = useRouter();
  const cache = useQueryClient();
  const path = usePathname();
  const user = useQuery({
    queryKey: ["identity"],
    queryFn: async ({ signal }) => {
      const identity = await api("/auth/me", identitySchema, { signal });
      const previous = cache.getQueryData<z.infer<typeof identitySchema>>([
        "identity",
      ]);
      if (previous && previous.username !== identity.username) {
        await cache.cancelQueries({
          predicate: (query) => query.queryKey[0] !== "identity",
        });
        cache.removeQueries({
          predicate: (query) => query.queryKey[0] !== "identity",
        });
        cache.getMutationCache().clear();
      }
      return identity;
    },
    staleTime: 60_000,
    refetchOnWindowFocus: true,
    refetchInterval: 60_000,
  });
  const [expired, setExpired] = useState(false);
  useEffect(() => {
    const expire = () => setExpired(true);
    window.addEventListener("study-session-expired", expire);
    return () => window.removeEventListener("study-session-expired", expire);
  }, []);
  useEffect(
    () =>
      cache.getQueryCache().subscribe((event) => {
        if (
          event.type === "updated" &&
          event.query.state.error instanceof ApiError &&
          event.query.state.error.status === 401
        )
          setExpired(true);
      }),
    [cache],
  );
  useEffect(() => {
    if (
      expired ||
      (user.error instanceof ApiError && user.error.status === 401)
    ) {
      void cache.cancelQueries();
      cache.clear();
      router.replace(`/login?reason=expired&next=${encodeURIComponent(path)}`);
    }
  }, [expired, user.error, cache, router, path]);
  const logout = useMutation({
    mutationFn: () => api("/auth/logout", z.undefined(), { method: "POST" }),
    onSuccess: async () => {
      await cache.cancelQueries();
      cache.clear();
      router.replace("/login");
    },
  });
  if (user.isPending || expired)
    return (
      <div className="page">
        <LoadingState />
      </div>
    );
  if (user.error)
    return (
      <div className="page">
        <ErrorState
          message={message(user.error)}
          retry={() => void user.refetch()}
        />
      </div>
    );
  return (
    <NavigationShell
      key={user.data.username}
      username={user.data.username}
      logout={
        <Button
          className="secondary"
          pending={logout.isPending}
          onClick={() => logout.mutate()}
        >
          <LogOut size={18} aria-hidden="true" />
          Đăng xuất
        </Button>
      }
    >
      <div className="stack">
        {logout.error && <ErrorState message={message(logout.error)} />}
        {children}
      </div>
    </NavigationShell>
  );
}
