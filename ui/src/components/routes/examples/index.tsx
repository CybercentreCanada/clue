/* eslint-disable react/jsx-no-literals */
import {
  Box,
  Button,
  Checkbox,
  Divider,
  Drawer,
  Grid2 as Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from '@mui/material';
import PageCenter from 'commons/components/pages/PageCenter';
import Graph from 'lib/components/display/graph';
import JSONViewer from 'lib/components/display/json';
import EnrichedCard from 'lib/components/EnrichedCard';
import EnrichedChip from 'lib/components/EnrichedChip';
import EnrichedTypography from 'lib/components/EnrichedTypography';
import Entry from 'lib/components/group/Entry';
import Group from 'lib/components/group/Group';
import RetryFailedEnrichments from 'lib/components/RetryFailedEnrichments';
import range from 'lodash-es/range';
import moment from 'moment';
import type { FC } from 'react';
import { useMemo, useState } from 'react';
import { v4 } from 'uuid';
import process from './process.json';
import process_vertical from './process_vertical.json';
import tree from './tree.json';

const Examples: FC = () => {
  const [forceDetails, setForceDetails] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [forceDetailsTypo, setForceDetailsTypo] = useState(false);
  const ipExamples = useMemo(
    () =>
      ['ip'].flatMap(_type => {
        if (_type === 'ip') {
          return range(20).map(() => [
            _type,
            `${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(
              Math.random() * 256
            )}.${Math.floor(Math.random() * 256)}`
          ]);
        }

        return [];
      }),
    []
  );

  const telemetryRows = useMemo(
    () =>
      range(10).map(() => ({
        id: v4(),
        timestamp: moment().subtract(Math.random() * 1000, 'hours'),
        username: 'test',
        ip: `${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(
          Math.random() * 256
        )}.${Math.floor(Math.random() * 256)}`
      })),
    []
  );
  const [selectedRows, setSelectedRows] = useState<{ [index: string]: boolean }>({});

  const ipRows = useMemo(
    () =>
      range(10).map(() => ({
        id: v4(),
        timestamp: moment().subtract(Math.random() * 1000, 'hours'),
        username: 'test',
        ip: `${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}.${Math.floor(
          Math.random() * 256
        )}.${Math.floor(Math.random() * 256)}`
      })),
    []
  );
  const [selectedIps, setSelectedIps] = useState<{ [index: string]: boolean }>({});

  return (
    <PageCenter maxWidth="1800px" textAlign="left" height="100%">
      <Drawer anchor={'right'} open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        <Stack direction="column" spacing={2} sx={{ p: 2 }} alignItems="start">
          <EnrichedChip type="ip" value="170.150.213.62" counters />
          <EnrichedChip type="domain" value="google.ca" counters />
          <EnrichedChip
            type="sha256"
            value="f2b1393e2311844e994d7f5716cca64e46c6bba05eac9a303fb1a345ff702550"
            counters
          />
        </Stack>
      </Drawer>
      <Stack direction="column" spacing={2} sx={{ minHeight: '100%', pb: 100 }} alignItems="start">
        <Stack direction={'row'} sx={{ width: '100%' }}>
          <Typography variant="h3" sx={{ flex: 1 }}>
            Examples
          </Typography>
          <RetryFailedEnrichments />
          <Button onClick={() => setDrawerOpen(true)}>Open drawer</Button>
        </Stack>
        <Divider orientation="horizontal" flexItem />
        <Typography variant="h5">Chips</Typography>
        <EnrichedChip type="sha256" value="f2b1393e2311844e994d7f5716cca64e46c6bba05eac9a303fb1a345ff702550" />
        <EnrichedChip type="ip" value="127.0.0.1" />
        <EnrichedChip type="ip" value="212.211.37.125" />
        <EnrichedChip type="ip" value="43.238.136.170" />
        <Typography sx={{ pb: 0, mb: 0 }}>With counters:</Typography>
        <EnrichedChip type="ip" value="170.150.213.62" counters />
        <EnrichedChip type="domain" value="google.ca" counters />
        <EnrichedChip type="url" value="c00ca169ce4a800b805b8fbf0bb8e525-thing.baduser.org" counters />
        <EnrichedChip type="sha256" value="f2b1393e2311844e994d7f5716cca64e46c6bba05eac9a303fb1a345ff702550" counters />
        <Divider orientation="horizontal" flexItem />
        <Typography sx={{ pb: 0, mb: 0 }}>External details trigger:</Typography>
        <Stack direction="row" spacing={1}>
          <EnrichedChip
            type="ip"
            value="170.150.213.62"
            hideDetails
            forceDetails={forceDetails}
            setForceDetails={setForceDetails}
          />
          <Button onClick={() => setForceDetails(true)}>Show details</Button>
        </Stack>
        <EnrichedChip type="ip" value="170.150.213.62" hideDetails useDetailsIcon />
        <Stack direction="row" spacing={1}>
          <EnrichedTypography
            type="ip"
            value="170.150.213.62"
            hideDetails
            forceDetails={forceDetailsTypo}
            setForceDetails={val => setForceDetailsTypo(val)}
          />
          <Button onClick={() => setForceDetailsTypo(true)}>Show details</Button>
        </Stack>
        <EnrichedTypography type="ip" value="170.150.213.62" hideDetails useDetailsIcon />
        <Divider orientation="horizontal" flexItem />
        <Typography sx={{ pb: 0, mb: 0 }}>Customized:</Typography>
        <EnrichedChip
          type="ip"
          value="170.150.213.62"
          counters
          variant="filled"
          color="warning"
          sx={{ '& p': { color: 'green', fontWeight: 'bold' } }}
        />
        <EnrichedChip type="ip" value="170.150.213.62" counters color="success" sx={{ width: '100%' }} />
        <EnrichedChip type="domain" value="google.ca" size="small" />
        <Divider orientation="horizontal" flexItem />
        <Typography variant="h5">Typography</Typography>
        <EnrichedTypography type="sha256" value="f2b1393e2311844e994d7f5716cca64e46c6bba05eac9a303fb1a345ff702550" />
        <EnrichedTypography type="ip" value="127.0.0.1" />
        <EnrichedTypography type="ip" value="212.211.37.125" />
        <EnrichedTypography type="ip" value="43.238.136.170" />
        <Typography sx={{ pb: 0, mb: 0 }}>With counters:</Typography>
        <EnrichedTypography type="ip" value="170.150.213.62" counters />
        <EnrichedTypography type="domain" value="google.ca" counters />
        <EnrichedTypography type="url" value="c00ca169ce4a800b805b8fbf0bb8e525-thing.baduser.org" counters />
        <Divider orientation="horizontal" flexItem />
        <Typography sx={{ pb: 0, mb: 0 }}>Customized:</Typography>
        <EnrichedTypography
          type="ip"
          value="170.150.213.62"
          color="warning"
          sx={{ color: 'green', fontWeight: 'bold' }}
        />
        <EnrichedTypography
          type="ip"
          value="170.150.213.62"
          counters
          sx={theme => ({ width: '100%', color: theme.palette.warning.main })}
        />
        <Typography variant="caption">Using slotProps to style the stack:</Typography>
        <EnrichedTypography
          type="ip"
          value="170.150.213.62"
          counters
          sx={theme => ({ width: '100%', color: theme.palette.warning.main })}
          slotProps={{ stack: { sx: { p: 1, pr: 10, border: 'thin solid white' } } }}
        />
        <EnrichedChip
          type="ip"
          value="170.150.213.62"
          label="An example of a chip using custom text"
          counters
          variant="outlined"
        />
        <EnrichedTypography
          slotProps={{
            stack: { sx: { width: 'fit-content' } },
            popover: {
              anchorOrigin: { horizontal: 'right', vertical: 'bottom' },
              transformOrigin: { horizontal: 'right', vertical: 'top' }
            }
          }}
          fontSize="unset"
          type="ip"
          value="127.0.0.1"
          hideDetails
          useDetailsIcon
        >
          Here&apos;s typography with test text in it that is very very long and very cool and chill for testing anchor
          origin changes - Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut
          labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut
          aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
          eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt
          mollit anim id est laborum.
        </EnrichedTypography>

        <Divider orientation="horizontal" flexItem />
        <Typography sx={{ pb: 0, mb: 0 }}>Additional Data:</Typography>
        <EnrichedTypography type="url" value="determine.ca" />
        <EnrichedTypography type="url" value="invite.com" />
        <EnrichedTypography type="ip" value="68.182.65.42" />
        <Divider orientation="horizontal" flexItem />
        <EnrichedTypography type="ip" value="47.92.109.95" />
        <EnrichedChip type="ip" value="47.92.109.95" />
        <EnrichedTypography type="ip" value="47.92.109.95" />
        <EnrichedChip type="ip" value="47.92.109.95" />
        <Divider orientation="horizontal" flexItem />
        <EnrichedTypography type="ip" value="60.82.56.85" />
        <EnrichedTypography type="domain" value="cyber.gc.ca" />
        <EnrichedTypography type="url" value="https://cyber.gc.ca" />
        <EnrichedTypography type="ip" value="20.151.96.73" />

        <EnrichedCard type="ip" value="212.211.37.125" />

        <Typography sx={{ pb: 0, mb: 0 }}>Case Sensitivity Tests:</Typography>
        <EnrichedChip type="domain" value="google.ca" counters />
        <EnrichedChip type="domain" value="GOOGLE.CA" counters />
        <EnrichedChip type="DOMAIN" value="GOOGLE.CA" counters />
        <EnrichedChip type="DOMAIN" value="google.ca" counters />

        <Divider orientation="horizontal" flexItem />
        <Typography sx={{ pb: 0, mb: 0 }}>Bulk Data:</Typography>
        <Grid container spacing={1}>
          {ipExamples.map(([type, value]) => (
            <Grid key={value}>
              <EnrichedChip size="small" type={type} value={value} />
            </Grid>
          ))}
        </Grid>
        <Divider orientation="horizontal" flexItem />
        <Typography variant="h5" sx={{ pb: 0, mb: 0 }}>
          Grouped (IP) Example:
        </Typography>
        <Group type="ip">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <Checkbox
                    checked={ipRows.every(row => selectedIps[row.id])}
                    onChange={(__, checked) =>
                      setSelectedIps(ipRows.reduce((acc, row) => ({ ...acc, [row.id]: checked }), {}))
                    }
                  />
                </TableCell>
                <TableCell>ID</TableCell>
                <TableCell>Timestamp</TableCell>
                <TableCell>Username</TableCell>
                <TableCell>IP</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {ipRows.map(row => (
                <Entry key={row.id} entry={row.ip} selected={!!selectedIps[row.id]}>
                  <TableRow key={row.id}>
                    <TableCell>
                      <Checkbox
                        checked={!!selectedIps[row.id]}
                        onChange={(__, checked) => setSelectedIps(_selected => ({ ..._selected, [row.id]: checked }))}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography>{row.id}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography>{row.timestamp.toString()}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography>{row.username}</Typography>
                    </TableCell>
                    <TableCell>
                      <Box display="flex" justifyContent="start">
                        <EnrichedTypography skipEnrichment value={row.ip} />
                      </Box>
                    </TableCell>
                  </TableRow>
                </Entry>
              ))}
            </TableBody>
          </Table>
        </Group>

        <Typography variant="h5" sx={{ pb: 0, mb: 0 }}>
          Grouped (Telemetry) Example:
        </Typography>
        <Group type="telemetry">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <Checkbox
                    checked={telemetryRows.every(row => selectedRows[row.id])}
                    onChange={(__, checked) =>
                      setSelectedRows(telemetryRows.reduce((acc, row) => ({ ...acc, [row.id]: checked }), {}))
                    }
                  />
                </TableCell>
                <TableCell>ID</TableCell>
                <TableCell>Timestamp</TableCell>
                <TableCell>Username</TableCell>
                <TableCell>IP</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {telemetryRows.map(row => (
                <Entry key={row.id} entry={row} selected={!!selectedRows[row.id]}>
                  <TableRow key={row.id}>
                    <TableCell>
                      <Checkbox
                        checked={!!selectedRows[row.id]}
                        onChange={(__, checked) => setSelectedRows(_selected => ({ ..._selected, [row.id]: checked }))}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography>{row.id}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography>{row.timestamp.toString()}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography>{row.username}</Typography>
                    </TableCell>
                    <TableCell>
                      <Box display="flex" justifyContent="start">
                        <EnrichedTypography skipEnrichment value={row.ip} />
                      </Box>
                    </TableCell>
                  </TableRow>
                </Entry>
              ))}
            </TableBody>
          </Table>
        </Group>

        <JSONViewer data={{ potato: 'test' }} />

        <Graph sx={{ minHeight: '750px' }} graph={tree as any} />

        <Graph sx={{ minHeight: '750px' }} graph={process as any} />

        <Graph sx={{ minHeight: '750px' }} graph={process_vertical as any} />
      </Stack>
    </PageCenter>
  );
};

export default Examples;
