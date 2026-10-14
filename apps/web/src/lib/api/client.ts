import { z } from "zod";
import type { components } from "./generated";
export type Schemas = components["schemas"];
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code: string,
    public requestId?: string,
  ) {
    super(message);
  }
}
export const identitySchema = z.object({
  username: z.string(),
}) satisfies z.ZodType<Schemas["Identity"]>;
export const documentSchema = z.object({
  id: z.number(),
  filename: z.string(),
  status: z.enum(["processing", "ready", "failed"]),
  page_count: z.number().nullable(),
  chunk_count: z.number().nullable(),
}) satisfies z.ZodType<Schemas["DocumentDTO"]>;
export const documentsSchema = z.array(documentSchema);
export const citationSchema = z.object({
  chunk_id: z.string(),
  document_id: z.string(),
  text: z.string(),
  source: z.string(),
  page_start: z.number().nullable(),
  page_end: z.number().nullable(),
  score: z.number().nullable().optional(),
}) satisfies z.ZodType<Schemas["CitationDTO"]>;
export const answerSchema = z.object({
  answer: z.string(),
  citations: z.array(citationSchema),
  trace_id: z.string(),
}) satisfies z.ZodType<Schemas["ChatResponse"]>;
export const readerSchema = z.array(
  z.object({
    chunk_id: z.string(),
    text: z.string(),
    page_start: z.number().nullable(),
    page_end: z.number().nullable(),
  }) satisfies z.ZodType<Schemas["ReaderChunk"]>,
);
export const quizSchema = z.object({
  quiz_id: z.string(),
  questions: z.array(
    z.object({
      question: z.string(),
      options: z.tuple([z.string(), z.string(), z.string(), z.string()]),
      topic: z.string(),
    }),
  ),
}) satisfies z.ZodType<Schemas["QuizDTO"]>;
export const gradeSchema = z.object({
  is_correct: z.boolean(),
  correct_index: z.number(),
  explanation: z.string(),
}) satisfies z.ZodType<Schemas["GradeDTO"]>;
export const progressSchema = z.object({
  total_attempts: z.number(),
  correct: z.number(),
  accuracy: z.number().nullable(),
  topics: z.array(z.string()),
}) satisfies z.ZodType<Schemas["ProgressDTO"]>;
export const pathSchema = z.object({
  concepts: z.array(z.string()),
  has_cycle: z.boolean(),
}) satisfies z.ZodType<Schemas["PathDTO"]>;
export async function api<T>(
  path: string,
  schema: z.ZodType<T>,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined")
      window.dispatchEvent(new Event("study-session-expired"));
    const parsed = z
      .object({
        message: z.string(),
        code: z.string(),
        request_id: z.string().optional(),
      })
      .safeParse(await response.json().catch(() => null));
    throw new ApiError(
      response.status,
      parsed.success
        ? parsed.data.message
        : "Yêu cầu thất bại. Vui lòng thử lại.",
      parsed.success ? parsed.data.code : "request_error",
      parsed.success ? parsed.data.request_id : undefined,
    );
  }
  if (response.status === 204) return schema.parse(undefined);
  return schema.parse(await response.json());
}
export function post<T>(path: string, schema: z.ZodType<T>, body: unknown) {
  return api(path, schema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export function message(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Không thể xử lý yêu cầu. Vui lòng thử lại.";
}
