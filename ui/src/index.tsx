import '@fontsource/roboto';
import App from 'components/app/App';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';
import 'i18n';
import 'index.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

dayjs.extend(utc);
dayjs.extend(duration);
dayjs.extend(relativeTime);

const root = createRoot(document.getElementById('root'));
root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
