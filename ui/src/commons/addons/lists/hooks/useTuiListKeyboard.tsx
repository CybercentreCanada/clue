import Throttler from 'commons/addons/utils/Throttler';
import { isArrowDown, isArrowUp, isEnter } from 'commons/components/utils/keyboard';
import { useCallback, useMemo } from 'react';
import { TuiListItemOnSelect } from '..';
import useTuiList from './useTuiListItems';

const THROTTLER = new Throttler(10);

export default function useTuiListKeyboard<T>(onSelect: TuiListItemOnSelect<T>) {
  const { items, movePrevious, moveNext } = useTuiList<T>();

  // Keyboard[keydown] event handler.
  const onKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // event.preventDefault();

      // going up.
      if (isArrowUp(event.key)) {
        event.preventDefault();
        THROTTLER.debounce(() => movePrevious());
      }

      // going down.
      else if (isArrowDown(event.key)) {
        event.preventDefault();
        THROTTLER.debounce(() => moveNext());
      }

      // select.
      else if (isEnter(event.key)) {
        const index = items.findIndex(i => !!i.cursor);
        onSelect(items[index], index);
      }
    },
    [items, movePrevious, moveNext, onSelect]
  );

  // Register keyboard event handler.
  const register = useCallback(
    (element: HTMLElement) => {
      if (element) {
        element.addEventListener('keydown', onKeyDown);
      }
      return () => {
        element.removeEventListener('keydown', onKeyDown);
      };
    },
    [onKeyDown]
  );

  return useMemo(
    () => ({
      register
    }),
    [register]
  );
}
