import useApp from './useApp';
import useAppConfigs from './useAppConfigs';

export default function useAppBanner() {
  const { theme } = useApp();
  const { preferences } = useAppConfigs();
  return theme === 'dark' ? preferences.bannerDark : preferences.bannerLight;
}
