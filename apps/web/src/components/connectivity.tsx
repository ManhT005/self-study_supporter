"use client";
import { useSyncExternalStore } from "react";
function subscribe(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}
export function Connectivity() {
  const online = useSyncExternalStore(
    subscribe,
    () => navigator.onLine,
    () => true,
  );
  return online ? null : (
    <div role="status" className="error">
      Bạn đang ngoại tuyến. Kết nối lại để tiếp tục tải dữ liệu và gửi yêu cầu.
    </div>
  );
}
