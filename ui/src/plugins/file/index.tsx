import FileResult from 'lib/components/actions/formats/FileResult';
import type { ActionResult } from 'lib/main';
import type { WithActionData } from 'lib/types/WithActionData';
import ClueUIPlugin from '../ClueUIPlugin';

class FilePlugin extends ClueUIPlugin {
  name = 'FilePlugin';
  format = 'file';
  version = '1.0.0';
  author = 'Miss Scarlett';
  description = 'Render a file action result with metadata, hash statistics, and download support.';

  actionResult({ result }: { result: WithActionData<ActionResult> }) {
    return <FileResult result={result} />;
  }
}
export default FilePlugin;
