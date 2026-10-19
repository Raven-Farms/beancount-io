import { ApolloServer } from "@apollo/server";
import { ApolloServerPluginDrainHttpServer } from "@apollo/server/plugin/drainHttpServer";
import { koaMiddleware } from "@as-integrations/koa";
import { buildSchema } from "type-graphql";
import type { GraphQLSchema } from "graphql";
import { printSchema } from "graphql";
import Router from "@koa/router";
import http from "http";
import { config as appConfig, type AppConfig } from "@/config/config";
import { apolloMetricsPlugin } from "@/metrics/apollo-plugin";
import { type AppLayers } from "@/foundation/composition";
import { resolvers, type ResolverContainer } from "./resolver-registry";

import type { IContext } from "./context";
import { createContext } from "./context";
import { graphqlScopeMiddleware } from "./scope-middleware";
import { errorLoggingPlugin } from "./plugins/error-logging";
import { formatError } from "./format-error";
import { bearerCookieMiddleware } from "./bearer-cookie-middleware";
import type { ScopeEnforcementMode } from "@/server/api/op-class";
import { graphqlRateLimitMiddleware } from "./rate-limit-middleware";

/**
 * Build the one GraphQL schema.
 *
 * The container is optional so the guard tests can enumerate the schema's ops
 * without standing up the service layer: TypeGraphQL instantiates resolvers
 * lazily, at execution time, so a schema built without one is structurally
 * identical to the served schema.
 */
export async function buildGraphqlSchema(options?: {
  container?: ResolverContainer;
  scopeEnforcement?: ScopeEnforcementMode;
}): Promise<GraphQLSchema> {
  return buildSchema({
    resolvers,
    ...(options?.container ? { container: options.container } : {}),
    globalMiddlewares: [
      // Budget first, then authorization: refusing an over-budget caller
      // before doing the authorization work is the point of having a limiter.
      graphqlRateLimitMiddleware(),
      graphqlScopeMiddleware(
        options?.scopeEnforcement ?? appConfig.api.scopeEnforcement,
      ),
    ],
    validate: true,
  });
}

/**
 * Publish the schema's SDL. Deliberately its own registration: it is the one
 * GraphQL mount that carries no caller and no op, so keeping it separate is
 * what lets the composition root mark it public without also excusing the
 * transport beside it.
 */
export function registerGraphqlSdlRoute(
  router: Router,
  schema: GraphQLSchema,
): void {
  const sdl = printSchema(schema);
  router.get("/api-gateway/schema.graphql", (ctx) => {
    ctx.type = "text/plain";
    ctx.body = sdl;
  });
}

/** Mount Apollo on the router — the GraphQL surface's transport. */
export async function registerGraphqlTransport(
  httpServer: http.Server,
  router: Router,
  schema: GraphQLSchema,
  layers: AppLayers,
  config: AppConfig = appConfig,
): Promise<void> {
  const server = new ApolloServer({
    schema,
    introspection: true,
    formatError,
    plugins: [
      ApolloServerPluginDrainHttpServer({ httpServer }),
      errorLoggingPlugin,
      apolloMetricsPlugin,
    ],
  });

  await server.start();

  router.all(
    "/api-gateway/",
    bearerCookieMiddleware(config),
    koaMiddleware(server, {
      context: async ({ ctx }): Promise<IContext> => {
        return createContext(ctx, layers.database, config);
      },
    }),
  );
}
