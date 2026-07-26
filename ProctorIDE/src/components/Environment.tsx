import React, { useState, useCallback, useRef, useEffect } from "react"
import Navbar from "./Navbar"
import QuestionPanel from "./QuestionTab"
import CodeEditor from "./CodeEditor"
import { useAuth } from "../context/AuthContext"
import { getCurrentWindow } from "@tauri-apps/api/window"
import { invoke } from "@tauri-apps/api/core"

type HydrateQuestion = {
  question_id: number
  title: string
  description: string
  diff_level: number
  default_code?: string | null
  snapshot?: {
    code: string
    version: number
    saved_at: string
  } | null
}

type SnapshotPayload = {
  questionId: number
  code: string
  version: number
}

type SnapshotResponse = {
  saved: boolean
  version: number
  saved_at: string
}

type PendingSubmissionEntry = {
  id: number
  session_id: number
  question_id: number
  payload: string
  synced: boolean
  retry_count: number
  created_at: string
}

function Environment() {
  const { sessionId, examId, cacheSeed } = useAuth()
  const [examState, setExamState] = useState<any>(null)
  
  const [leftWidth, setLeftWidth] = useState(45) // percentage
  const [code, setCode] = useState<string | undefined>("# Write your Python code here...\n")
  const [customInput, setCustomInput] = useState<string>("")
  const [activeQuestionId, setActiveQuestionId] = useState<number>(1)
  const [remainingSeconds, setRemainingSeconds] = useState<number>(0)
  const terminalRef = useRef<any>(null)
  const questionCodesRef = useRef<Record<number, string>>({})
  const questionVersionsRef = useRef<Record<number, number>>({})
  const lastSavedCodeRef = useRef<Record<number, string>>({})
  const autosaveTimerRef = useRef<number | null>(null)
  const saveQueueRef = useRef(Promise.resolve())
  const closingRef = useRef(false)
  const activeQuestionIdRef = useRef(activeQuestionId)
  const retryingPendingRef = useRef(false)

  const SNAPSHOT_FLUSH_INTERVAL_MS = 2 * 60 * 1000

  const [loading, setLoading] = useState(true)
const [error, setError] = useState<string | null>(null)

const applyHydrateData = useCallback((data: any) => {
  if (!data || !Array.isArray(data.questions)) {
    throw new Error("Hydrate response missing questions[]")
  }

  setExamState(data)
  if (typeof data.remaining_seconds === "number") {
    setRemainingSeconds(data.remaining_seconds)
  }

  const hydratedQuestions = data.questions as HydrateQuestion[]
  const nextCodes: Record<number, string> = {}
  const nextVersions: Record<number, number> = {}

  hydratedQuestions.forEach((question) => {
    const initialCode = question.snapshot?.code ?? question.default_code ?? ""
    nextCodes[question.question_id] = initialCode
    nextVersions[question.question_id] = question.snapshot?.version ?? 1
  })

  questionCodesRef.current = nextCodes
  questionVersionsRef.current = nextVersions
  lastSavedCodeRef.current = { ...nextCodes }

  if (hydratedQuestions.length > 0) {
    const firstQuestion = hydratedQuestions[0]
    setActiveQuestionId(firstQuestion.question_id)
    setCode(nextCodes[firstQuestion.question_id])
  }
}, [])

useEffect(() => {
  activeQuestionIdRef.current = activeQuestionId
}, [activeQuestionId])

const clearAutosaveTimer = useCallback(() => {
  if (autosaveTimerRef.current !== null) {
    window.clearTimeout(autosaveTimerRef.current)
    autosaveTimerRef.current = null
  }
}, [])

const getSnapshotPayload = useCallback((questionId: number): SnapshotPayload => {
  return {
    questionId,
    code: questionCodesRef.current[questionId] ?? "",
    version: questionVersionsRef.current[questionId] ?? 1,
  }
}, [])

const persistSnapshot = useCallback((payload: SnapshotPayload, keepalive = false) => {
  if (!sessionId) return Promise.resolve(false)

  const execute = async () => {
    const currentSavedCode = lastSavedCodeRef.current[payload.questionId]
    const currentVersion = questionVersionsRef.current[payload.questionId] ?? 1
    if (currentSavedCode === payload.code && currentVersion === payload.version) {
      return false
    }

    const response = await fetch("http://127.0.0.1:8000/snapshots/save", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        question_id: payload.questionId,
        code: payload.code,
        version: payload.version,
      }),
      ...(keepalive ? { keepalive: true } : {}),
    })

    if (!response.ok) {
      throw new Error(`Snapshot save failed: ${response.status}`)
    }

    const result = await response.json() as SnapshotResponse
    questionVersionsRef.current[payload.questionId] = result.version
    lastSavedCodeRef.current[payload.questionId] = payload.code
    if (cacheSeed) {
      void invoke("cache_snapshot", {
        cacheSeed,
        sessionId,
        questionId: payload.questionId,
        code: payload.code,
        version: result.version,
        savedAt: result.saved_at,
      }).catch((cacheError) => {
        console.error("[Environment] Failed to cache snapshot locally", cacheError)
      })
    }
    return true
  }

  const nextSave = saveQueueRef.current.then(execute, execute)
  saveQueueRef.current = nextSave.then(
    () => undefined,
    () => undefined,
  )
  return nextSave
}, [cacheSeed, sessionId])

const scheduleAutosave = useCallback((questionId: number) => {
  clearAutosaveTimer()
  autosaveTimerRef.current = window.setTimeout(() => {
    autosaveTimerRef.current = null
    void persistSnapshot(getSnapshotPayload(questionId))
  }, 5000)
}, [clearAutosaveTimer, getSnapshotPayload, persistSnapshot])

const flushAutosave = useCallback((questionId: number, keepalive = false) => {
  clearAutosaveTimer()
  return persistSnapshot(getSnapshotPayload(questionId), keepalive)
}, [clearAutosaveTimer, getSnapshotPayload, persistSnapshot])

useEffect(() => {
  if (!sessionId || !examId) return

  const intervalId = window.setInterval(() => {
    void flushAutosave(activeQuestionIdRef.current)
  }, SNAPSHOT_FLUSH_INTERVAL_MS)

  return () => {
    window.clearInterval(intervalId)
  }
}, [examId, flushAutosave, sessionId])

const savePendingSubmissionLocally = useCallback(async (submissionPayload: Record<string, any>) => {
  if (!sessionId || !cacheSeed) return null

  return invoke<number>("queue_pending_submission", {
    cacheSeed,
    sessionId,
    questionId: submissionPayload.question_id,
    payloadJson: JSON.stringify(submissionPayload),
  })
}, [cacheSeed, sessionId])

const retryPendingSubmissions = useCallback(async () => {
  if (!sessionId || !cacheSeed || retryingPendingRef.current) return
  if (!navigator.onLine) return

  retryingPendingRef.current = true
  try {
    const pendingSubmissions = await invoke<PendingSubmissionEntry[]>("list_pending_submissions", {
      cacheSeed,
    })

    for (const pending of pendingSubmissions) {
      try {
        await invoke("increment_pending_submission_retry", { id: pending.id })
        const submissionPayload = JSON.parse(pending.payload)
        const response = await fetch("http://localhost:8000/submissions/submit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(submissionPayload),
        })

        if (!response.ok) {
          throw new Error(`Retry failed: ${response.status}`)
        }

        await invoke("mark_pending_submission_synced", { id: pending.id })
      } catch (error) {
        console.error("[Environment] Pending submission retry failed", error)
      }
    }
  } finally {
    retryingPendingRef.current = false
  }
}, [cacheSeed, sessionId])

useEffect(() => {
  if (!sessionId || !examId) return

  let cancelled = false

  const loadExam = async () => {
  setLoading(true)
  setError(null)

    try {
      const response = await fetch(`http://127.0.0.1:8000/exams/session/${sessionId}/hydrate`)
      if (!response.ok) throw new Error(`Hydrate failed: ${response.status}`)

      const data = await response.json()
      applyHydrateData(data)
      if (cacheSeed) {
        void invoke("cache_hydrate_payload", {
          cacheSeed,
          sessionId,
          payloadJson: JSON.stringify(data),
        }).catch((cacheError) => {
          console.error("[Environment] Failed to cache hydrate payload", cacheError)
        })
      }
      return
    } catch (err) {
      console.error("[Environment] Error fetching exam data", err)
      try {
        if (!cacheSeed) {
          throw err
        }

        const cachedPayload = await invoke<string | null>("load_cached_hydrate_payload", {
          cacheSeed,
          sessionId,
        })

        if (!cachedPayload) {
          throw err
        }

        applyHydrateData(JSON.parse(cachedPayload))
      } catch (cacheError) {
        console.error("[Environment] Error restoring cached exam data", cacheError)
        setError((err as Error).message || "Failed to load exam")
      }
    } finally {
      if (!cancelled) {
        setLoading(false)
      }
    }
  }

  void loadExam()

  return () => {
    cancelled = true
  }
}, [cacheSeed, sessionId, examId])

useEffect(() => {
  const appWindow = getCurrentWindow()
  let unlistenClose: (() => void) | undefined

  const registerCloseHandler = async () => {
    try {
      unlistenClose = await appWindow.onCloseRequested(async (event) => {
        if (closingRef.current) {
          return
        }

        closingRef.current = true

        try {
          event.preventDefault()
          await flushAutosave(activeQuestionIdRef.current, true)
        } finally {
          await appWindow.destroy()
        }
      })
    } catch (error) {
      console.error("[Environment] Failed to register close handler", error)
    }
  }

  void registerCloseHandler()

  const handleBeforeUnload = () => {
    flushAutosave(activeQuestionIdRef.current, true)
  }

  window.addEventListener("beforeunload", handleBeforeUnload)

  return () => {
    window.removeEventListener("beforeunload", handleBeforeUnload)
    clearAutosaveTimer()
    if (unlistenClose) {
      void unlistenClose()
    }
  }
}, [clearAutosaveTimer, flushAutosave])

const handleQuestionChange = useCallback((nextQuestionId: number) => {
  if (nextQuestionId === activeQuestionIdRef.current) return

  flushAutosave(activeQuestionIdRef.current)
  setActiveQuestionId(nextQuestionId)
  setCode(questionCodesRef.current[nextQuestionId] ?? "")
}, [flushAutosave])

const handleCodeChange = useCallback((val: string | undefined) => {
  const nextCode = val ?? ""
  setCode(nextCode)
  questionCodesRef.current[activeQuestionIdRef.current] = nextCode
  scheduleAutosave(activeQuestionIdRef.current)
}, [scheduleAutosave])



  const handleRun = async () => {
    if (!terminalRef.current) return;
    const term = terminalRef.current;
    
    console.log("[Environment] Running code", { questionId: activeQuestionId })
    flushAutosave(activeQuestionId)
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
    
    console.log("[Environment] Submitting code", { questionId: activeQuestionId })
    void flushAutosave(activeQuestionId)
    term.writeln("\x1b[34m\r\nSubmitting code for grading...\x1b[0m");

    const submissionPayload = {
      code: code || "",
      language: "python",
      question_id: activeQuestionId,
      session_id: sessionId,
    }

    const pendingSubmissionId = await savePendingSubmissionLocally(submissionPayload).catch((cacheError) => {
      console.error("[Environment] Failed to queue pending submission", cacheError)
      return null
    })
    
    try {
      const response = await fetch("http://localhost:8000/submissions/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(submissionPayload)
      });
      
      const result = await response.json();

      // Mark the queued submission as synced after a successful backend save.
      if (pendingSubmissionId !== null) {
        await invoke("mark_pending_submission_synced", { id: pendingSubmissionId })
      }
      
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

  useEffect(() => {
    void retryPendingSubmissions()

    const handleOnline = () => {
      void retryPendingSubmissions()
    }

    window.addEventListener("online", handleOnline)
    return () => window.removeEventListener("online", handleOnline)
  }, [retryPendingSubmissions])

  // if (!examState) return <div className="h-screen w-full bg-gray-900 text-white flex items-center justify-center">Loading Exam Environment...</div>;
if (loading) {
  return <div className="h-screen w-full bg-gray-900 text-white flex items-center justify-center">Loading Exam Environment...</div>
}
if (error) {
  return <div className="h-screen w-full bg-gray-900 text-red-300 flex items-center justify-center">Error: {error}</div>
}
  return (
    <div className="w-full h-screen flex flex-col overflow-hidden">

      <Navbar remainingSeconds={remainingSeconds} />

      <div className="flex flex-row flex-1 overflow-hidden">

        <aside
          style={{ width: `${leftWidth}%` }}
          className="shrink-0 bg-gray-700 flex flex-col overflow-y-auto"
        >
            <QuestionPanel questions={examState.questions} activeId={activeQuestionId} setActiveId={handleQuestionChange} />
        </aside>

        <div
          onMouseDown={handleMouseDown}
          className="w-1 bg-gray-500 hover:bg-blue-400 cursor-col-resize shrink-0 transition-colors duration-150"
        />

        <div
          style={{ width: `${100 - leftWidth}%` }}
          className="shrink-0 bg-gray-900 overflow-hidden"
        >
          <CodeEditor 
            value={code} 
            onChange={handleCodeChange}
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