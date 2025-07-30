import type { IconButtonProps } from '@mui/material';
import { IconButton } from '@mui/material';

interface ExpandMoreProps extends IconButtonProps {
  expand: boolean;
}

const ExpandMoreButton = (props: ExpandMoreProps) => {
  const { expand, ...other } = props;
  return (
    <IconButton
      {...other}
      sx={{
        transform: !expand ? 'rotate(0deg)' : 'rotate(180deg)',
        transition: theme => theme.transitions.create('transform')
      }}
    />
  );
};

export default ExpandMoreButton;
