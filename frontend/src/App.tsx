import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { useState, useEffect, useRef, useCallback } from "react";
import { ProcessedEvent } from "@/components/ActivityTimeline";
import { WorkspaceLayout } from "@/components/workspace/WorkspaceLayout";
import { SmartExplorer } from "@/components/workspace/SmartExplorer";
import { AdaptiveReader } from "@/components/reader/AdaptiveReader";
import { QnAPanel, type QAPlan, type NoteJobStatus } from "@/components/qa/QnAPanel";
import { Button } from "@/components/ui/button";

const API_BASE = import.meta.env.DEV ? "http://localhost:2024" : "http://localhost:8123";

type ExplorerFilter = "all" | "paper" | "note";

type WorkspaceResource = {
  paper_id: string;
  title: string;
  pdf_path: string;
  pdf_url?: string | null;
  has_summary: boolean;
  has_notes: boolean;
  summary_path?: string | null;
  notes_path?: string | null;
};

export default function App() {
  const [processedEventsTimeline, setProcessedEventsTimeline] = useState<ProcessedEvent[]>([]);
  const [historicalActivities, setHistoricalActivities] = useState<Record<string, ProcessedEvent[]>>({});
  const [paperPath, setPaperPath] = useState<string | null>(null);
  const [paperSourcePath, setPaperSourcePath] = useState<string | null>(null);
  const [paperId, setPaperId] = useState<string | null>(null);
  const [paperTitle, setPaperTitle] = useState<string | null>(null);
  const [workspaceResources, setWorkspaceResources] = useState<WorkspaceResource[]>([]);
  const [summaryText, setSummaryText] = useState<string | null>(null);
  const [qaAnswer, setQaAnswer] = useState<string | null>(null);
  const [qaCitations, setQaCitations] = useState<string[]>([]);
  const [qaPlan, setQaPlan] = useState<QAPlan | null>(null);
  const [qaThreadId, setQaThreadId] = useState<string | null>(null);
  const [qaIsPlanning, setQaIsPlanning] = useState(false);
  const [qaIsAnswering, setQaIsAnswering] = useState(false);
  const [noteJob, setNoteJob] = useState<NoteJobStatus>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryPrompts, setSummaryPrompts] = useState("summary");
  const [explorerFilter, setExplorerFilter] = useState<ExplorerFilter>("all");
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const hasFinalizeEventOccurredRef = useRef(false);

  const thread = useStream<{
    messages: Message[];
    paper_id: string;
    paper_title: string;
    pdf_path: string;
    mode: string;
    user_question: string;
    qa_history_window?: Message[];
  }>({
    apiUrl: API_BASE,
    assistantId: "agent",
    messagesKey: "messages",
    onUpdateEvent: (event: any) => {
      let processedEvent: ProcessedEvent | null = null;
      if (event.parse_and_chunk) {
        processedEvent = {
          title: "Parsing PDF",
          data: "Reading the uploaded paper and splitting it into Markdown sections.",
        };
      } else if (event.summarize_section) {
        processedEvent = {
          title: "Summarizing Section",
          data: event.summarize_section?.section_summaries?.[0]?.section_title || "Section summary running.",
        };
      } else if (event.reflection) {
        processedEvent = {
          title: "Reflection",
          data: "Checking whether the summary is complete.",
        };
      } else if (event.finalize_summary) {
        processedEvent = {
          title: "Finalizing Summary",
          data: "Writing the final markdown summary.",
        };
        hasFinalizeEventOccurredRef.current = true;
      }
      if (processedEvent) {
        setProcessedEventsTimeline((prevEvents) => [...prevEvents, processedEvent]);
      }
    },
    onError: (streamError: any) => {
      setError(streamError.message);
    },
  });

  const refreshWorkspace = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/workspace`);
      if (!response.ok) return;
      const data = await response.json();
      if (data.error) {
        console.warn("Workspace API error:", data.error);
      }
      setWorkspaceResources(Array.isArray(data.resources) ? data.resources : []);
    } catch {
      setWorkspaceResources([]);
    }
  }, []);

  const loadWorkspaceDocument = useCallback(async (paperIdValue: string) => {
    const response = await fetch(`${API_BASE}/api/workspace/${paperIdValue}`);
    if (!response.ok) {
      throw new Error("Workspace document failed to open");
    }
    const data = await response.json();
    const summaryResponse = await fetch(`${API_BASE}/api/workspace/${paperIdValue}/summary`);
    const summaryTextValue = summaryResponse.ok ? await summaryResponse.text() : "";
    const pdfUrl = data.pdf_url
      ? new URL(data.pdf_url, API_BASE).toString()
      : new URL(`/api/workspace/${paperIdValue}/pdf`, API_BASE).toString();
    setPaperPath(pdfUrl);
    setPaperSourcePath(data.pdf_path);
    setPaperId(data.paper_id);
    setPaperTitle(data.paper_title);
    setSummaryText(summaryTextValue || null);
    setQaAnswer(null);
    setQaCitations([]);
    setQaPlan(null);
    setQaThreadId(null);
    setNoteJob(null);
    setHasStarted(true);
  }, []);

  useEffect(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollViewport = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]");
      if (scrollViewport) {
        scrollViewport.scrollTop = scrollViewport.scrollHeight;
      }
    }
  }, [thread.messages]);

  useEffect(() => {
    if (hasFinalizeEventOccurredRef.current && !thread.isLoading && thread.messages.length > 0) {
      const lastMessage = thread.messages[thread.messages.length - 1];
      if (lastMessage && lastMessage.type === "ai" && lastMessage.id) {
        setHistoricalActivities((prev) => ({
          ...prev,
          [lastMessage.id!]: [...processedEventsTimeline],
        }));
      }
      hasFinalizeEventOccurredRef.current = false;
    }
  }, [thread.messages, thread.isLoading, processedEventsTimeline]);

  const handleUploadPdf = useCallback(
    async (file: File) => {
      try {
        setError(null);
        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(`${API_BASE}/api/upload`, {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          throw new Error("PDF upload failed");
        }
        const data = await response.json();
        setPaperPath(new URL(data.pdf_url ?? data.pdf_path, API_BASE).toString());
        setPaperSourcePath(data.pdf_path);
        setPaperId(data.paper_id);
        setPaperTitle(file.name.replace(/\.pdf$/i, ""));
        setSummaryText(null);
        setQaAnswer(null);
        setQaCitations([]);
        setQaPlan(null);
        setQaThreadId(null);
        setNoteJob(null);
        await refreshWorkspace();
      } catch (err: any) {
        setError(err.message || "PDF upload failed");
      }
    },
    [refreshWorkspace]
  );

  const handleOpenWorkspace = useCallback(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  const handleSelectPaper = useCallback(
    async (paperIdValue: string) => {
      try {
        setError(null);
        await loadWorkspaceDocument(paperIdValue);
      } catch (err: any) {
        setError(err.message || "Workspace open failed");
      }
    },
    [loadWorkspaceDocument]
  );

  const submitSummary = useCallback(
    async (promptValue: string) => {
      if (!paperPath || !paperId) {
        setError("Please upload a PDF first.");
        return;
      }
      try {
        setHasStarted(true);
        setSummaryLoading(true);
        setProcessedEventsTimeline([]);
        hasFinalizeEventOccurredRef.current = false;
        setError(null);
        const payload = {
          pdf_path: paperSourcePath ?? paperPath,
          paper_id: paperId,
          paper_title: paperTitle,
          summary_prompts: promptValue,
        };
        const response = await fetch(`${API_BASE}/api/summary`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) throw new Error("Summary request failed");
        const data = await response.json();
        setSummaryText(data.summary || "");
        await refreshWorkspace();
      } catch (err: any) {
        setError(err.message || "Summary request failed");
      } finally {
        setSummaryLoading(false);
      }
    },
    [paperPath, paperSourcePath, paperId, paperTitle, refreshWorkspace]
  );

  const startQAPlan = useCallback(
    async (question: string) => {
      if (!paperId) {
        setError("Please upload a PDF first.");
        return;
      }
      try {
        setQaIsPlanning(true);
        setError(null);
        setQaAnswer(null);
        setQaCitations([]);
        setQaPlan(null);
        setQaThreadId(null);
        const payload = {
          paper_id: paperId,
          paper_title: paperTitle,
          user_question: question,
          qa_history_window: thread.messages.slice(-10),
        };
        const response = await fetch(`${API_BASE}/api/qa/plan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) throw new Error("QA plan request failed");
        const data = await response.json();
        setQaPlan(data.plan || null);
        setQaThreadId(data.thread_id || null);
      } catch (err: any) {
        setError(err.message || "QA plan request failed");
      } finally {
        setQaIsPlanning(false);
      }
    },
    [paperId, paperTitle, thread.messages]
  );

  const handleApproveQAPlan = useCallback(
    async (plan: QAPlan) => {
      if (!qaThreadId) {
        setError("QA thread missing, please ask the question again.");
        return;
      }
      try {
        setQaIsAnswering(true);
        setError(null);
        const response = await fetch(`${API_BASE}/api/qa/resume`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ thread_id: qaThreadId, plan }),
        });
        if (!response.ok) throw new Error("QA resume request failed");
        const data = await response.json();
        setQaAnswer(data.answer || "");
        setQaCitations(Array.isArray(data.citations) ? data.citations : []);
        setQaPlan(null);
        setQaThreadId(null);
      } catch (err: any) {
        setError(err.message || "QA resume request failed");
      } finally {
        setQaIsAnswering(false);
      }
    },
    [qaThreadId]
  );

  const handleCancelQAPlan = useCallback(() => {
    setQaPlan(null);
    setQaThreadId(null);
  }, []);

  const handleExtractNote = useCallback(
    async (keyword: string) => {
      if (!paperId) {
        setError("Please upload a PDF first.");
        return;
      }
      try {
        setError(null);
        const payload = {
          paper_id: paperId,
          paper_title: paperTitle,
          note_keyword: keyword,
          qa_history_window: thread.messages.slice(-10),
        };
        const response = await fetch(`${API_BASE}/api/note/extract`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) throw new Error("Note extract request failed");
        const data = await response.json();
        setNoteJob({ jobId: data.job_id, status: "queued" });
      } catch (err: any) {
        setError(err.message || "Note extract request failed");
      }
    },
    [paperId, paperTitle, thread.messages]
  );

  // 轮询笔记任务状态（仅以 jobId 为依赖，避免每次 status 更新重启 timer）
  useEffect(() => {
    if (!noteJob) return;
    if (noteJob.status === "done" || noteJob.status === "error") return;
    const jobId = noteJob.jobId;
    let stopped = false;
    const tick = async () => {
      if (stopped) return;
      try {
        const r = await fetch(`${API_BASE}/api/note/status/${jobId}`);
        if (!r.ok) return;
        const data = await r.json();
        if (stopped) return;
        if (data.status === "done") {
          stopped = true;
          setNoteJob({ jobId, status: "done", notePath: data.note_path });
          await refreshWorkspace();
        } else if (data.status === "error") {
          stopped = true;
          setNoteJob({ jobId, status: "error", error: data.error });
        }
        // running / queued 不再回写，避免触发 useEffect 重新创建 timer
      } catch {
        /* swallow */
      }
    };
    const timer = setInterval(tick, 2000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
    // 仅依赖 jobId，状态变化（终止态）由内部 setNoteJob 自动让 effect 重新评估并 return
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noteJob?.jobId]);

  const handleQnASubmit = useCallback(
    (
      submittedInputValue: string,
      promptValue: string,
      _effort: string,
      _model: string,
      nextMode: "summary" | "qa"
    ) => {
      if (nextMode === "summary") {
        void submitSummary(promptValue || summaryPrompts);
      } else {
        void startQAPlan(submittedInputValue);
      }
    },
    [submitSummary, startQAPlan, summaryPrompts]
  );

  const handleCancel = useCallback(() => {
    thread.stop();
  }, [thread]);

  const handleGenerateSummary = useCallback(() => {
    void submitSummary(summaryPrompts);
  }, [submitSummary, summaryPrompts]);

  const explorerResources = workspaceResources.filter((item) => {
    if (explorerFilter === "all") return true;
    if (explorerFilter === "paper") return true;
    return item.has_notes;
  });

  const workspace = (
    <WorkspaceLayout
      left={
        <SmartExplorer
          papers={explorerResources.map((item) => ({
            id: item.paper_id,
            name: item.title,
            type: item.has_notes ? ("note" as const) : ("paper" as const),
            status: item.has_summary ? ("done" as const) : ("empty" as const),
          }))}
          activeFilter={explorerFilter}
          onFilterChange={setExplorerFilter}
          onUploadPdf={handleUploadPdf}
          onOpenWorkspace={handleOpenWorkspace}
          onSelectPaper={handleSelectPaper}
        />
      }
      center={
        <AdaptiveReader
          paperUrl={paperPath}
          summaryText={summaryText}
          isLoading={summaryLoading}
          summaryPrompts={summaryPrompts}
          onSummaryPromptChange={setSummaryPrompts}
          onGenerateSummary={handleGenerateSummary}
        />
      }
      right={
        <QnAPanel
          messages={thread.messages}
          isLoading={summaryLoading || qaIsPlanning || qaIsAnswering}
          scrollAreaRef={scrollAreaRef}
          onSubmit={handleQnASubmit}
          onCancel={handleCancel}
          onUploadPdf={handleUploadPdf}
          liveActivityEvents={processedEventsTimeline}
          historicalActivities={historicalActivities}
          qaAnswer={qaAnswer}
          qaCitations={qaCitations}
          qaPlan={qaPlan}
          qaIsPlanning={qaIsPlanning}
          qaIsAnswering={qaIsAnswering}
          onApprovePlan={handleApproveQAPlan}
          onCancelPlan={handleCancelQAPlan}
          onExtractNote={handleExtractNote}
          noteJob={noteJob}
        />
      }
    />
  );

  return (
    <>
      {error ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 px-4 text-center">
          <div className="max-w-md rounded-2xl border border-red-500/30 bg-slate-950 p-6 text-slate-100 shadow-2xl">
            <h1 className="text-2xl font-bold text-red-400">Error</h1>
            <p className="mt-3 text-sm text-slate-300">{JSON.stringify(error)}</p>
            <Button className="mt-6" variant="destructive" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </div>
      ) : null}

      {!hasStarted && thread.messages.length === 0 ? (
        <div className="h-screen overflow-hidden">{workspace}</div>
      ) : (
        workspace
      )}
    </>
  );
}
