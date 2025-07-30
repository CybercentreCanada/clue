import '@fontsource/roboto';
import App from 'components/app/App';
import 'i18n';
import 'index.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

const root = createRoot(document.getElementById('root'));
root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
