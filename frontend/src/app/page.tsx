import { Header } from "@/components/layout/Header";
import { GitPullRequest, BookOpen, Activity, Code2 } from "lucide-react";
import { StatCard } from "@/components/dashboard/StatCard";

export default function DashboardPage() {
  return (
    <div>
      <Header title="Dashboard" />
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="Open PRs" value="—" icon={GitPullRequest} />
          <StatCard title="Repositories" value="—" icon={Code2} />
          <StatCard title="Knowledge Docs" value="—" icon={BookOpen} />
          <StatCard title="System Health" value="—" icon={Activity} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-800 mb-4">Recent Activity</h3>
            <p className="text-sm text-gray-400">No activity yet.</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-800 mb-4">Quick Actions</h3>
            <p className="text-sm text-gray-400">Coming soon.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
