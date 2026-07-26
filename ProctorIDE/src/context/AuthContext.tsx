import { createContext, useContext, useState, ReactNode } from "react";

interface AuthContextType {
  examStarted: boolean;
  sessionId: number | null;
  examId: number | null;
  cacheSeed: string | null;
  startExam: (sessionId: number, examId: number, cacheSeed?: string) => void;
  endExam: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [examStarted, setExamStarted] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [examId, setExamId] = useState<number | null>(null);
  const [cacheSeed, setCacheSeed] = useState<string | null>(null);

  const startExam = (nextSessionId: number, nextExamId: number, nextCacheSeed?: string) => {
    console.log("[Auth] Starting exam", { sessionId: nextSessionId, examId: nextExamId });
    setSessionId(nextSessionId);
    setExamId(nextExamId);
    setCacheSeed(nextCacheSeed ?? null);
    setExamStarted(true);
  };

  const endExam = () => {
    console.log("[Auth] Ending exam");
    setSessionId(null);
    setExamId(null);
    setCacheSeed(null);
    setExamStarted(false);
  };

  return (
    <AuthContext.Provider value={{ examStarted, sessionId, examId, cacheSeed, startExam, endExam }}>
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