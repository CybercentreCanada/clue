/* eslint-disable react/jsx-no-literals */
import { MenuItem, Select, TableCell, TableRow, Typography } from '@mui/material';
import useLocalStorageItem from 'commons/components/utils/hooks/useLocalStorageItem';
import { StorageKey } from 'lib/utils/constants';
import type { FC } from 'react';
import { useTranslation } from 'react-i18next';
import EditRow from './EditRow';
import SettingsSection from './SettingsSection';

const CELL_SX = { borderBottom: 0, paddingBottom: 0.5 };

const LocalSection: FC = () => {
  const { t } = useTranslation();
  const [compactJson, setCompactJson] = useLocalStorageItem(StorageKey.COMPACT_JSON, false);
  const [flattenJson, setFlattenJson] = useLocalStorageItem(StorageKey.FLATTEN_JSON, false);
  const [pageCount, setPageCount] = useLocalStorageItem(StorageKey.PAGE_COUNT, 25);

  return (
    <SettingsSection title={t('page.settings.local.title')} colSpan={3}>
      <EditRow
        titleKey="page.settings.local.compact.json"
        descriptionKey="page.settings.local.compact.json.description"
        value={compactJson}
        type="checkbox"
        onEdit={async value => setCompactJson(JSON.parse(value))}
      />
      <EditRow
        titleKey="page.settings.local.flatten.json"
        descriptionKey="page.settings.local.flatten.json.description"
        value={flattenJson}
        type="checkbox"
        onEdit={async value => setFlattenJson(JSON.parse(value))}
      />
      <TableRow>
        <TableCell colSpan={3} sx={{ paddingTop: '0 !important' }}>
          <Typography variant="caption" color="text.secondary">
            {t('page.settings.local.hits.layout.description')}
          </Typography>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell sx={CELL_SX} style={{ whiteSpace: 'nowrap' }}>
          {t('page.settings.local.results.count')}
        </TableCell>
        <TableCell sx={CELL_SX} colSpan={2} align="right">
          <Select
            size="small"
            sx={{ minWidth: '75px', textAlign: 'left' }}
            value={pageCount}
            onChange={event =>
              setPageCount(typeof event.target.value === 'string' ? parseInt(event.target.value) : event.target.value)
            }
          >
            <MenuItem value={25}>25</MenuItem>
            <MenuItem value={50}>50</MenuItem>
            <MenuItem value={75}>75</MenuItem>
            <MenuItem value={100}>100</MenuItem>
            <MenuItem value={150}>150</MenuItem>
            <MenuItem value={250}>250</MenuItem>
          </Select>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={3} sx={{ paddingTop: '0 !important' }}>
          <Typography variant="caption" color="text.secondary">
            {t('page.settings.local.results.count.description')}
          </Typography>
        </TableCell>
      </TableRow>
    </SettingsSection>
  );
};

export default LocalSection;
