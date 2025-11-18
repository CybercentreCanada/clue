export const safeDispatchEvent = (event: Event) => {
  // Ensuring window exists (may be missing in some test environments, in some circumstances)
  if (typeof window === 'undefined') {
    return;
  }

  window.dispatchEvent(event);
};

export const safeRemoveEventListener = (
  type: string,
  listener: (this: Window, ev: any) => any,
  options?: boolean | EventListenerOptions
) => {
  // Ensuring window exists (may be missing in some test environments, in some circumstances)
  if (typeof window === 'undefined') {
    return;
  }

  window.removeEventListener(type, listener, options);
};

export const safeAddEventListener = (
  type: string,
  listener: (this: Window, ev: any) => any,
  options?: boolean | AddEventListenerOptions
) => {
  // Ensuring window exists (may be missing in some test environments, in some circumstances)
  if (typeof window === 'undefined') {
    return;
  }

  window.addEventListener(type, listener, options);

  return () => safeRemoveEventListener(type, listener, options);
};
