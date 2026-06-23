import Graph from 'lib/components/display/graph';
import type { ActionResult, FetcherResult } from 'lib/main';
import type { NestedDataset } from 'lib/types/graph';
import tree_example from '../../../components/routes/examples/tree.json';
import ClueUIPlugin from '../ClueUIPlugin';
import { validateJsonData } from '../utils';

class GraphPlugin extends ClueUIPlugin {
  name = 'GraphPlugin';
  format = 'graph';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security Matthew.Rafuse@cyber.gc.ca';
  description = 'Renders an interactive tree visualization.';

  actionResult({ result }: { result: ActionResult }) {
    const json = validateJsonData(result.output);
    if (json !== null && json !== undefined) {
      return <Graph graph={json as NestedDataset} sx={{ minHeight: '600px' }} />;
    }
    return null;
  }

  fetcherResult({ result }: { result: FetcherResult }) {
    const json = validateJsonData(result.data);
    if (json !== null && json !== undefined) {
      <Graph graph={json as NestedDataset} sx={{ minHeight: '600px' }} />;
    }
    return null;
  }

  editorLanguage() {
    return 'json';
  }

  exampleInput() {
    return JSON.stringify(tree_example, null, 2);
  }

  documentation() {
    return `This plugin renders an interactive tree visualization. It can be used by specifying "graph" as the format in the plugin configuration.`;
  }
}
export default GraphPlugin;
