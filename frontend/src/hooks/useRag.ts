import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { RagRequest, RagResponse } from "@/types/rag";

export function useRagChat() {
  return useMutation<RagResponse, Error, RagRequest>({
    mutationFn: async (request) => {
      const { data } = await apiClient.post<RagResponse>("/rag/chat", request);
      return data;
    },
  });
}
