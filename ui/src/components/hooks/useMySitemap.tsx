import { Article, Code, Dashboard, Help, Settings, SystemUpdateAlt } from '@mui/icons-material';
import type { AppSiteMapConfigs } from 'commons/components/app/AppConfigs';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

// SiteMapContextProps configuration properties.
// exceptLast: boolean = false (default) -> render all breadcrumb except the current route.
// allLinks: boolean = false (default) -> render all breadcrumbs as links.
// lastOnly: boolean = false (default) -> only render the current route.
// itemsBefore: number = 1 (default) -> the number of items to show before the ellipsis.
// itemsAfter: number = 1 (default) -> the number of items to show after the ellipsis.
// routes: SiteMapRoute[] = [] (default) -> the list of routes that will define the application sitemap.

// For each individual SiteMapRoute:
// path: string -> the react router path to this route.
// title: string -> the title/lable to display in breadcrumbs for this route.
// icon?: React.ReactNode -> the icon component to show beside the title/lable.
// isRoot?: boolean = false -> when true, indicates that the breadcrumbs will reset to this one path each time it is encountered.
// isLeaf?: boolean = false -> when true, indicates that this path does not aggregate in breadcrumbs, i.e. will be replaced by next path.
// excluded?: boolean = false -> when true, indicates to breadcrumbs component to not render this route.
// breadcrumbs?: string[] -> a static list of breadcrumb paths to be rendered for the given route.
// textWidth?: number -> the max width of the text when rendering the breadcrumb.
export default function useMySitemap(): AppSiteMapConfigs {
  const { t } = useTranslation();
  return useMemo(
    () => ({
      routes: [
        {
          path: '/',
          title: t('route.home'),
          isRoot: true,
          icon: <Dashboard />
        },
        {
          path: '/settings',
          title: t('page.settings.sitemap'),
          isRoot: true,
          icon: <Settings />
        },
        {
          path: '/examples',
          title: t('route.examples'),
          isRoot: true,
          icon: <Code />
        },
        {
          path: '/fetchers',
          title: t('route.fetchers'),
          isRoot: true,
          icon: <SystemUpdateAlt />
        },
        {
          path: '/help',
          title: t('route.help'),
          isRoot: true,
          icon: <Help />
        },
        {
          path: '/help/contributing',
          title: t('route.help.contributing'),
          isRoot: true,
          icon: <Help />,
          breadcrumbs: ['/help']
        },
        {
          path: '/help/:plugin',
          title: t('route.plugin'),
          isLeaf: true,
          icon: <Article />,
          breadcrumbs: ['/help']
        }
      ]
    }),
    [t]
  );
}
