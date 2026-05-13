import { useEffect, useState } from "react";
import { onOpenUrl } from "@tauri-apps/plugin-deep-link";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

import Token from "./components/Token";
import Environment from "./components/Environment";

import { useAuth } from "./context/AuthContext";

import { useExamRestrictions } from "./hooks/useExamRestrictions";
import { useAdminMode } from "./hooks/useAdminMode";

import { getCurrentWindow } from "@tauri-apps/api/window";

function App() {
  const { examStarted, startExam } = useAuth();

  // Initialize window to lockdown mode on app mount with retry
  useEffect(() => {
    const initializeWindow = async () => {
      let retries = 0;
      const maxRetries = 5;
      
      const attemptLockdown = async () => {
        try {
          console.log(`[Attempt ${retries + 1}/${maxRetries}] Setting lockdown mode...`);
          const appWindow = getCurrentWindow();
          
          // Set properties with small delays between each to ensure they take effect
          await appWindow.setDecorations(false);
          await new Promise(resolve => setTimeout(resolve, 50));
          
          await appWindow.setResizable(false);
          await new Promise(resolve => setTimeout(resolve, 50));
          
          await appWindow.setAlwaysOnTop(true);
          await new Promise(resolve => setTimeout(resolve, 50));
          
          const isFullscreen = await appWindow.isFullscreen();
          console.log("Current fullscreen state:", isFullscreen);
          
          await appWindow.setFullscreen(true);
          await new Promise(resolve => setTimeout(resolve, 100));
          
          const finalFullscreen = await appWindow.isFullscreen();
          console.log("Final fullscreen state:", finalFullscreen);
          
          if (finalFullscreen) {
            console.log("✓ Window successfully set to fullscreen lockdown mode");
          } else if (retries < maxRetries) {
            console.log("Fullscreen not applied, retrying...");
            retries++;
            setTimeout(attemptLockdown, 500);
          } else {
            console.error("Failed to apply fullscreen after maximum retries");
          }
        } catch (error) {
          console.error(`[Attempt ${retries + 1}] Error setting lockdown:`, error);
          if (retries < maxRetries) {
            retries++;
            setTimeout(attemptLockdown, 500);
          }
        }
      };

      // Start after a longer initial delay to ensure window is fully ready
      setTimeout(attemptLockdown, 500);
    };

    initializeWindow();
  }, []);

  useEffect(() => {
    // 1. Check if launched directly with a deep link argument (Linux typical behavior)
    invoke<string[]>("get_cli_args").then((args) => {
      console.log("CLI args:", args);
      const urlStr = args.find((arg) => arg.startsWith("proctoride://"));
      if (urlStr) {
        try {
          const url = new URL(urlStr);
          const sessionId = url.searchParams.get("session_id");
          const examId = url.searchParams.get("exam_id");
          if (sessionId && examId) {
            startExam(`${sessionId}-${examId}`);
          }
        } catch (e) {
          console.error("Failed to parse initial URL:", e);
        }
      }
    });

    // 2. Listen for deep links when the app is already open
    const unsubscribe = onOpenUrl((urls) => {
      console.log("Received deep link URL:", urls);
      if (urls.length > 0) {
        const urlStr = urls[0];
        try {
          const url = new URL(urlStr);
          const sessionId = url.searchParams.get("session_id");
          const examId = url.searchParams.get("exam_id");
          if (sessionId && examId) {
            startExam(`${sessionId}-${examId}`);
          }
        } catch (e) {
          console.error("Failed to parse URL:", e);
        }
      }
    });

    return () => {
      unsubscribe.then((fn) => fn());
    };
  }, [startExam]);

  const [restrictionsPaused, setRestrictionsPaused] = useState(false);

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

  return (
    <main className="w-screen min-h-screen p-0 m-0 flex items-center justify-center">

      {!examStarted ? (
        <Token />
      ) : (
        <Environment />
      )}

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