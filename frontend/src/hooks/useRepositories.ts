import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { RepositoryListResponse } from "@/types";

export function useRepositories(page = 1) {
  return useQuery<RepositoryListResponse>({
    queryKey: ["repositories", page],
    queryFn: async () => {
      const { data } = await apiClient.get<RepositoryListResponse>("/github/repos", {
        params: { page, per_page: 20 },
      });
      return data;
    },
  });
}
