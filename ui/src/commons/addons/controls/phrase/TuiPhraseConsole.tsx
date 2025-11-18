import { FilterAlt } from '@mui/icons-material';
import { Chip, darken, lighten, Paper, Stack, Typography, useTheme } from '@mui/material';
import { MuiColorType } from 'commons/addons';
import { useCallback } from 'react';
import { v4 as uuid } from 'uuid';
import { TuiPhraseAnalysis, TuiPhraseToken } from '.';

type TuiPhraseConsoleProps = {
  analysis: TuiPhraseAnalysis;
};

export default function TuiPhraseConsole({ analysis }: TuiPhraseConsoleProps) {
  const theme = useTheme();
  const valueRenderer = useCallback(
    (value: string, type: string) => {
      if (type === 'whitespace') {
        return (
          <span
            key={uuid()}
            style={{
              backgroundColor:
                theme.palette.mode === 'light'
                  ? darken(theme.palette.background.default, 0.1)
                  : lighten(theme.palette.background.default, 0.2)
            }}
          >
            {value}
          </span>
        );
      }
      return value;
    },
    [theme]
  );

  const tokenRenderer = useCallback(
    (token: TuiPhraseToken) => {
      return (
        <pre>
          <i>
            <b>
              {token.type}[{token.startIndex},{token.endIndex}]
            </b>
          </i>
          &nbsp;
          {token.children
            ? token.children.map(c => valueRenderer(c.value, c.type))
            : valueRenderer(token.value, token.type)}
        </pre>
      );
    },
    [valueRenderer]
  );

  return (
    <Paper elevation={3} sx={{ padding: 0, borderRadius: 0 }}>
      <Paper elevation={2} sx={{ margin: 0, borderRadius: 0, padding: 1 }}>
        <Typography variant="caption">Phrase Console</Typography>
      </Paper>
      <Stack direction="column" sx={{ padding: 1 }}>
        <Typography component="div" variant="caption">
          cursor: {analysis.cursor}
        </Typography>
        <Typography component="div" variant="caption">
          filter: {analysis.suggest.value}
        </Typography>

        <div>
          {analysis.tokens.map((t, i) => {
            const isCurrent = analysis.parent === t;
            const isFilter = t === analysis.suggest.token;
            let color: MuiColorType = 'default';
            if (t.type.startsWith('matcher')) {
              color = 'primary';
            } else if (t.type.startsWith('sorter')) {
              color = 'secondary';
            }
            return (
              <Chip
                key={i}
                variant={isCurrent ? 'filled' : 'outlined'}
                label={<div>{tokenRenderer(t)}</div>}
                color={color}
                sx={{ margin: 0.5 }}
                icon={isFilter ? <FilterAlt fontSize="small" /> : null}
              />
            );
          })}
        </div>
      </Stack>
    </Paper>
  );
}
