import { Stack } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import type { FC } from 'react';
import FileResult from './FileResult';

const Result: FC<{ result: WithActionData<ActionResult> }> = ({ result }) => {
  if (result.format === 'markdown') {
    return <Markdown md={result.output} />;
  }

  if (result.format === 'json') {
    return <JSONViewer data={result.output} collapse forceCompact />;
  }

  if (result.format === 'file') {
    return <FileResult result={result} />;
  }

  return (
    <Stack sx={{ overflowY: 'auto' }}>
      <Markdown md={'`' + result.format + '` is not recognized as a format in this application.'} />
      <JSONViewer data={result} collapse forceCompact />
    </Stack>
  );
};

export default Result;
