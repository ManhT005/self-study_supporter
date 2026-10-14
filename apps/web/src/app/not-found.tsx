import Link from "next/link";
import { EmptyState } from "@/components/ui";
export default function NotFound() {
  return (
    <div className="page">
      <EmptyState
        title="Không tìm thấy trang"
        action={
          <Link href="/dashboard" className="button">
            Về Hôm nay
          </Link>
        }
      >
        Kiểm tra đường dẫn hoặc quay về không gian học.
      </EmptyState>
    </div>
  );
}
