import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthForm, AuthenticatedWorkspace } from "@/features/auth";
const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/dashboard",
}));
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});
function mount(
  content: React.ReactNode,
  cache = new QueryClient({ defaultOptions: { queries: { retry: false } } }),
) {
  render(<QueryClientProvider client={cache}>{content}</QueryClientProvider>);
  return cache;
}
async function credentials() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Tên đăng nhập"), "alice");
  await user.type(screen.getByLabelText("Mật khẩu"), "secret-pass");
  return user;
}
describe("account flows", () => {
  it("logs in with same-origin cookies and clears prior cached data", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(Response.json({ username: "alice" }));
    vi.stubGlobal("fetch", fetch);
    const cache = mount(<AuthForm />);
    cache.setQueryData(["documents"], [{ id: 999 }]);
    const user = await credentials();
    await user.click(screen.getByRole("button", { name: "Đăng nhập" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(cache.getQueryData(["documents"])).toBeUndefined();
    expect(fetch.mock.calls[0][1].credentials).toBe("same-origin");
  });
  it("retains values and reports rejected credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          Response.json(
            { code: "unauthenticated", message: "Thông tin chưa đúng" },
            { status: 401 },
          ),
        ),
    );
    mount(<AuthForm />);
    const user = await credentials();
    await user.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Thông tin chưa đúng",
    );
    expect(screen.getByLabelText("Tên đăng nhập")).toHaveValue("alice");
  });
  it("blocks duplicate submission while awaiting the server", async () => {
    const fetch = vi.fn().mockImplementation(() => new Promise(() => {}));
    vi.stubGlobal("fetch", fetch);
    mount(<AuthForm />);
    const user = await credentials();
    await user.dblClick(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Đăng nhập" })).toBeDisabled();
  });
  it("checks the cookie session after a fresh load", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json({ username: "alice" })),
    );
    mount(
      <AuthenticatedWorkspace>
        <p>Private lesson</p>
      </AuthenticatedWorkspace>,
    );
    expect(await screen.findByText("Private lesson")).toBeVisible();
  });
  it("removes cached account data on expiry", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json({ username: "alice" })),
    );
    const cache = mount(
      <AuthenticatedWorkspace>
        <p>Private lesson</p>
      </AuthenticatedWorkspace>,
    );
    await screen.findByText("Private lesson");
    cache.setQueryData(["documents"], [{ id: 999 }]);
    window.dispatchEvent(new Event("study-session-expired"));
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith(
        expect.stringContaining("reason=expired"),
      ),
    );
    expect(cache.getQueryData(["documents"])).toBeUndefined();
  });
  it("clears previous account cache when a different cookie identity is observed", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(Response.json({ username: "alice" }))
      .mockResolvedValueOnce(Response.json({ username: "bobby" }));
    vi.stubGlobal("fetch", fetch);
    const cache = mount(
      <AuthenticatedWorkspace>
        <p>Private lesson</p>
      </AuthenticatedWorkspace>,
    );
    await screen.findByText("Private lesson");
    cache.setQueryData(["documents"], [{ id: 999 }]);
    await cache.invalidateQueries({ queryKey: ["identity"] });
    await waitFor(() =>
      expect(screen.getByLabelText("Cài đặt tài khoản bobby")).toBeVisible(),
    );
    expect(cache.getQueryData(["documents"])).toBeUndefined();
  });
});
