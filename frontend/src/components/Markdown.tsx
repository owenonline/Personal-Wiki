import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders assistant text as GitHub-flavored markdown, styled via the `.md` class. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
