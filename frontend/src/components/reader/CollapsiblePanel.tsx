import type { ReactNode } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

interface CollapsiblePanelProps {
  title: string;
  collapsed: boolean;
  onToggle: () => void;
  children: ReactNode;
  tone?: "light" | "neutral";
}

export function CollapsiblePanel({
  title,
  collapsed,
  onToggle,
  children,
  tone = "light",
}: CollapsiblePanelProps) {
  return (
    <section
      className={`rounded-2xl border ${
        tone === "light"
          ? "border-slate-200 bg-white"
          : "border-slate-200 bg-slate-100"
      } shadow-sm`}
    >
      <button
        type="button"
        className="flex w-full items-center justify-between border-b border-slate-200 px-4 py-3 text-left"
        onClick={onToggle}
      >
        <span className="text-sm font-semibold text-slate-800">{title}</span>
        {collapsed ? (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronUp className="h-4 w-4 text-slate-500" />
        )}
      </button>
      {!collapsed ? <div className="p-4">{children}</div> : null}
    </section>
  );
}
