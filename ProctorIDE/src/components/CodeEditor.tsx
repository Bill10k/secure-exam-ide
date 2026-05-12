import { useState, useCallback } from 'react';
import { Editor } from '@monaco-editor/react';
import Toolbar from './Toolbar';
import OutputBar from './OutputBar';

interface CodeEditorProps {
  value?: string;
  onChange?: (value: string | undefined) => void;
  inputValue?: string;
  onInputChange?: (value: string) => void;
  onRun?: () => void;
  onSubmit?: () => void;
  onTerminalInit?: (terminal: any) => void;
}



window.addEventListener("contextmenu", (e) => {
  e.preventDefault();
});

function CodeEditor({ value, onChange, inputValue, onInputChange, onRun, onSubmit, onTerminalInit }: CodeEditorProps) {
  const [outputH, setOutputH] = useState(220);

  const handleHeightChange = useCallback((h: number) => {
    setOutputH(h);
  }, []);

  // editor fills whatever's left after toolbar (~40px) and OutputBar
  const editorHeight = `calc(100svh - 40px - ${outputH}px)`;

  return (
    <div className="h-svh w-full flex flex-col overflow-hidden">
      <Toolbar onRun={onRun} onSubmit={onSubmit} />

      <Editor
        height={editorHeight}
        width="100%"
        defaultLanguage="python"
        theme="vs-dark"
        value={value}
        onChange={onChange}
        options={{
          lineNumbersMinChars: 2,
          lineDecorationsWidth: 4,
          fontSize: 13,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontLigatures: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          renderLineHighlight: "line",
          padding: { top: 12 },
          tabSize: 2,
          wordWrap: "on",
          cursorBlinking: "smooth",
          smoothScrolling: true,
        }}
      />

      <OutputBar onHeightChange={handleHeightChange} onTerminalInit={onTerminalInit} inputValue={inputValue} onInputChange={onInputChange} />
    </div>
  );
}

export default CodeEditor;