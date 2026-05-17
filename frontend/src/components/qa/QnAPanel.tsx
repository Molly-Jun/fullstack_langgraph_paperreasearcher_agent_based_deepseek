import ReactMarkdown from "react-markdown";
import { useState } from "react";
import type { Message } from "@langchain/langgraph-sdk";
import type { ProcessedEvent } from "@/components/ActivityTimeline";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export type QAPlan = {
  plan_text?: string;
  research_steps?: string[];
};

export type NoteJobStatus = {
  jobId: string;
  status: "queued" | "running" | "done" | "error";
  notePath?: string | null;
  error?: string | null;
} | null;

interface QnAPanelProps {
  messages: Message[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  onSubmit: (
    inputValue: string,
    summaryPrompts: string,
    effort: string,
    model: string,
    mode: "summary" | "qa"
  ) => void;
  onCancel: () => void;
  liveActivityEvents: ProcessedEvent[];
  historicalActivities: Record<string, ProcessedEvent[]>;
  qaAnswer: string | null;
  qaCitations: string[];
  qaPlan: QAPlan | null;
  qaIsPlanning: boolean;
  qaIsAnswering: boolean;
  onApprovePlan: (plan: QAPlan) => void;
  onCancelPlan: () => void;
  onExtractNote: (keyword: string) => void;
  noteJob: NoteJobStatus;
}

function planToText(plan: QAPlan | null): string {
  if (!plan) return "";
  const parts: string[] = [];
  if (plan.plan_text) parts.push(plan.plan_text);
  if (plan.research_steps?.length) {
    parts.push("**调研步骤：**\n" + plan.research_steps.map((s) => `- ${s}`).join("\n"));
  }
  return parts.join("\n\n");
}

export function QnAPanel({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  liveActivityEvents,
  historicalActivities,
  qaAnswer,
  qaCitations,
  qaPlan,
  qaIsPlanning,
  qaIsAnswering,
  onApprovePlan,
  onCancelPlan,
  onExtractNote,
  noteJob,
}: QnAPanelProps) {
  const [planEditValue, setPlanEditValue] = useState("");
  const [noteKeyword, setNoteKeyword] = useState("");

  const planText = planToText(qaPlan);
  const noteRunning = noteJob && (noteJob.status === "queued" || noteJob.status === "running");

  return (
    <div className="flex h-full flex-col bg-[#0b0f17] text-slate-100">
      <div className="flex-1 overflow-hidden px-3 py-3">
        <div className="flex h-full flex-col gap-3 overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/40 p-3">
          {qaIsPlanning ? (
            <div className="shrink-0 rounded-2xl border border-slate-700 bg-slate-900/70 p-3 text-sm text-slate-300">
              正在阅读全文并生成《调研/答题计划》……
            </div>
          ) : null}

          {qaPlan ? (
            <div className="shrink-0 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-3">
              <div className="mb-2 text-xs uppercase tracking-[0.2em] text-cyan-200">
                答题计划审批（HITL）
              </div>
              <ScrollArea className="h-64 pr-3">
                <div className="prose prose-invert max-w-none text-sm leading-7 text-slate-100">
                  <ReactMarkdown>{planText}</ReactMarkdown>
                </div>
              </ScrollArea>
              <Textarea
                value={planEditValue}
                onChange={(e) => setPlanEditValue(e.target.value)}
                placeholder="如需修改计划，可在此粘贴或编辑后再点【同意并执行】"
                className="mt-3 min-h-28 border-slate-700 bg-slate-950 text-slate-100"
              />
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  type="button"
                  className="bg-cyan-500 text-white hover:bg-cyan-400"
                  disabled={qaIsAnswering}
                  onClick={() => {
                    if (planEditValue.trim()) {
                      onApprovePlan({ ...qaPlan, plan_text: planEditValue.trim() });
                    } else {
                      onApprovePlan(qaPlan);
                    }
                    setPlanEditValue("");
                  }}
                >
                  {qaIsAnswering ? "答题中…" : "同意并执行"}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={qaIsAnswering}
                  onClick={() => {
                    setPlanEditValue("");
                    onCancelPlan();
                  }}
                >
                  取消
                </Button>
              </div>
            </div>
          ) : null}

          <div className="shrink-0 rounded-2xl border border-slate-800 bg-slate-900/80 p-3">
            <div className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-500">
              当前问答结果
            </div>
            {qaAnswer ? (
              <ScrollArea className="h-52 pr-3">
                <div className="prose prose-invert max-w-none text-sm leading-7 text-slate-100">
                  <ReactMarkdown>{qaAnswer}</ReactMarkdown>
                </div>
                {qaCitations.length > 0 ? (
                  <div className="mt-3 text-xs text-slate-400">
                    <div className="mb-1 font-medium text-slate-300">引用</div>
                    <div>{qaCitations.join("， ")}</div>
                  </div>
                ) : null}
              </ScrollArea>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-700 px-4 py-6 text-sm text-slate-500">
                尚未生成问答结果。
              </div>
            )}
          </div>

          <div className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-slate-800 bg-[#0b0f17]">
            <ChatMessagesView
              messages={messages}
              isLoading={isLoading}
              scrollAreaRef={scrollAreaRef}
              onSubmit={onSubmit}
              onCancel={onCancel}
              liveActivityEvents={liveActivityEvents}
              historicalActivities={historicalActivities}
            />
          </div>
        </div>
      </div>

      <div className="border-t border-slate-800/80 px-4 py-3">
        <div className="flex items-center gap-2">
          <input
            value={noteKeyword}
            onChange={(e) => setNoteKeyword(e.target.value)}
            placeholder="笔记关键词（可选）"
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500"
          />
          <Button
            type="button"
            className="bg-cyan-500 text-white hover:bg-cyan-400"
            disabled={!!noteRunning}
            onClick={() => onExtractNote(noteKeyword)}
          >
            {noteRunning ? "笔记生成中…" : "提取笔记"}
          </Button>
        </div>
        {noteJob ? (
          <div className="mt-2 text-xs text-slate-400">
            {noteJob.status === "done"
              ? `笔记已写入 ${noteJob.notePath ?? "data/note"}`
              : noteJob.status === "error"
              ? `笔记生成失败：${noteJob.error ?? ""}`
              : "笔记 Agent 正在后台运行……"}
          </div>
        ) : null}
      </div>
    </div>
  );
}
