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
  const [bodyCollapsed, setBodyCollapsed] = useState(false);
  const [summaryDocked, setSummaryDocked] = useState(false);

  useEffect(() => {
    setBodyCollapsed(false);
    setSummaryDocked(false);
  }, [paperUrl]);

  const bodyVisible = !bodyCollapsed;
  const summaryVisible = !summaryDocked;
  const bodyFlex = bodyVisible && summaryVisible ? "flex-[0.78]" : "flex-1";
  const summaryFlex = bodyVisible && summaryVisible ? "flex-[0.22]" : "flex-1";

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <div className="flex min-h-0 flex-1 flex-col gap-3">
        <div className={`min-h-0 ${bodyFlex}`}>
          <CollapsiblePanel
            title="正文区"
            collapsed={!bodyVisible}
            onToggle={() => setBodyCollapsed((value) => !value)}
            tone="light"
          >
            <div className="min-h-0">
              {paperUrl ? (
                <object
                  data={paperUrl}
                  type="application/pdf"
                  className="h-[80vh] w-full rounded-xl border border-slate-200 bg-white"
                >
                  <iframe
                    title="paper"
                    src={paperUrl}
                    className="h-[80vh] w-full rounded-xl border border-slate-200 bg-white"
                  />
                </object>
              ) : (
                <div className="flex h-[78vh] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-400">
                  点击左侧任意文档后，这里会直接显示 PDF。
                </div>
              )}
            </div>
          </CollapsiblePanel>
        </div>

        <div className={summaryVisible ? `min-h-0 ${summaryFlex}` : "mt-auto min-h-0"}>
          <CollapsiblePanel
            title="摘要区"
            collapsed={!summaryVisible}
            onToggle={() => setSummaryDocked((value) => !value)}
            tone="light"
          >
            <div className="flex max-h-[24vh] min-h-0 flex-col gap-4 overflow-y-auto pr-1">
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
