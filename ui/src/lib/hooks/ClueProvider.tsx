import type { FC, PropsWithChildren } from 'react';
import type { ClueActionProps } from './ClueActionContext';
import { ClueActionProvider } from './ClueActionContext';
import type { ClueComponentContextType } from './ClueComponentContext';
import { ClueComponentProvider } from './ClueComponentContext';
import type { ClueConfigContextProps } from './ClueConfigProvider';
import { ClueConfigProvider } from './ClueConfigProvider';
import type { ClueDatabaseContextProps } from './ClueDatabaseContext';
import { ClueDatabaseProvider } from './ClueDatabaseContext';
import { ClueEnrichProvider } from './ClueEnrichContext';
import type { ClueEnrichProps } from './ClueEnrichProps';
import { ClueFetcherProvider } from './ClueFetcherContext';
import { CluePopupProvider } from './CluePopupContext';

const ClueProvider: FC<
  PropsWithChildren<
    ClueEnrichProps & ClueActionProps & ClueComponentContextType & ClueDatabaseContextProps & ClueConfigContextProps
  >
> = ({ children, ...props }) => {
  return (
    <ClueComponentProvider {...props}>
      <ClueConfigProvider config={props.config}>
        <ClueDatabaseProvider {...props}>
          <ClueEnrichProvider {...props}>
            <ClueFetcherProvider {...props}>
              <ClueActionProvider {...props}>
                <CluePopupProvider>{children}</CluePopupProvider>
              </ClueActionProvider>
            </ClueFetcherProvider>
          </ClueEnrichProvider>
        </ClueDatabaseProvider>
      </ClueConfigProvider>
    </ClueComponentProvider>
  );
};

export { ClueProvider };
