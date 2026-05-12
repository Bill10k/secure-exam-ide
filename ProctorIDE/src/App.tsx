import "./App.css";

import Token from "./components/Token";
import Environment from "./components/Environment";

import { useAuth } from "./context/AuthContext";

import { useExamRestrictions } from "./hooks/useExamRestrictions";
import { useAdminMode } from "./hooks/useAdminMode";

import { useState, useEffect } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";

function App() {
  const { examStarted } = useAuth();

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
    timeout: 60000,
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

    const appWindow = getCurrentWindow();

   
    if (adminMode) {

      // EXIT FULLSCREEN FIRST
      await appWindow.setFullscreen(false);

      // THEN RESTORE WINDOW FEATURES
      await appWindow.setDecorations(true);

      await appWindow.setResizable(true);

      await appWindow.setAlwaysOnTop(false);

    } else {

      // LOCKDOWN MODE

      await appWindow.setDecorations(false);

      await appWindow.setResizable(false);

      await appWindow.setAlwaysOnTop(true);

      // RETURN TO FULLSCREEN LAST
      await appWindow.setFullscreen(true);
    }
  };


  updateWindow();

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