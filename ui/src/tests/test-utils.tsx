import { act, render, RenderResult, screen } from '@testing-library/react';
import i18n from 'i18n';
import { ClueDatabase } from 'lib/database/types';
import { ClueProvider } from 'lib/hooks/ClueProvider';
import React, { FC, PropsWithChildren } from 'react';
import { I18nextProvider, useTranslation } from 'react-i18next';

/**
 * Convenience function for rendering a component and waiting for any active promises.
 * @param element The element to render.
 * @returns       The result of the render.
 */
export async function renderComponent(element: React.JSX.Element, database?: ClueDatabase): Promise<RenderResult> {
  const result: RenderResult = render(<ProviderWrapper database={database}>{element}</ProviderWrapper>);

  await flush();

  return result;
}

/**
 * Flush pending promises.
 */
export async function flush(): Promise<void> {
  await act(async () => {
    if (vi.isFakeTimers()) {
      await vi.runAllTimersAsync();
    }
  });
}

const ProviderWrapper: FC<PropsWithChildren<{ database?: ClueDatabase }>> = ({ children, database }) => {
  const translation = useTranslation('translation');
  return (
    <I18nextProvider i18n={i18n}>
      <ClueProvider
        skipConfigCall={true}
        i18next={translation}
        enabled={false}
        publicIconify={false}
        defaultTimeout={5}
        database={database}
        debugLogging={!!process.env.ENABLE_DEBUG_LOGGNIG}
      >
        {children}
      </ClueProvider>
    </I18nextProvider>
  );
};

/**
 * Find an element.
 * @param id            The element id.
 * @param index         Optional index of the element with the same id.
 * @param checkDisabled Set to true to check if the element is disabled.
 */
export function findElement(id: string, index?: number, checkDisabled?: boolean): HTMLElement {
  const element: HTMLElement = index === undefined ? screen.getByTestId(id) : screen.getAllByTestId(id)[index];

  if (checkDisabled && element.hasAttribute('disabled')) {
    throw Error(
      `Element with id:${id} (index: ${index}) is disabled, so firing events on it will not have expected results.`
    );
  }

  return element;
}

/**
 * Verify if an element has the given text.
 * @param id    The element id.
 * @param text  The expected text.
 * @param index Optional index of the element with the same id.
 */
export function verifyText(id: string, text: string | RegExp, index?: number): void {
  verifyElementText(findElement(id, index), text);
}

/**
 * Verify if an element has the expected text.
 * @param element The element.
 * @param text    The expected text.
 */
export function verifyElementText(element: Element, text: string | RegExp): void {
  if (text !== undefined) {
    expect(element).toHaveTextContent(text, { normalizeWhitespace: false });
  } else {
    throw new Error('Undefined text to compare. Was this intended?');
  }
}

/**
 * Verify an element exists.
 * @param id     The element id.
 * @param exists Set to true if expected to exist (Default) or false if it shouldn't exist.
 */
export function verifyExistence(id: string, exists = true): void {
  if (exists) {
    try {
      expect(screen.queryAllByTestId(id).length).toBeGreaterThan(0);
    } catch (error) {
      // catch the fail to make it clearer.
      throw new Error(`Element with ID '${id}' doesn't exist as expected.`);
    }
  } else {
    expect(screen.queryByTestId(id)).toBeNull();
  }
}
