from pony.orm import flush
from shared.api_helpers.query_parameters_validator import QueryParametersValidator


class ModelDefinitionMixin:

    PARAMETERS = []
    NEEDS_RELOAD = True # Only false for not db objects (eg. API keys)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        '''
        Returns a dict with the following items:
            - properties: JSON schema definition of the properties
            - create_required: list of required properties for create operation (None or [] for all)
            - create_allowed: list of visible properties for create operation (None or [] for all)
            - create_forbidden: list of invisible properties for create operation
            - edit_required: list of required properties for edit operation (None or [] for all)
            - edit_allowed: list of visible properties for edit operation (None or [] for all)
            - edit_forbidden: list of invisible properties for edit operation
            - view_required: list of required properties for view operation (i.e. always present, None or [] for all)
            - view_allowed: list of visible properties for view operation (None or [] for all)
            - view_forbidden: list of invisible properties for view operation
        }
        '''
        raise NotImplementedError
    
    @classmethod
    def parse_parameters(cls, kwargs):
        return QueryParametersValidator.validate_and_decode(kwargs, cls.PARAMETERS)

    def get_serialized_object(self, **kwargs):
        if hasattr(self, 'id') and not self.id: flush()
        model = kwargs.pop('model') if 'model' in kwargs else self.__class__
        if 'op' not in kwargs:
            kwargs['op'] = 'view'
        model_def = getattr(model, 'get_model_definition')(**kwargs)
        allowed = model_def[kwargs['op']+'_allowed']
        forbidden = model_def.get(kwargs['op']+'_forbidden', [])
        return {p: d['value'](self) for p, d in model_def['properties'].items() if p not in forbidden and (not allowed or p in allowed)}

    @classmethod
    def get_model_schema(cls, op='view', for_validate=False, **kwargs):
        model_def = cls.get_model_definition(op=op, **kwargs)
        if 'heirs' in model_def:
            if not model_def['heirs']:
                return {}
            return {
                ("oneOf" if op != 'edit' else "anyOf"): [model.get_model_schema(op=op, for_validate=for_validate, **kwargs) for model in model_def['heirs']]
            }
        assert 'properties' in model_def, str(model_def)
        props = model_def['properties']
        required = model_def[op+'_required']
        allowed = model_def[op+'_allowed']
        forbidden = model_def.get(op+'_forbidden', [])
        schema = {
            "type": "object",
            "properties": {p: cls._process_property(props[p], op, **kwargs) for p in props if p not in forbidden and (not allowed or p in allowed)},
            "additionalProperties": False,
            "required": required
        }
        if 'title' in model_def:
            schema.update({
                'title': model_def['title']
            })
        if for_validate:
            # any changes due to difference in supported features of json schema (validation)
            # and Open API standard (documentaton), like mutually exclusive required properties
            if 'allOf' in model_def:
                schema.update({
                    "allOf": model_def['allOf'],
                    'required': []
                })
        else:
            for p in model_def.get(op+'_no_docs', []):
                if p in schema['properties']:
                    del schema['properties'][p]
            for p in model_def.get('no_docs', []):
                if p in schema['properties']:
                    del schema['properties'][p]
        return schema
   
    @classmethod
    def _process_property(cls, prop_info, op='view', **kwargs):
        base = {d: prop_info[d] for d in prop_info if d not in ['value', 'itemsModel']}
        if prop_info.get('type') == 'array' and 'itemsModel' in prop_info:
            base.update({
                "items":  prop_info['itemsModel'].get_model_schema('bulk_'+op, **kwargs),
            })
        return base
    
    @classmethod
    def get_example(cls, schema):
        if 'example' in schema:
            return schema['example']
        if 'const' in schema:
            return schema['const']
        if 'enum' in schema:
            return schema['enum'][0]
        if 'items' in schema:
            return [cls.get_example(schema['items'])]
        if 'properties' in schema:
            return {k: cls.get_example(v) for k, v in schema['properties'].items()}
        if 'oneOf' in schema:
            return cls.get_example(schema['oneOf'][0])

    @classmethod
    def get_model_example(cls, op='view', **kwargs):
        model_def = cls.get_model_definition(op=op, **kwargs)
        if 'heirs' in model_def:
            if not model_def['heirs']:
                return {}
            return model_def['heirs'][0].get_model_example(op=op, **kwargs)
        props = model_def['properties']
        allowed = model_def[op+'_allowed']
        forbidden = model_def.get(op+'_forbidden', [])
        return {p: cls.get_example(props[p]) for p in props if p not in forbidden and (not allowed or p in allowed)}
