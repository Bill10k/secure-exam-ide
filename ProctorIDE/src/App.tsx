
import { useEffect } from "react";
import { onOpenUrl } from "@tauri-apps/plugin-deep-link";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

import Token from "./components/Token";
import { useAuth } from "./context/AuthContext";
import Environment from "./components/Environment";

function App() {
  const {examStarted, startExam} = useAuth()

  useEffect(() => {
    // 1. Check if launched directly with a deep link argument (Linux typical behavior)
    invoke<string[]>("get_cli_args").then((args) => {
      console.log("CLI args:", args);
      const urlStr = args.find(arg => arg.startsWith("proctoride://"));
      if (urlStr) {
        try {
          const url = new URL(urlStr);
          const sessionId = url.searchParams.get('session_id');
          const examId = url.searchParams.get('exam_id');
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
      console.log('Received deep link URL:', urls);
      if (urls.length > 0) {
        const urlStr = urls[0];
        try {
          const url = new URL(urlStr);
          const sessionId = url.searchParams.get('session_id');
          const examId = url.searchParams.get('exam_id');
          if (sessionId && examId) {
            startExam(`${sessionId}-${examId}`);
          }
        } catch (e) {
          console.error("Failed to parse URL:", e);
        }
      }
    });

    return () => {
      unsubscribe.then(fn => fn());
    };
  }, [startExam]);

  return (
    <main className="w-screen min-h-screen p-0 m-0 flex items-center justify-center">
     {!examStarted ? (
        <Token />
      ) : (
        
          <Environment/>
          // <h1>
          //   home
          // </h1>
          
        
      )}
      {/* <Timer time={{hours: 2}}/> */}

      
      {/* <h1>Welcome to Tauri + React</h1>

      <div className="row">
        <a href="https://vite.dev" target="_blank">
          <img src="/vite.svg" className="logo vite" alt="Vite logo" />
        </a>
        <a href="https://tauri.app" target="_blank">
          <img src="/tauri.svg" className="logo tauri" alt="Tauri logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <p>Click on the Tauri, Vite, and React logos to learn more.</p>

      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          greet();
        }}
      >
        <input
          id="greet-input"
          onChange={(e) => setName(e.currentTarget.value)}
          placeholder="Enter a name..."
        />
        <button type="submit">Greet</button>
      </form>
      <p>{greetMsg}</p> */}
    </main>
  );
}

export default App;
