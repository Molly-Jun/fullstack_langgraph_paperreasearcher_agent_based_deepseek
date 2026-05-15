import { Upload, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

type ExplorerFilter = "all" | "paper" | "note";

interface ExplorerItem {
  id: string;
  name: string;
  type: "paper" | "note";
  status?: "done" | "empty";
  children?: ExplorerItem[];
}

interface SmartExplorerProps {
  papers: ExplorerItem[];
  activeFilter: ExplorerFilter;
  onFilterChange: (filter: ExplorerFilter) => void;
  onUploadPdf: (file: File) => void;
  onOpenWorkspace?: () => void;
  onSelectPaper?: (paperId: string) => void;
}

export function SmartExplorer({
  papers,
  activeFilter,
  onFilterChange,
  onUploadPdf,
  onOpenWorkspace,
  onSelectPaper,
}: SmartExplorerProps) {
  const filteredItems = papers.filter((item) => {
    if (activeFilter === "all") return true;
    if (activeFilter === "note") return item.type === "note";
    return item.type === activeFilter;
  });

  return (
    <div className="flex h-full flex-col px-4 py-4 text-slate-100">
      <div className="mb-4">
        <div className="text-xs uppercase tracking-[0.28em] text-slate-400">
          Smart Explorer
        </div>
        <div className="mt-2 text-lg font-semibold text-slate-50">
          智能资源管理器
        </div>
      </div>

      <div className="mb-4 flex gap-2">
        <Button
          type="button"
          variant="secondary"
          className="flex-1 bg-slate-800 text-slate-100 hover:bg-slate-700"
          onClick={onOpenWorkspace}
        >
          <FolderOpen className="mr-2 h-4 w-4" />
          打开工作区
        </Button>
        <label className="flex-1 cursor-pointer">
          <div className="inline-flex w-full items-center justify-center rounded-md bg-cyan-500 px-3 py-2 text-sm font-medium text-white transition hover:bg-cyan-400">
            <Upload className="mr-2 h-4 w-4" />
            上传论文
          </div>
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUploadPdf(file);
            }}
          />
        </label>
      </div>

      <div className="mb-4 flex gap-2 text-xs">
        {[
          ["all", "全部"],
          ["paper", "论文"],
          ["note", "笔记"],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={`rounded-full border px-3 py-1 transition ${
              activeFilter === value
                ? "border-cyan-400 bg-cyan-500/15 text-cyan-200"
                : "border-slate-700 bg-slate-900 text-slate-400 hover:border-slate-600 hover:text-slate-200"
            }`}
            onClick={() => onFilterChange(value as ExplorerFilter)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        <div className="space-y-2">
          {filteredItems.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectPaper?.(item.id)}
              className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 shadow-[0_0_0_1px_rgba(15,23,42,0.35)] transition hover:border-cyan-500/40"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-slate-100">{item.name}</div>
                  <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                    {item.type === "paper" ? "PDF" : item.type === "notes" ? "NOTE" : "SUMMARY"}
                  </div>
                </div>
                {item.status === "done" ? (
                  <span
                    className="h-3 w-3 rounded-full border border-emerald-400 bg-emerald-400"
                    title="已生成摘要"
                  />
                ) : null}
              </div>
            </div>
          ))}
          {filteredItems.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-700 px-4 py-6 text-sm text-slate-500">
              当前没有可显示的资源。
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
