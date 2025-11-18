import type { JSONSchema7 } from 'json-schema';
import cloneDeep from 'lodash-es/cloneDeep';
import get from 'lodash-es/get';

export const adaptSchema = (_schema: JSONSchema7): JSONSchema7 => {
  const requiredFields: string[] = [];

  const schema = cloneDeep(_schema);

  const newSchema = {
    ...schema,
    properties: Object.fromEntries(
      Object.entries(schema.properties ?? {})
        .filter(([name]) => !['raw_data', 'selector', 'selectors'].includes(name))
        .map(([name, def]) => {
          requiredFields.push(name);

          // the definition can be boolean, but we don't want to run any adaptations in that case.
          if (typeof def === 'boolean') {
            return [name, def];
          }

          // first case: https://github.com/pydantic/pydantic/issues/7161
          if (def.anyOf?.length === 2) {
            if (typeof def.anyOf[1] === 'boolean') {
              return [name, def];
            }

            if (def.anyOf[1].type === 'null' && typeof def.anyOf[0] !== 'boolean') {
              if (def.anyOf[0].enum) {
                def.enum = def.anyOf[0].enum;
              }

              def.type = [...(Array.isArray(def.anyOf[0].type) ? def.anyOf[0].type : [def.anyOf[0].type]), 'null'];

              delete def.anyOf;
              requiredFields.pop();
            }
          }

          // Pydantic uses allOf for enums, let's fix this.
          if (def.allOf?.length > 0) {
            if (typeof def.allOf[0] !== 'boolean' && def.allOf[0].$ref) {
              def = {
                ...def,
                ...get(schema, def.allOf[0].$ref.replace('#/', '').replaceAll('/', '.')),
                title: def.title
              };

              delete def.allOf;
            }
          }

          return [name, def];
        })
    )
  };

  newSchema.required = requiredFields;

  return newSchema;
};
