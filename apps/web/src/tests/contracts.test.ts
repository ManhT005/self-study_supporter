import { describe, expect, it } from "vitest";
import { answerSchema, quizSchema } from "@/lib/api/client";
import { pageLabel } from "@/features/tutor";
describe("evidence and assessment contract", () => {
  it("does not invent absent pages and keeps multi-page bounds", () => {
    expect(pageLabel(null, null)).toBe("");
    expect(pageLabel(2, 4)).toBe(" · trang 2–4");
  });
  it("rejects quiz payloads without exactly four options", () => {
    expect(
      quizSchema.safeParse({
        quiz_id: "q",
        questions: [{ question: "Q", topic: "T", options: ["a", "b"] }],
      }).success,
    ).toBe(false);
  });
  it("accepts an answer with no citations", () => {
    expect(
      answerSchema.parse({
        answer: "No evidence",
        citations: [],
        trace_id: "r",
      }).citations,
    ).toEqual([]);
  });
});
