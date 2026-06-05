import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { RepositoryScanResponse, SyncRequest, SyncResponse } from "@/types/scanner";

const QUERY_KEY = ["scanner", "repositories"];

export function useScannedRepositories() {
  return useQuery<RepositoryScanResponse>({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<RepositoryScanResponse>("/repositories");
      return data;
    },
    refetchInterval: 10_000,
  });
}

export function useSyncRepositories() {
  const qc = useQueryClient();
  return useMutation<SyncResponse, Error, SyncRequest>({
    mutationFn: async (request) => {
      const { data } = await apiClient.post<SyncResponse>("/repositories/sync", request);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useDiscoverRepositories() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.post("/repositories/discover");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
