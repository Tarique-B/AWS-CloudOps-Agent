import React, { useState } from 'react';
import { 
  Cloud, 
  ShieldCheck, 
  CreditCard, 
  Server, 
  Database,
  User,
  Hash,
  RefreshCw,
  ChevronDown,
  Info,
  Brain,
  ChevronsLeft
} from 'lucide-react';

const AccordionItem = ({ title, id, children, icon, isOpen, onToggle }) => (
  <div className="border-b border-white/5 last:border-b-0">
    <button
      onClick={() => onToggle(id)}
      className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/5 transition-colors"
    >
      <div className="flex items-center gap-2 text-xs font-semibold text-gray-400">
        {icon}
        <span>{title}</span>
      </div>
      <ChevronDown 
        size={14} 
        className={`text-gray-600 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
      />
    </button>
    <div 
      className={`overflow-hidden transition-all duration-300 ease-in-out ${
        isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
      }`}
    >
      <div className="px-4 pb-4 pt-1">
        {children}
      </div>
    </div>
  </div>
);

const Sidebar = ({ onQuickAction, status, sessionInfo, onNewSession, latency, onUpdateActorId, onCloseSidebar }) => {
  const [openSection, setOpenSection] = useState('actions'); // 'actions' | 'about' | 'session' | null
  const [isEditingActor, setIsEditingActor] = useState(false);
  const [tempActorId, setTempActorId] = useState('');

  const toggleSection = (section) => {
    setOpenSection(openSection === section ? null : section);
  };

  const handleActorIdSubmit = (e) => {
    e.preventDefault();
    onUpdateActorId(tempActorId);
    setIsEditingActor(false);
  };

  const startEditingActor = () => {
    setTempActorId(sessionInfo?.actorId || '');
    setIsEditingActor(true);
  };

  const quickActions = [
    { label: "List S3 Buckets", icon: <Database size={16} />, prompt: "List all S3 buckets in my account" },
    { label: "Running Instances", icon: <Server size={16} />, prompt: "Show me all running EC2 instances" },
    { label: "Cost Analysis", icon: <CreditCard size={16} />, prompt: "Analyze my AWS costs for the last month" },
    { label: "Security Audit", icon: <ShieldCheck size={16} />, prompt: "Perform a security check on my IAM users" },
  ];

  const isHealthy = status?.status === 'healthy' && status?.agent_initialized;
  const isMemoryEnabled = status?.memory_enabled;
  const memoryId = status?.memory_id;

  return (
    <div className="w-full h-full bg-stealth-surface flex flex-col">
      
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-6 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-primary to-neon-accent flex items-center justify-center text-black font-bold shadow-[0_0_15px_rgba(0,255,157,0.3)]">
            <Cloud size={20} />
          </div>
          <div>
            <h1 className="font-bold text-gray-100 text-sm tracking-wide">AWS ASSISTANT</h1>
            <p className="text-[10px] text-gray-500 font-mono">INTELLIGENT CLOUD OPS</p>
          </div>
        </div>
        <button 
          onClick={onCloseSidebar}
          className="text-gray-500 hover:text-white transition-colors"
          title="Collapse Sidebar"
        >
          <ChevronsLeft size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        
        {/* Quick Actions */}
        <div className="p-4 border-b border-white/5">
          <h2 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3 px-2">Common Tasks</h2>
          <div className="space-y-1">
            {quickActions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => onQuickAction(action.prompt)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all duration-200 group text-left border border-transparent hover:border-white/5"
              >
                <span className="text-gray-500 group-hover:text-neon-primary transition-colors">{action.icon}</span>
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dropdowns */}
        <div className="border-t border-white/5">
          
          <AccordionItem 
            title="Session Details" 
            id="session" 
            icon={<Hash size={14} className="text-neon-primary" />}
            isOpen={openSection === 'session'}
            onToggle={toggleSection}
          >
             <div className="space-y-4">
                <div className="bg-stealth-bg border border-white/5 rounded-xl p-3 space-y-3">
                  <div className="space-y-1">
                    <div className="flex items-center justify-between gap-2 text-[10px] text-gray-500 mb-1">
                      <div className="flex items-center gap-2">
                        <User size={10} />
                        <span>Actor ID</span>
                      </div>
                      <button 
                        onClick={startEditingActor}
                        className="text-neon-primary hover:text-white transition-colors text-[9px] uppercase font-semibold"
                      >
                        Change
                      </button>
                    </div>
                    
                    {isEditingActor ? (
                      <form onSubmit={handleActorIdSubmit} className="flex gap-1">
                        <input
                          type="text"
                          value={tempActorId}
                          onChange={(e) => setTempActorId(e.target.value)}
                          className="w-full bg-black/30 border border-neon-primary/30 rounded px-2 py-1 text-[10px] text-gray-200 focus:outline-none focus:border-neon-primary"
                          placeholder="Enter username..."
                          autoFocus
                        />
                        <button 
                          type="submit"
                          className="px-2 py-1 bg-neon-primary/10 text-neon-primary rounded border border-neon-primary/20 hover:bg-neon-primary/20"
                        >
                          ✓
                        </button>
                      </form>
                    ) : (
                      <div className="font-mono text-[10px] text-gray-300 break-all bg-black/30 p-1.5 rounded border border-white/5">
                        {sessionInfo?.actorId || 'Anonymous'}
                      </div>
                    )}
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-[10px] text-gray-500 mb-1">
                      <Hash size={10} />
                      <span>Session ID</span>
                    </div>
                    <div className="font-mono text-[10px] text-gray-300 break-all bg-black/30 p-1.5 rounded border border-white/5">
                      {sessionInfo?.sessionId || 'N/A'}
                    </div>
                  </div>
                </div>

                <button
                  onClick={onNewSession}
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-[11px] text-gray-300 transition-colors border border-white/5 hover:border-white/20"
                >
                  <RefreshCw size={12} />
                  Start New Session
                </button>
             </div>
          </AccordionItem>

          <AccordionItem 
            title="About" 
            id="about" 
            icon={<Info size={14} className="text-blue-400" />}
            isOpen={openSection === 'about'}
            onToggle={toggleSection}
          >
            <div className="space-y-4">
              <p className="text-[11px] text-gray-400 leading-relaxed">
                An advanced cloud operations assistant designed to simplify AWS management through natural language.
              </p>
              
              <div>
                <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Powered By</h4>
                <div className="space-y-1.5">
                  {[
                    "Strands Agent Framework",
                    "AWS Bedrock FMs",
                    "AWS Bedrock AgentCore Runtime",
                    "AWS Bedrock AgentCore Memory"
                  ].map((tech, i) => (
                    <div key={i} className="flex items-center gap-2 text-[10px] text-gray-300 bg-white/5 px-2 py-1.5 rounded border border-white/5">
                      <div className="w-1 h-1 rounded-full bg-neon-primary/70" />
                      {tech}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </AccordionItem>

        </div>
      </div>


      {/* Footer Status */}
      <div className="p-4 border-t border-white/5 bg-stealth-bg/50">
        
        {/* Agent Status */}
        <div className="bg-stealth-bg rounded-xl p-3 border border-white/5 mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs text-gray-500">Agent Status</span>
            <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
              isHealthy 
                ? 'bg-neon-primary/10 text-neon-primary border-neon-primary/20' 
                : 'bg-red-500/10 text-red-500 border-red-500/20'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-neon-primary animate-pulse' : 'bg-red-500'}`} />
              {isHealthy ? 'ONLINE' : 'OFFLINE'}
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-[10px]">
              <span className="text-gray-600">Model</span>
              <span className="text-gray-400 font-mono">Claude 3.5 Sonnet</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-gray-600">Latency</span>
              <span className="text-gray-400 font-mono">{latency ? `${latency}ms` : '~'}</span>
            </div>
          </div>
        </div>

        {/* Memory Status */}
        <div className="bg-stealth-bg rounded-xl p-3 border border-white/5">
           <div className="flex justify-between items-center mb-2">
             <div className="flex items-center gap-1.5">
               <Brain size={12} className={isMemoryEnabled ? "text-neon-secondary" : "text-gray-600"} />
               <span className="text-xs text-gray-500">Memory</span>
             </div>
             <span className={`text-[10px] px-1.5 py-0.5 rounded border ${isMemoryEnabled ? 'bg-neon-secondary/10 text-neon-secondary border-neon-secondary/20' : 'bg-gray-800 text-gray-500 border-gray-700'}`}>
               {isMemoryEnabled ? 'ACTIVE' : 'DISABLED'}
             </span>
           </div>
           
           {isMemoryEnabled && memoryId && (
             <div className="flex justify-between text-[10px] items-center pt-1 border-t border-white/5 mt-1">
                <span className="text-gray-600">AgentCore Memory ID</span>
                <span className="font-mono text-gray-400 max-w-[120px] truncate" title={memoryId}>
                  {memoryId}
                </span>
             </div>
           )}
        </div>
      </div>

    </div>
  );
};

export default Sidebar;
