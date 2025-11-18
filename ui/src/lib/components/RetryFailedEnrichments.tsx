import { Button } from '@mui/material';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import useClueEnrichSelector from 'lib/hooks/selectors';
import { useContextSelector } from 'use-context-selector';

const RetryFailedEnrichments = () => {
  const enrichFailedEnrichments = useClueEnrichSelector(ctx => ctx.enrichFailedEnrichments);
  const { t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);

  return <Button onClick={enrichFailedEnrichments}>{t('retry.enrich')}</Button>;
};

export default RetryFailedEnrichments;
