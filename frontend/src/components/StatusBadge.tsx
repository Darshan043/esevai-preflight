import { AlertTriangle, CircleCheck, CircleX, Clock, LoaderCircle, Upload } from "lucide-react";

import type { SlotStatus } from "@/lib/slot-status";

const styles: Record<SlotStatus, { className: string; Icon: typeof Clock }> = {
  Pending: { className: "bg-zinc-100 text-zinc-700", Icon: Clock },
  Uploaded: { className: "bg-blue-100 text-blue-800", Icon: Upload },
  Processing: { className: "bg-amber-100 text-amber-800", Icon: LoaderCircle },
  Passed: { className: "bg-green-100 text-green-800", Icon: CircleCheck },
  "Needs fix": { className: "bg-red-100 text-red-800", Icon: AlertTriangle },
  Failed: { className: "bg-red-100 text-red-800", Icon: CircleX },
};

export function StatusBadge({ status }: { status: SlotStatus }) {
  const { className, Icon } = styles[status];

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border border-black/5 px-2.5 py-1 text-sm font-semibold ${className}`}>
      <Icon aria-hidden="true" className="h-4 w-4" />
      {status}
    </span>
  );
}
