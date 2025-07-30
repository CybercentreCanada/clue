import BugIcon from './BugIcon';
import HostIcon from './HostIcon';
import NetworkIcon from './NetworkIcon';
import ProcessIcon from './ProcessIcon';
import TargetIcon from './TargetIcon';

const ICON_MAP = {
  bug: BugIcon,
  target: TargetIcon,
  host: HostIcon,
  network: NetworkIcon,
  process: ProcessIcon
};

const getIcon = (icon: string) => ICON_MAP[icon];

export default getIcon;
