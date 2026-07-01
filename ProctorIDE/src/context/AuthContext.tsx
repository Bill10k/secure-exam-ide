import { createContext, useContext, useState, ReactNode } from "react";

interface AuthContextType {
  examStarted: boolean;
  sessionId: number | null;
  examId: number | null;
  startExam: (sessionId: number, examId: number) => void;
  endExam: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [examStarted, setExamStarted] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [examId, setExamId] = useState<number | null>(null);

  const startExam = (nextSessionId: number, nextExamId: number) => {
    console.log("[Auth] Starting exam", { sessionId: nextSessionId, examId: nextExamId });
    setSessionId(nextSessionId);
    setExamId(nextExamId);
    setExamStarted(true);
  };

  const endExam = () => {
    console.log("[Auth] Ending exam");
    setSessionId(null);
    setExamId(null);
    setExamStarted(false);
  };

  return (
    <AuthContext.Provider value={{ examStarted, sessionId, examId, startExam, endExam }}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook to use Auth context easily
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};