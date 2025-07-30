/* eslint-disable react/jsx-no-literals */
import type { SxProps, Theme } from '@mui/material';
import { Card, CardContent, Collapse, Divider, Stack, Typography } from '@mui/material';
import { flatten } from 'flat';
import type { RawEntry } from 'lib/types/graph';
import { cssImportant } from 'lib/utils/graph';
import omit from 'lodash-es/omit';
import type { FC } from 'react';
import { Fragment, useCallback, useEffect, useState } from 'react';
import Iconified from '../../icons/Iconified';
import JSONViewer from '../../json';
import Markdown from '../../markdown';
import ExpandMoreButton from '../ExpandMoreButton';
import NodeTag from './NodeTag';

interface NodeCardOptions {
  node: RawEntry;
  sx?: SxProps<Theme>;
}

const NodeCard: FC<NodeCardOptions> = ({ node, sx = {} }: NodeCardOptions) => {
  const [expanded, setExpanded] = useState(false);
  const [nodeExtraData, setNodeExtraData] = useState<{ [index: string]: any }>();

  const handleExpandClick = () => {
    setExpanded(!expanded);
  };

  useEffect(() => {
    setNodeExtraData(omit(node, ['id', 'edges']));
  }, [node]);

  const renderEdgeList = useCallback((edgeIds: string[]) => {
    return (
      <Stack alignSelf="stretch">
        <Typography textAlign="left" variant="body2" color="text.secondary">
          Edges
        </Typography>
        <Stack spacing={0.25}>
          {edgeIds.map(edgeId => (
            <NodeTag key={edgeId} nodeId={edgeId} />
          ))}
        </Stack>
      </Stack>
    );
  }, []);

  return (
    <Card
      variant="outlined"
      sx={{
        position: 'relative',
        overflow: 'auto',
        zIndex: expanded ? 100 : 'initial',
        '& *': {
          opacity: 1
        },
        ...sx
      }}
    >
      <CardContent sx={{ p: 1 }}>
        <Stack
          spacing={1}
          sx={{
            textAlign: 'left',
            wordBreak: 'break-all',
            '& pre': {
              whiteSpace: 'pre-wrap'
            }
          }}
        >
          <NodeTag nodeId={node.id} label={node.id} type="header">
            <ExpandMoreButton
              expand={expanded}
              onClick={handleExpandClick}
              aria-expanded={expanded}
              aria-label="show more"
              size="small"
            >
              <Iconified icon="ic:baseline-expand-more" fontSize="medium" />
            </ExpandMoreButton>
          </NodeTag>
          {node.markdown && (
            <>
              <Divider flexItem />
              <Markdown md={node.markdown} components={flatten(node)} />
            </>
          )}
          {!!node?.edges?.length && (
            <Fragment>
              <Divider flexItem />
              {renderEdgeList(node?.edges)}
            </Fragment>
          )}
          <Collapse in={expanded} timeout="auto">
            <Stack
              justifyContent="start"
              alignItems="start"
              spacing={1}
              sx={theme => ({
                '& > ul': {
                  width: '100%',
                  textAlign: 'left',
                  p: cssImportant(theme.spacing(1)),
                  mx: cssImportant('0'),
                  backgroundColor: cssImportant(theme.palette.background.paper)
                }
              })}
            >
              <Divider flexItem />
              <Typography textAlign="left" variant="body1">
                Metadata:
              </Typography>
              <JSONViewer data={nodeExtraData} />
            </Stack>
          </Collapse>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default NodeCard;
