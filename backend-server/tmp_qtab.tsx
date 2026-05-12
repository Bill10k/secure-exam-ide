import { useState } from "react";
import { questions } from "../data/questions";
import React from "react";

const difficultyStyles: Record<string, string> = {
  Easy: "text-emerald-400 bg-emerald-400/10 border border-emerald-400/30",
  Medium: "text-amber-400 bg-amber-400/10 border border-amber-400/30",
  Hard: "text-red-400 bg-red-400/10 border border-red-400/30",
};

export default function QuestionPanel() {
  const [activeId, setActiveId] = useState(questions[0].id);
  const active = questions.find((q) => q.id === activeId)!;

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100 font-mono text-sm">

    
     {/* Tab bar */}
<div className="flex flex-row align-items-center bg-gray-800 border-b border-gray-700 shrink-0">
  {questions.map((q, index) => (
    <React.Fragment key={q.id}>
      <button
        onClick={() => setActiveId(q.id)}
        className={`
          px-4 py-2 whitespace-nowrap text-xs !bg-transparent font-semibold tracking-wide transition-colors
          ${
            activeId === q.id
              ? "text-white bg-gray-900 border-b-2 border-blue-500"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-700"
          }
        `}
      >
        Question {q.id}
      </button>

      {/* Divider — skip after last tab */}
      {index < questions.length - 1 && (
        <span className="self-center text-gray-600 select-none">|</span>
      )}
    </React.Fragment>
  ))}
</div>
      {/* Question content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">

        {/* Title + difficulty */}
        <div className="flex items-center gap-3">
          <h2 className="text-base font-bold text-white">
            {active.id}. {active.title}
          </h2>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-semibold ${difficultyStyles[active.difficulty]}`}
          >
            {active.difficulty}
          </span>
        </div>

        {/* Description */}
        <p className="text-gray-300 leading-relaxed text-xs">
          {active.description}
        </p>

        {/* Example */}
        <div className="space-y-2">
          <p className="text-gray-400 text-xs uppercase tracking-widest">Example</p>
          <div className="bg-gray-800 rounded-lg p-3 space-y-1 border border-gray-700">
            <div>
              <span className="text-gray-500 text-xs">Input: </span>
              <span className="text-blue-300 text-xs">
                {JSON.stringify(active.inputExample)}
              </span>
            </div>
            <div>
              <span className="text-gray-500 text-xs">Output: </span>
              <span className="text-emerald-300 text-xs">
                {JSON.stringify(active.outputExample)}
              </span>
            </div>
          </div>
        </div>

        {/* Constraints */}
        <div className="space-y-2">
          <p className="text-gray-400 text-xs uppercase tracking-widest">Constraints</p>
          <ul className="space-y-1">
            {active.constraints.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-gray-400">
                <span className="text-blue-500 mt-0.5">▸</span>
                <code className="text-gray-300">{c}</code>
              </li>
            ))}
          </ul>
        </div>

      </div>
    </div>
  );
}