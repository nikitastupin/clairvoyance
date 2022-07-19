"""Define the primitives used in the Clairvoyance system."""

from enum import Enum, unique


@unique
class GraphQLPrimitive(str, Enum):

    """The default GraphQL Scalar primitives.

    ref: https://spec.graphql.org/draft/#sec-Input-Values
    """

    ID = 'ID'
    INT = 'Int'
    STRING = 'String'
    BOOLEAN = 'Boolean'
    FLOAT = 'Float'


@unique
class GraphQLKind(str, Enum):

    """The default GraphQL kinds.

    ref: https://spec.graphql.org/draft/#sec-Types
    """

    SCALAR = 'SCALAR'
    OBJECT = 'OBJECT'
    INTERFACE = 'INTERFACE'
    UNION = 'UNION'
    ENUM = 'ENUM'
    INPUTOBJECT = 'INPUT_OBJECT'
