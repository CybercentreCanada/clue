import { ClueGroupContext } from 'lib/hooks/ClueGroupContext';
import isEqual from 'lodash-es/isEqual';
import type { FC, PropsWithChildren } from 'react';
import { memo, useEffect } from 'react';
import { useContextSelector } from 'use-context-selector';

interface ClueEntryProps {
  entry: any;
  selected?: boolean;
}

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const Entry: FC<PropsWithChildren<ClueEntryProps>> = ({ children, entry, selected = false }) => {
  const setValues = useContextSelector(ClueGroupContext, ctx => ctx?.setValues);

  useEffect(() => {
    setValues?.(_values => [..._values.filter(value => !isEqual(value, entry)), ...(selected ? [entry] : [])]);
  }, [entry, selected, setValues]);

  return children;
};

export default memo(Entry);
