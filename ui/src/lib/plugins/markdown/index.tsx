import Markdown from 'lib/components/display/markdown';
import type { ActionResult } from 'lib/types/action';
import type { FetcherResult } from 'lib/types/fetcher';
import ClueUIPlugin from '../ClueUIPlugin';

class MarkdownPlugin extends ClueUIPlugin {
  name = 'MarkdownPlugin';
  format = 'markdown';
  version = '1.0.0';
  author = 'Canadian Centre for Cyber Security Matthew.Rafuse@cyber.gc.ca';
  description = 'Renders Markdown.';

  actionResult({ result }: { result: ActionResult }) {
    return <Markdown md={result.output} />;
  }

  fetcherResult({ result }: { result: FetcherResult }) {
    return <Markdown md={result.data} />;
  }

  editorLanguage() {
    return 'markdown';
  }

  exampleInput() {
    return `# Markdown Plugin
This is an example of the Markdown plugin.
You can use **Markdown** syntax to format your text.`;
  }

  documentation() {
    return `This plugin renders Markdown. It can be used by specifying "markdown" as the format in the plugin configuration. The input should be a string in Markdown format.`;
  }
}
export default MarkdownPlugin;
