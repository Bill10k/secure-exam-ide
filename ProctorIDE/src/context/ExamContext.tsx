import { createContext, useContext, useState, ReactNode } from "react";

type ExamSession = {
  session_id: string;
  exam_id: string;
} | null;

type ExamContextType = {
  session: ExamSession;
  setSession: (data: ExamSession) => void;
};

const ExamContext = createContext<ExamContextType | undefined>(undefined);

export function ExamProvider({ children }: { children: ReactNode }) {
const [session, setSession] = useState<ExamSession | null>(null);

  return (
    <ExamContext.Provider value={{ session, setSession }}>
      {children}
    </ExamContext.Provider>
  );
}

export function useExam() {
  const context = useContext(ExamContext);

  if (!context) {
    throw new Error("useExam must be used inside ExamProvider");
  }

  return context;
}