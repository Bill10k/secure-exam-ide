import React from 'react'
import Timer from './Timer'

function Navbar() {
  return (

<nav className="relative w-full bg-gray-800/50">
  <div className="mx-auto max-w-7xl px-2 sm:px-6 lg:px-8">
    <div className="relative flex h-16 items-center justify-between">

      {/* Spacer left */}
      <div className="flex-1" />

      {/* Centered Exam Name */}
      <div className="flex items-center justify-center">
        <h1 className="text-white font-semibold text-lg whitespace-nowrap ">
          Mid Semester Examinations
        </h1>
      </div>

      {/* Timer - right aligned */}
      <div className="flex-1 flex justify-end items-center">
        <Timer time={{ hours: 1 }} />
      </div>

    </div>
  </div>
</nav>

  )
}

export default Navbar