import React, { useState, useCallback } from 'react'
import Navbar from './Navbar'
import QuestionPanel from './QuestionTab'
import CodeEditor from './CodeEditor'

function Environment() {
  const [leftWidth, setLeftWidth] = useState(45) // percentage

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const startWidth = leftWidth

    const onMouseMove = (moveEvent: MouseEvent) => {
      const containerWidth = window.innerWidth
      const delta = moveEvent.clientX - startX
      const newWidth = startWidth + (delta / containerWidth) * 100
      // Clamp between 20% and 80%
      setLeftWidth(Math.min(80, Math.max(20, newWidth)))
    }

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [leftWidth])

  return (
    <div className='w-full h-screen flex flex-col overflow-hidden'>

      <Navbar />

      {/* Body: aside + divider + main side by side */}
      <div className='flex flex-row flex-1 overflow-hidden'>

        {/* Sidebar */}
        <aside
          style={{ width: `${leftWidth}%` }}
          className='flex-shrink-0 bg-gray-700 flex flex-col overflow-y-auto'
        >
          {/* <div className='flex flex-row justify-center items-center text-lg bg-gray-600 gap-3 py-1 px-2 border-b border-gray-500'> */}
           <QuestionPanel></QuestionPanel>
          
          <div className='p-4 text-white'>
            {/* question body */}
          </div>
        </aside>

        {/* Drag handle */}
        <div
          onMouseDown={handleMouseDown}
          className='w-1 bg-gray-500 hover:bg-blue-400 cursor-col-resize flex-shrink-0 transition-colors duration-150'
        />

        {/* Coding section */}
        <div
          style={{ width: `${100 - leftWidth}%` }}
          className='flex-shrink-0 //bg-amber-500 overflow-hidden'
        >
          <CodeEditor></CodeEditor>
        </div>

      </div>
    </div>
  )
}

export default Environment