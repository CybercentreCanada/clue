import buildDatabase from 'lib/database';
import React from 'react';
import { renderComponent, verifyExistence, verifyText } from '../../tests/test-utils';
import EnrichedTypography from './EnrichedTypography';

const database = await buildDatabase({ devMode: false, storageType: 'memory' });

test('EnrichedTypography - with no children text, displays the provided value', async () => {
  const type = 'ip';
  const value = '127.0.0.1';
  await mountComponent(type, value);
  verifyText(`enriched-${type}-value`, value);
});

test('EnrichedTypography - with children, displays the child and not the value', async () => {
  const type = 'ip';
  const value = '127.0.0.1';
  await mountComponent(type, value, <span id="hello-world">hello world</span>);
  verifyExistence(`enriched-${type}-value`, false);
  verifyText(`hello-world`, 'hello world');
});

async function mountComponent(type: string, value: string, children?: React.JSX.Element): Promise<void> {
  await renderComponent(
    <EnrichedTypography value={value} type={type}>
      {children}
    </EnrichedTypography>,
    database
  );
}
