import usePageProps, { PageProps } from 'commons/components/pages/hooks/usePageProps';
import { memo, ReactNode } from 'react';

type FlexVerticalProps = PageProps & {
  flex?: number;
  children: ReactNode;
};

const FlexVertical = ({ flex = 1, children, ...props }: FlexVerticalProps) => {
  const pageProps = usePageProps({ props, defaultOverrides: { mb: 0, ml: 0, mr: 0, mt: 0 } });
  return (
    <div
      className={pageProps.className ? pageProps.className : ''}
      style={{
        display: 'flex',
        flexDirection: 'column',
        flex,
        ...pageProps.style
      }}
    >
      {children}
    </div>
  );
};

export default memo(FlexVertical);
