import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';

const ChatInput = ({ onSendMessage, disabled }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input);
      setInput('');
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full mx-auto">
      <div className="relative flex items-end gap-2 p-2 bg-stealth-card border border-white/10 rounded-xl shadow-2xl focus-within:border-neon-primary/50 focus-within:shadow-[0_0_20px_rgba(0,255,157,0.1)] transition-all duration-300">
        
        <div className="pl-2 pb-3 text-gray-500">
          <Sparkles size={18} className={input ? "text-neon-primary animate-pulse" : ""} />
        </div>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask AWS Assistant to deploy, analyze, or explain..."
          rows={1}
          disabled={disabled}
          className="w-full bg-transparent text-gray-100 placeholder-gray-600 p-3 max-h-48 resize-none focus:outline-none text-sm leading-relaxed scrollbar-hide"
          style={{ minHeight: '44px' }}
        />

        <button
          type="submit"
          disabled={!input.trim() || disabled}
          className={`
            p-2.5 rounded-lg mb-0.5 transition-all duration-200
            ${input.trim() && !disabled
              ? 'bg-neon-primary text-black hover:bg-neon-primary/90 hover:scale-105 shadow-[0_0_10px_rgba(0,255,157,0.3)]' 
              : 'bg-white/5 text-gray-600 cursor-not-allowed'}
          `}
        >
          <Send size={18} strokeWidth={2.5} />
        </button>
      </div>
    </form>
  );
};

export default ChatInput;

