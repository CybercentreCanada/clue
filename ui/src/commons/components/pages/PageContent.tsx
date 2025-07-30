import { memo, ReactNode } from 'react';
import usePageProps, { PageProps } from './hooks/usePageProps';

type PageContentProps = PageProps & {
  children?: ReactNode;
};

const PageContent = ({ children, ...props }: PageContentProps) => {
  const pageProps = usePageProps({ props });
  return <div {...pageProps}>{children}</div>;
};

export default memo(PageContent);
