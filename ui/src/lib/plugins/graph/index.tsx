import Graph from 'lib/components/display/graph';
import type { ActionResult, FetcherResult } from 'lib/main';
import tree_example from '../../components/routes/examples/tree.json';
import ClueUIPlugin from '../ClueUIPlugin';

class GraphPlugin extends ClueUIPlugin {
  name = 'GraphPlugin';
  format = 'graph';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security Matthew.Rafuse@cyber.gc.ca';
  description = 'Renders an interactive tree visualization.';

  actionResult({ result }: { result: ActionResult }) {
    let json = result.output;
    if (typeof json === 'string') {
      try {
        json = JSON.parse(json);
      } catch {
        // do nothing, just render the string as is
      }
    }
    return <Graph graph={json} sx={{ minHeight: '600px' }} />;
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
    return (
      <Graph
        graph={json}
        sx={{
          minHeight: '600px'
        }}
      />
    );
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
