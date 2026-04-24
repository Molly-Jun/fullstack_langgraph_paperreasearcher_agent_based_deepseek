import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { useState, useEffect, useRef, useCallback } from "react";
import { ProcessedEvent } from "@/components/ActivityTimeline";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import ReactMarkdown from "react-markdown";

const API_BASE = import.meta.env.DEV ? "http://localhost:2024" : "http://localhost:8123";

export default function App() {
  const [processedEventsTimeline, setProcessedEventsTimeline] = useState<ProcessedEvent[]>([]);
  const [historicalActivities, setHistoricalActivities] = useState<Record<string, ProcessedEvent[]>>({});
  const [paperPath, setPaperPath] = useState<string | null>(null);
  const [paperId, setPaperId] = useState<string | null>(null);
  const [summaryText, setSummaryText] = useState<string | null>(null);
  const [qaAnswer, setQaAnswer] = useState<string | null>(null);
  const [qaCitations, setQaCitations] = useState<string[]>([]);
  const [hasStarted, setHasStarted] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const hasFinalizeEventOccurredRef = useRef(false);
  const [error, setError] = useState<string | null>(null);

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
      setPaperPath(data.pdf_path);
      setPaperId(data.paper_id);
      setSummaryText(null);
      setQaAnswer(null);
      setQaCitations([]);
    } catch (err: any) {
      setError(err.message || "PDF upload failed");
    }
  }, []);

  const handleSubmit = useCallback(
    async (
      submittedInputValue: string,
      summaryPrompts: string,
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
        setIsBusy(true);
        setProcessedEventsTimeline([]);
        hasFinalizeEventOccurredRef.current = false;
        setError(null);

        const payload = {
          pdf_path: paperPath,
          paper_id: paperId,
          mode: nextMode,
          user_question: submittedInputValue,
          summary_prompts: summaryPrompts,
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
        } else {
          setQaAnswer(data.answer || "");
          setQaCitations(Array.isArray(data.citations) ? data.citations : []);
        }
        setIsBusy(false);
      } catch (err: any) {
        setError(err.message || "Request failed");
        setIsBusy(false);
      }
    },
    [paperPath, paperId]
  );

  const handleCancel = useCallback(() => {
    thread.stop();
    setIsBusy(false);
  }, [thread]);

  return (
    <div className="flex h-screen bg-neutral-800 text-neutral-100 font-sans antialiased overflow-hidden">
      <main className="h-full w-full max-w-4xl mx-auto overflow-hidden">
        {!hasStarted && thread.messages.length === 0 ? (
          <WelcomeScreen
            handleSubmit={handleSubmit}
            isLoading={isBusy || thread.isLoading}
            onCancel={handleCancel}
            onUploadPdf={handleUploadPdf}
          />
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="flex flex-col items-center justify-center gap-4">
              <h1 className="text-2xl text-red-400 font-bold">Error</h1>
              <p className="text-red-400">{JSON.stringify(error)}</p>
              <Button variant="destructive" onClick={() => window.location.reload()}>
                Retry
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex h-full flex-col overflow-hidden">
            {summaryText ? (
              <div className="border-b border-neutral-700 p-4 md:p-6 shrink-0">
                <h2 className="text-lg font-semibold mb-3">摘要</h2>
                <ScrollArea className="h-64 rounded-xl bg-neutral-700 p-4">
                  <ReactMarkdown>{summaryText}</ReactMarkdown>
                </ScrollArea>
              </div>
            ) : null}
            {qaAnswer ? (
              <div className="border-b border-neutral-700 p-4 md:p-6 shrink-0">
                <h2 className="text-lg font-semibold mb-2">问答结果</h2>
                <ScrollArea className="max-h-40 rounded-xl bg-neutral-700 p-4">
                  <div className="whitespace-pre-wrap leading-7">{qaAnswer}</div>
                  {qaCitations.length > 0 ? (
                    <div className="mt-3 text-sm text-neutral-300">
                      <div className="font-medium mb-1">引用</div>
                      <div>{qaCitations.join("， ")}</div>
                    </div>
                  ) : null}
                </ScrollArea>
              </div>
            ) : null}
            <div className="flex-1 min-h-0">
              <ChatMessagesView
                messages={thread.messages}
                isLoading={isBusy || thread.isLoading}
                scrollAreaRef={scrollAreaRef}
                onSubmit={handleSubmit}
                onCancel={handleCancel}
                onUploadPdf={handleUploadPdf}
                liveActivityEvents={processedEventsTimeline}
                historicalActivities={historicalActivities}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
