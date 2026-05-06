import { useState, useRef, useCallback, useEffect } from "react";
import React from "react";

const TerminalIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="4 17 10 11 4 5" />
    <line x1="12" y1="19" x2="20" y2="19" />
  </svg>
);

const OutputIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <line x1="8" y1="21" x2="16" y2="21" />
    <line x1="12" y1="17" x2="12" y2="21" />
  </svg>
);

const ChevronDown = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const ChevronUp = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="18 15 12 9 6 15" />
  </svg>
);

const TABS = [
  { id: "terminal", label: "Terminal", icon: <TerminalIcon /> },
  { id: "output",   label: "Output",   icon: <OutputIcon />   },
] as const;

type TabId = (typeof TABS)[number]["id"];

function TerminalContent() {
  return (

    <></>
    // <div className="p-4 space-y-1 font-mono text-xs">
    //   <p><span className="text-emerald-400">$</span> <span className="text-gray-300">node solution.js</span></p>
    //   <p className="text-gray-500">Running tests…</p>
    //   <p className="text-emerald-400">✓ Test 1 passed</p>
    //   <p className="text-emerald-400">✓ Test 2 passed</p>
    //   <p className="text-amber-400">⚠ Test 3 — time limit 200 ms (used 187 ms)</p>
    //   <p className="text-gray-500 mt-2">Process exited with code 0</p>
    // </div>
  );
}

function OutputContent() {
  return (

    <></>
    // <div className="p-4 space-y-3 font-mono text-xs">
    //   <div className="bg-gray-800 rounded-lg p-3 border border-gray-700 space-y-1">
    //     <p className="text-gray-500 uppercase tracking-widest text-[10px]">stdout</p>
    //     <p className="text-blue-300">[1, 2, 3] → 6</p>
    //     <p className="text-blue-300">[4, 5, 6] → 15</p>
    //   </div>
    //   <div className="bg-gray-800 rounded-lg p-3 border border-gray-700 space-y-1">
    //     <p className="text-gray-500 uppercase tracking-widest text-[10px]">result</p>
    //     <p className="text-emerald-400 font-semibold">All test cases passed ✓</p>
    //   </div>
    // </div>
  );
}

// TAB_BAR_H must match the actual rendered tab bar height.
// py-2 = 8px top + 8px bottom, text-xs line-height ~16px → 32px total.
// border-b = 1px. Total: 33px. Round up to 34 for safety.
const TAB_BAR_H  = 100;
const COLLAPSED_H = TAB_BAR_H;
const DEFAULT_H   = 220;

interface OutputBarProps {
  onHeightChange?: (h: number) => void;
}

export default function OutputBar({ onHeightChange }: OutputBarProps) {
  const [activeTab,  setActiveTab]  = useState<TabId>("terminal");
  const [collapsed,  setCollapsed]  = useState(false);
  const [panelH,     setPanelH]     = useState(DEFAULT_H);
  const [isResizing, setIsResizing] = useState(false);

  const resizing    = useRef(false);
  const resizeStart = useRef({ my: 0, h: DEFAULT_H });

  const currentH = collapsed ? COLLAPSED_H : panelH;

  useEffect(() => {
    onHeightChange?.(currentH);
  }, [currentH, onHeightChange]);

  const onResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    resizing.current = true;
    setIsResizing(true);
    resizeStart.current = { my: e.clientY, h: panelH };
  }, [panelH]);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!resizing.current) return;
      const delta = resizeStart.current.my - e.clientY; // up = bigger
      const next  = Math.max(TAB_BAR_H + 40, Math.min(600, resizeStart.current.h + delta));
      setPanelH(next);
    };
    const onMouseUp = () => {
      resizing.current = false;
      setIsResizing(false);
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup",   onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup",   onMouseUp);
    };
  }, []);

  return (
    <div
      style={{ height: currentH }}
      className={`
        relative flex flex-col shrink-0
        bg-gray-900 text-gray-100 font-mono text-sm
        border-t border-gray-700 overflow-hidden select-none
        ${isResizing ? "" : "transition-[height] duration-200 ease-in-out"}
      `}
    >
      {/* resize handle — only interactive when open */}
      <div
        onMouseDown={collapsed ? undefined : onResizeMouseDown}
        className={`
          absolute top-0 left-0 right-0 h-[5px] z-20 group
          ${collapsed ? "cursor-default" : "cursor-ns-resize"}
        `}
      >
        {!collapsed && (
          <div className="absolute inset-x-0 top-[2px] h-[1px] bg-gray-600 group-hover:bg-blue-500 transition-colors" />
        )}
      </div>

      {/* tab bar — ALWAYS rendered so collapsed state shows it */}
      <div className="flex flex-row items-center bg-gray-800 border-b border-gray-700 shrink-0">
        {TABS.map((tab, index) => (
          <React.Fragment key={tab.id}>
            <button
              onClick={() => {
                setActiveTab(tab.id);
                if (collapsed) setCollapsed(false);
              }}
              className={`
                flex items-center gap-1.5 px-4 py-2 whitespace-nowrap text-xs
                !bg-transparent font-semibold tracking-wide transition-colors
                ${activeTab === tab.id && !collapsed
                  ? "text-white border-b-2 border-blue-500"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-700"}
              `}
            >
              {tab.icon}
              {tab.label}
            </button>
            {index < TABS.length - 1 && (
              <span className="self-center text-gray-600 select-none">|</span>
            )}
          </React.Fragment>
        ))}

        <div className="flex-1" />

        <button
          onClick={() => setCollapsed((c) => !c)}
          className="mr-2 p-1.5 rounded text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
          title={collapsed ? "Expand" : "Collapse"}
        >
          {collapsed ? <ChevronUp /> : <ChevronDown />}
        </button>
      </div>

      {/* content — always in DOM, overflow-hidden hides it when collapsed */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "terminal" && <TerminalContent />}
        {activeTab === "output"   && <OutputContent />}
      </div>
    </div>
  );
}