"use client";

import { useState } from "react";
import { MessageCircleQuestion, Send } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  type ClarificationType,
  getClarificationIcon,
  getClarificationLabel,
} from "@/core/messages/clarification";

interface ClarificationCardProps {
  question: string;
  context?: string;
  options?: string[];
  clarificationType: ClarificationType;
  onRespond: (response: string) => void;
  className?: string;
}

export function ClarificationCard({
  question,
  context,
  options,
  clarificationType,
  onRespond,
  className,
}: ClarificationCardProps) {
  const [customResponse, setCustomResponse] = useState("");
  const [hasResponded, setHasResponded] = useState(false);

  const icon = getClarificationIcon(clarificationType);
  const label = getClarificationLabel(clarificationType);

  const handleOptionClick = (option: string) => {
    if (hasResponded) return;
    setHasResponded(true);
    onRespond(option);
  };

  const handleCustomSubmit = () => {
    if (hasResponded || !customResponse.trim()) return;
    setHasResponded(true);
    onRespond(customResponse.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleCustomSubmit();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("w-full", className)}
    >
      <Card className="border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base font-medium">
            <span className="text-xl">{icon}</span>
            <span>{label}</span>
          </CardTitle>
          {context && (
            <CardDescription className="text-sm text-muted-foreground">
              {context}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Question */}
          <div className="text-sm font-medium text-foreground">
            <MessageCircleQuestion className="inline-block w-4 h-4 mr-1 text-amber-500" />
            {question}
          </div>

          {/* Options */}
          {options && options.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {options.map((option, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => handleOptionClick(option)}
                  disabled={hasResponded}
                  className="bg-background hover:bg-amber-100 dark:hover:bg-amber-900"
                >
                  {option}
                </Button>
              ))}
            </div>
          )}

          {/* Custom input */}
          <div className="flex gap-2">
            <Textarea
              value={customResponse}
              onChange={(e) => setCustomResponse(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的回复..."
              disabled={hasResponded}
              className="min-h-[60px] flex-1 resize-none bg-background"
            />
            <Button
              onClick={handleCustomSubmit}
              disabled={hasResponded || !customResponse.trim()}
              size="icon"
              className="shrink-0"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>

          {hasResponded && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-sm text-muted-foreground text-center"
            >
              已发送回复，等待 AI 继续...
            </motion.div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
