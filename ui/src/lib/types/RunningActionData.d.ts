import type { ActionContextInformation, ActionDefinition, ActionResult } from 'lib/types/action';
import type { Selector } from 'lib/types/lookup';
import type { WithActionData } from './WithActionData';

interface RunningActionData {
  id: string;
  action: ActionDefinition;
  selectors: Selector[];
  params: { [index: string]: any };
  context?: ActionContextInformation;
  onComplete?: (result: WithActionData<ActionResult>) => void;
  timeout?: number;
}

export default RunningActionData;
