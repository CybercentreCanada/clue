import Graph from 'lib/components/display/graph';
import type { ActionResult } from 'lib/types/action';
import type { FetcherResult } from 'lib/types/fetcher';
import type { NestedDataset } from 'lib/types/graph';
import ClueUIPlugin from '../ClueUIPlugin';
import { validateJsonData } from '../utils';
import tree_example from './example/tree.json';

class GraphPlugin extends ClueUIPlugin {
  name = 'GraphPlugin';
  format = 'graph';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security Matthew.Rafuse@cyber.gc.ca';
  description = 'Renders an interactive tree visualization.';

  actionResult({ result }: { result: ActionResult }) {
    const json = validateJsonData(result.output);

    return <Graph graph={json as NestedDataset} sx={{ minHeight: '600px' }} />;
  }

  fetcherResult({ result }: { result: FetcherResult }) {
    const json = validateJsonData(result.data);

    return <Graph graph={json as NestedDataset} sx={{ minHeight: '600px' }} />;
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
