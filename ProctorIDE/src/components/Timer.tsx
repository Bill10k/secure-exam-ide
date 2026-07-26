function Timer({ remainingSeconds }: { remainingSeconds: number }) {
  const totalSeconds = Math.max(remainingSeconds, 0);

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

      {totalSeconds <= 0
        ? "Time is up"
        : `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`}
    </div>
  );
}

export default Timer;
