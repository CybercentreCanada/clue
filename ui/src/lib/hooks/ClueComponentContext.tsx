import type { ReactJsonViewProps } from '@microlink/react-json-view';
import type { ComponentType, FC, PropsWithChildren } from 'react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { createContext } from 'use-context-selector';

export type ClueComponentContextType = {
  ReactJson?: ComponentType<ReactJsonViewProps>;
  i18next?: ReturnType<typeof useTranslation>;
};

export const ClueComponentContext = createContext<ClueComponentContextType>(null);

/**
 * If no i18n is provided to {@link ClueComponentProvider}, use {@link ClueComponentI18nProvider}.
 */
const ClueComponentI18nProvider: FC<PropsWithChildren<Omit<ClueComponentContextType, 'i18next'>>> = ({
  children,
  ReactJson
}) => {
  const i18next = useTranslation();

  const context = useMemo(
    () => ({
      ReactJson,
      i18next: i18next
    }),
    [ReactJson, i18next]
  );

  return <ClueComponentContext.Provider value={context}>{children}</ClueComponentContext.Provider>;
};

export const ClueComponentProvider: FC<PropsWithChildren<ClueComponentContextType>> = ({
  children,
  ReactJson,
  i18next = null
}) => {
  const context = useMemo(
    () => ({
      ReactJson,
      i18next: i18next
    }),
    [ReactJson, i18next]
  );

  if (!i18next) {
    return <ClueComponentI18nProvider ReactJson={ReactJson}>{children}</ClueComponentI18nProvider>;
  }

  return <ClueComponentContext.Provider value={context}>{children}</ClueComponentContext.Provider>;
};
