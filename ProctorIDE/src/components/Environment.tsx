import React, { useState, useCallback, useRef, useEffect } from "react"
import Navbar from "./Navbar"
import QuestionPanel from "./QuestionTab"
import CodeEditor from "./CodeEditor"
import { useAuth } from "../context/AuthContext"

function Environment() {
  const { token } = useAuth()
  const [examState, setExamState] = useState<any>(null)
  
  const [leftWidth, setLeftWidth] = useState(45) // percentage
  const [code, setCode] = useState<string | undefined>("# Write your Python code here...\n")
  const [customInput, setCustomInput] = useState<string>("")
  const [activeQuestionId, setActiveQuestionId] = useState<number>(1)
  const terminalRef = useRef<any>(null)

  useEffect(() => {
    if (token && token.includes("-")) {
      const [sessionId, examId] = token.split("-")
      fetch(`http://localhost:8000/exams/session/${sessionId}/hydrate`)
        .then(res => res.json())
        .then(data => {
          setExamState(data)
          if (data.questions && data.questions.length > 0) {
            setActiveQuestionId(data.questions[0].question_id)
            if (data.questions[0].default_code) {
               setCode(data.questions[0].default_code)
            }
          }
        })
        .catch(err => console.error("Error fetching exam data", err))
    }
  }, [token])

  const handleRun = async () => {
    if (!terminalRef.current) return;
    const term = terminalRef.current;
    
    term.writeln("\x1b[33m\r\nRunning code...\x1b[0m");
    
    try {
      const response = await fetch("http://localhost:8000/submissions/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: code || "",
          language: "python",
          question_id: activeQuestionId,
          custom_input: customInput
        })
      });
      
      const result = await response.json();
      
      if (result.stdout) {
        term.writeln(result.stdout.replace(/\n/g, "\r\n"));
      }
      if (result.stderr) {
        term.writeln(`\x1b[31m${result.stderr.replace(/\n/g, "\r\n")}\x1b[0m`);
      }
      
      term.writeln(`\x1b[36mProcess exited with code ${result.exit_code} in ${result.execution_time}s\x1b[0m`);
    } catch (e: any) {
      term.writeln(`\x1b[31mError connecting to execution engine: ${e.message}\x1b[0m`);
    }
  };

  const handleSubmit = async () => {
    if (!terminalRef.current) return;
    const term = terminalRef.current;
    
    term.writeln("\x1b[34m\r\nSubmitting code for grading...\x1b[0m");
    
    try {
      const response = await fetch("http://localhost:8000/submissions/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: code || "",
          language: "python",
          question_id: activeQuestionId 
        })
      });
      
      const result = await response.json();
      
      term.writeln(`Status: ${result.status === "passed" ? "\x1b[32mPassed\x1b[0m" : "\x1b[31mFailed\x1b[0m"} (${result.score}%)`);
      if (result.feedback) {
        term.writeln(result.feedback.replace(/\n/g, "\r\n"));
      }
    } catch (e: any) {
      term.writeln(`\x1b[31mError submitting code: ${e.message}\x1b[0m`);
    }
  };

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const startWidth = leftWidth

    const onMouseMove = (moveEvent: MouseEvent) => {
      const containerWidth = window.innerWidth
      const delta = moveEvent.clientX - startX
      const newWidth = startWidth + (delta / containerWidth) * 100
      setLeftWidth(Math.min(80, Math.max(20, newWidth)))
    }

    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove)
      document.removeEventListener("mouseup", onMouseUp)
    }

    document.addEventListener("mousemove", onMouseMove)
    document.addEventListener("mouseup", onMouseUp)
  }, [leftWidth])

  if (!examState) return <div className="h-screen bg-gray-900 text-white flex items-center justify-center">Loading Exam Environment...</div>;

  return (
    <div className="w-full h-screen flex flex-col overflow-hidden">

      <Navbar />

      <div className="flex flex-row flex-1 overflow-hidden">

        <aside
          style={{ width: `${leftWidth}%` }}
          className="flex-shrink-0 bg-gray-700 flex flex-col overflow-y-auto"
        >
           <QuestionPanel questions={examState.questions} activeId={activeQuestionId} setActiveId={setActiveQuestionId} />
        </aside>

        <div
          onMouseDown={handleMouseDown}
          className="w-1 bg-gray-500 hover:bg-blue-400 cursor-col-resize flex-shrink-0 transition-colors duration-150"
        />

        <div
          style={{ width: `${100 - leftWidth}%` }}
          className="flex-shrink-0 bg-gray-900 overflow-hidden"
        >
          <CodeEditor 
            value={code} 
            onChange={(val) => setCode(val)}
            inputValue={customInput}
            onInputChange={setCustomInput}
            onRun={handleRun}
            onSubmit={handleSubmit}
            onTerminalInit={(term) => { terminalRef.current = term; }}
          />
        </div>

      </div>
    </div>
  )
}

export default Environment
