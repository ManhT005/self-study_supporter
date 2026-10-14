import { AuthForm } from "@/features/auth";
export default async function Login({
  searchParams,
}: {
  searchParams: Promise<{ reason?: string }>;
}) {
  const { reason } = await searchParams;
  return <AuthForm expired={reason === "expired"} />;
}
