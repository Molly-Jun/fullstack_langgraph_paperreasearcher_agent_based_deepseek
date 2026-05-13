import type { ReactNode } from "react";

interface WorkspaceLayoutProps {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
}

export function WorkspaceLayout({ left, center, right }: WorkspaceLayoutProps) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#0b0f17] text-slate-100">
      <aside className="w-[20%] min-w-[260px] max-w-[360px] border-r border-slate-800/80 bg-[#0c111b]">
        {left}
      </aside>
      <section className="w-[55%] min-w-[520px] border-r border-slate-300/70 bg-slate-50 text-slate-900">
        {center}
      </section>
      <aside className="w-[25%] min-w-[320px] bg-[#0b0f17]">
        {right}
      </aside>
    </div>
  );
}
