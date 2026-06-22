import { ChatMessage } from "../api/client";

export function ToolSteps({ steps }: { steps: ChatMessage["tool_steps"] }) {
  if (!steps.length) return null;
  return (
    <div className="tool-steps">
      {steps.map((s, i) => (
        <span key={i} className="chip">
          🔧 {s.tool}
        </span>
      ))}
    </div>
  );
}
