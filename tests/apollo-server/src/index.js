const {
  ApolloServer
} = require('apollo-server');
const typeDefs = require('./schema');

const server = new ApolloServer({
  typeDefs: typeDefs,
  debug: false
});

server.listen().then(({
  url
}) => {
  console.log(`🚀 Server ready at ${url}`);
});