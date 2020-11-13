import urllib3
import requests

import json
import logging
from typing import List
from typing import Dict
from typing import Any
from typing import Set
from typing import Tuple


def post(url, data=None, json=None, **kwargs):
    session = requests.Session()

    retries = urllib3.util.Retry(
        status=5,
        method_whitelist={
            "DELETE",
            "GET",
            "HEAD",
            "OPTIONS",
            "PUT",
            "TRACE",
            "POST",
        },
        status_forcelist=range(500, 600),
        backoff_factor=2,
    )

    adapter = requests.adapters.HTTPAdapter(max_retries=retries)

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    response = session.post(url, data=data, json=json, **kwargs)

    return response


class Schema:
    def __init__(
        self,
        queryType: str = None,
        mutationType: str = None,
        subscriptionType: str = None,
        schema: Dict[str, Any] = None,
    ):
        if schema:
            self._schema = {
                "directives": schema["data"]["__schema"]["directives"],
                "mutationType": schema["data"]["__schema"]["mutationType"],
                "queryType": schema["data"]["__schema"]["queryType"],
                "subscriptionType": schema["data"]["__schema"]["subscriptionType"],
                "types": [],
            }
            self.types = {}
            for t in schema["data"]["__schema"]["types"]:
                typ = Type.from_json(t)
                self.types[typ.name] = typ
        else:
            self.queryType = {"name": queryType} if queryType else None
            self.mutationType = {"name": mutationType} if mutationType else None
            self.subscriptionType = (
                {"name": subscriptionType} if subscriptionType else None
            )
            self._schema = {
                "directives": [],
                "mutationType": self.mutationType,
                "queryType": self.queryType,
                "subscriptionType": self.subscriptionType,
                "types": [],
            }
            self.types = {
                "String": Type(name="String", kind="SCALAR"),
                "ID": Type(name="ID", kind="SCALAR"),
            }
            if self.queryType:
                self.add_type(queryType, "OBJECT")
            if self.mutationType:
                self.add_type(mutationType, "OBJECT")
            if self.subscriptionType:
                self.add_type(subscriptionType, "OBJECT")

    # Adds type to schema if it's not exists already
    def add_type(self, name: str, kind: str) -> None:
        if name not in self.types:
            typ = Type(name=name, kind=kind)
            self.types[name] = typ

    def to_json(self):
        schema = {"data": {"__schema": self._schema}}

        for t in self.types.values():
            schema["data"]["__schema"]["types"].append(t.to_json())

        output = json.dumps(schema, indent=4, sort_keys=True)
        return output

    def get_path_from_root(self, name: str) -> List[str]:
        logging.debug(f"Entered get_path_from_root({name})")
        path_from_root = []

        if name not in self.types:
            raise Exception(f"Type '{name}' not in schema!")

        roots = [
            self._schema["queryType"]["name"] if self._schema["queryType"] else "",
            self._schema["mutationType"]["name"]
            if self._schema["mutationType"]
            else "",
            self._schema["subscriptionType"]["name"]
            if self._schema["subscriptionType"]
            else "",
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

    @property
    def roots(self) -> List[str]:
        roots = [
            self._schema["queryType"]["name"] if self._schema["queryType"] else "",
            self._schema["mutationType"]["name"]
            if self._schema["mutationType"]
            else "",
            self._schema["subscriptionType"]["name"]
            if self._schema["subscriptionType"]
            else "",
        ]
        roots = [r for r in roots if r]

        if not roots:
            raise Exception("No root types")

        return roots

    def get_path_from_root_ex(self, name: str) -> Tuple[List[str], List[str]]:
        logging.debug(f"Entered get_path_from_root_ex({name})")

        fpath = None  # field path
        apath = None  # argument path

        if name not in self.types:
            raise Exception(f"Type '{name}' not in schema!")

        kind = self.types[name].kind

        if kind == "OBJECT":
            fpath = self.get_path_from_root(name)
        elif kind == "INPUT_OBJECT":
            cur = name
            roots = self.roots

            while cur not in roots:
                for t in self.types.values():

                    if t.kind == "OBJECT":
                        for f in t.fields:
                            for a in f.args:
                                if a.type.name == cur:
                                    apath.insert(0, a.name)
                                    fpath = self.get_path_from_root(f.type.name)
                                    cur = roots[0]  # to break from outer loop
                                    break
                    elif t.kind == "INPUT_OBJECT":
                        raise Exception(f"Handling for kind {t.kind} not implemented")
                    else:
                        raise Exception(f"Handling for kind {t.kind} not implemented")
        else:
            raise Exception(f"Handling of {kind} not implemented")

        return fpath, apath

    def get_type_without_fields(self, ignore: Set[str]) -> "Type":
        for t in self.types.values():
            if not t.fields and t.name not in ignore:
                return t

        return None

    def convert_path_to_document(self, path: List[str]) -> str:
        logging.debug(f"Entered convert_path_to_document({path})")
        doc = "FUZZ"

        while len(path) > 1:
            doc = f"{path.pop()} {{ {doc} }}"

        if path[0] == self._schema["queryType"]["name"]:
            doc = f"query {{ {doc} }}"
        elif path[0] == self._schema["mutationType"]["name"]:
            doc = f"mutation {{ {doc} }}"
        elif path[0] == self._schema["subscriptionType"]["name"]:
            doc = f"subscription {{ {doc} }}"
        else:
            raise Exception("Unknown operation type")

        return doc

    # fpath - field path
    # apath - argument path
    def convert_path_to_document_ex(self, fpath: List[str], apath: List[str]) -> str:
        logging.debug(f"Entered convert_path_to_document_ex({fpath}, {apath})")

        if len(fpath) < 2:
            raise Exception(f"len(fpath) is {len(fpath)} but must be at least 2")

        doc = None

        if fpath and apath:
            args = "FUZZ"

            while apath:
                args = f"{apath.pop()}: {{ {args} }}"

            doc = f"{fpath.pop()} ({args})"

            while len(fpath) > 1:
                doc = f"{fpath.pop()} {{ {doc} }}"

            if path[0] == self._schema["queryType"]["name"]:
                doc = f"query {{ {doc} }}"
            elif path[0] == self._schema["mutationType"]["name"]:
                doc = f"mutation {{ {doc} }}"
            elif path[0] == self._schema["subscriptionType"]["name"]:
                doc = f"subscription {{ {doc} }}"
            else:
                raise Exception(f"Unknown operation type {path[0]}")
        elif fpath and not apath:
            doc = self.convert_path_to_document(fpath)
        else:
            raise Exception("Not implemented")

        return doc


class Config:
    def __init__(self):
        self.url = ""
        self.headers = dict()
        self.bucket_size = 4096


class TypeRef:
    def __init__(
        self,
        name: str,
        kind: str,
        is_list: bool = False,
        non_null_item: bool = False,
        non_null: bool = False,
    ):
        if not is_list and non_null_item:
            raise Exception("elements can't be NON_NULL if TypeRef is not LIST")
        self.name = name
        self.kind = kind
        self.is_list = is_list
        self.non_null = non_null
        self.list = self.is_list
        self.non_null_item = non_null_item

    def __eq__(self, other):
        if isinstance(other, TypeRef):
            for attr in self.__dict__.keys():
                if self.__dict__[attr] != other.__dict__[attr]:
                    return False
            return True
        return False

    def __str__(self):
        return str(self.__dict__)

    def to_json(self) -> Dict[str, Any]:
        j = {"kind": self.kind, "name": self.name, "ofType": None}

        if self.non_null_item:
            j = {"kind": "NON_NULL", "name": None, "ofType": j}

        if self.list:
            j = {"kind": "LIST", "name": None, "ofType": j}

        if self.non_null:
            j = {"kind": "NON_NULL", "name": None, "ofType": j}

        return j


class InputValue:
    def __init__(self, name: str, typ: TypeRef):
        self.name = name
        self.type = typ

    def __str__(self):
        return f'{{ "name": {self.name}, "type": {str(self.type)} }}'

    def to_json(self):
        return {
            "defaultValue": None,
            "description": None,
            "name": self.name,
            "type": self.type.to_json(),
        }

    @classmethod
    def from_json(cls, jso: Dict[str, Any]) -> "InputValue":
        name = jso["name"]
        typ = field_or_arg_type_from_json(jso["type"])

        return cls(name=name, typ=typ)


def field_or_arg_type_from_json(jso: Dict[str, Any]) -> "TypeRef":
    typ = None

    if jso["kind"] not in ["NON_NULL", "LIST"]:
        typ = TypeRef(name=jso["name"], kind=jso["kind"])
    elif not jso["ofType"]["ofType"]:
        actual_type = jso["ofType"]

        if jso["kind"] == "NON_NULL":
            typ = TypeRef(
                name=actual_type["name"],
                kind=actual_type["kind"],
                non_null=True,
            )
        elif jso["kind"] == "LIST":
            typ = TypeRef(
                name=actual_type["name"], kind=actual_type["kind"], is_list=True
            )
        else:
            raise Exception(f"Unexpected type.kind: {jso['kind']}")
    elif not jso["ofType"]["ofType"]["ofType"]:
        actual_type = jso["ofType"]["ofType"]

        if jso["kind"] == "NON_NULL":
            typ = TypeRef(actual_type["name"], actual_type["kind"], True, False, True)
        elif jso["kind"] == "LIST":
            typ = TypeRef(
                name=actual_type["name"],
                kind=actual_type["kind"],
                is_list=True,
                non_null_item=True,
            )
        else:
            raise Exception(f"Unexpected type.kind: {jso['kind']}")
    elif not jso["ofType"]["ofType"]["ofType"]["ofType"]:
        actual_type = jso["ofType"]["ofType"]["ofType"]
        typ = TypeRef(
            name=actual_type["name"],
            kind=actual_type["kind"],
            is_list=True,
            non_null_item=True,
            non_null=True,
        )
    else:
        raise Exception("Invalid field or arg (too many 'ofType')")

    return typ


class Field:
    def __init__(self, name: str, typeref: TypeRef, args: List[InputValue] = None):
        if not typeref:
            raise Exception(f"Can't create {name} Field from {typeref} TypeRef.")

        self.name = name
        self.type = typeref
        self.args = args or []

    def to_json(self):
        return {
            "args": [a.to_json() for a in self.args],
            "deprecationReason": None,
            "description": None,
            "isDeprecated": False,
            "name": self.name,
            "type": self.type.to_json(),
        }

    @classmethod
    def from_json(cls, jso: Dict[str, Any]) -> "Field":
        name = jso["name"]
        typ = field_or_arg_type_from_json(jso["type"])

        args = []
        for a in jso["args"]:
            args.append(InputValue.from_json(a))

        return cls(name, typ, args)


class Type:
    def __init__(self, name: str = "", kind: str = "", fields: List[Field] = None):
        self.name = name
        self.kind = kind
        self.fields = fields or []  # type: List[Field]

    def to_json(self):
        # dirty hack
        if not self.fields:
            field_typeref = TypeRef(name="String", kind="SCALAR")
            dummy = Field("dummy", field_typeref)
            self.fields.append(dummy)

        output = {
            "description": None,
            "enumValues": None,
            "interfaces": [],
            "kind": self.kind,
            "name": self.name,
            "possibleTypes": None,
        }

        if self.kind in ["OBJECT", "INTERFACE"]:
            output["fields"] = [f.to_json() for f in self.fields]
            output["inputFields"] = None
        elif self.kind == "INPUT_OBJECT":
            output["fields"] = None
            output["inputFields"] = [f.to_json() for f in self.fields]

        return output

    @classmethod
    def from_json(cls, jso: Dict[str, Any]) -> "Type":
        name = jso["name"]
        kind = jso["kind"]
        fields = []

        if kind in ["OBJECT", "INTERFACE", "INPUT_OBJECT"]:
            fields_field = ""
            if kind in ["OBJECT", "INTERFACE"]:
                fields_field = "fields"
            elif kind == "INPUT_OBJECT":
                fields_field = "inputFields"

            for f in jso[fields_field]:
                # Don't add dummy fields!
                if f["name"] == "dummy":
                    continue
                fields.append(Field.from_json(f))

        return cls(name=name, kind=kind, fields=fields)
