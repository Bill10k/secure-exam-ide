import { useState, useCallback } from 'react';
import { Editor } from '@monaco-editor/react';
import Toolbar from './Toolbar';
import OutputBar from './OutputBar';

function CodeEditor() {
  const [outputH, setOutputH] = useState(220);

  const handleHeightChange = useCallback((h: number) => {
    setOutputH(h);
  }, []);

  // editor fills whatever's left after toolbar (~40px) and OutputBar
  const editorHeight = `calc(100svh - 40px - ${outputH}px)`;

  return (
    <div className="h-svh w-full flex flex-col overflow-hidden">
      <Toolbar />

      <Editor
        height={editorHeight}
        width="100%"
        defaultLanguage="python"
        theme="vs-dark"
        defaultValue="// start coding..."
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

      <OutputBar onHeightChange={handleHeightChange} />
    </div>
  );
}

export default CodeEditor;