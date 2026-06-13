import { createContext, useContext, useState, ReactNode } from "react";

interface AuthContextType {
  examStarted: boolean;
  startExam:() => void;
  endExam: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [examStarted, setExamStarted] = useState(false);
  // const [token, setToken] = useState("");

  const startExam = () => {
    // setToken(t);
    setExamStarted(true);
  };

  const endExam = () => {
    // setToken("");
    setExamStarted(false);
  };

  return (
    <AuthContext.Provider value={{ examStarted, startExam, endExam }}>
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