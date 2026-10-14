import { Tutor } from "@/features/tutor";
import { notFound } from "next/navigation";
export default async function Study({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const id = Number(documentId);
  if (!Number.isSafeInteger(id) || id < 1) notFound();
  return <Tutor key={id} documentId={id} />;
}
