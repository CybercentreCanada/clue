import JSONViewer from 'lib/components/display/json';
import type { ActionResult, FetcherResult } from 'lib/main';
import ClueUIPlugin from '../ClueUIPlugin';
import { validateJsonData } from '../utils';

class JsonPlugin extends ClueUIPlugin {
  name = 'JsonPlugin';
  format = 'json';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security Matthew.Rafuse@cyber.gc.ca';
  description =
    'Renders JSON with the default renderer or the overridden json component defined in the clue component provider.';

  actionResult({ result }: { result: ActionResult }) {
    const json = validateJsonData(result.output);
    if (json !== null && json !== undefined) {
      return <JSONViewer data={json} collapse forceCompact />;
    }
    return null;
  }

  fetcherResult({ result }: { result: FetcherResult }) {
    const json = validateJsonData(result.data);
    if (json !== null && json !== undefined) {
      return <JSONViewer data={json} collapse forceCompact />;
    }
    return null;
  }

  editorLanguage() {
    return 'json';
  }

  exampleInput() {
    return '{ "key": "value" }';
  }

  documentation() {
    return `This plugin renders JSON. It can be used by specifying "json" as the format in the plugin configuration. The input should be a JSON object or a stringified JSON.`;
  }
}
export default JsonPlugin;
