import { Typography } from '@mui/material';
import type { ActionResult, FetcherResult } from 'lib/main';
import ClueUIPlugin from '../ClueUIPlugin';

class TestPlugin extends ClueUIPlugin {
  name = 'TestPlugin';
  format = 'test';
  version = '0.0.1';
  author = 'Col. Mustard';
  description = 'This plugin is a test.';

  actionResult(_props: { result: ActionResult }) {
    return <Typography variant="h1">{'Test Plugin!'}</Typography>;
  }

  fetcherResult(_props: { result: FetcherResult }) {
    return <Typography variant="h1">{'Test Plugin!'}</Typography>;
  }
}
export default TestPlugin;
