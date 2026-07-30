import { Typography } from '@mui/material';
import type { ActionResult } from 'lib/types/action';
import type { FetcherResult } from 'lib/types/fetcher';
import ClueUIPlugin from '../ClueUIPlugin';

class TestPlugin extends ClueUIPlugin {
  name = 'TestPlugin';
  format = 'test';
  version = '0.0.1';
  author = 'Canadian Centre for Cyber Security Matthew.Rafuse@cyber.gc.ca';
  description = 'This plugin is a test.';

  actionResult(_props: { result: ActionResult }) {
    return <Typography variant="h1">{'Test Plugin!'}</Typography>;
  }

  fetcherResult(_props: { result: FetcherResult }) {
    return <Typography variant="h1">{'Test Plugin!'}</Typography>;
  }
}
export default TestPlugin;
