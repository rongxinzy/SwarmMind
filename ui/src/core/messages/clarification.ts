/**
 * Parse clarification tool message content
 * The content is formatted by ClarificationMiddleware with the following structure:
 * 
 * [icon] [context]
 * [question]
 * 
 *   1. [option1]
 *   2. [option2]
 *   ...
 */

export type ClarificationType =
  | "missing_info"
  | "ambiguous_requirement"
  | "approach_choice"
  | "risk_confirmation"
  | "suggestion";

export interface ParsedClarification {
  question: string;
  context?: string;
  options: string[];
  clarificationType: ClarificationType;
}

const TYPE_ICONS: Record<string, ClarificationType> = {
  "❓": "missing_info",
  "🤔": "ambiguous_requirement",
  "🔀": "approach_choice",
  "⚠️": "risk_confirmation",
  "💡": "suggestion",
};

export function parseClarificationContent(content: string): ParsedClarification {
  const lines = content.split("\n");
  
  let context: string | undefined;
  let question = "";
  const options: string[] = [];
  let clarificationType: ClarificationType = "missing_info";

  // Parse first line to get icon and context/question
  if (lines.length > 0) {
    const firstLine = lines[0];
    
    // Check for icon at the start
    for (const [icon, type] of Object.entries(TYPE_ICONS)) {
      if (firstLine.startsWith(icon)) {
        clarificationType = type;
        const rest = firstLine.slice(icon.length).trim();
        // Check if there's a second line (question) or if it's all on one line
        if (lines.length > 1 && lines[1].trim() && !lines[1].match(/^\s*\d+\./)) {
          context = rest;
          question = lines[1].trim();
        } else {
          question = rest;
        }
        break;
      }
    }
    
    // If no icon found, treat entire line as question
    if (!question) {
      question = firstLine;
    }
  }

  // Parse options (lines starting with "  1. ", "  2. ", etc.)
  for (const line of lines) {
    const match = line.match(/^\s*\d+\.\s+(.+)$/);
    if (match) {
      options.push(match[1]);
    }
  }

  return {
    question,
    context,
    options,
    clarificationType,
  };
}

export function getClarificationIcon(type: ClarificationType): string {
  const icons: Record<ClarificationType, string> = {
    missing_info: "❓",
    ambiguous_requirement: "🤔",
    approach_choice: "🔀",
    risk_confirmation: "⚠️",
    suggestion: "💡",
  };
  return icons[type];
}

export function getClarificationLabel(type: ClarificationType): string {
  const labels: Record<ClarificationType, string> = {
    missing_info: "需要更多信息",
    ambiguous_requirement: "需求不够明确",
    approach_choice: "需要选择方案",
    risk_confirmation: "需要确认风险",
    suggestion: "建议确认",
  };
  return labels[type];
}
