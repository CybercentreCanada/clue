import { Button, Divider, Stack, Table, TableBody, TableCell, TableRow, Typography } from '@mui/material';
import Iconified from 'lib/components/display/icons/Iconified';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import type { FC } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { useContextSelector } from 'use-context-selector';

export interface File {
  data: string;
  mime_type: string;
  file_name: string;
}

/**
 * Decode a base64 payload into raw bytes.
 */
const decodeBase64ToBytes = (base64Data: string): Uint8Array<ArrayBuffer> => {
  const byteCharacters = atob(base64Data);
  const byteArray = new Uint8Array(new ArrayBuffer(byteCharacters.length));

  // Convert each decoded character into its numeric byte value.
  for (let i = 0; i < byteCharacters.length; i++) {
    byteArray[i] = byteCharacters.charCodeAt(i);
  }

  return byteArray;
};

/**
 * Format a byte count using common binary units (B, KB, MB, GB).
 */
const formatBytes = (bytes: number): string => {
  if (bytes === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** unitIndex;

  return `${value.toFixed(unitIndex === 0 ? 0 : 2)} ${units[unitIndex]}`;
};

/**
 * Create a browser download from a server-provided file payload.
 */
const saveFileFromServer = (output: File): void => {
  const byteArray = decodeBase64ToBytes(output.data);

  // Build a Blob from the decoded bytes and trigger an anchor download.
  const blob = new Blob([byteArray], { type: output.mime_type || 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = output.file_name || 'result.txt';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
};

/**
 * Render a file action result with metadata, hash statistics, and download support.
 */
const FileResult: FC<{ result: WithActionData<ActionResult<File>> }> = ({ result }) => {
  const { t } = useContextSelector(ClueComponentContext, ctx => ctx?.i18next);

  const [sha256Hash, setSha256Hash] = useState<string>('');

  const actionName = result.action?.name ?? t('actions.result.file.unknown');

  const outputBytes = useMemo(() => {
    if (!result.output?.data) {
      return null;
    }

    try {
      return decodeBase64ToBytes(result.output.data);
    } catch {
      return null;
    }
  }, [result.output?.data]);

  useEffect(() => {
    let cancelled = false;

    const generateHash = async () => {
      if (!outputBytes || typeof crypto === 'undefined' || !crypto.subtle) {
        setSha256Hash('N/A');
        return;
      }

      // Compute a SHA-256 digest over the decoded file bytes.
      const digest = await crypto.subtle.digest('SHA-256', outputBytes);
      const digestArray = Array.from(new Uint8Array(digest));
      const digestHex = digestArray.map(value => value.toString(16).padStart(2, '0')).join('');

      if (!cancelled) {
        setSha256Hash(digestHex);
      }
    };

    setSha256Hash('');
    generateHash();

    return () => {
      // Prevent late async updates after unmount or dependency changes.
      cancelled = true;
    };
  }, [outputBytes]);

  return (
    <Stack sx={{ overflowY: 'auto' }} spacing={3}>
      <Typography variant="h5">{t('actions.result.file.title', { actionName })}</Typography>
      <Typography>{t('actions.result.file.description', { actionName })}</Typography>

      <Divider flexItem />

      <Typography variant="h6">{t('actions.result.file.stats.title')}</Typography>

      {outputBytes && (
        <Table sx={{ maxWidth: 900 }}>
          <TableBody>
            <TableRow>
              <TableCell sx={{ width: '35%' }}>{t('actions.result.file.stats.label.decoded_size')}</TableCell>
              <TableCell>{formatBytes(outputBytes.length) || 'n/a'}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ width: '35%' }}>{t('actions.result.file.stats.label.decoded_bytes')}</TableCell>
              <TableCell>{outputBytes.length || 'n/a'}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ width: '35%' }}>{t('actions.result.file.stats.label.base64_length')}</TableCell>
              <TableCell>{result.output?.data.length ?? 'n/a'}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ width: '35%' }}>{t('actions.result.file.stats.label.sha256')}</TableCell>
              <TableCell>
                <code>{sha256Hash || t('actions.result.file.stats.calculating')}</code>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )}

      <Button
        startIcon={<Iconified icon="ic:baseline-download" />}
        variant="outlined"
        sx={{ alignSelf: 'center' }}
        disabled={!result.output?.data}
        onClick={() => result.output && saveFileFromServer(result.output)}
        name="download"
        role="button"
      >
        {t('download', { file: result.output?.file_name ?? 'result.txt' })}
      </Button>
    </Stack>
  );
};

export default FileResult;
