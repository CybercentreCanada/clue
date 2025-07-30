import usePageProps, { PageProps } from 'commons/components/pages/hooks/usePageProps';
import { memo, ReactNode } from 'react';

type FlexHorizontalProps = PageProps & {
  flex?: number;
  alignItems?: string;
  children: ReactNode;
};

const FlexHorizontal = ({ flex, alignItems, children, ...props }: FlexHorizontalProps) => {
  const pageProps = usePageProps({ props, defaultOverrides: { height: '100%', mb: 0, ml: 0, mr: 0, mt: 0 } });
  return (
    <div
      className={pageProps.className ? pageProps.className : ''}
      style={{
        display: 'flex',
        flexDirection: 'row',
        flex,
        alignItems,
        ...pageProps.style
      }}
    >
      {children}
    </div>
  );
};

export default memo(FlexHorizontal);
