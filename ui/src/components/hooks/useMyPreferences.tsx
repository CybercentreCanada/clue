import {
  Code,
  Dashboard,
  Description,
  ExitToApp,
  Help,
  HelpCenter,
  Settings,
  SupervisorAccount,
  SystemUpdateAlt
} from '@mui/icons-material';
import { Avatar, Stack } from '@mui/material';
import type { AppLeftNavElement, AppPreferenceConfigs } from 'commons/components/app/AppConfigs';
import Classification from 'components/elements/display/Classification';

import { useMemo } from 'react';

// This is your App Name that will be displayed in the left drawer and the top navbar
const APP_NAME = 'Clue';

// This is your app logo, it should definitely be an svg logo but we will use an icon here instead
const APP_LOGO_LIGHT = (
  <Avatar
    variant="rounded"
    style={{
      backgroundColor: 'transparent',
      height: 44,
      width: 44,
      marginLeft: -10
    }}
  >
    <img src="/svg/light/clue-icon2.svg" style={{ width: 43, height: 43 }} alt="Clue" />
  </Avatar>
);

const APP_LOGO_DARK = (
  <Avatar
    variant="rounded"
    style={{
      backgroundColor: 'transparent',
      height: 44,
      width: 44,
      marginLeft: -10
    }}
  >
    <img src="/svg/dark/clue-icon2.svg" style={{ width: 43, height: 43 }} alt="Clue" />
  </Avatar>
);

const APP_BANNER_LIGHT = (
  <Stack mt={2} mb={2} alignItems="center">
    {/* <Landscape color="primary" fontSize="inherit" style={{ fontSize: '3em' }} />
    <Box m={1} />
    <Typography variant="inherit">{APP_NAME}</Typography> */}
    <img src="/svg/light/clue-h.svg" alt="Clue" />
  </Stack>
);
const APP_BANNER_DARK = (
  <Stack mt={2} mb={2} alignItems="center">
    {/* <Landscape color="primary" fontSize="inherit" style={{ fontSize: '3em' }} />
    <Box m={1} />
    <Typography variant="inherit">{APP_NAME}</Typography> */}
    <img src="/svg/dark/clue-h.svg" alt="Clue" />
  </Stack>
);

export default function useMyPreferences(): AppPreferenceConfigs {
  // The following menu items will show up in the Left Navigation Drawer
  const MENU_ITEMS = useMemo<AppLeftNavElement[]>(
    () => {
      const defaultRoutes: AppLeftNavElement[] = [
        {
          type: 'item',
          element: {
            id: 'dashboard',
            i18nKey: 'route.home',
            route: '/',
            icon: <Dashboard />
          }
        },
        {
          type: 'item',
          element: {
            id: 'fetchers',
            i18nKey: 'route.fetchers',
            route: '/fetchers',
            icon: <SystemUpdateAlt />
          }
        },
        {
          type: 'group',
          element: {
            id: 'help',
            i18nKey: 'route.help',
            icon: <Help />,
            items: [
              {
                id: 'help',
                i18nKey: 'route.help.dashboard',
                route: '/help',
                icon: <HelpCenter />
              },
              {
                id: 'contributing',
                i18nKey: 'route.help.contributing',
                route: '/help/contributing',
                icon: <Description />
              }
            ]
          }
        }
      ];

      if (
        window.location.origin.includes('localhost') ||
        window.location.origin.includes('dev') ||
        window.location.origin.includes('stg')
      ) {
        defaultRoutes.push({
          type: 'item',
          element: {
            id: 'examples',
            i18nKey: 'route.examples',
            route: '/examples',
            icon: <Code />
          }
        });
      }

      return defaultRoutes;
    },
    // prettier-ignore
    []
  );

  // This is the basic user menu, it is a menu that shows up in account avatar popover.
  const USER_MENU_ITEMS = useMemo(
    () => [
      {
        i18nKey: 'usermenu.settings',
        route: '/settings',
        icon: <Settings />
      },
      {
        i18nKey: 'usermenu.logout',
        route: '/logout',
        icon: <ExitToApp />
      }
    ],
    []
  );

  // This is the basic administrator menu, it is a menu that shows up under the user menu in the account avatar popover.
  const ADMIN_MENU_ITEMS = useMemo(
    () => [
      {
        i18nKey: 'adminmenu.users',
        route: '/admin/users',
        icon: <SupervisorAccount />
      }
    ],
    []
  );

  // Return memoized config to prevent unnecessary re-renders.
  return useMemo(
    () => ({
      appName: APP_NAME,
      allowGravatar: false,
      allowQuickSearch: false,
      appIconDark: APP_LOGO_DARK,
      appIconLight: APP_LOGO_LIGHT,
      bannerLight: APP_BANNER_LIGHT,
      defaultShowQuickSearch: false,
      bannerDark: APP_BANNER_DARK,
      avatarD: 'retro',
      topnav: {
        apps: [],
        userMenu: USER_MENU_ITEMS,
        userMenuI18nKey: 'usermenu',
        adminMenu: ADMIN_MENU_ITEMS,
        adminMenuI18nKey: 'adminmenu',
        quickSearchParam: 'query',
        quickSearchURI: '/hits',
        rightBeforeSearch: <Classification />
      },
      leftnav: {
        elements: MENU_ITEMS
      }
    }),
    [USER_MENU_ITEMS, ADMIN_MENU_ITEMS, MENU_ITEMS]
  );
}
