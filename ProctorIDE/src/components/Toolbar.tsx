import { useState } from "react";

type ToolbarState = "idle" | "running" | "debugging";

function Toolbar() {
  const [state, setState] = useState<ToolbarState>("idle");

  const handleRun = () => setState(prev => prev === "running" ? "idle" : "running");
  const handleDebug = () => setState(prev => prev === "debugging" ? "idle" : "debugging");
  const handleStop = () => setState("idle");

  const primaryTools = [
    {
      name: "Run",
      icon: "play_arrow",
      activeColor: "text-green-400 bg-green-400/10 border-green-400/30",
      hoverColor: "hover:text-green-400 hover:bg-green-400/10 hover:border-green-400/30",
      isActive: state === "running",
      onClick: handleRun,
      shortcut: "F5",
    },
    {
      name: "Debug",
      icon: "bug_report",
      activeColor: "text-amber-400 bg-amber-400/10 border-amber-400/30",
      hoverColor: "hover:text-amber-400 hover:bg-amber-400/10 hover:border-amber-400/30",
      isActive: state === "debugging",
      onClick: handleDebug,
      shortcut: "F9",
    },
  ];

  const secondaryTools = [
    {
      name: "Step Over",
      icon: "skip_next",
      onClick: () => {},
      shortcut: "F10",
      disabled: state !== "debugging",
    },
    {
      name: "Step Into",
      icon: "arrow_downward",
      onClick: () => {},
      shortcut: "F11",
      disabled: state !== "debugging",
    },
    {
      name: "Restart",
      icon: "replay",
      onClick: () => setState(s => s),
      shortcut: "⇧F5",
      disabled: state === "idle",
    },
    {
      name: "Stop",
      icon: "stop",
      onClick: handleStop,
      shortcut: "⇧F5",
      disabled: state === "idle",
    },
  ];

  return (
    <>
      {/* Load Material Icons */}
      <link
        href="https://fonts.googleapis.com/icon?family=Material+Icons"
        rel="stylesheet"
      />

      <div className="flex items-center gap-1 px-3 h-11 bg-gray-900 border-b border-gray-700/60 font-[Inter]">

        {/* Primary Actions */}
        <div className="flex items-center gap-1">
          {primaryTools.map((tool) => (
            <button
              key={tool.name}
              onClick={tool.onClick}
              title={`${tool.name} (${tool.shortcut})`}
              className={`
                flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium
                border transition-all duration-150 select-none
                ${tool.isActive
                  ? tool.activeColor
                  : `text-gray-400 border-transparent ${tool.hoverColor}`
                }
              `}
            >
              <span className={`material-icons text-base leading-none ${tool.isActive ? "animate-pulse" : ""}`}>
                {tool.icon}
              </span>
              {tool.name}
            </button>
          ))}
        </div>

        {/* Divider */}
        <div className="w-px h-5 bg-gray-700 mx-1" />

        {/* Secondary Actions */}
        <div className="flex items-center gap-0.5">
          {secondaryTools.map((tool) => (
            <button
              key={tool.name}
              onClick={tool.onClick}
              disabled={tool.disabled}
              title={`${tool.name} (${tool.shortcut})`}
              className={`
                flex items-center justify-center w-8 h-8 rounded
                transition-all duration-150 select-none
                ${tool.disabled
                  ? "text-gray-600 cursor-not-allowed"
                  : "text-gray-400 hover:text-gray-100 hover:bg-gray-700/60"
                }
              `}
            >
              <span className="material-icons text-base leading-none">
                {tool.icon}
              </span>
            </button>
          ))}
        </div>

        {/* Status Indicator */}
        {state !== "idle" && (
          <>
            <div className="w-px h-5 bg-gray-700 mx-1" />
            <div className="flex items-center gap-1.5 text-xs">
              <span
                className={`w-1.5 h-1.5 rounded-full animate-pulse ${
                  state === "running" ? "bg-green-400" : "bg-amber-400"
                }`}
              />
              <span className={state === "running" ? "text-green-400" : "text-amber-400"}>
                {state === "running" ? "Running" : "Debugging"}
              </span>
            </div>
          </>
        )}

      </div>
    </>
  );
}

export default Toolbar;