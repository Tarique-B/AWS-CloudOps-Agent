import React, { useState } from 'react';
import { Cloud, ArrowRight } from 'lucide-react';

const WelcomeScreen = ({ onJoin }) => {
  const [username, setUsername] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (username.trim()) {
      onJoin(username.trim());
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-stealth-bg">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] right-[-5%] w-[600px] h-[600px] bg-neon-primary/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-5%] w-[600px] h-[600px] bg-neon-secondary/5 rounded-full blur-[120px]" />
      </div>

      <div className="relative w-full max-w-md p-8 bg-stealth-card border border-white/5 rounded-2xl shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 mb-6 rounded-2xl bg-gradient-to-br from-neon-primary to-neon-accent flex items-center justify-center text-white shadow-[0_0_30px_rgba(168,85,247,0.3)]">
            <Cloud size={40} strokeWidth={2.5} />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">AWS CloudOps Assistant</h1>
          <p className="text-gray-400 text-center text-sm">
            Your intelligent companion for cloud operations. <br/>
            Enter your username to begin.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 pl-1">
              Username
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-neon-primary/50 focus:bg-black/50 transition-all"
              placeholder="e.g. cloud_ninja"
              autoFocus
              autoComplete="off"
            />
          </div>

          <button
            type="submit"
            disabled={!username.trim()}
            className={`
              w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold transition-all duration-300
              ${username.trim() 
                ? 'bg-gradient-to-r from-neon-primary to-neon-accent text-white hover:shadow-[0_0_20px_rgba(168,85,247,0.4)] hover:scale-[1.02]' 
                : 'bg-white/5 text-gray-500 cursor-not-allowed'}
            `}
          >
            Start Session
            <ArrowRight size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default WelcomeScreen;

