export const validateJsonData = (data: unknown): object => {
  let json: unknown = data;

  if (typeof json === 'string') {
    try {
      json = JSON.parse(json);
    } catch (err) {
      // failed to parse json string
      throw new Error(`Failed to parse JSON string: ${String(err)}`, {
        cause: err instanceof Error ? err : undefined
      });
    }
  }

  if (json === null || typeof json !== 'object') {
    // can only parse objects or json objects as strings
    throw new Error(`Input must be a JSON object or a JSON object encoded as a string. Got: ${typeof data}`);
  }

  return json;
};
