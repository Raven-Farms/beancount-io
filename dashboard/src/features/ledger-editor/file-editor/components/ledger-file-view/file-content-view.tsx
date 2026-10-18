import { useMemo } from "react";
import type { GetLedgerFileQuery, BeancountError } from "@/graphql/definitions";
import {
  ImageFileView,
  PDFFileView,
  UnknownFileView,
} from "../non-text-file-views";
import {
  getFilename,
  getFileType,
  isPreviewableTextContent,
} from "../../../shared/lib/utils";
import { TextFileView } from "./text-file-view";

export interface FileContentViewProps {
  filePath: string;
  fileContent: NonNullable<GetLedgerFileQuery["getLedgerFile"]>;
  onSave: (content: string) => Promise<void>;
  /** Absent when the file cannot be deleted (the ledger's root main.bean). */
  onDelete?: () => void;
  isSaving: boolean;
  isEditMode?: boolean;
  lineNumber?: number;
  errors?: BeancountError[];
  onEnterEditMode: () => void;
  onExitEditMode: () => void;
}

/**
 * File content view component - coordinator component that determines file type
 * and delegates to appropriate view component
 * - Images, PDFs and unknown binary files → view-only components
 * - Known text files → TextFileView with edit capability
 * - Small unknown UTF-8 files → read-only TextFileView
 */
export function FileContentView({
  filePath,
  fileContent,
  onSave,
  onDelete,
  isSaving,
  isEditMode: isEditModeInput,
  lineNumber,
  errors,
  onEnterEditMode,
  onExitEditMode,
}: FileContentViewProps) {
  const filename = getFilename(filePath);

  // Determine file type based on filename
  const fileType = getFileType(filename);
  const isUnknownText = useMemo(
    () =>
      fileType === "unknown" &&
      isPreviewableTextContent(fileContent.content, fileContent.size),
    [fileType, fileContent.content, fileContent.size],
  );

  // Delegate to appropriate view component based on file type
  if (fileType === "image") {
    return (
      <ImageFileView
        filePath={filePath}
        fileContent={fileContent}
        onDelete={onDelete}
      />
    );
  }

  if (fileType === "pdf") {
    return (
      <PDFFileView
        filePath={filePath}
        fileContent={fileContent}
        onDelete={onDelete}
      />
    );
  }

  if (fileType === "unknown" && !isUnknownText) {
    return (
      <UnknownFileView
        filePath={filePath}
        fileContent={fileContent}
        onDelete={onDelete}
      />
    );
  }

  // Content-sniffed text is preview-only, even for writers or edit-mode URLs.
  return (
    <TextFileView
      filePath={filePath}
      fileContent={fileContent}
      onSave={onSave}
      onDelete={onDelete}
      isSaving={isSaving}
      isEditMode={isEditModeInput}
      readOnly={isUnknownText}
      lineNumber={lineNumber}
      errors={errors}
      onEnterEditMode={onEnterEditMode}
      onExitEditMode={onExitEditMode}
    />
  );
}
