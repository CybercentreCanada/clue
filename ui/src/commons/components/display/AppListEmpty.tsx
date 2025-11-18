import AppInfoPanel, { AppInfoPanelProps } from './AppInfoPanel';

export default function AppListEmpty(props: Omit<AppInfoPanelProps, 'i18nKey'>) {
  return <AppInfoPanel {...props} i18nKey="app.list.empty" />;
}
