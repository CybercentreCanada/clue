import Graph from 'lib/components/display/graph';
import type { ActionResult, FetcherResult } from 'lib/main';
import ClueUIPlugin from '../ClueUIPlugin';

class GraphPlugin extends ClueUIPlugin {
  name = 'GraphPlugin';
  format = 'graph';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security <some.email@cyber.gc.ca>';
  description = 'Renders an interactive tree visualization.';

  actionResult({ result }: { result: ActionResult }) {
    return <Graph graph={result.output} sx={{ minHeight: '600px' }} />;
  }

  fetcherResult({ result }: { result: FetcherResult }) {
    return <Graph graph={result.data} sx={{ minHeight: '600px' }} />;
  }
}
export default GraphPlugin;
