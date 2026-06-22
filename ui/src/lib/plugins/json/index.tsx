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
    return <JSONViewer data={result.output} collapse forceCompact />;
  }

  fetcherResult({ result }: { result: FetcherResult }) {
    return <JSONViewer data={result.data} />;
  }
}
export default JsonPlugin;
