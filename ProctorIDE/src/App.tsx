import { useEffect, useState } from "react";

import { getCurrentWindow } from "@tauri-apps/api/window";

import "./App.css";

import Environment from "./components/Environment";

import { useExamTiming } from "./context/ExamTimingContext";

import { useExamRestrictions } from "./hooks/useExamRestrictions";
import { useAdminMode } from "./hooks/useAdminMode";

import { useDeepLink } from "./hooks/Deeplink";
import { useExam } from "./context/ExamContext";


function App() {
  const { examStarted } = useExamTiming();
  const { setSession , session } = useExam();


  const [restrictionsPaused, setRestrictionsPaused] = useState(false);

  useDeepLink((data) => {
    if (!data) return;

    console.log("✅ Session received:", data);
    setSession({
      session_id: data.sessionId,
      exam_id: data.examId,
    });
  });

  // =========================
  // SESSION HANDLER (centralized)
  // =========================

// useEffect(() => {
//   const boot = async () => {
//     try {
//       const result = await invoke<string | null>("get_deep_link");

//       if (result) {
//         console.log("🚀 Boot session from Rust:", result);

//         // const url = new URL(result);

//         // const session_id = url.searchParams.get("session_id");
//         // const exam_id = url.searchParams.get("exam_id");

//         // if (session_id && exam_id) {
//         //   setSession({ session_id, exam_id });
//         // }
//       }
//     } catch (err) {
//       console.error("Boot session error:", err);
//     } finally {
//       // 🔥 IMPORTANT: always release boot gate
//       // setBooting(false);
//     }
//   };

//   boot();
// }, []);

// useEffect(() => {
//   const unlistenPromise = listen<string>("deep-link", (event) => {
//     const urlStr = event.payload;

//     console.log("🔥 Deep link received:", urlStr);

//     try {
//       const url = new URL(urlStr);

//       const session_id = url.searchParams.get("session_id");
//       const exam_id = url.searchParams.get("exam_id");

//       if (!session_id || !exam_id) return;

//       // setSession({ session_id, exam_id });

//       console.log("✅ Session set from deep link");
//     } catch (e) {
//       console.error("URL parse error:", e);
//     }
//   });

//   return () => {
//     unlistenPromise.then((fn) => fn());
//   };
// }, []);

  // =========================
  // WINDOW LOCKDOWN (unchanged logic)
  // =========================
  useEffect(() => {
    const initializeWindow = async () => {
      try {
        const appWindow = getCurrentWindow();

        await appWindow.setDecorations(false);
        await appWindow.setResizable(false);
        await appWindow.setAlwaysOnTop(true);
        await appWindow.setFullscreen(true);

        console.log("Window locked down");
      } catch (err) {
        console.error("Window init error:", err);
      }
    };

    initializeWindow();
  }, []);

  // ADMIN MODE
  const {
    adminMode,
    showAdminModal,
    inputPassword,
    setInputPassword,
    validateAdmin,
    closeAdminModal,
    error,
    setAdminMode,
  } = useAdminMode({
    password: "LIDE_ADMIN_2026",
    //timeout: 60000,
  });

  // AUTO PAUSE WHEN ADMIN MODE IS ACTIVE
  useEffect(() => {
    if (adminMode) {
      setRestrictionsPaused(true);
    } else {
      setRestrictionsPaused(false);
    }
  }, [adminMode]);
  useEffect(() => {
    const updateWindow = async () => {
      try {
        const appWindow = getCurrentWindow();

        if (adminMode) {
          console.log("Entering admin mode - exiting lockdown");
          // EXIT FULLSCREEN FIRST
          await appWindow.setFullscreen(false);
          // THEN RESTORE WINDOW FEATURES
          await appWindow.setDecorations(true);
          await appWindow.setResizable(true);
          await appWindow.setAlwaysOnTop(false);
          console.log("Admin mode enabled - window unlocked");
        } else {
          console.log("Entering lockdown mode - securing window");
          // LOCKDOWN MODE
          await appWindow.setDecorations(false);
          await appWindow.setResizable(false);
          await appWindow.setAlwaysOnTop(true);
          // RETURN TO FULLSCREEN LAST
          await appWindow.setFullscreen(true);
          console.log("Lockdown mode enabled - window fullscreen");
        }
      } catch (error) {
        console.error("Error updating window state:", error);
      }
    };

    // Add a small delay to ensure window is ready
    const timer = setTimeout(updateWindow, 100);
    return () => clearTimeout(timer);
  }, [adminMode]);

  // EXAM RESTRICTIONS
  useExamRestrictions({
    enabled: examStarted && !restrictionsPaused,
    onViolation: (event) => {
      console.log("Integrity Event:", event);
    },
  });

//  if (booting) {
//   return (
//     <div className="h-screen flex items-center justify-center bg-black text-white">
//       Initializing secure exam environment...
//     </div>
//   );
// }

// if (!session) {
//   return (
//     <>

//      <div className="h-screen flex items-center justify-center bg-black text-white">
//       Waiting for exam session...
//     </div>
//     <DetectUrl/>
    
    
//     </>
   
//   );
// }

if (!session) {
  return (
    <div className="h-screen flex items-center justify-center bg-black text-white">
      Waiting for exam session...
    </div>
  );
}

  return (
    <main className="w-screen min-h-screen p-0 m-0 flex items-center justify-center">
      {/* <DetectUrl/> */}

      {/* {!examStarted ? (
      <button
        onClick={startExam}
        className="bg-blue-600 text-white px-4 py-2 rounded"
      >
        Start Exam
      </button>
    ) : (
      <Environment />
    )} */}

      <Environment />
      {/* ADMIN MODAL */}
      {showAdminModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">

          <div className="bg-gray-700 p-6 rounded-xl w-[400px]">

            <h2 className="text-2xl font-bold mb-4">
              Admin Access
            </h2>

            <input
              type="password"
              value={inputPassword}
              onChange={(e) =>
                setInputPassword(e.target.value)
              }
              placeholder="Enter admin password"
              className="border p-3 w-full rounded-lg"
            />

            {error && (
              <p className="text-red-500 mt-2">
                {error}
              </p>
            )}

            <div className="flex justify-end gap-3 mt-5">

              <button
                onClick={closeAdminModal}
                className="bg-gray-700 px-4 py-2 rounded-lg"
              >
                Cancel
              </button>

              <button
                onClick={validateAdmin}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg"
              >
                Unlock
              </button>

            </div>

          </div>

        </div>
      )}

      {/* ADMIN CONTROLS */}
      {adminMode && (
        <div className="fixed bottom-5 right-5 bg-white shadow-2xl rounded-xl p-4 z-50 w-[250px]">

          <h3 className="font-bold text-lg mb-3">
            Admin Controls
          </h3>

          {/* PAUSE / RESUME */}
          <button
            onClick={() =>
              setRestrictionsPaused((prev) => !prev)
            }
            className="w-full bg-yellow-500 text-white py-2 rounded-lg mb-2"
          >
            {restrictionsPaused
              ? "Resume Restrictions"
              : "Pause Restrictions"}
          </button>

          <button
            onClick={() => setAdminMode(false)}
            className="w-full bg-gray-500 text-white py-2 rounded-lg"
          >
            Close Admin Mode
          </button>

        </div>
      )}

    </main>
  );
}

export default App;