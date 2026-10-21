import { useEffect, useMemo, useSyncExternalStore } from "react";
import { useApolloClient } from "@apollo/client";
import { useSession } from "@/common/hooks/use-session";
import {
  DiscoverLedgersDocument,
  type DiscoverLedgersQuery,
  MyDiscoveryLedgersDocument,
  type MyDiscoveryLedgersQuery,
  StarredDiscoveryLedgersDocument,
  type StarredDiscoveryLedgersQuery,
  DiscoveryIdentityDocument,
  type DiscoveryIdentityQuery,
  StarDiscoveryLedgerDocument,
  type StarDiscoveryLedgerMutation,
  UnstarDiscoveryLedgerDocument,
  type UnstarDiscoveryLedgerMutation,
} from "@/generated-graphql/graphql";
import { DiscoveryStore, type DiscoveryItem } from "./discovery-store";
import { queryCatalogPage } from "./catalog-query";
import { collectPages } from "./collect-pages";

const PAGE_SIZE = 30;
export function useDiscovery() {
  const client = useApolloClient();
  const { userId, serverUrl } = useSession();
  const store = useMemo(
    () =>
      new DiscoveryStore({
        page: async (tab, q, page, signal) => {
          const context = {
            fetchOptions: { signal },
            queryDeduplication: false,
          };
          if (tab === "explore") {
            const data = await queryCatalogPage<
              DiscoverLedgersQuery,
              { q: string; page: number; limit: number }
            >(
              client,
              {
                query: DiscoverLedgersDocument,
                variables: { q, page, limit: PAGE_SIZE },
                context,
              },
              "searchLedgers",
            );
            return {
              items: data.searchLedgers,
              hasMore: data.searchLedgers.length === PAGE_SIZE,
            };
          }
          // Load all account lists so local search never silently searches only page one.
          let username: string | undefined;
          if (tab === "starred") {
            const { data } = await client.query<DiscoveryIdentityQuery>({
              query: DiscoveryIdentityDocument,
              variables: { userId },
              fetchPolicy: "no-cache",
              context,
            });
            username = data.userProfile?.username ?? undefined;
            if (!username) throw new Error("Missing account username");
          }
          const items = await collectPages<DiscoveryItem>(
            async (current) => {
              if (tab === "starred") {
                const { data } =
                  await client.query<StarredDiscoveryLedgersQuery>({
                    query: StarredDiscoveryLedgersDocument,
                    variables: { username, page: current, limit: PAGE_SIZE },
                    fetchPolicy: "no-cache",
                    context,
                  });
                return data.getUserStarredRepos.repositories.map((repo) => ({
                  ...repo,
                  id: repo.fullName,
                  private: repo.isPrivate,
                  isStarred: true,
                }));
              }
              const data = await queryCatalogPage<
                MyDiscoveryLedgersQuery,
                { page: number; limit: number }
              >(
                client,
                {
                  query: MyDiscoveryLedgersDocument,
                  variables: { page: current, limit: PAGE_SIZE },
                  context,
                },
                "listLedgers",
              );
              return data.listLedgers;
            },
            PAGE_SIZE,
            (item) => item.id,
            signal,
          );
          return { items, hasMore: false };
        },
        star: async (ledgerId, starred) => {
          const result = starred
            ? (
                await client.mutate<StarDiscoveryLedgerMutation>({
                  mutation: StarDiscoveryLedgerDocument,
                  variables: { ledgerId },
                })
              ).data?.starLedger
            : (
                await client.mutate<UnstarDiscoveryLedgerMutation>({
                  mutation: UnstarDiscoveryLedgerDocument,
                  variables: { ledgerId },
                })
              ).data?.unstarLedger;
          if (!result?.success) throw new Error("Star change failed");
          return result.isStarred;
        },
      }),
    [client, userId, serverUrl],
  );
  useEffect(() => () => store.dispose(), [store]);
  return {
    store,
    state: useSyncExternalStore(store.subscribe, store.getSnapshot),
  };
}
