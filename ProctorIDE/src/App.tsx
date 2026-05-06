
import "./App.css";

import Token from "./components/Token";
import { useAuth } from "./context/AuthContext";
import Environment from "./components/Environment";

function App() {
  const {examStarted} = useAuth()

  return (
    <main className="w-screen min-h-screen p-0 m-0 flex items-center justify-center">
     {!examStarted ? (
        <Token />
      ) : (
        
          <Environment/>
          // <h1>
          //   home
          // </h1>
          
        
      )}
      {/* <Timer time={{hours: 2}}/> */}

      
      {/* <h1>Welcome to Tauri + React</h1>

      <div className="row">
        <a href="https://vite.dev" target="_blank">
          <img src="/vite.svg" className="logo vite" alt="Vite logo" />
        </a>
        <a href="https://tauri.app" target="_blank">
          <img src="/tauri.svg" className="logo tauri" alt="Tauri logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <p>Click on the Tauri, Vite, and React logos to learn more.</p>

      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          greet();
        }}
      >
        <input
          id="greet-input"
          onChange={(e) => setName(e.currentTarget.value)}
          placeholder="Enter a name..."
        />
        <button type="submit">Greet</button>
      </form>
      <p>{greetMsg}</p> */}
    </main>
  );
}

export default App;
