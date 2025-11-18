import type { ActionDefinition, ActionResult } from 'api/actions';
import type { Selector } from 'lib/types/lookup';
import type WithActionData from './WithActionData';

interface RunningActionData {
  id: string;
  action: ActionDefinition;
  selectors: Selector[];
  params: { [index: string]: any };
  onComplete?: (result: WithActionData<ActionResult>) => void;
  timeout?: number;
}

export default RunningActionData;
