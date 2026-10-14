"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Connectivity } from "./connectivity";
import { useState, type ReactNode } from "react";
export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: false } },
      }),
  );
  return <QueryClientProvider client={client}><Connectivity />{children}</QueryClientProvider>;
}
