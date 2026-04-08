"use client";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { PaperclipIcon, XIcon, ImageIcon, FileIcon, Loader2Icon } from "lucide-react";
import {
  type ChangeEvent,
  type ClipboardEvent,
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

// ============================================================================
// Types
// ============================================================================

export interface FileAttachment {
  id: string;
  file: File;
  previewUrl?: string;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

export interface PromptInputValue {
  text: string;
  files: FileAttachment[];
}

export interface PromptInputProps {
  value?: string;
  onChange?: (value: string) => void;
  onSubmit?: (value: PromptInputValue) => void | Promise<void>;
  onFilesChange?: (files: FileAttachment[]) => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  accept?: string;
  maxFiles?: number;
  maxFileSize?: number; // in bytes
  className?: string;
  footer?: ReactNode;
}

// ============================================================================
// Helper Functions
// ============================================================================

function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

function isImageFile(file: File): boolean {
  return file.type.startsWith("image/");
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

// ============================================================================
// PromptInput Component
// ============================================================================

export function PromptInput({
  value: controlledValue,
  onChange,
  onSubmit,
  onFilesChange,
  placeholder = "输入消息...",
  disabled = false,
  loading = false,
  accept,
  maxFiles = 10,
  maxFileSize = 10 * 1024 * 1024, // 10MB default
  className,
  footer,
}: PromptInputProps) {
  // Text input state
  const [internalValue, setInternalValue] = useState("");
  const value = controlledValue !== undefined ? controlledValue : internalValue;
  
  // Files state
  const [files, setFiles] = useState<FileAttachment[]>([]);
  
  // Refs
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // Sync files to parent
  useEffect(() => {
    onFilesChange?.(files);
  }, [files, onFilesChange]);

  // Cleanup preview URLs on unmount
  useEffect(() => {
    return () => {
      files.forEach((f) => {
        if (f.previewUrl) {
          URL.revokeObjectURL(f.previewUrl);
        }
      });
    };
  }, []);

  // Handle text change
  const handleTextChange = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    if (controlledValue === undefined) {
      setInternalValue(newValue);
    }
    onChange?.(newValue);
  }, [controlledValue, onChange]);

  // Add files
  const addFiles = useCallback((newFiles: FileList | File[] | null) => {
    if (!newFiles) return;

    const filesArray = Array.from(newFiles);
    
    // Check max files
    if (files.length + filesArray.length > maxFiles) {
      console.warn(`最多只能上传 ${maxFiles} 个文件`);
      return;
    }

    const newAttachments: FileAttachment[] = filesArray.map((file) => {
      // Check file size
      if (file.size > maxFileSize) {
        return {
          id: generateId(),
          file,
          status: "error",
          error: `文件大小超过 ${formatFileSize(maxFileSize)}`,
        };
      }

      // Create preview for images
      const previewUrl = isImageFile(file) ? URL.createObjectURL(file) : undefined;

      return {
        id: generateId(),
        file,
        previewUrl,
        status: "pending",
      };
    });

    setFiles((prev) => [...prev, ...newAttachments]);
  }, [files.length, maxFiles, maxFileSize]);

  // Remove file
  const removeFile = useCallback((id: string) => {
    setFiles((prev) => {
      const file = prev.find((f) => f.id === id);
      if (file?.previewUrl) {
        URL.revokeObjectURL(file.previewUrl);
      }
      return prev.filter((f) => f.id !== id);
    });
  }, []);

  // Handle file input change
  const handleFileInputChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    addFiles(e.target.files);
    // Reset input so same file can be selected again
    e.target.value = "";
  }, [addFiles]);

  // Handle paste
  const handlePaste = useCallback((e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData.items;
    if (!items) return;

    const pastedFiles: File[] = [];

    for (const item of items) {
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) {
          pastedFiles.push(file);
        }
      }
    }

    if (pastedFiles.length > 0) {
      e.preventDefault();
      addFiles(pastedFiles);
    }
  }, [addFiles]);

  // Handle key down
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      formRef.current?.requestSubmit();
      return;
    }

    // Remove last file on Backspace when empty
    if (e.key === "Backspace" && value === "" && files.length > 0) {
      e.preventDefault();
      const lastFile = files[files.length - 1];
      if (lastFile) {
        removeFile(lastFile.id);
      }
    }
  }, [value, files, removeFile]);

  // Handle submit
  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    
    if (disabled || loading) return;
    if (!value.trim() && files.length === 0) return;

    const validFiles = files.filter((f) => f.status !== "error");
    
    await onSubmit?.({
      text: value,
      files: validFiles,
    });

    // Clear after submit
    if (controlledValue === undefined) {
      setInternalValue("");
    }
    
    // Clear files and revoke URLs
    files.forEach((f) => {
      if (f.previewUrl) {
        URL.revokeObjectURL(f.previewUrl);
      }
    });
    setFiles([]);
  }, [value, files, disabled, loading, onSubmit, controlledValue]);

  // Handle drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  // Open file dialog
  const openFileDialog = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      className={cn("relative", className)}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple
        className="hidden"
        onChange={handleFileInputChange}
      />

      {/* File attachments */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 p-3 border-b bg-secondary/30">
          {files.map((file) => (
            <FileAttachmentChip
              key={file.id}
              attachment={file}
              onRemove={() => { removeFile(file.id); }}
            />
          ))}
        </div>
      )}

      {/* Textarea */}
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={handleTextChange}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        placeholder={placeholder}
        disabled={disabled}
        className="min-h-[100px] resize-none border-0 bg-transparent px-4 py-3 text-sm focus-visible:ring-0 focus-visible:ring-offset-0"
        rows={3}
      />

      {/* Footer */}
      <div className="flex items-center justify-between gap-2 border-t bg-secondary/30 px-3 py-2">
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            disabled={disabled || files.length >= maxFiles}
            onClick={openFileDialog}
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            <PaperclipIcon className="size-4" />
          </Button>
        </div>
        
        {footer}
      </div>
    </form>
  );
}

// ============================================================================
// FileAttachmentChip Component
// ============================================================================

interface FileAttachmentChipProps {
  attachment: FileAttachment;
  onRemove: () => void;
}

function FileAttachmentChip({ attachment, onRemove }: FileAttachmentChipProps) {
  const { file, previewUrl, status, error } = attachment;
  const isImage = isImageFile(file);

  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-lg border bg-card p-2 pr-8 transition-all",
        status === "error" && "border-red-300 bg-red-50",
        status === "uploading" && "opacity-70"
      )}
    >
      {/* Thumbnail */}
      <div className="relative size-10 shrink-0 overflow-hidden rounded-md bg-secondary">
        {isImage && previewUrl ? (
          <img
            src={previewUrl}
            alt={file.name}
            className="size-full object-cover"
          />
        ) : (
          <div className="flex size-full items-center justify-center text-muted-foreground">
            {isImage ? <ImageIcon className="size-5" /> : <FileIcon className="size-5" />}
          </div>
        )}
        
        {status === "uploading" && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/20">
            <Loader2Icon className="size-4 animate-spin text-white" />
          </div>
        )}
      </div>

      {/* File info */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-foreground" title={file.name}>
          {file.name}
        </p>
        <p className="text-[10px] text-muted-foreground">
          {error || formatFileSize(file.size)}
        </p>
      </div>

      {/* Remove button */}
      <button
        type="button"
        onClick={onRemove}
        className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-secondary hover:text-foreground group-hover:opacity-100"
      >
        <XIcon className="size-3.5" />
      </button>
    </div>
  );
}

// ============================================================================
// Hooks
// ============================================================================

export function usePromptInput() {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<FileAttachment[]>([]);

  const reset = useCallback(() => {
    setText("");
    // Cleanup preview URLs
    files.forEach((f) => {
      if (f.previewUrl) {
        URL.revokeObjectURL(f.previewUrl);
      }
    });
    setFiles([]);
  }, [files]);

  return {
    text,
    setText,
    files,
    setFiles,
    reset,
    value: { text, files },
  };
}
