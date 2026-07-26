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

type HydrateExam = {
  questions: HydrateQuestion[]
  remaining_seconds?: number
  server_time?: string
  session_started_at?: string
  session_duration_seconds?: number
  session_ends_at?: string
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
  const [isTimedOut, setIsTimedOut] = useState(false)
  const [timeoutMessage, setTimeoutMessage] = useState<string | null>(null)
  const [isSubmitLocked, setIsSubmitLocked] = useState(false)
  const [shutdownCountdown, setShutdownCountdown] = useState<number | null>(null)
  const [submitOverlayMessage, setSubmitOverlayMessage] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const terminalRef = useRef<any>(null)
  const questionCodesRef = useRef<Record<number, string>>({})
  const questionVersionsRef = useRef<Record<number, number>>({})
  const lastSavedCodeRef = useRef<Record<number, string>>({})
  const autosaveTimerRef = useRef<number | null>(null)
  const saveQueueRef = useRef(Promise.resolve())
  const closingRef = useRef(false)
  const deadlineMsRef = useRef<number | null>(null)
  const timeoutSubmitStartedRef = useRef(false)
  const submissionInFlightRef = useRef(false)
  const activeQuestionIdRef = useRef(activeQuestionId)
  const retryingPendingRef = useRef(false)
  const [submissionComplete, setSubmissionComplete] = useState(false)
  const successfulSubmitRef = useRef(false)

  const SNAPSHOT_FLUSH_INTERVAL_MS = 2 * 60 * 1000

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedLanguage, setSelectedLanguage] = useState<string>("python")

const applyHydrateData = useCallback((data: HydrateExam) => {
  if (!data || !Array.isArray(data.questions)) {
    throw new Error("Hydrate response missing questions[]")
  }

  setExamState(data)
  if (typeof data.remaining_seconds === "number") {
    setRemainingSeconds(data.remaining_seconds)
  }

  const serverTimeMs = data.server_time ? Date.parse(data.server_time) : Number.NaN
  const sessionEndsAtMs = data.session_ends_at ? Date.parse(data.session_ends_at) : Number.NaN
  if (Number.isFinite(serverTimeMs) && Number.isFinite(sessionEndsAtMs)) {
    deadlineMsRef.current = Date.now() + Math.max(sessionEndsAtMs - serverTimeMs, 0)
  } else if (typeof data.remaining_seconds === "number") {
    deadlineMsRef.current = Date.now() + Math.max(data.remaining_seconds, 0) * 1000
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
  if (isTimedOut || isSubmitLocked) return
  if (nextQuestionId === activeQuestionIdRef.current) return

  flushAutosave(activeQuestionIdRef.current)
  setActiveQuestionId(nextQuestionId)
  setCode(questionCodesRef.current[nextQuestionId] ?? "")
}, [flushAutosave, isSubmitLocked, isTimedOut])

const handleCodeChange = useCallback((val: string | undefined) => {
  if (isTimedOut || isSubmitLocked) return
  const nextCode = val ?? ""
  setCode(nextCode)
  questionCodesRef.current[activeQuestionIdRef.current] = nextCode
  scheduleAutosave(activeQuestionIdRef.current)
}, [isSubmitLocked, isTimedOut, scheduleAutosave])

const handleTerminalInit = useCallback((term: any) => {
  terminalRef.current = term
}, [])

const closeExamWindow = useCallback(async () => {
  console.log("[Close] Entered");
  closingRef.current = true;

  try {
    await Promise.race([
      flushAutosave(activeQuestionIdRef.current, true),
      new Promise((resolve) => window.setTimeout(resolve, 1500)),
    ]);
    console.log("[Close] Autosave flushed");
  } catch (e) {
    console.error("[Close] Autosave failed", e);
  }

  const appWindow = getCurrentWindow();

  try {
    console.log("[Close] Calling force_exit_app()");
    await invoke("force_exit_app");
    console.log("[Close] force_exit_app() returned");
  } catch (e) {
    console.error("[Close] force_exit_app() threw", e);
  }

  try {
    console.log("[Close] Calling window.destroy()");
    await appWindow.destroy();
    console.log("[Close] window.destroy() returned");
  } catch (e) {
    console.error("[Close] window.destroy() threw", e);

    try {
      console.log("[Close] Calling window.close()");
      await appWindow.close();
      console.log("[Close] window.close() returned");
    } catch (closeError) {
      console.error("[Close] window.close() threw", closeError);
    }
  }
}, [flushAutosave]);

const submitCurrentQuestion = useCallback(async (forcedByTimeout = false) => {
  if (submissionInFlightRef.current) return
  submissionInFlightRef.current = true

  const questionId = activeQuestionIdRef.current
  const currentCode = questionCodesRef.current[questionId] ?? code ?? ""
  const term = terminalRef.current

  try {
    await flushAutosave(questionId)

    if (term) {
      term.writeln(
        forcedByTimeout
          ? "\x1b[31m\r\nTime is up. Submitting latest code...\x1b[0m"
          : "\x1b[34m\r\nSubmitting code for grading...\x1b[0m",
      )
    }

    const submissionPayload = {
      code: currentCode,
      language: "python",
      question_id: questionId,
      session_id: sessionId,
    }

    const pendingSubmissionId = forcedByTimeout
      ? null
      : await savePendingSubmissionLocally(submissionPayload).catch((cacheError) => {
          console.error("[Environment] Failed to queue pending submission", cacheError)
          return null
        })

    const controller = new AbortController()
    const timeoutId = forcedByTimeout
      ? window.setTimeout(() => controller.abort(), 5000)
      : null

    try {
      const response = await fetch("http://localhost:8000/submissions/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(submissionPayload),
        signal: controller.signal,
      })

      const result = await response.json().catch(() => null)
      if (!response.ok) {
        const detail = result?.detail || `Submission failed: ${response.status}`
        throw new Error(detail)
      }

      if (pendingSubmissionId !== null) {
        await invoke("mark_pending_submission_synced", { id: pendingSubmissionId }).catch((cacheError) => {
          console.error("[Environment] Failed to mark pending submission as synced", cacheError)
        })
      }

      if (term) {
        term.writeln(`Status: ${result.status === "passed" ? "\x1b[32mPassed\x1b[0m" : "\x1b[31mFailed\x1b[0m"} (${result.score}%)`)
        if (result.feedback) {
          term.writeln(result.feedback.replace(/\n/g, "\r\n"))
        }
      }
    } finally {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
      }
    }
  } finally {
    submissionInFlightRef.current = false
  }
}, [code, flushAutosave, savePendingSubmissionLocally, sessionId])

const handleExamTimeout = useCallback(async () => {
  if (timeoutSubmitStartedRef.current) return
  timeoutSubmitStartedRef.current = true
  setIsTimedOut(true)
  setTimeoutMessage("Time is up. Submitting your latest code...")

  const fallbackCloseId = window.setTimeout(() => {
    void closeExamWindow()
  }, 7000)

  try {
    await submitCurrentQuestion(true)
    setTimeoutMessage("Time is up. Submission complete. Closing ProctorIDE...")
  } catch (error) {
    const message = error instanceof Error ? error.message : "Submission could not be confirmed"
    console.error("[Environment] Timeout submission failed", error)
    setTimeoutMessage(`Time is up. ${message}. Closing ProctorIDE...`)
  } finally {
    window.clearTimeout(fallbackCloseId)
    window.setTimeout(() => {
      void closeExamWindow()
    }, 1500)
  }
}, [closeExamWindow, submitCurrentQuestion])

useEffect(() => {
  if (!submissionComplete || shutdownCountdown === null) return;

  if (shutdownCountdown <= 0) {
    void closeExamWindow();
    return;
  }

  const timeoutId = window.setTimeout(() => {
    setShutdownCountdown((current) =>
      current === null ? null : Math.max(current - 1, 0)
    );
  }, 1000);

  return () => window.clearTimeout(timeoutId);
}, [submissionComplete, shutdownCountdown, closeExamWindow]);

useEffect(() => {
  if (!deadlineMsRef.current) return

  const updateRemainingTime = () => {
    const nextRemaining = Math.max(Math.ceil((deadlineMsRef.current! - Date.now()) / 1000), 0)
    setRemainingSeconds(nextRemaining)
  }

  updateRemainingTime()
  const intervalId = window.setInterval(updateRemainingTime, 1000)
  return () => window.clearInterval(intervalId)
}, [examState])

useEffect(() => {
  if (loading || !examState || remainingSeconds > 0) return
  void handleExamTimeout()
}, [examState, handleExamTimeout, loading, remainingSeconds])



  const handleRun = async () => {
    if (isTimedOut || isSubmitLocked) return
    if (!terminalRef.current) return;
    const term = terminalRef.current;
    
    console.log("[Environment] Running code", { questionId: activeQuestionId })
    void flushAutosave(activeQuestionId)
    term.writeln("\x1b[33m\r\nRunning code...\x1b[0m");
    
    try {
      const response = await fetch("http://localhost:8000/submissions/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: code || "",
          language: selectedLanguage,
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
    if (isTimedOut || isSubmitLocked || successfulSubmitRef.current) {
    return;
  }

  console.log("[Submit] Starting submission");

  setSubmitError(null);
  setIsSubmitLocked(true);
  setSubmitOverlayMessage("Submitting your code. Please wait...");

  try {
    console.log("[Submit] Calling submitCurrentQuestion()");

    await submitCurrentQuestion(false);

    successfulSubmitRef.current = true;
    setSubmissionComplete(true);

    console.log("[Submit] Setting completion state");

    setSubmitOverlayMessage(
      "Submission complete. ProctorIDE will close automatically."
    );

    setShutdownCountdown(10);

    console.log("[Submit] Countdown started:", 10);
  } catch (e: any) {
    console.error("[Submit] Submission failed", e);

    setIsSubmitLocked(false);
    setSubmitOverlayMessage(null);
    setShutdownCountdown(null);

    setSubmitError(e.message || "Submission failed. Please try again.");

    terminalRef.current?.writeln(
      `\x1b[31mError submitting code: ${e.message}\x1b[0m`
    );
  }
};

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (isTimedOut || isSubmitLocked) return
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
  }, [isSubmitLocked, isTimedOut, leftWidth])

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

      {submitError && (
        <div className="absolute left-1/2 top-20 z-40 w-[min(92vw,560px)] -translate-x-1/2 rounded border border-red-400/40 bg-red-950/95 px-4 py-3 text-sm text-red-100 shadow-xl">
          {submitError}
        </div>
      )}

      <div className="flex flex-row flex-1 overflow-hidden">

        <aside
          style={{ width: `${leftWidth}%` }}
          className="shrink-0 bg-gray-700 flex flex-col overflow-y-auto"
        >
            <QuestionPanel questions={examState.questions} activeId={activeQuestionId} setActiveId={handleQuestionChange} disabled={isTimedOut || isSubmitLocked} />
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
            language={selectedLanguage}
            onChange={handleCodeChange}
            inputValue={customInput}
            onInputChange={setCustomInput}
            onRun={handleRun}
            onSubmit={handleSubmit}
            onTerminalInit={handleTerminalInit}
            disabled={isTimedOut || isSubmitLocked}
            onLanguageChange={setSelectedLanguage}
            selectedLanguage={selectedLanguage}
          />
        </div>

      </div>

      {isSubmitLocked && !isTimedOut && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75">
          <div className="max-w-md rounded-lg border border-blue-400/40 bg-gray-900 px-6 py-5 text-center shadow-2xl">
            <h2 className="text-xl font-semibold text-blue-200">
              {shutdownCountdown === null ? "Submitting exam" : "Submission complete"}
            </h2>
            <p className="mt-3 text-sm text-gray-200">
              {submitOverlayMessage ?? "Submitting your code. Please wait..."}
            </p>
            {shutdownCountdown !== null && (
              <p className="mt-4 text-lg font-semibold text-white">
                Closing in {shutdownCountdown} second{shutdownCountdown === 1 ? "" : "s"}
              </p>
            )}
          </div>
        </div>
      )}

      {isTimedOut && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75">
          <div className="max-w-md rounded-lg border border-red-500/40 bg-gray-900 px-6 py-5 text-center shadow-2xl">
            <h2 className="text-xl font-semibold text-red-300">Time is up</h2>
            <p className="mt-3 text-sm text-gray-200">
              {timeoutMessage ?? "Submitting your latest code..."}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default Environment