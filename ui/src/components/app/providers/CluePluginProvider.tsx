import { useEffect, type FC, type PropsWithChildren } from 'react';
import { PluginProvider } from 'react-pluggable';
import clueUIPluginStore from '../../../plugins/store';

const CluePluginProvider: FC<PropsWithChildren> = ({ children }) => {
  useEffect(() => {
    const loadPlugin = async () => {
      const testPlugin = await import('../../../plugins/test');
      clueUIPluginStore.install(new testPlugin.default());
    };
    loadPlugin();
  }, []);

  return <PluginProvider pluginStore={clueUIPluginStore.pluginStore}>{children}</PluginProvider>;
};

export { CluePluginProvider };

// import { type FC, type PropsWithChildren } from 'react';
// import { PluginProvider } from 'react-pluggable';
// import clueUIPluginStore from '../../../plugins/store';

// const testPluginModule = await import('../../../plugins/test');
// const testPlugin = new testPluginModule.default();

// const CluePluginProvider: FC<PropsWithChildren> = ({ children }) => {
//   clueUIPluginStore.install(testPlugin);

//   return <PluginProvider pluginStore={clueUIPluginStore.pluginStore}>{children}</PluginProvider>;
// };

// export { CluePluginProvider };
