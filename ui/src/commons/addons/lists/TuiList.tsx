import { memo } from 'react';
import { TuiListItemOnSelect, TuiListItemRenderer } from '.';
import TuiListBase from './TuiListBase';
import TuiListElement from './TuiListElement';
import TuiListEmpty from './TuiListEmpty';

type TuiListProps<T> = {
  keyboard?: boolean;
  children: TuiListItemRenderer<T>;
  onSelection?: TuiListItemOnSelect<T>;
};

const TuiList = <T,>({ keyboard, children, onSelection }: TuiListProps<T>) => {
  return (
    <TuiListBase keyboard={keyboard} onSelect={onSelection}>
      {(items, onSelect) =>
        items && items.length > 0 ? (
          items.map((element, i) => (
            <TuiListElement key={element.id} position={i} item={element} onSelect={onSelect}>
              {children}
            </TuiListElement>
          ))
        ) : (
          <TuiListEmpty />
        )
      }
    </TuiListBase>
  );
};

export default memo(TuiList);
