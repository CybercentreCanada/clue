import throttle from 'lodash-es/throttle';
import { addRxPlugin, createRxDatabase, type RxJsonSchema } from 'rxdb';
import { wrappedKeyCompressionStorage } from 'rxdb/plugins/key-compression';
import { getRxStorageLocalstorage } from 'rxdb/plugins/storage-localstorage';
import { getRxStorageMemory } from 'rxdb/plugins/storage-memory';
import { RxDBUpdatePlugin } from 'rxdb/plugins/update';
import { wrappedValidateAjvStorage } from 'rxdb/plugins/validate-ajv';
import selectorSchema from './selector.schema.json';
import statusSchema from './status.schema.json';
import type {
  ClueDatabase,
  ClueDatabaseCollections,
  DatabaseConfig,
  SelectorDocMethods,
  SelectorDocType,
  SelectorDocument,
  StatusCollection,
  StatusCollectionMethods,
  StatusDocMethods,
  StatusDocType,
  StatusDocument
} from './types';

const checkVitest = () => {
  try {
    return !!process?.env?.VITEST;
  } catch {
    return false;
  }
};
const IS_VITEST = checkVitest();

const selectorMethods: SelectorDocMethods = {
  getAnnotations: function (this: SelectorDocument) {
    return this.annotations.map(annotation => ({
      ...annotation,
      latency: this.latency,
      classification: this.classification
    }));
  }
};

const statusMethods: StatusDocMethods = {
  toSelector: function (this: StatusDocument) {
    return {
      type: this.type,
      value: this.value,
      classification: this.classification
    };
  }
};

const queuedValues: StatusDocType[] = [];
const listeners: ((doc: StatusDocument[]) => void)[] = [];
const _process = throttle(
  async (_collection: StatusCollection) => {
    const _listeners = [...listeners];
    _collection
      .bulkInsert([...queuedValues])
      .then(({ success }) => _listeners.forEach(_listener => _listener(success)));

    queuedValues.length = 0;
    listeners.length = 0;
  },
  50,
  { leading: false, trailing: true }
);

const statusStatics: StatusCollectionMethods = {
  queueInsert: function (this: StatusCollection, value: StatusDocType) {
    queuedValues.push(value);

    _process(this);

    return new Promise((res, rej) => {
      listeners.push(docs => {
        const result = docs.find(({ id }) => id === value.id);

        if (result) {
          res(result);
        } else {
          rej();
        }
      });
    });
  }
};

const buildDatabase = async (_config: DatabaseConfig = {}) => {
  const config = {
    storageType: 'sessionStorage',
    testing: IS_VITEST,
    devMode: !import.meta.env.PROD,
    ..._config
  };

  addRxPlugin(RxDBUpdatePlugin);

  /* v8 ignore next 10 -- @preserve */
  if (config.devMode) {
    await import('rxdb/plugins/dev-mode').then(module => {
      addRxPlugin(module.RxDBDevModePlugin);

      if (config.testing) {
        module.disableWarnings();
      }
    });
  }

  const database: ClueDatabase = await createRxDatabase<ClueDatabaseCollections>({
    name: 'clue',

    /* v8 ignore next 7 -- @preserve */
    storage:
      config.storageType === 'memory'
        ? wrappedValidateAjvStorage({ storage: getRxStorageMemory() })
        : wrappedKeyCompressionStorage({
            storage: wrappedValidateAjvStorage({
              storage: getRxStorageLocalstorage({ localStorage: sessionStorage })
            })
          }),
    closeDuplicates: true,
    allowSlowCount: config.devMode
  });

  if (config.storageType === 'memory') {
    selectorSchema.keyCompression = false;
    statusSchema.keyCompression = false;
  }

  await database.addCollections({
    selectors: {
      schema: selectorSchema as RxJsonSchema<SelectorDocType>,
      methods: selectorMethods
    },
    status: {
      schema: statusSchema as RxJsonSchema<StatusDocType>,
      methods: statusMethods,
      statics: statusStatics
    }
  });

  try {
    await database.status.find({ selector: { status: 'in-progress' } }).remove();
    /* v8 ignore next 3 @preserve*/
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('Error on status wipe:', e);
  }

  return database;
};

export default buildDatabase;
