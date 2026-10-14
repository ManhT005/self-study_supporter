import { AuthenticatedWorkspace } from "@/features/auth";
export default function Layout({ children }: { children: React.ReactNode }) {
  return <AuthenticatedWorkspace>{children}</AuthenticatedWorkspace>;
}
