// import React from "react";
import ReactDOM from "react-dom/client";
// import "./output.css";
import App from "./App";
import "./index.css";
import { AuthProvider } from "./context/AuthContext";
import { ExamTimingProvider } from "./context/ExamTimingContext";
import { ExamProvider } from "./context/ExamContext";



ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  // <React.StrictMode>
    <AuthProvider>
      <ExamProvider>
        <ExamTimingProvider>
          <App />
        </ExamTimingProvider>
      </ExamProvider>
    </AuthProvider>
  // </React.StrictMode>,
);
