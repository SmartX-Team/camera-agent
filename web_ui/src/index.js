import React from 'react';
import ReactDOM from 'react-dom';
import './tailwind.css';  // index.css 대신 tailwind.css를 import
import App from './App';
import reportWebVitals from './reportWebVitals';

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root')
);

reportWebVitals();