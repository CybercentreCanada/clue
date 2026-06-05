import Markdown from 'lib/components/display/markdown';
import type { ActionResult, FetcherResult } from 'lib/main';
import ClueUIPlugin from '../ClueUIPlugin';

class MarkdownPlugin extends ClueUIPlugin {
  name = 'MarkdownPlugin';
  format = 'markdown';
  version = '1.0.0';
  author = 'Professor Plum';
  description = 'Renders Markdown.';

  renderActionResult({ result }: { result: ActionResult }) {
    return <Markdown md={result.output} />;
  }

  renderFetcherResult({ result }: { result: FetcherResult }) {
    return <Markdown md={result.data} />;
  }
}
export default MarkdownPlugin;
