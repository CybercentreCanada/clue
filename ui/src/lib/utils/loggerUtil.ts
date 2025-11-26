/**
 * Utility for logging debug messages if clue is configured to allow debug logging.
 * @param message The debug message.
 * @param loggingEnabled the flag to determine if debugging is enabled.
 */
export const clueDebugLogger = (message: string, loggingEnabled: boolean) => {
  if (loggingEnabled) {
    // eslint-disable-next-line no-console
    console.debug(message);
  }
};
