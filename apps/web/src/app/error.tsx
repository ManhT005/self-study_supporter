"use client";
import { ErrorState } from "@/components/ui";
export default function Error({ reset }: { reset: () => void }) {
  return (
    <div className="page">
      <ErrorState
        message="Không thể mở trang này. Vui lòng thử lại."
        retry={reset}
      />
    </div>
  );
}
