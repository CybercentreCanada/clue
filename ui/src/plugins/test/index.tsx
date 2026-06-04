import { Typography } from '@mui/material';
import type { ActionResult } from 'lib/main';
import type { WithActionData } from 'lib/types/WithActionData';
import ClueUIPlugin from '../CluePlugin';

class TestPlugin extends ClueUIPlugin {
  name = 'TestPlugin';
  format = 'none';
  version = '0.0.1';
  author = 'Col. Mustard';
  description = 'This plugin is a test.';

  render(_props: { result: WithActionData<ActionResult> }) {
    return <Typography variant="h1">{'Test Plugin!'}</Typography>;
  }
}
export default TestPlugin;
