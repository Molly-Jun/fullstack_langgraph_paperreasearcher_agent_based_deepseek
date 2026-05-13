import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { useState, useEffect, useRef, useCallback } from "react";
import { ProcessedEvent } from "@/components/ActivityTimeline";
import { WorkspaceLayout } from "@/components/workspace/WorkspaceLayout";
import { SmartExplorer } from "@/components/workspace/SmartExplorer";
import { AdaptiveReader } from "@/components/reader/AdaptiveReader";
import { QnAPanel } from "@/components/qa/QnAPanel";
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

type WorkspacePage = { page: number; text: string };

export default function App() {
  const [processedEventsTimeline, setProcessedEventsTimeline] = useState<ProcessedEvent[]>([]);
  const [historicalActivities, setHistoricalActivities] = useState<Record<string, ProcessedEvent[]>>({});
  const [paperPath, setPaperPath] = useState<string | null>(null);
  const [paperSourcePath, setPaperSourcePath] = useState<string | null>(null);
  const [paperId, setPaperId] = useState<string | null>(null);
  const [paperTitle, setPaperTitle] = useState<string | null>(null);
  const [workspaceResources, setWorkspaceResources] = useState<WorkspaceResource[]>([]);
  const [workspacePages, setWorkspacePages] = useState<WorkspacePage[]>([]);
  const [summaryText, setSummaryText] = useState<string | null>(null);
  const [qaAnswer, setQaAnswer] = useState<string | null>(null);
  const [qaCitations, setQaCitations] = useState<string[]>([]);
  const [hasStarted, setHasStarted] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
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
  }>({
    apiUrl: API_BASE,
    assistantId: "agent",
    messagesKey: "messages",
    onUpdateEvent: (event: any) => {
      let processedEvent: ProcessedEvent | null = null;
      if (event.parse_and_chunk) {
        processedEvent = {
          title: "Parsing PDF",
          data: "Reading the uploaded paper and splitting it into sections.",
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
      } else if (event.answer_question) {
        processedEvent = {
          title: "Answering Question",
          data: "Generating an answer grounded in the paper.",
        };
      } else if (event.save_note) {
        processedEvent = {
          title: "Saving Note",
          data: "Appending the Q&A note to markdown.",
        };
      }

      if (processedEvent) {
        setProcessedEventsTimeline((prevEvents) => [...prevEvents, processedEvent!]);
      }
    },
    onError: (error: any) => {
      setError(error.message);
      setIsBusy(false);
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
    const pdfUrl = data.pdf_url ? new URL(data.pdf_url, API_BASE).toString() : new URL(`/api/workspace/${paperIdValue}/pdf`, API_BASE).toString();
    setPaperPath(pdfUrl);
    setPaperSourcePath(data.pdf_path);
    setPaperId(data.paper_id);
    setPaperTitle(data.paper_title);
    setWorkspacePages(Array.isArray(data.pages) ? data.pages : []);
    setSummaryText(summaryTextValue || null);
    setQaAnswer(null);
    setQaCitations([]);
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
      setIsBusy(false);
    }
  }, [thread.messages, thread.isLoading, processedEventsTimeline]);

  const handleUploadPdf = useCallback(async (file: File) => {
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
      setWorkspacePages([]);
      setSummaryText(null);
      setQaAnswer(null);
      setQaCitations([]);
      await refreshWorkspace();
    } catch (err: any) {
      setError(err.message || "PDF upload failed");
    }
  }, [refreshWorkspace]);

  const handleOpenWorkspace = useCallback(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  const handleSelectPaper = useCallback(async (paperIdValue: string) => {
    try {
      setError(null);
      await loadWorkspaceDocument(paperIdValue);
    } catch (err: any) {
      setError(err.message || "Workspace open failed");
    }
  }, [loadWorkspaceDocument]);

  const handleSubmit = useCallback(
    async (
      submittedInputValue: string,
      promptValue: string,
      effort: string,
      model: string,
      nextMode: "summary" | "qa"
    ) => {
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
          mode: nextMode,
          user_question: submittedInputValue,
          summary_prompts: promptValue,
          effort,
          model,
        };

        const response = await fetch(`${API_BASE}/api/summary`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error("Request failed");
        }
        const data = await response.json();
        if (nextMode === "summary") {
          setSummaryText(data.summary || "");
          await refreshWorkspace();
        } else {
          setQaAnswer(data.answer || "");
          setQaCitations(Array.isArray(data.citations) ? data.citations : []);
        }
      } catch (err: any) {
        setError(err.message || "Request failed");
      } finally {
        setSummaryLoading(false);
      }
    },
    [paperPath, paperSourcePath, paperId, paperTitle, refreshWorkspace]
  );

  const handleCancel = useCallback(() => {
    thread.stop();
    setIsBusy(false);
  }, [thread]);

  const handleGenerateSummary = useCallback(() => {
    handleSubmit("", summaryPrompts, "medium", "deepseek-chat", "summary");
  }, [handleSubmit, summaryPrompts]);

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
          isLoading={summaryLoading}
          scrollAreaRef={scrollAreaRef}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          onUploadPdf={handleUploadPdf}
          liveActivityEvents={processedEventsTimeline}
          historicalActivities={historicalActivities}
          qaAnswer={qaAnswer}
          qaCitations={qaCitations}
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
