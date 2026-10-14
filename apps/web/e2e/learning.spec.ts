import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";

const pdf = Buffer.from(
  "%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 71>>stream\nBT /F1 12 Tf 72 720 Td (First sentence. Second sentence.) Tj ET\nendstream\nendobj\ntrailer<</Root 1 0 R>>\n%%EOF",
);

test("real HTTP learning flow, responsive layout and accessible states", async ({
  page,
}, info) => {
  const username = `browser-${info.project.name}-${Date.now()}`;
  await page.goto("/register");
  await page.getByLabel("Tên đăng nhập").fill(username);
  await page.getByLabel("Mật khẩu", { exact: true }).fill("fixture-password");
  await page.getByRole("button", { name: "Tạo tài khoản" }).click();
  await expect(page.getByRole("status")).toContainText("Tài khoản đã được tạo");
  await page.getByRole("link", { name: "Đăng nhập", exact: true }).click();
  await page.getByLabel("Tên đăng nhập").fill(username);
  await page.getByLabel("Mật khẩu", { exact: true }).fill("fixture-password");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Hôm nay, bạn muốn học gì?" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Hôm nay, bạn muốn học gì?" }),
  ).toBeVisible();
  const screenshots = "../../docs/design/ui-v1/screenshots";
  await mkdir(screenshots, { recursive: true });
  for (const width of [360, 390, 768, 1024, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await page.setViewportSize(
    info.project.use.viewport ?? { width: 1440, height: 900 },
  );
  await page.screenshot({
    path: `${screenshots}/${info.project.name}-dashboard.png`,
    fullPage: true,
  });
  let accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.getByRole("link", { name: "Thêm tài liệu", exact: true }).click();
  await page
    .getByLabel("Chọn tài liệu PDF")
    .setInputFiles({
      name: "fixture.pdf",
      mimeType: "application/pdf",
      buffer: pdf,
    });
  await expect(
    page.getByText("Tài liệu đã sẵn sàng để học.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Học fixture.pdf", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Học cùng AI" }),
  ).toBeVisible();
  await page.getByLabel("Câu hỏi của bạn").fill("First sentence?");
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "Đọc", exact: true }).click();
    await expect(
      page.getByText("First sentence. Second sentence.", { exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Hỏi AI", exact: true }).click();
    await expect(page.getByLabel("Câu hỏi của bạn")).toHaveValue(
      "First sentence?",
    );
  }
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await page
    .getByRole("button", { name: "fixture.pdf · trang 1", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("First sentence.");
  accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({
    path: `${screenshots}/${info.project.name}-citation.png`,
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "fixture.pdf · trang 1", exact: true })).toBeFocused();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.screenshot({
    path: `${screenshots}/${info.project.name}-tutor.png`,
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "Luyện tập", exact: true })
    .filter({ visible: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Tạo bài luyện tập" }).click();
  await expect(page.getByRole("heading", { name: "Câu 1 / 1" })).toBeVisible();
  expect(await page.getByRole("radio").count()).toBe(4);
  await page.getByRole("radio").nth(1).check();
  await page.getByRole("button", { name: "Nộp đáp án" }).click();
  await expect(page.getByText("Chính xác!", { exact: true })).toBeVisible();
  accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({
    path: `${screenshots}/${info.project.name}-quiz.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Xem kết quả" }).click();
  await page.getByRole("link", { name: "Xem tiến độ", exact: true }).click();
  await expect(page.getByText("1 câu đúng · 0 câu cần ôn")).toBeVisible();
  await page.goto("/settings");
  await page
    .getByRole("main")
    .getByRole("button", { name: "Đăng xuất" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Chào mừng trở lại" }),
  ).toBeVisible();
  await page.goto("/progress");
  await expect(
    page.getByRole("heading", { name: "Chào mừng trở lại" }),
  ).toBeVisible();
});
