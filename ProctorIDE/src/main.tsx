// import React from "react";
import ReactDOM from "react-dom/client";
// import "./output.css";
import App from "./App";
import "./index.css";
import { ExamTimingProvider } from "./context/ExamTimingContext";
import { ExamProvider } from "./context/ExamContext";

// const blockKeys = (e: KeyboardEvent) => {

//   // Block copy/paste shortcuts
//   if (
//     (e.ctrlKey || e.metaKey) &&
//     ["c", "v", "x", "a"].includes(e.key.toLowerCase())
//   ) {
//     e.preventDefault();
//   }

//   // Block F12
//   if (e.key === "F12") {
//     e.preventDefault();
//   }

//   // Block Ctrl+Shift+I
//   if (
//     (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "i")
//   ) {
//     e.preventDefault();
//   }

//   // Block Ctrl+U
//   if (
//     e.ctrlKey &&
//     e.key.toLowerCase() === "u"
//   ) {
//     e.preventDefault();
//   }
// };

// window.addEventListener("keydown", blockKeys);

// window.addEventListener("contextmenu", (e) => {
//   e.preventDefault();
// });

// window.addEventListener("contextmenu", (e) => {
//   e.preventDefault();
// });

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  // <React.StrictMode>
    <ExamProvider>
    <ExamTimingProvider>
    <App />
    </ExamTimingProvider>
    </ExamProvider>
  // </React.StrictMode>,
);
