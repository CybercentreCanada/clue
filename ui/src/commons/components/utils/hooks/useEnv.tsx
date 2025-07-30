import { useMemo } from 'react';

const APP_ENV = import.meta.env;

export default function useAppEnv(key?: string) {
  return useMemo(() => {
    if (key) {
      return APP_ENV[key];
    }
    return APP_ENV;
  }, [key]);
}
