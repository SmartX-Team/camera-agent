import React from 'react';
import AgentList from './components/AgentList';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Camera Agent Project</h1>
      </header>
      <main>
        <AgentList />
      </main>
    </div>
  );
}

export default App;