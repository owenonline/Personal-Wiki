import { ChatMessage } from "../api/client";

export function ToolSteps({ steps }: { steps: ChatMessage["tool_steps"] }) {
  if (!steps.length) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
      {steps.map((s, i) => (
        <span
          key={i}
          style={{
            fontSize: 11,
            color: "var(--muted)",
            border: "1px dashed var(--surface2)",
            borderRadius: 6,
            padding: "1px 6px",
          }}
        >
          🔧 {s.tool}
        </span>
      ))}
    </div>
  );
}
