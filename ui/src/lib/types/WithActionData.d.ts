import type { ActionDefinition, ActionResult } from './action';

export type WithActionData<T> = T & {
  actionId: string;
  action: ActionDefinition;
  onComplete?: (result: WithActionData<ActionResult>) => void;
};

export default WithActionData;
