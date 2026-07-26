import { createContext, useContext, useState, ReactNode } from "react";

interface ExamTimingContextType {
  examStarted: boolean;
  startExam: () => void;
  endExam: () => void;
}

const ExamTimingContext = createContext<ExamTimingContextType | undefined>(undefined);

export const ExamTimingProvider = ({ children }: { children: ReactNode }) => {
  const [examStarted, setExamStarted] = useState(false);

  const startExam = () => {
    setExamStarted(true);
  };

  const endExam = () => {
    setExamStarted(false);
  };

  return (
    <ExamTimingContext.Provider value={{ examStarted, startExam, endExam }}>
      {children}
    </ExamTimingContext.Provider>
  );
};

// hook
export const useExamTiming = () => {
  const context = useContext(ExamTimingContext);
  if (!context) {
    throw new Error("useExamTiming must be used within ExamTimingProvider");
  }
  return context;
};