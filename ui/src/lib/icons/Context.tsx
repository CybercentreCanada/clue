import type { IconProps } from '@iconify/react';
import { Icon } from '@iconify/react';
import { Divider, Stack } from '@mui/material';
import AnnotationEntry from 'lib/components/AnnotationEntry';
import CountBadge from 'lib/components/CountBadge';
import Iconified from 'lib/components/display/icons/Iconified';
import { CluePopupContext } from 'lib/hooks/CluePopupContext';
import type { Annotation, Selector, WithExtra } from 'lib/types/lookup';
import groupBy from 'lodash-es/groupBy';
import type { FC, ReactNode } from 'react';
import { memo, useEffect, useMemo, useRef } from 'react';
import { useContextSelector } from 'use-context-selector';

const ContextIcon: FC<
  {
    annotations: WithExtra<Annotation>[];
    value: Selector;
    counters?: boolean;
    disableTooltip?: boolean;
    showExtraIcon?: boolean;
    ubiquitous?: boolean;
  } & Omit<IconProps, 'icon'>
> = ({
  annotations,
  value,
  counters = true,
  disableTooltip = false,
  showExtraIcon = false,
  ubiquitous = false,
  ...otherProps
}) => {
  const showInfo = useContextSelector(CluePopupContext, state => state.showInfo);
  const closeInfo = useContextSelector(CluePopupContext, state => state.closeInfo);

  const anchorRef = useRef<HTMLElement>();

  const contextAnnotations = useMemo(
    () => annotations.filter(annotation => annotation.type === 'context' && annotation.ubiquitous === ubiquitous),
    [annotations, ubiquitous]
  );

  const additionalIcons = useMemo(() => contextAnnotations.filter(annotation => annotation.icon), [contextAnnotations]);

  useEffect(() => {
    if (disableTooltip) {
      closeInfo('context', value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disableTooltip]);

  if (contextAnnotations?.length < 1) {
    return null;
  }

  const icons: ReactNode[] = [];

  if (additionalIcons.length) {
    Object.entries(groupBy(additionalIcons, 'icon')).forEach(([icon, _annotations]) =>
      icons.push(
        <span
          key={icon}
          ref={anchorRef}
          style={{ display: 'flex' }}
          onMouseOver={
            disableTooltip
              ? undefined
              : () =>
                  showInfo('context', anchorRef.current, value, {
                    content: (
                      <Stack
                        onClick={e => e.stopPropagation()}
                        spacing={1}
                        divider={<Divider flexItem orientation="horizontal" />}
                      >
                        {_annotations.map(annotation => (
                          <AnnotationEntry key={JSON.stringify(annotation)} annotation={annotation} />
                        ))}
                      </Stack>
                    )
                  })
          }
          onMouseLeave={disableTooltip ? undefined : () => closeInfo('context', value)}
        >
          <Icon
            icon={icon}
            fontSize={otherProps.fontSize ?? '1.25em'}
            style={{ filter: 'drop-shadow(0px 0px 1px rgb(0 0 0 / 0.4))', ...(otherProps.style ?? {}) }}
            {...otherProps}
          />
        </span>
      )
    );
  }

  const additionalSize = contextAnnotations.length - additionalIcons.length;
  if (additionalSize > 0 && showExtraIcon) {
    icons.push(
      <CountBadge key="extra" disabled={!counters} count={additionalSize}>
        <Iconified icon="ic:baseline-newspaper" style={{ zIndex: 2, ...(otherProps.style ?? {}) }} />
      </CountBadge>
    );
  }

  return (
    <Stack direction="row" spacing={1}>
      {icons}
    </Stack>
  );
};

export default memo(ContextIcon);
