import { useState, useEffect } from "react";
import React from "react";

const difficultyStyles: Record<number, string> = {
  1: "text-emerald-400 bg-emerald-400/10 border border-emerald-400/30",
  2: "text-amber-400 bg-amber-400/10 border border-amber-400/30",
  3: "text-red-400 bg-red-400/10 border border-red-400/30",
};

const diffLabels: Record<number, string> = {
  1: "Easy",
  2: "Medium",
  3: "Hard"
};

export default function QuestionPanel({ questions, activeId, setActiveId }: { questions: any[], activeId: number, setActiveId: (id: number) => void }) {
  if (!questions || questions.length === 0) return <div className="p-4 text-white">No questions available</div>;

  const active = questions.find((q) => q.question_id === activeId) || questions[0];

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100 font-mono text-sm">
      <div className="flex flex-row align-items-center bg-gray-800 border-b border-gray-700 shrink-0 overflow-x-auto">
        {questions.map((q, index) => (
          <React.Fragment key={q.question_id}>
            <button
              onClick={() => setActiveId(q.question_id)}
              className={`
                px-4 py-2 whitespace-nowrap text-xs !bg-transparent font-semibold tracking-wide transition-colors
                ${
                  activeId === q.question_id
                    ? "text-white bg-gray-900 border-b-2 border-blue-500"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-700"
                }
              `}
            >
              Question {index + 1}
            </button>
            {index < questions.length - 1 && (
              <span className="self-center text-gray-600 select-none">|</span>
            )}
          </React.Fragment>
        ))}
      </div>
      
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        <div className="flex items-center gap-3">
          <h2 className="text-base font-bold text-white">
            {active.question_id}. {active.title}
          </h2>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-semibold ${difficultyStyles[active.diff_level] || difficultyStyles[1]}`}
          >
            {diffLabels[active.diff_level] || "Easy"}
          </span>
        </div>
        <p className="text-gray-300 leading-relaxed text-xs">
          {active.description}
        </p>
      </div>
    </div>
  );
}
