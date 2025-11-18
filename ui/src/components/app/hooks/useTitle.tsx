import useMySitemap from 'components/hooks/useMySitemap';
import { useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';

const useTitle = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const sitemap = useMySitemap();

  const setTitle = useCallback((title: string) => {
    document.querySelector('title').innerHTML = title;
  }, []);

  const runChecks = useCallback(async () => {
    const matchingRoute = sitemap.routes.find(_route => _route.path === location.pathname);

    if (matchingRoute) {
      setTitle(`Clue - ${t(matchingRoute.title)}`);
    }
  }, [location.pathname, setTitle, sitemap.routes, t]);

  useEffect(() => {
    runChecks();
  }, [runChecks]);
};

export default useTitle;
