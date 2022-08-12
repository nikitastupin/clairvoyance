"""Define the primitives used in the Clairvoyance system."""

from enum import Enum, unique

from clairvoyance.entities.meta import MetaEnum


@unique
class GraphQLPrimitive(str, Enum, metaclass=MetaEnum):

    """The default GraphQL Scalar primitives.

    ref: https://spec.graphql.org/draft/#sec-Input-Values
    """

    ID = 'ID'
    INT = 'Int'
    STRING = 'String'
    BOOLEAN = 'Boolean'
    FLOAT = 'Float'


@unique
class GraphQLKind(str, Enum, metaclass=MetaEnum):

    """The default GraphQL kinds.

    ref: https://spec.graphql.org/draft/#sec-Types
    """

    SCALAR = 'SCALAR'
    OBJECT = 'OBJECT'
    INTERFACE = 'INTERFACE'
    UNION = 'UNION'
    ENUM = 'ENUM'
    INPUT_OBJECT = 'INPUT_OBJECT'
    LIST = 'LIST'
    NON_NULL = 'NON_NULL'
