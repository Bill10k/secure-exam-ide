import { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

interface TerminalOutputProps {
  onTerminalInit?: (terminal: Terminal) => void;
}

export function TerminalOutput({ onTerminalInit }: TerminalOutputProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize xterm.js
    const term = new Terminal({
      cursorBlink: true,
      theme: {
        background: '#1e1e1e',
        foreground: '#f6f6f6'
      }
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    term.open(terminalRef.current);
    fitAddon.fit();

    term.writeln('Welcome to the Secure Exam IDE Terminal');
    term.writeln('This terminal is ready for code execution output...\r\n');

    xtermRef.current = term;

    if (onTerminalInit) {
      onTerminalInit(term);
    }

    // Handle window resize
    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
    };
  }, [onTerminalInit]);

  return (
    <div
      ref={terminalRef}
      className="terminal-container"
      style={{ width: '100%', height: '300px', textAlign: 'left' }}
    />
  );
}
