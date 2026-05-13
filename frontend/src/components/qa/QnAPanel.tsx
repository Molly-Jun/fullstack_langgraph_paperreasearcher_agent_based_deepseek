import ReactMarkdown from "react-markdown";
import { useState } from "react";
import type { Message } from "@langchain/langgraph-sdk";
import type { ProcessedEvent } from "@/components/ActivityTimeline";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import { NotePromptBar } from "./NotePromptBar";
import { ScrollArea } from "@/components/ui/scroll-area";

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
  onUploadPdf: (file: File) => void;
  liveActivityEvents: ProcessedEvent[];
  historicalActivities: Record<string, ProcessedEvent[]>;
  qaAnswer: string | null;
  qaCitations: string[];
}

export function QnAPanel({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  onUploadPdf,
  liveActivityEvents,
  historicalActivities,
  qaAnswer,
  qaCitations,
}: QnAPanelProps) {
  const [isNoteActive, setIsNoteActive] = useState(false);

  return (
    <div className="flex h-full flex-col bg-[#0b0f17] text-slate-100">
      <div className="border-b border-slate-800/80 px-4 py-4">
        <div className="text-xs uppercase tracking-[0.24em] text-slate-500">
          Q&amp;A Panel
        </div>
        <div className="mt-2 text-xl font-semibold text-slate-50">
          笔记预留入口
        </div>
      </div>

      <div className="flex-1 overflow-hidden px-3 py-3">
        <div className="flex h-full flex-col gap-3 overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/40 p-3">
          <div className="shrink-0 rounded-2xl border border-slate-800 bg-slate-900/80 p-3">
            <div className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-500">
              当前问答结果
            </div>
            {qaAnswer ? (
              <ScrollArea className="max-h-44 pr-3">
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
              onUploadPdf={onUploadPdf}
              liveActivityEvents={liveActivityEvents}
              historicalActivities={historicalActivities}
            />
          </div>
        </div>
      </div>

      <NotePromptBar onNoteClick={() => setIsNoteActive((prev) => !prev)} isActive={isNoteActive} />
      {isNoteActive ? (
        <div className="px-4 pb-4 text-xs text-cyan-200">
          后续可在这里接入独立的笔记抽取流程。
        </div>
      ) : null}
    </div>
  );
}
