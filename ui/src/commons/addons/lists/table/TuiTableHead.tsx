import TuiSearchTerms from 'commons/addons/search/models/TuiSearchTerms';
import useVsBox from 'commons/addons/vsbox/hooks/useVsBox';
import { TuiTableColumn } from '.';
import TuiTableHeader from './TuiTableHeader';
import TuiTableLayout from './TuiTableLayout';

type TuiTableHeaderProps = {
  layout: TuiTableLayout;
  columns: TuiTableColumn[];
  sorters?: TuiSearchTerms;
  onSort?: (terms: TuiSearchTerms) => void;
};

export default function TuiTableHead({ layout, columns, sorters, onSort }: TuiTableHeaderProps) {
  const {
    state: { scrollTop }
  } = useVsBox();
  return (
    <div
      data-tuitable-header="true"
      className="tui-table-head tui-table-divider"
      style={{ position: scrollTop ? 'sticky' : null, top: scrollTop || null }}
    >
      {columns.map(column => (
        <TuiTableHeader
          key={column.column}
          width={layout.getWidth(column.column, true)}
          column={column}
          sorters={sorters}
          onClick={onSort}
        />
      ))}
    </div>
  );
}
