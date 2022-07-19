from enum import unique

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
    
    SCALAR = 'Scalar'
    OBJECT = 'Object'
    INTERFACE = 'Interface'
    UNION = 'Union'
    ENUM = 'Enum'
    INPUTOBJECT = 'InputObject'