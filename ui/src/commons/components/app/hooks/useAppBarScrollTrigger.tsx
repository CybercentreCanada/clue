import { useScrollTrigger } from '@mui/material';

export default function useAppBarScrollTrigger() {
  return useScrollTrigger({
    disableHysteresis: true,
    threshold: 0
  });
}
