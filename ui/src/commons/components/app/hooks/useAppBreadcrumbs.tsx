import { AppBreadcrumbsContext } from 'commons/components/app/providers/AppBreadcrumbsProvider';
import { useContext } from 'react';

//
export default function useAppBreadcrumbs() {
  return useContext(AppBreadcrumbsContext);
}
