import { Header } from "@/components/layout/Header";
import { Database } from "lucide-react";

export default function KnowledgePage() {
  return (
    <div>
      <Header title="Knowledge Base" />
      <div className="p-6 flex flex-col items-center justify-center py-24 text-center">
        <Database className="h-12 w-12 text-gray-300 mb-4" />
        <h3 className="text-lg font-semibold text-gray-700">Knowledge Base</h3>
        <p className="text-sm text-gray-400 mt-2 max-w-sm">
          RAG-powered document ingestion and semantic search will be available here.
          Foundation is ready — Qdrant is running.
        </p>
      </div>
    </div>
  );
}
