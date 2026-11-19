import type { ReactNode } from "react";

import { AdminNav } from "@/components/admin/AdminNav";

export function AdminChrome({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-6">
      <AdminNav />
      {children}
    </div>
  );
}
