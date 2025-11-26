import { Alert, Box, Paper, Table, TableCell, TableContainer, TableHead, TableRow, useTheme } from '@mui/material';
import type { FC, ReactElement } from 'react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';

const customComponents = (type: string, children: any) => {
  const child = children instanceof Array ? children[0] : children;
  if (type === 'alert') {
    return (
      <Alert severity="info" variant="outlined" sx={{ '.MuiAlert-message': { whiteSpace: 'normal' } }}>
        {child}
      </Alert>
    );
  }

  return <code>{child}</code>;
};

const Markdown: FC<{
  md: string;
  components?: { [index: string]: ReactElement };
}> = ({ md, components = {} }) => {
  const { t } = useTranslation();
  const theme = useTheme();

  const isDark = useMemo(() => theme.palette.mode === 'dark', [theme]);

  return (
    <ReactMarkdown
      rehypePlugins={[rehypeRaw]}
      remarkPlugins={[remarkGfm]}
      components={{
        code: ({ node, className, children, ...props }) => {
          if (node.children?.length === 1 && node.children[0].type === 'text') {
            if (node.children[0].value.startsWith('t(')) {
              return <span>{t(node.children[0].value.replace(/t\((.+)\)/, '$1'))}</span>;
            } else if (components[node.children[0].value]) {
              return components[node.children[0].value];
            }
          }

          const match = /language-(\w+)/.exec(className || '');

          if (match && ['alert', 'notebook', 'tabs'].includes(match[1])) {
            return customComponents(match[1], children);
          }

          return !(props as any).inline && match ? (
            <SyntaxHighlighter
              // eslint-disable-next-line react/no-children-prop
              children={String(children).replace(/\n$/, '')}
              style={isDark ? oneDark : oneLight}
              language={match[1]}
              PreTag="div"
              {...props}
            />
          ) : (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
        blockquote: ({ children, style }) => {
          return (
            <Box
              style={style ?? {}}
              sx={{
                pl: 1,
                borderLeft: `2px solid ${theme.palette.divider}`
              }}
            >
              {children}
            </Box>
          );
        },
        img: ({ node: _node, ...props }) => {
          // eslint-disable-next-line jsx-a11y/alt-text
          return <img {...props} style={{ ...props.style, maxWidth: '75%' }} />;
        },
        table: ({ children, style }) => {
          return (
            <TableContainer component={Paper}>
              <Table style={style ?? {}}>{children}</Table>
            </TableContainer>
          );
        },
        thead: ({ children, style }) => {
          return <TableHead style={style ?? {}}>{children}</TableHead>;
        },
        tr: ({ children, style }) => {
          return <TableRow style={style ?? {}}>{children}</TableRow>;
        },
        th: ({ children, ...props }) => {
          return <TableCell style={props.style}>{children}</TableCell>;
        },
        td: ({ children, ...props }) => {
          return <TableCell style={props.style}>{children}</TableCell>;
        },
        a: ({ node: _node, children, ...props }) => {
          if (props.href?.startsWith('/')) {
            return (
              <Link to={props.href} {...props}>
                {children}
              </Link>
            );
          } else {
            return <a {...props}>{children}</a>;
          }
        }
      }}
    >
      {md?.replace(/<!--.+?-->/g, '')}
    </ReactMarkdown>
  );
};

export default Markdown;
