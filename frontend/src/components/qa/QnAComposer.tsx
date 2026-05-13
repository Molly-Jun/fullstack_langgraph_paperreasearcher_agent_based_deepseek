import { InputForm } from "@/components/InputForm";

interface QnAComposerProps {
  onSubmit: (
    inputValue: string,
    summaryPrompts: string,
    effort: string,
    model: string,
    mode: "summary" | "qa"
  ) => void;
  onCancel: () => void;
  isLoading: boolean;
  onUploadPdf: (file: File) => void;
}

export function QnAComposer({ onSubmit, onCancel, isLoading, onUploadPdf }: QnAComposerProps) {
  return <InputForm onSubmit={onSubmit} onCancel={onCancel} isLoading={isLoading} hasHistory onUploadPdf={onUploadPdf} />;
}
