import type { ActionDefinition, ActionResult } from './action';

export type WithActionData<T> = T & {
  actionId: string;
  action: ActionDefinition;
  onUpdate?: (result: WithActionData<ActionResult>) => void;
  onComplete?: (result: WithActionData<ActionResult>) => void;
};

export default WithActionData;
