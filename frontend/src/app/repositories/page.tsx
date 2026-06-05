"use client";

import { Header } from "@/components/layout/Header";
import { useRepositories } from "@/hooks/useRepositories";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { formatRelativeTime } from "@/lib/utils";
import { ExternalLink, Star, AlertCircle } from "lucide-react";

export default function RepositoriesPage() {
  const { data, isLoading, error } = useRepositories();

  return (
    <div>
      <Header title="Repositories" />
      <div className="p-6">
        {isLoading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        )}
        {error && <ErrorMessage message={error.message} />}
        {data && (
          <div className="space-y-3">
            <p className="text-sm text-gray-500">{data.total} repositories</p>
            {data.repositories.map((repo) => (
              <div
                key={repo.id}
                className="bg-white rounded-xl border border-gray-200 p-4 flex items-start justify-between gap-4"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <a
                      href={repo.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium text-brand-500 hover:underline truncate"
                    >
                      {repo.name}
                    </a>
                    {repo.language && (
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                        {repo.language}
                      </span>
                    )}
                  </div>
                  {repo.description && (
                    <p className="text-sm text-gray-500 mt-1 truncate">{repo.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-400 shrink-0">
                  <span className="flex items-center gap-1">
                    <Star className="h-3 w-3" /> {repo.stargazers_count}
                  </span>
                  <span className="flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" /> {repo.open_issues_count}
                  </span>
                  <span>{formatRelativeTime(repo.updated_at)}</span>
                  <a href={repo.html_url} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-3.5 w-3.5 hover:text-brand-500" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
