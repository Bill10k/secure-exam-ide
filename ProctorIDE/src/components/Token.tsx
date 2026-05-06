import  { useState } from "react";
import { useAuth } from "../context/AuthContext";

function Token() {
  const { startExam } = useAuth();
  const [tokenInput, setTokenInput] = useState("");

  return (
    <div className="tokenDiag ">
      <h1>Enter a Token</h1>
      <div className="tokenForm">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            // Optional: validate token here
            startExam(tokenInput);
          }}
        >
           {/* Student Details */}
           
           <div className="flex flex-col">
            {/* Username */}
             <div className="flex flex-col">
            <label htmlFor="username">Username or Email</label>
             <input
             placeholder="Username"
             type="text"
             name="username"
            
             />
            </div>

           {/* ------- */}
           
           {/* Passowrd */}

          <label htmlFor="pword">Password</label>
         <input placeholder=" password" type="password" name="pword"/>



           {/* ------- */}

           
        



         <label htmlFor="token">Token</label>

          <input
            value={tokenInput}
            onChange={(e) => setTokenInput(e.currentTarget.value)}
            placeholder="Enter token to begin exam"
            name="token"
          />
          


           </div>
          

          

          <button className="rounded-lg border border-transparent px-5 py-2 text-base font-medium font-inherit text-[#0f0f0f] bg-white transition-colors duration-200 shadow-[0_2px_2px_rgba(0,0,0,0.2)]" type="submit">Start</button>
        </form>
      </div>
    </div>
  );
}

export default Token;