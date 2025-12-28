import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { Bot, User, Copy, Check } from 'lucide-react';

const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button 
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
      title="Copy code"
    >
      {copied ? <Check size={14} className="text-neon-primary" /> : <Copy size={14} />}
    </button>
  );
};

const ChatMessage = ({ message }) => {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-full md:max-w-[90%] lg:max-w-[95%] ${isUser ? 'flex-row-reverse' : 'flex-row'} gap-3`}>
        
        {/* Avatar */}
        <div className={`
          flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
          ${isUser 
            ? 'bg-neon-primary/10 border border-neon-primary/20 text-neon-primary' 
            : 'bg-neon-secondary/10 border border-neon-secondary/20 text-neon-secondary'}
        `}>
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>

        {/* Message Bubble */}
        <div className={`
          p-4 rounded-2xl text-sm leading-relaxed overflow-hidden relative group
          ${isUser 
            ? 'bg-stealth-card border border-neon-primary/20 text-gray-100 rounded-tr-sm shadow-[0_0_15px_rgba(0,255,157,0.05)]' 
            : 'bg-stealth-surface border border-white/5 text-gray-300 rounded-tl-sm'}
        `}>
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <div className="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-[#0f0f0f] prose-pre:border prose-pre:border-white/10 prose-p:mb-2 prose-ul:my-2 prose-li:my-0.5">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm, remarkBreaks]}
                components={{
                  code({node, inline, className, children, ...props}) {
                    const match = /language-(\w+)/.exec(className || '')
                    return !inline && match ? (
                      <div className="relative group/code">
                        <CopyButton text={String(children).replace(/\n$/, '')} />
                        <code className={className} {...props}>
                          {children}
                        </code>
                      </div>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    )
                  },
                  p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                  ul: ({node, ...props}) => <ul className="list-disc ml-4 mb-2" {...props} />,
                  ol: ({node, ...props}) => <ol className="list-decimal ml-4 mb-2" {...props} />,
                  li: ({node, ...props}) => <li className="mb-1" {...props} />,
                  a: ({node, ...props}) => <a className="text-neon-primary hover:underline" {...props} />,
                  table: ({node, ...props}) => <div className="overflow-x-auto my-4 rounded-lg border border-white/10"><table className="min-w-full divide-y divide-white/10" {...props} /></div>,
                  thead: ({node, ...props}) => <thead className="bg-white/5" {...props} />,
                  tbody: ({node, ...props}) => <tbody className="divide-y divide-white/10 bg-transparent" {...props} />,
                  tr: ({node, ...props}) => <tr className="hover:bg-white/5 transition-colors" {...props} />,
                  th: ({node, ...props}) => <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" {...props} />,
                  td: ({node, ...props}) => <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300" {...props} />,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;

