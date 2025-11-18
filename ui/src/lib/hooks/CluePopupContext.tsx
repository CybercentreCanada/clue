import type { PopoverProps } from '@mui/material';
import AnnotationDetailPopover from 'lib/components/AnnotationDetailPopover';
import AnnotationPreview from 'lib/components/AnnotationPreview';
import { HIDE_EVENT_ID, SHOW_EVENT_ID } from 'lib/data/event';
import type { Annotation, Selector } from 'lib/types/lookup';
import { safeAddEventListener, safeDispatchEvent } from 'lib/utils/window';
import isNull from 'lodash-es/isNull';
import type { FC, PropsWithChildren } from 'react';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createContext } from 'use-context-selector';

type PopupType = 'details' | 'actionResults' | Annotation['type'];

export interface ShowInfoOptions {
  content?: React.ReactNode;
  onClose?: () => void;
  popoverProps?: Omit<PopoverProps, 'open'>;
}

export interface CluePopupContextType {
  showInfo: (type: PopupType, anchorEl: HTMLElement, value: Selector, options?: ShowInfoOptions) => void;

  closeInfo: (type: PopupType, value: Selector) => void;

  __detailsContent: React.ReactNode | null;
}

export interface PopupEventType {
  type: PopupType;
  value: Selector;
  anchorEl: HTMLElement;
  options?: ShowInfoOptions;
}

export const CluePopupContext = createContext<CluePopupContextType>(null);

export const CluePopupProvider: FC<PropsWithChildren> = ({ children }) => {
  const [popupType, setPopupType] = useState<PopupType | null>(null);
  const [detailsAnchorEl, setDetailsAnchorEl] = useState<HTMLElement | null>(null);
  const [detailsData, setDetailsData] = useState<Selector | null>(null);
  const [detailsContent, setDetailsContent] = useState<React.ReactNode>(null);
  const [popoverProps, setPopoverProps] = useState<Omit<PopoverProps, 'open'>>({});

  const externalOnClose = useRef<() => void>(null);

  const showInfo: CluePopupContextType['showInfo'] = useCallback((type, anchorEl, value, options) => {
    safeDispatchEvent(
      new CustomEvent(SHOW_EVENT_ID, {
        detail: {
          type,
          anchorEl,
          value,
          options
        }
      })
    );
  }, []);

  const closeInfo: CluePopupContextType['closeInfo'] = useCallback(
    (type, value) => {
      safeDispatchEvent(
        new CustomEvent(HIDE_EVENT_ID, {
          detail: {
            type,
            value
          }
        })
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const handleShowPopup = useCallback((event: CustomEvent<PopupEventType>) => {
    const { detail } = event;
    setPopupType(detail.type);
    setDetailsData(detail.value);
    if (detail.options) {
      if (detail.options.content) {
        setDetailsContent(detail.options.content);
      }

      if (detail.options.onClose) {
        externalOnClose.current = detail.options.onClose;
      }

      if (detail.options.popoverProps) {
        setPopoverProps(detail.options.popoverProps);
      }
    }
    setDetailsAnchorEl(detail.anchorEl);
  }, []);

  const handleHidePopup = useCallback(
    (event: CustomEvent<PopupEventType>) => {
      const { detail } = event;
      // check to see if the state of the popover has changed
      if (
        detailsData &&
        (detail.type !== popupType ||
          detailsData.type !== detail.value.type ||
          detailsData.value !== detail.value.value)
      ) {
        return;
      }

      setPopupType(null);
      setDetailsAnchorEl(null);
      setDetailsData(null);
      setDetailsContent(null);
      setPopoverProps({});
      externalOnClose.current = null;
    },
    [detailsData, popupType]
  );

  useEffect(() => {
    const cleanupShow = safeAddEventListener(SHOW_EVENT_ID, handleShowPopup);
    const cleanupHide = safeAddEventListener(HIDE_EVENT_ID, handleHidePopup);

    return () => {
      cleanupShow();
      cleanupHide();
    };
  }, [handleShowPopup, handleHidePopup]);

  const context = useMemo(
    () => ({
      showInfo,
      closeInfo,
      __detailsContent: detailsContent
    }),
    [closeInfo, detailsContent, showInfo]
  );

  return (
    <CluePopupContext.Provider value={context}>
      {children}
      <AnnotationDetailPopover
        {...popoverProps}
        anchorEl={detailsAnchorEl}
        open={!!detailsAnchorEl && popupType === 'details'}
        enrichRequest={detailsData}
        onClose={() => {
          if (externalOnClose.current) {
            externalOnClose.current();
          } else {
            closeInfo('details', detailsData);
          }
        }}
      />
      <AnnotationPreview
        {...popoverProps}
        anchorEl={detailsAnchorEl}
        open={!!detailsAnchorEl && !isNull(popupType) && popupType !== 'details'}
        annotationType={popupType as Exclude<typeof popupType, 'details'>}
        enrichRequest={detailsData}
      />
    </CluePopupContext.Provider>
  );
};
