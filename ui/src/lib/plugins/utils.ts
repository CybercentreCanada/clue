export const validateJsonData: (data: any) => object = (data: any) => {
  let json = data;
  if (typeof json === 'string') {
    try {
      json = JSON.parse(json);
    } catch (err) {
      // failed to parse json string
      throw new Error('Failed to parse JSON string: ', { cause: err });
    }
  }
  if (typeof json !== 'object') {
    // can only parse objects or json objects as strings
    throw new Error('Input must be string or object type. Cannot parse type : ' + typeof data);
  }
  return json;
};
