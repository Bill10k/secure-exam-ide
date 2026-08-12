import React from "react";

const difficultyStyles: Record<number, string> = {
  1: "text-emerald-400 bg-emerald-400/10 border border-emerald-400/30",
  2: "text-amber-400 bg-amber-400/10 border border-amber-400/30",
  3: "text-red-400 bg-red-400/10 border border-red-400/30",
};

const diffLabels: Record<number, string> = {
  1: "Easy",
  2: "Medium",
  3: "Hard",
};

function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="bg-gray-950 text-blue-300 px-1.5 py-0.5 rounded font-mono text-[11px] border border-gray-800">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-bold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

function FormattedText({ content }: { content: string }) {
  if (!content) return <span className="text-gray-500 italic">No description provided.</span>;

  const blocks = content.split(/\n\n+/);

  return (
    <div className="space-y-3 font-mono text-xs text-gray-200 leading-relaxed">
      {blocks.map((block, bIdx) => {
        const trimmed = block.trim();
        if (!trimmed) return null;

        if (trimmed.startsWith("```") && trimmed.endsWith("```")) {
          const lines = trimmed.slice(3, -3).split("\n");
          const firstLine = lines[0].trim();
          const hasLang = firstLine && !firstLine.includes(" ");
          const codeText = hasLang ? lines.slice(1).join("\n") : lines.join("\n");
          return (
            <pre
              key={bIdx}
              className="bg-gray-950 p-3 rounded-lg border border-gray-800 text-blue-300 font-mono text-xs overflow-x-auto whitespace-pre-wrap my-2"
            >
              {codeText}
            </pre>
          );
        }

        if (/^#{1,6}\s+/.test(trimmed)) {
          const level = (trimmed.match(/^#+/)?.[0] || "").length;
          const title = trimmed.replace(/^#{1,6}\s+/, "");
          const headingClass =
            level === 1
              ? "text-base font-bold text-white border-b border-gray-800 pb-1 mt-3"
              : level === 2
              ? "text-sm font-bold text-blue-400 mt-2"
              : "text-xs font-bold text-gray-300 uppercase tracking-wider mt-2";
          return (
            <div key={bIdx} className={headingClass}>
              {renderInline(title)}
            </div>
          );
        }

        const lines = trimmed.split("\n");
        const isBulletList = lines.every((l) => /^\s*[-*]\s+/.test(l));
        if (isBulletList) {
          return (
            <ul key={bIdx} className="list-disc list-inside space-y-1.5 pl-2 text-gray-300">
              {lines.map((l, lIdx) => (
                <li key={lIdx}>{renderInline(l.replace(/^\s*[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }

        const isNumberedList = lines.every((l) => /^\s*\d+\.\s+/.test(l));
        if (isNumberedList) {
          return (
            <ol key={bIdx} className="list-decimal list-inside space-y-1.5 pl-2 text-gray-300">
              {lines.map((l, lIdx) => (
                <li key={lIdx}>{renderInline(l.replace(/^\s*\d+\.\s+/, ""))}</li>
              ))}
            </ol>
          );
        }

        return (
          <p key={bIdx} className="whitespace-pre-wrap text-gray-300">
            {lines.map((line, lIdx) => (
              <React.Fragment key={lIdx}>
                {lIdx > 0 && <br />}
                {renderInline(line)}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

export default function QuestionPanel({
  questions,
  activeId,
  setActiveId,
  disabled = false,
}: {
  questions: any[];
  activeId: number;
  setActiveId: (id: number) => void;
  disabled?: boolean;
}) {
  if (!questions || questions.length === 0)
    return <div className="p-4 text-white">No questions available</div>;

  const active = questions.find((q) => q.question_id === activeId) || questions[0];

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100 font-mono text-sm">
      {/* Question Selection Tabs */}
      <div className="flex flex-row items-center bg-gray-800/90 border-b border-gray-700/80 shrink-0 overflow-x-auto">
        {questions.map((q, index) => (
          <React.Fragment key={q.question_id}>
            <button
              type="button"
              onClick={() => {
                if (!disabled) setActiveId(q.question_id);
              }}
              disabled={disabled}
              className={`
                px-4 py-2.5 whitespace-nowrap text-xs font-semibold tracking-wide transition-colors flex items-center gap-1.5
                ${
                  disabled
                    ? "text-gray-600 cursor-not-allowed"
                    : activeId === q.question_id
                    ? "text-white bg-gray-900 border-b-2 border-blue-500 font-bold"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/50"
                }
              `}
            >
              <span className={`w-4 h-4 rounded-full text-[10px] flex items-center justify-center font-bold ${activeId === q.question_id ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'}`}>
                {index + 1}
              </span>
              Question {index + 1}
            </button>
            {index < questions.length - 1 && (
              <span className="self-center text-gray-700 select-none">|</span>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Question Content Panel */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div className="flex items-center gap-3">
          <h2 className="text-base font-bold text-white tracking-wide">
            {active.question_id}. {active.title}
          </h2>
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
              difficultyStyles[active.diff_level] || difficultyStyles[1]
            }`}
          >
            {diffLabels[active.diff_level] || "Easy"}
          </span>
        </div>

        {/* Formatted Question Description */}
        <div className="bg-gray-950/60 border border-gray-800 rounded-xl p-4 text-xs text-gray-200 leading-relaxed font-mono">
          <FormattedText content={active.description} />
        </div>
      </div>
    </div>
  );
}
