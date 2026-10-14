import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Navigation } from "@/components/navigation";
import { Button, ErrorState } from "@/components/ui";
vi.mock("next/navigation", () => ({
  usePathname: () => "/documents/42/study",
}));
describe("workspace primitives", () => {
  it("marks the owning section active on nested routes", () => {
    render(<Navigation />);
    expect(screen.getByRole("link", { name: "Môn học" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
  it("has exactly four labeled mobile destinations", () => {
    render(<Navigation mobile />);
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });
  it("prevents pending actions and exposes errors", () => {
    render(
      <>
        <Button pending>Đăng nhập</Button>
        <ErrorState message="Phiên đã hết hạn" />
      </>,
    );
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("Phiên đã hết hạn");
  });
});
