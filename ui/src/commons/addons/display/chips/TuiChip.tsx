import { Chip, ChipProps, styled } from '@mui/material';
import { memo } from 'react';
import { Link } from 'react-router-dom';

const StyledLink = styled(Link)({
  display: 'inline-flex',
  textDecoration: 'none'
});

type LinkChipProps = ChipProps & {
  route?: string;
};

const TuiChip = ({ route, ...chipProps }: LinkChipProps) => {
  const onLinkClick = event => {
    if (chipProps.onClick) {
      event.preventDefault();
    }
  };
  return route ? (
    <StyledLink to={route} onClick={onLinkClick}>
      <Chip {...chipProps} clickable />
    </StyledLink>
  ) : (
    <Chip {...chipProps} />
  );
};

export default memo(TuiChip);
