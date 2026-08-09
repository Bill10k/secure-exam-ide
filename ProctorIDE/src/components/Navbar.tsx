import Timer from './Timer'
import logo from '../assets/logo.png'

type NavbarProps = {
  remainingSeconds?: number
  examTitle?: string
}

function Navbar({ remainingSeconds = 0, examTitle }: NavbarProps) {
  return (

<nav className="relative w-full bg-gray-800/50 border-b border-gray-700/60">
  <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
    <div className="relative flex h-16 items-center justify-between">

      {/* Left: App Logo & Brand Name */}
      <div className="flex-1 flex items-center gap-2.5">
        <img src={logo} alt="ProctorIDE Logo" className="h-7 w-auto object-contain" />
        <span className="text-white font-extrabold text-lg tracking-tight">Proctor<span className="text-blue-400">IDE</span></span>
      </div>

      {/* Centered Exam Name */}
      <div className="flex items-center justify-center">
        <h1 className="text-white font-semibold text-lg whitespace-nowrap">
          {examTitle || "Examination"}
        </h1>
      </div>

      {/* Timer - right aligned */}
      <div className="flex-1 flex justify-end items-center">
        <Timer remainingSeconds={remainingSeconds} />
      </div>

    </div>
  </div>
</nav>

  )
}

export default Navbar