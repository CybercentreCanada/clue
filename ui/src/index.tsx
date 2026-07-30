import '@fontsource/roboto';
import api from 'api';
import App from 'components/app/App';
import 'i18n';
import 'index.css';
import buildDatabase from 'lib/database';
import type { ClueDatabase } from 'lib/database/types';
import type { ApiType } from 'lib/types/config';
import { StorageKey } from 'lib/utils/constants';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { getStored } from 'utils/localStorage';

const root = createRoot(document.getElementById('root'));

const init = async () => {
  let config: ApiType | null = null;
  let database: ClueDatabase | null = null;

  try {
    config = await api.configs.get();
    database = await buildDatabase({
      storageType: 'memory',
      replicate: config?.configuration?.ui?.replicate,
      getToken: () => getStored(StorageKey.APP_TOKEN)
    });
  } catch (e) {
    // If pre-initialization fails, mount React anyway so it can handle auth/errors normally
    console.warn('exception on initialization:', e);
  }

  root.render(
    <StrictMode>
      <App config={config} database={database} />
    </StrictMode>
  );
};

init();
