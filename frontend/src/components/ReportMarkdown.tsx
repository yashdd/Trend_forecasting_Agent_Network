import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

const components: Components = {
  h1: ({ children }) => (
    <h1 className="font-display text-2xl sm:text-3xl font-semibold tracking-tight text-white mt-0 mb-6 pb-3 border-b border-white/10">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg sm:text-xl font-semibold text-white mt-10 mb-3 first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base sm:text-lg font-semibold text-white/90 mt-8 mb-2">{children}</h3>
  ),
  p: ({ children }) => <p className="text-white/80 leading-relaxed mb-4 last:mb-0">{children}</p>,
  ul: ({ children }) => (
    <ul className="list-disc pl-5 space-y-2 mb-4 text-white/80 marker:text-cyan-300">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal pl-5 space-y-2 mb-4 text-white/80 marker:text-cyan-300 marker:font-medium">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed pl-1">{children}</li>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-cyan-200 font-medium underline decoration-cyan-400/30 underline-offset-2 hover:text-cyan-100 hover:decoration-cyan-300/60 break-words"
    >
      {children}
    </a>
  ),
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }) => <em className="italic text-white/70">{children}</em>,
  hr: () => <hr className="my-8 border-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />,
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-cyan-300/30 bg-white/5 rounded-r-2xl py-3 px-4 my-4 text-white/80">
      {children}
    </blockquote>
  ),
  code: ({ className, children, ...props }) => {
    if (className) {
      return (
        <code className={`text-sm font-mono text-emerald-50 ${className}`} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="rounded-md bg-white/6 px-1.5 py-0.5 text-[0.9em] font-mono text-white/85 border border-white/10"
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="mb-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/30 p-4">{children}</pre>
  ),
  table: ({ children }) => (
    <div className="my-6 overflow-x-auto rounded-2xl border border-white/10">
      <table className="min-w-full text-sm text-left">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-white/6 text-white font-semibold">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-white/10">{children}</tbody>,
  tr: ({ children }) => <tr className="hover:bg-white/4">{children}</tr>,
  th: ({ children }) => <th className="px-4 py-3 font-semibold">{children}</th>,
  td: ({ children }) => <td className="px-4 py-3 text-white/80">{children}</td>,
};

export function ReportMarkdown(props: { markdown: string }) {
  return (
    <article className="report-markdown max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {props.markdown}
      </ReactMarkdown>
    </article>
  );
}
