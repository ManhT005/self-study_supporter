import { DocumentDetail } from "@/features/document-detail";
import { notFound } from "next/navigation";
export default async function Document({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const id = Number(documentId);
  if (!Number.isSafeInteger(id) || id < 1) notFound();
  return <DocumentDetail documentId={id} />;
}
