import { useEffect, useState } from "react";
import { CollapsiblePanel } from "./CollapsiblePanel";
import { SummaryControlPanel } from "./SummaryControlPanel";
import { SummaryMarkdownView } from "./SummaryMarkdownView";

interface AdaptiveReaderProps {
  paperUrl?: string | null;
  summaryText: string | null;
  isLoading: boolean;
  summaryPrompts: string;
  onSummaryPromptChange: (value: string) => void;
  onGenerateSummary: () => void;
}

export function AdaptiveReader({
  paperUrl,
  summaryText,
  isLoading,
  summaryPrompts,
  onSummaryPromptChange,
  onGenerateSummary,
}: AdaptiveReaderProps) {
  const [summaryDocked, setSummaryDocked] = useState(false);

  useEffect(() => {
    setSummaryDocked(false);
  }, [paperUrl]);

  const summaryVisible = !summaryDocked;
  const bodyFlex = summaryVisible ? "flex-[0.62]" : "flex-1";
  const summaryFlex = summaryVisible ? "flex-[0.38]" : "flex-1";

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <div className="flex min-h-0 flex-1 flex-col gap-3">
        <div className={`min-h-0 ${bodyFlex}`}>
          <div className="h-full min-h-0 rounded-2xl border border-slate-200 bg-white shadow-sm">
            {paperUrl ? (
              <object
                data={paperUrl}
                type="application/pdf"
                className="h-full min-h-0 w-full rounded-2xl bg-white"
              >
                <iframe
                  title="paper"
                  src={paperUrl}
                  className="h-full min-h-0 w-full rounded-2xl bg-white"
                />
              </object>
            ) : (
              <div className="flex h-full min-h-0 items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-400">
                点击左侧任意文档后，这里会直接显示 PDF。
              </div>
            )}
          </div>
        </div>

        <div className={summaryVisible ? `min-h-0 ${summaryFlex}` : "mt-auto min-h-0"}>
          <CollapsiblePanel
            title="摘要区"
            collapsed={!summaryVisible}
            onToggle={() => setSummaryDocked((value) => !value)}
            tone="light"
          >
            <div className="max-h-[36vh] overflow-y-auto pr-1">
              {!summaryText ? (
                <SummaryControlPanel
                  value={summaryPrompts}
                  onChange={onSummaryPromptChange}
                  onGenerate={onGenerateSummary}
                  isLoading={isLoading}
                />
              ) : null}
              {summaryText ? <SummaryMarkdownView summaryText={summaryText} /> : null}
            </div>
          </CollapsiblePanel>
        </div>
      </div>
    </div>
  );
}
