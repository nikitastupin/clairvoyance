import json
from typing import Any, Dict, List, Optional, Set

from clairvoyance.entities import GraphQLPrimitive
from clairvoyance.entities.context import log
from clairvoyance.entities.primitives import GraphQLKind


class Schema:

    """Host of the introspection data."""

    def __init__(
        self,
        query_type: str = None,
        mutation_type: str = None,
        subscription_type: str = None,
        schema: Dict[str, Any] = None,
    ):
        if schema:
            self._schema = {
                'directives': schema['data']['__schema']['directives'],
                'mutationType': schema['data']['__schema']['mutationType'],
                'queryType': schema['data']['__schema']['queryType'],
                'subscriptionType': schema['data']['__schema']['subscriptionType'],
                'types': [],
            }
            self.types = {}
            for t in schema['data']['__schema']['types']:
                typ = Type.from_json(t)
                self.types[typ.name] = typ
        else:
            self.query_type = {'name': query_type} if query_type else None
            self.mutation_type = {'name': mutation_type} if mutation_type else None
            self.subscription_type = ({'name': subscription_type} if subscription_type else None)
            self._schema = {
                'directives': [],
                'queryType': self.query_type,
                'mutationType': self.mutation_type,
                'subscriptionType': self.subscription_type,
                'types': [],
            }
            self.types = {
                GraphQLPrimitive.STRING: Type(
                    name=GraphQLPrimitive.STRING,
                    kind=GraphQLKind.SCALAR,
                ),
                GraphQLPrimitive.ID: Type(
                    name=GraphQLPrimitive.ID,
                    kind=GraphQLKind.SCALAR,
                ),
            }
            if query_type:
                self.add_type(query_type, 'OBJECT')
            if mutation_type:
                self.add_type(mutation_type, 'OBJECT')
            if subscription_type:
                self.add_type(subscription_type, 'OBJECT')

    # Adds type to schema if it's not exists already
    def add_type(
        self,
        name: str,
        kind: str,
    ) -> None:
        """Adds type to schema if it's not exists already."""

        if name not in self.types:
            typ = Type(name=name, kind=kind)
            self.types[name] = typ

    def __repr__(self) -> str:
        """String representation of the schema."""

        schema = {'data': {'__schema': self._schema}}

        for t in self.types.values():
            schema['data']['__schema']['types'].append(t.to_json())

        output = json.dumps(schema, indent=4, sort_keys=True)
        return output

    def get_path_from_root(
        self,
        name: str,
    ) -> List[str]:
        """Getting path starting from root."""

        log().debug(f'Entered get_path_from_root({name})')
        path_from_root: List[str] = []

        if name not in self.types:
            raise Exception(f'Type \'{name}\' not in schema!')

        roots = [
            self._schema['queryType']['name'] if self._schema['queryType'] else '',
            self._schema['mutationType']['name'] if self._schema['mutationType'] else '',
            self._schema['subscriptionType']['name'] if self._schema['subscriptionType'] else '',
        ]
        roots = [r for r in roots if r]

        while name not in roots:
            for t in self.types.values():
                for f in t.fields:
                    if f.type.name == name:
                        path_from_root.insert(0, f.name)
                        name = t.name

        # Prepend queryType or mutationType
        path_from_root.insert(0, name)

        return path_from_root

    def get_type_without_fields(
        self,
        ignored: Set[str] = None,
    ) -> str:
        """Gets the type without a field."""
        ignored = ignored or set()

        for t in self.types.values():
            if not t.fields and t.name not in ignored and t.kind != GraphQLKind.INPUT_OBJECT:
                return t.name

        return ''

    def convert_path_to_document(
        self,
        path: List[str],
    ) -> str:
        """Converts a path to document."""

        log().debug(f'Entered convert_path_to_document({path})')
        doc = 'FUZZ'

        while len(path) > 1:
            doc = f'{path.pop()} {{ {doc} }}'

        if path[0] == self._schema['queryType']['name']:
            doc = f'query {{ {doc} }}'
        elif path[0] == self._schema['mutationType']['name']:
            doc = f'mutation {{ {doc} }}'
        elif path[0] == self._schema['subscriptionType']['name']:
            doc = f'subscription {{ {doc} }}'
        else:
            raise Exception('Unknown operation type')

        return doc


class TypeRef:

    def __init__(
        self,
        name: str,
        kind: str,
        is_list: bool = False,
        non_null_item: bool = False,
        non_null: bool = False,
    ) -> None:
        if not is_list and non_null_item:
            raise Exception('elements can\'t be NON_NULL if TypeRef is not LIST')

        self.name = name
        self.kind = kind
        self.is_list = is_list
        self.non_null = non_null
        self.list = self.is_list
        self.non_null_item = non_null_item

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TypeRef):
            for key, attr in self.__dict__.items():
                if attr != other.__dict__[key]:
                    return False
            return True
        return False

    def __str__(self) -> str:
        return str(self.__dict__)

    def to_json(self) -> Dict[str, Any]:
        j: Dict[str, Any] = {'kind': self.kind, 'name': self.name, 'ofType': None}

        if self.non_null_item:
            j = {'kind': GraphQLKind.NON_NULL, 'name': None, 'ofType': j}

        if self.list:
            j = {'kind': GraphQLKind.LIST, 'name': None, 'ofType': j}

        if self.non_null:
            j = {'kind': GraphQLKind.NON_NULL, 'name': None, 'ofType': j}

        return j


class InputValue:

    def __init__(
        self,
        name: str,
        typ: TypeRef,
    ) -> None:
        self.name = name
        self.type = typ

    def __str__(self) -> str:
        return f'{{ \'name\': {self.name}, \'type\': {str(self.type)} }}'

    def to_json(self) -> dict:
        return {
            'defaultValue': None,
            'description': None,
            'name': self.name,
            'type': self.type.to_json(),
        }

    @classmethod
    def from_json(
        cls,
        _json: Dict[str, Any],
    ) -> 'InputValue':
        name = _json['name']
        typ = field_or_arg_type_from_json(_json['type'])

        return cls(
            name=name,
            typ=typ,
        )


def field_or_arg_type_from_json(_json: Dict[str, Any]) -> 'TypeRef':
    typ = None

    if _json['kind'] not in [GraphQLKind.NON_NULL, GraphQLKind.LIST]:
        typ = TypeRef(
            name=_json['name'],
            kind=_json['kind'],
        )
    elif not _json['ofType']['ofType']:
        actual_type = _json['ofType']

        if _json['kind'] == GraphQLKind.NON_NULL:
            typ = TypeRef(
                name=actual_type['name'],
                kind=actual_type['kind'],
                non_null=True,
            )
        elif _json['kind'] == GraphQLKind.LIST:
            typ = TypeRef(
                name=actual_type['name'],
                kind=actual_type['kind'],
                is_list=True,
            )
        else:
            raise Exception(f'Unexpected type.kind: {_json["kind"]}')
    elif not _json['ofType']['ofType']['ofType']:
        actual_type = _json['ofType']['ofType']

        if _json['kind'] == GraphQLKind.NON_NULL:
            typ = TypeRef(
                actual_type['name'],
                actual_type['kind'],
                True,
                False,
                True,
            )
        elif _json['kind'] == GraphQLKind.LIST:
            typ = TypeRef(
                name=actual_type['name'],
                kind=actual_type['kind'],
                is_list=True,
                non_null_item=True,
            )
        else:
            raise Exception(f'Unexpected type.kind: {_json["kind"]}')
    elif not _json['ofType']['ofType']['ofType']['ofType']:
        actual_type = _json['ofType']['ofType']['ofType']
        typ = TypeRef(
            name=actual_type['name'],
            kind=actual_type['kind'],
            is_list=True,
            non_null_item=True,
            non_null=True,
        )
    else:
        raise Exception('Invalid field or arg (too many \'ofType\')')

    return typ


class Field:

    def __init__(
        self,
        name: str,
        typeref: Optional[TypeRef],
        args: List[InputValue] = None,
    ):
        if not typeref:
            raise Exception(f'Can\'t create {name} Field from {typeref} TypeRef.')

        self.name = name
        self.type = typeref
        self.args = args or []

    def to_json(self) -> dict:
        return {
            'args': [a.to_json() for a in self.args],
            'deprecationReason': None,
            'description': None,
            'isDeprecated': False,
            'name': self.name,
            'type': self.type.to_json(),
        }

    @classmethod
    def from_json(cls, _json: Dict[str, Any]) -> 'Field':
        name = _json['name']
        typ = field_or_arg_type_from_json(_json['type'])

        args = []
        for a in _json['args']:
            args.append(InputValue.from_json(a))

        return cls(name, typ, args)


class Type:

    def __init__(
        self,
        name: str = '',
        kind: str = '',
        fields: List[Field] = None,
    ):
        self.name = name
        self.kind = kind
        self.fields: List[Field] = fields or []

    def to_json(self) -> Dict[str, Any]:
        # dirty hack

        if not self.fields:
            field_typeref = TypeRef(
                name=GraphQLPrimitive.STRING,
                kind=GraphQLKind.SCALAR,
            )
            dummy = Field('dummy', field_typeref)
            self.fields.append(dummy)

        output: Dict[str, Any] = {
            'description': None,
            'enumValues': None,
            'interfaces': [],
            'kind': self.kind,
            'name': self.name,
            'possibleTypes': None,
        }

        if self.kind in [GraphQLKind.OBJECT, GraphQLKind.INTERFACE]:
            output['fields'] = [f.to_json() for f in self.fields]
            output['inputFields'] = None
        elif self.kind == GraphQLKind.INPUT_OBJECT:
            output['fields'] = None
            output['inputFields'] = [f.to_json() for f in self.fields]

        return output

    @classmethod
    def from_json(
        cls,
        _json: Dict[str, Any],
    ) -> 'Type':
        name = _json['name']
        kind = _json['kind']
        fields = []

        if kind in [GraphQLKind.OBJECT, GraphQLKind.INTERFACE, GraphQLKind.INPUT_OBJECT]:
            fields_field = ''
            if kind in [GraphQLKind.OBJECT, GraphQLKind.INTERFACE]:
                fields_field = 'fields'
            elif kind == GraphQLKind.INPUT_OBJECT:
                fields_field = 'inputFields'

            for f in _json[fields_field]:
                # Don't add dummy fields!
                if f['name'] == 'dummy':
                    continue
                fields.append(Field.from_json(f))

        return cls(
            name=name,
            kind=kind,
            fields=fields,
        )
