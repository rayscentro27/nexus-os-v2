import React, { useState } from 'react';
import { X, Sparkles, FolderPlus } from 'lucide-react';
import { useNexus } from '../../context/NexusContext';

export const NewProjectModal: React.FC = () => {
  const { isNewProjectModalOpen, setIsNewProjectModalOpen, createProject, navigateToObject } = useNexus();
  const [projectName, setProjectName] = useState('');
  const [department, setDepartment] = useState('Research');
  const [client, setClient] = useState('Nexus Ventures');
  const [priority, setPriority] = useState<'High' | 'Medium' | 'Low'>('High');

  if (!isNewProjectModalOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) return;

    const created = createProject({
      name: projectName,
      department,
      client,
      priority,
    });
    setIsNewProjectModalOpen(false);
    setProjectName('');
    navigateToObject('projects', created.id, 'project');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="bg-white rounded-2xl w-full max-w-lg border border-slate-200 shadow-2xl p-6 relative">
        <button
          type="button"
          onClick={() => setIsNewProjectModalOpen(false)}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center">
            <FolderPlus className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Create New Nexus Project</h3>
            <p className="text-xs text-slate-500">Registers a first-class durable project across departments</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs sm:text-sm">
          <div>
            <label className="block font-medium text-slate-700 mb-1.5">Project Name</label>
            <input
              type="text"
              required
              value={projectName}
              onChange={e => setProjectName(e.target.value)}
              placeholder="e.g. Winter Solstice Ceramic Bundle"
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none text-slate-800"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-slate-700 mb-1.5">Track / Client</label>
              <select
                value={client}
                onChange={e => setClient(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white focus:border-blue-500 outline-none text-slate-800"
              >
                <option value="Nexus Ventures">Nexus Ventures</option>
                <option value="GoClear Institutional">GoClear Institutional</option>
                <option value="Trading R1 Core">Trading R1 Core</option>
                <option value="Internal Infrastructure">Internal Infrastructure</option>
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1.5">Starting Department</label>
              <select
                value={department}
                onChange={e => setDepartment(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white focus:border-blue-500 outline-none text-slate-800"
              >
                <option value="Research">Research</option>
                <option value="Marketing">Marketing</option>
                <option value="Creative">Creative</option>
                <option value="Commerce">Commerce</option>
                <option value="Distribution">Distribution</option>
                <option value="Systems">Systems</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1.5">Priority</label>
            <div className="grid grid-cols-3 gap-2">
              {(['High', 'Medium', 'Low'] as const).map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPriority(p)}
                  className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                    priority === p
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={() => setIsNewProjectModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 font-medium text-xs cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-1.5 cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Create Project</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
