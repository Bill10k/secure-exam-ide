import { useState, useEffect } from "react";

interface Duration {
  hours: number;
  minutes?: number;
  seconds?: number;
}

function Timer({ time }: { time: Duration }) {
  const initialTotalSeconds =
    (time.hours ?? 0) * 3600 +
    (time.minutes ?? 0) * 60 +
    (time.seconds ?? 0);

  const [totalSeconds, setTotalSeconds] = useState(initialTotalSeconds);

  useEffect(() => {
    if (totalSeconds <= 0) return;
    const interval = setInterval(() => {
      setTotalSeconds(prev => {
        if (prev <= 1) { clearInterval(interval); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [totalSeconds]);

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const isWarning = totalSeconds <= 300; // 5 minutes

  return (
    <div
      className={`flex items-center gap-2 text-2xl font-mono transition-all duration-500 ${
        isWarning
          ? "text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.9)] animate-pulse"
          : "text-white"
      }`}
    >
      {/* Clock SVG */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-6 h-6"
      >
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>

      {String(hours).padStart(2, "0")}:
      {String(minutes).padStart(2, "0")}:
      {String(seconds).padStart(2, "0")}
    </div>
  );
}

export default Timer;