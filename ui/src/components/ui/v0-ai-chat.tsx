"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string;
}

const EXAMPLE_PROMPTS = [
  { label: "📊 Q3 Financial Report", prompt: "Generate a Q3 financial summary report" },
  { label: "🐛 Code Review", prompt: "Review this code for bugs and improvements: [paste code]" },
  { label: "📝 Write Email", prompt: "Write a professional email to follow up on our meeting" },
  { label: "💡 Brainstorm", prompt: "Help me brainstorm ideas for a new product feature" },
];

function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

async function streamChat(
  message: string,
  onText: (text: string) => void,
  onThinking: (thinking: string) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  try {
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      onError(`HTTP ${response.status}`);
      return;
    }

    if (!response.body) {
      onError("No response body");
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.trim()) continue;
        // "0:" = text delta, "1:" = thinking delta
        if (line.startsWith("0:")) {
          try {
            const text = JSON.parse(line.substring(2));
            onText(text);
          } catch {
            // ignore parse errors
          }
        } else if (line.startsWith("1:")) {
          try {
            const thinking = JSON.parse(line.substring(2));
            onThinking(thinking);
          } catch {
            // ignore parse errors
          }
        }
      }
    }

    // Process remaining buffer
    if (buffer.trim()) {
      if (buffer.startsWith("0:")) {
        try {
          const text = JSON.parse(buffer.substring(2));
          onText(text);
        } catch {
          // ignore
        }
      } else if (buffer.startsWith("1:")) {
        try {
          const thinking = JSON.parse(buffer.substring(2));
          onThinking(thinking);
        } catch {
          // ignore
        }
      }
    }

    onDone();
  } catch (err) {
    onError(err instanceof Error ? err.message : "Unknown error");
  }
}

export function V0Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = useCallback(async (prompt?: string) => {
    const text = (prompt ?? input).trim();
    if (!text || isLoading) return;

    if (!prompt) {
      setInput("");
    }
    setIsLoading(true);
    setError(null);

    const userMessage: Message = { id: generateId(), role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);

    const assistantId = generateId();
    let assistantContent = "";
    let assistantThinking = "";

    await streamChat(
      text,
      (text) => {
        assistantContent += text;
        setMessages((prev) => {
          const exists = prev.find((m) => m.id === assistantId);
          if (exists) {
            return prev.map((m) =>
              m.id === assistantId ? { ...m, content: assistantContent } : m
            );
          }
          return [...prev, { id: assistantId, role: "assistant", content: text }];
        });
      },
      (thinking) => {
        assistantThinking += thinking;
        setMessages((prev) => {
          const exists = prev.find((m) => m.id === assistantId);
          if (exists) {
            return prev.map((m) =>
              m.id === assistantId ? { ...m, thinking: assistantThinking } : m
            );
          }
          return [...prev, { id: assistantId, role: "assistant", content: "", thinking }];
        });
      },
      () => {
        setIsLoading(false);
      },
      (err) => {
        setError(err);
        setIsLoading(false);
        setMessages((prev) => [
          ...prev,
          { id: generateId(), role: "assistant", content: `Error: ${err}` },
        ]);
      }
    );
  }, [input, isLoading]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="text-center py-6 px-4 border-b bg-muted/30">
        <h1 className="text-2xl font-bold text-foreground">Ask me anything</h1>
        <p className="text-sm text-muted-foreground mt-1">
          I&apos;ll help coordinate the agent team to get it done
        </p>
      </div>

      {/* Example prompts */}
      {messages.length === 0 && !isLoading && (
        <div className="px-4 pt-6 pb-2">
          <p className="text-xs text-muted-foreground mb-3 text-center">
            Try one of these:
          </p>
          <div className="flex flex-wrap gap-2 justify-center">
            {EXAMPLE_PROMPTS.map((example, i) => (
              <button
                key={i}
                onClick={() => handleSubmit(example.prompt)}
                className="px-3 py-2 text-xs rounded-full bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors border"
              >
                {example.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat thread */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="text-center text-muted-foreground text-sm py-8">
            Or type your question below
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={
              message.role === "user"
                ? "flex justify-end"
                : "flex justify-start"
            }
          >
            {message.role === "user" ? (
              <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap bg-primary text-primary-foreground">
                {message.content}
              </div>
            ) : (
              <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm bg-muted text-foreground">
                {/* Thinking section - collapsible */}
                {message.thinking && (
                  <details className="mb-2">
                    <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground select-none">
                      Thinking...
                    </summary>
                    <div className="mt-2 text-xs text-muted-foreground/70 whitespace-pre-wrap font-mono border-l-2 border-muted-foreground/20 pl-3">
                      {message.thinking}
                    </div>
                  </details>
                )}
                {/* Main content - rendered as markdown */}
                {message.content && (
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                )}
                {!message.content && !message.thinking && (
                  <span className="animate-pulse">Thinking...</span>
                )}
              </div>
            )}
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Composer input */}
      <div className="px-4 pb-4">
        <div className="relative bg-neutral-900 rounded-xl border border-neutral-800">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question or describe what you need..."
            className="w-full px-4 py-3 resize-none bg-transparent border-none text-white text-sm placeholder:text-neutral-500 focus:outline-none min-h-[60px] max-h-[120px]"
            rows={2}
            disabled={isLoading}
          />
          <div className="flex items-center justify-end p-3 border-t border-neutral-800">
            <button
              type="button"
              onClick={() => handleSubmit()}
              disabled={!input.trim() || isLoading}
              className="px-4 py-1.5 rounded-lg text-sm bg-white text-black hover:bg-neutral-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Sending..." : "Send"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="px-4 pb-4 text-destructive text-sm text-center">{error}</div>
      )}
    </div>
  );
}
