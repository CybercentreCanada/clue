import type { TypographyProps } from '@mui/material';
import { Typography } from '@mui/material';
import type { Annotation } from 'lib/types/lookup';
import isNil from 'lodash-es/isNil';
import sumBy from 'lodash-es/sumBy';
import type { FC } from 'react';
import { useMemo } from 'react';

const FrequencyText: FC<{ annotations: Annotation[]; value: string } & TypographyProps> = ({
  annotations,
  value,
  ...otherProps
}) => {
  const frequencyAnnotations = useMemo(
    () => annotations.filter(annotation => annotation.type === 'frequency'),
    [annotations]
  );

  const frequency = useMemo(
    () =>
      frequencyAnnotations.length > 0 ? sumBy(frequencyAnnotations, annotation => annotation.value as number) : null,
    [frequencyAnnotations]
  );

  const color = useMemo(() => {
    if (isNil(frequency)) {
      return null;
    }

    if (frequency < 1) {
      return 'error';
    }

    if (frequency < 1000) {
      return 'secondary';
    }

    if (frequency < 1000000) {
      return 'disabled';
    }

    return null;
  }, [frequency]);

  if (isNil(frequency)) {
    return (
      <Typography {...otherProps} color={color}>
        {value}
      </Typography>
    );
  }

  return (
    <Typography
      {...otherProps}
      color={color ?? otherProps.color}
      sx={{ fontWeight: !isNil(frequency) && frequency < 10 ? 'bold' : 'inherit' }}
    >
      {value}
    </Typography>
  );
};

export default FrequencyText;
