import type { ActionDefinition } from './action';

export type WithActionData<T> = T & {
  actionId: string;
  action: ActionDefinition;
};

export default WithActionData;
