import JSONViewer from 'lib/components/display/json';
import type { ActionResult } from 'lib/types/action';
import type { FetcherResult } from 'lib/types/fetcher';
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

    return <JSONViewer data={json} collapse forceCompact />;
  }

  fetcherResult({ result }: { result: FetcherResult }) {
    const json = validateJsonData(result.data);

    return <JSONViewer data={json} collapse forceCompact />;
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
