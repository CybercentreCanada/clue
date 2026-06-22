import JSONViewer from 'lib/components/display/json';
import type { ActionResult, FetcherResult } from 'lib/main';
import ClueUIPlugin from '../ClueUIPlugin';

class JsonPlugin extends ClueUIPlugin {
  name = 'JsonPlugin';
  format = 'json';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security <some.email@cyber.gc.ca>';
  description =
    'Renders JSON with the default renderer or the overridden json component defined in the clue component provider.';

  actionResult({ result }: { result: ActionResult }) {
    let json = result.output;
    if (typeof json === 'string') {
      try {
        json = JSON.parse(json);
      } catch {
        // do nothing, just render the string as is
      }
    }
    return <JSONViewer data={json} collapse forceCompact />;
  }

  fetcherResult({ result }: { result: FetcherResult }) {
    let json = result.data;
    if (typeof json === 'string') {
      try {
        json = JSON.parse(json);
      } catch {
        // do nothing, just render the string as is
      }
    }
    return <JSONViewer data={json} />;
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
