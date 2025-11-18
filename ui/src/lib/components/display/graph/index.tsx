import type { StackProps } from '@mui/material';
import {
  alpha,
  Autocomplete,
  Card,
  Collapse,
  darken,
  FormControl,
  IconButton,
  InputLabel,
  lighten,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  useTheme
} from '@mui/material';
import { parseEvent } from 'commons/components/utils/keyboard';
import * as d3 from 'd3';
import useComparator from 'lib/hooks/useComparator';
import { useMyLocalStorageItem } from 'lib/hooks/useMyLocalStorage';
import type { NestedDataset } from 'lib/types/graph';
import { StorageKey } from 'lib/utils/constants';
import get from 'lodash-es/get';
import type { FC, KeyboardEventHandler } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { cssImportant } from '../../../utils/graph';
import Iconified from '../icons/Iconified';
import ExpandMoreButton from './ExpandMoreButton';
import Cloud from './visualizations/cloud';
import NodePanel from './visualizations/panels/NodePanel';
import Tree from './visualizations/tree';

const Graph: FC<{ graph: NestedDataset; sx?: StackProps['sx'] }> = ({ graph, sx = {} }) => {
  const theme = useTheme();
  const isDark = useMemo(() => theme.palette.mode === 'dark', [theme]);
  const { runComparator } = useComparator();

  const svgRef = useRef<SVGSVGElement>();
  const pointRef = useRef<DOMPoint>();

  const [showMousePos] = useMyLocalStorageItem(StorageKey.SHOW_MOUSE_POS, false);
  const [showCoordinates] = useMyLocalStorageItem(StorageKey.SHOW_COORDINATES, false);
  const [panelLocation] = useMyLocalStorageItem(StorageKey.PANEL_LOCATION, 'vertical');
  const [relativeMousePos, setRelativeMousePos] = useState<[string, string]>(['0', '0']);
  const [absoluteMousePos, setAbsoluteMousePos] = useState<[string, string]>(['0', '0']);
  const [showPanel, setShowPanel] = useState(false);

  const nodeIds = useMemo(() => (graph?.data ?? []).flat(2).map(node => node.id), [graph?.data]);
  const zoom = useMemo(() => d3.zoom().scaleExtent([0.1, 6]), []);

  const [currentZoom, setCurrentZoom] = useState<d3.ZoomTransform>(d3.zoomIdentity);
  const [nodeId, setNodeId] = useState('');
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [viz, setViz] = useState<keyof typeof visualizations>(
    (graph?.metadata.display?.visualization?.type as keyof typeof visualizations) ?? 'tree'
  );
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setShowPanel(selectedNodeIds.length > 0);
  }, [selectedNodeIds]);

  const labelKeys = useMemo(
    () =>
      graph?.metadata.display?.displayField?.filter(entry => (entry.zoom ?? Number.MAX_SAFE_INTEGER) > currentZoom.k),
    [graph?.metadata.display?.displayField, currentZoom.k]
  );

  const onNodeChange = useCallback(node => {
    setNodeId(node);
  }, []);

  const checkForNode = useCallback((_nodeId: string) => {
    const selector = _nodeId === 'view' ? _nodeId : `node-${_nodeId ?? 'will\\%never\\$ever\\*exist'}`;

    return d3.select<SVGGElement, unknown>(`#${selector}`);
  }, []);

  const selectNode = useCallback(() => {
    if (!nodeId) {
      setHasError(true);
      return;
    }

    const nodeToGet = checkForNode(nodeId.replace(/[^A-Za-z0-9]*/g, ''));
    if (nodeToGet.empty()) {
      setHasError(true);
      return;
    }

    setHasError(false);
    setSelectedNodeIds([nodeId]);

    const clientRect = svgRef.current.getBoundingClientRect();

    const svg = d3.select(svgRef.current);
    const box = nodeToGet.node().getBBox();

    svg
      .transition()
      .duration(500)
      .call(
        zoom.transform,
        d3.zoomIdentity
          .translate(clientRect.width / 2, clientRect.height / 2)
          .scale(4)
          .translate(-box.x, -box.y)
      );

    // svg.call(zoom.transform, d3.zoomIdentity.translate(-box.x, -box.y));
  }, [checkForNode, nodeId, zoom.transform]);

  const onKeyPress: KeyboardEventHandler<HTMLDivElement> = useCallback(
    event => {
      const parsedEvent = parseEvent(event);
      if (parsedEvent.isCtrl && parsedEvent.isEnter) {
        selectNode();
      }
    },
    [selectNode]
  );

  const findNode = useCallback(id => (graph?.data ?? []).flat().find(n => n.id === id), [graph?.data]);

  const resetZoom = useCallback(
    (instant = false) => {
      if (!graph) {
        return;
      }
      const box = d3.select(svgRef.current).select<SVGGElement>('#view').node().getBBox();

      const clientRect = svgRef.current.getBoundingClientRect();

      const zoomLevel = Math.min(clientRect.width / (box.width + 25), (clientRect.height - 96) / box.height);

      let selection = d3.select<SVGElement, any>(svgRef.current);
      if (!instant) {
        selection = selection.transition().duration(500) as any;
      }

      selection.call(
        zoom.transform,
        d3.zoomIdentity
          .translate(clientRect.width / 2, (clientRect.height + 96) / 2)
          .scale(zoomLevel)
          .translate(-box.width / 2, -box.height / 2 - 10)
      );
    },
    [zoom.transform, graph]
  );

  const onNodeSelectionChanged = useCallback(_nodeIds => setSelectedNodeIds(_nodeIds), []);

  useEffect(() => {
    if (!graph) {
      return;
    }
    pointRef.current = svgRef.current.createSVGPoint();

    d3.select(svgRef.current).call(
      zoom.on('zoom', event => {
        setCurrentZoom?.(event.transform);
        d3.select(svgRef.current).select('#view').attr('transform', event.transform);
      })
    );
  }, [setCurrentZoom, zoom, viz, graph]);

  useEffect(() => {
    if (showMousePos) {
      d3.select(svgRef.current).on('mousemove', event => {
        const _zoom = d3.zoomTransform(d3.select(svgRef.current).select<SVGGElement>('#view').node());
        setAbsoluteMousePos(_zoom.invert(d3.pointer(event)).map(n => n.toFixed(0)) as [string, string]);
        setRelativeMousePos(d3.pointer(event).map(n => n.toFixed(0)) as [string, string]);
      });
    }
  }, [showMousePos, graph]);

  useEffect(() => {
    resetZoom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viz, graph?.data]);

  useEffect(() => {
    if (graph?.metadata.display?.visualization?.type) {
      setViz(graph?.metadata.display?.visualization?.type as keyof typeof visualizations);
    }
  }, [graph?.metadata.display?.visualization?.type]);

  const treeOptions = useMemo(
    () => ({
      textColor: theme.palette.text.primary,
      backgroundColor: theme.palette.background.paper,
      nodeColor: {
        border: (isDark ? lighten : darken)(theme.palette.background.paper, 0.3),
        center: 'white'
      }
    }),
    [isDark, theme.palette.background.paper, theme.palette.text.primary]
  );

  const cloudOptions = useMemo(
    () => ({
      textColor: theme.palette.text.primary,
      backgroundColor: theme.palette.background.paper,
      nodeColor: {
        border: (isDark ? lighten : darken)(theme.palette.background.paper, 0.3),
        center: 'white'
      }
    }),
    [isDark, theme.palette.background.paper, theme.palette.text.primary]
  );

  const visualizations = useMemo(
    () => ({
      tree: () => (
        <Tree
          svgRef={svgRef}
          graph={graph}
          labelKeys={labelKeys}
          onNodeSelectionChanged={onNodeSelectionChanged}
          zoom={currentZoom}
          options={treeOptions}
        />
      ),
      cloud: () => <Cloud svgRef={svgRef} graph={graph} options={cloudOptions} />
    }),
    [cloudOptions, currentZoom, graph, labelKeys, onNodeSelectionChanged, treeOptions]
  );

  const suggestions: { id: string; value: string }[] = useMemo(() => {
    return nodeIds.flatMap((id: string) => {
      const node = (graph?.data?.flat() ?? []).find(_node => _node.id === id);

      if (!node) {
        return { id, value: id };
      }

      const key = labelKeys?.filter(comparator => runComparator(comparator, node)).pop()?.label ?? 'id';

      const value = key
        .split(',')
        .map(_key => get(node, _key)?.toString())
        .filter(val => !!val)
        .map(_value => ({ id, value: _value.trim() }));

      return value;
    });
  }, [graph?.data, labelKeys, nodeIds, runComparator]);

  return (
    <Stack
      direction={panelLocation === 'vertical' ? 'row' : 'column'}
      spacing={1}
      overflow="hidden"
      height="100%"
      width="100%"
      sx={sx}
    >
      <Stack direction="column" spacing={1} sx={{ position: 'relative', flex: 1 }}>
        <Card
          variant="outlined"
          sx={{
            flex: 1,
            position: 'relative',
            maxHeight: `calc(100vh - 64px - ${theme.spacing(1)})`,
            '& #viz': {
              maxHeight: `calc(100vh - 64px - ${theme.spacing(1)})`,
              width: '100%',
              height: '100%',
              backgroundColor: theme.palette.background.paper
            },
            '& .path': {
              transition: theme.transitions.create(['opacity'], {
                duration: theme.transitions.duration.short
              })
            },
            '& .node': {
              cursor: 'pointer',
              '& > path, & > text, & > polygon, & circle': {
                transition: theme.transitions.create(['stroke', 'fill', 'fill-opacity', 'stroke-opacity'], {
                  duration: theme.transitions.duration.short
                })
              },
              '&.hover > .center': {
                stroke: cssImportant(theme.palette.primary.main)
              },
              '&.hover > .border': {
                stroke: cssImportant(theme.palette.primary.dark)
              },
              '&.selected > .center': {
                stroke: cssImportant(theme.palette.success.main)
              },
              '&.selected > .border': {
                stroke: cssImportant(theme.palette.success.dark)
              },
              '&.selected.hover > .center': {
                stroke: cssImportant(theme.palette.primary.main)
              },
              '&.selected.hover > .border': {
                stroke: cssImportant(theme.palette.primary.dark)
              }
            }
          }}
        >
          {graph ? (
            visualizations[viz]()
          ) : (
            <>
              <svg id="viz" ref={svgRef}>
                <g id="view" />
              </svg>
              <Typography
                variant="h1"
                color="text.secondary"
                sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  opacity: 0.3,
                  transform: 'translateX(-50%) translateY(-50%)'
                }}
              >
                No dataset has been selected!
              </Typography>
            </>
          )}
          <Stack
            direction="column"
            spacing={1}
            sx={{
              position: 'absolute',
              top: theme.spacing(1),
              left: theme.spacing(1),
              right: theme.spacing(1)
            }}
          >
            <Stack
              direction="row"
              spacing={1}
              sx={{
                '& > div:first-of-type': {
                  flex: 1,
                  maxWidth: '775px',
                  backgroundColor: alpha(theme.palette.background.paper, 0.8)
                }
              }}
            >
              <Autocomplete
                disablePortal
                onChange={(__, value) => onNodeChange(value.id)}
                onKeyDown={onKeyPress}
                options={suggestions}
                sx={{ width: '400px' }}
                getOptionLabel={option => option.value}
                filterOptions={(options, state) =>
                  options.filter(opt => opt.value.toLowerCase().includes(state.inputValue))
                }
                renderOption={(props, option) => (
                  <li {...props} key={option.id + option.value}>
                    {option.value}
                  </li>
                )}
                renderInput={params => (
                  <TextField
                    {...params}
                    error={hasError}
                    label="Enter a node ID, and press [ctrl + enter] to select it. [ctrl + space] will open an autocomplete menu."
                  />
                )}
              />
              <FormControl sx={{ minWidth: '150px', backgroundColor: alpha(theme.palette.background.paper, 0.8) }}>
                <InputLabel id="viz-label">Visualization</InputLabel>
                <Select
                  label="Visualization"
                  labelId="viz-label"
                  value={viz}
                  onChange={event => setViz(event.target.value as 'tree' | 'cloud')}
                  sx={{ textTransform: 'capitalize' }}
                >
                  {Object.keys(visualizations).map(_viz => (
                    <MenuItem key={_viz} value={_viz} sx={{ textTransform: 'capitalize' }}>
                      {_viz}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <ExpandMoreButton
                disabled={selectedNodeIds.length < 1}
                expand={showPanel}
                onClick={() => setShowPanel(!showPanel)}
                aria-expanded={showPanel}
                aria-label="show more"
                size="small"
                sx={{
                  marginLeft: 'auto !important',
                  alignSelf: 'center'
                }}
              >
                <Iconified
                  icon={panelLocation === 'vertical' ? 'ic:baseline-chevron-left' : 'ic:baseline-expand-more'}
                  fontSize="medium"
                />
              </ExpandMoreButton>
            </Stack>
          </Stack>

          <Card
            variant={showCoordinates ? 'elevation' : 'outlined'}
            elevation={showCoordinates ? 4 : 0}
            sx={{
              position: 'absolute',
              bottom: theme.spacing(0.5),
              right: theme.spacing(0.5),
              px: 1,
              py: 0.5,
              border: 'none !important'
            }}
          >
            <Stack direction="row" spacing={0.5} alignItems="center">
              {showCoordinates && (
                <span>
                  {currentZoom.x.toFixed(0)}, {currentZoom.y.toFixed(0)} ({currentZoom.k.toFixed(2)}x)
                </span>
              )}
              <IconButton
                size={showCoordinates ? 'small' : 'medium'}
                onClick={() => resetZoom()}
                disabled={currentZoom.k === d3.zoomIdentity.k && currentZoom.x === 0 && currentZoom.y === 0}
              >
                <Iconified icon="ic:baseline-refresh" fontSize={showCoordinates ? 'small' : 'medium'} />
              </IconButton>
            </Stack>
          </Card>
          {showMousePos && (
            <Card
              variant="elevation"
              elevation={4}
              sx={{
                position: 'absolute',
                bottom: theme.spacing(0.5),
                left: theme.spacing(0.5),
                px: 1,
                py: 0.5
              }}
            >
              <code>
                <Stack direction="row" spacing={1}>
                  <span>(abs: {absoluteMousePos.join(', ')})</span>
                  <span>(rel: {relativeMousePos.join(', ')})</span>
                </Stack>
              </code>
            </Card>
          )}
        </Card>
      </Stack>
      <Collapse
        in={showPanel && selectedNodeIds.length > 0}
        orientation={panelLocation === 'vertical' ? 'horizontal' : 'vertical'}
        appear
        unmountOnExit
      >
        <Stack
          direction="column"
          spacing={1}
          sx={panelLocation === 'vertical' ? { width: '450px', height: '100%' } : { width: '100%', height: '300px' }}
          pb={1}
        >
          <NodePanel selectedNodeIds={selectedNodeIds} findNode={findNode} />
        </Stack>
      </Collapse>
    </Stack>
  );
};

export default Graph;
