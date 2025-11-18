/**
 * Utility for logging debug messages if clue is configured to allow debug logging.
 * @param message The debug message.
 * @param loggingEnabled the flag to determine if debugging is enabled.
 */
export function clueDebugLogger(message: string, loggingEnabled: boolean) {
  if (loggingEnabled) {
    console.debug(message);
  }
}
