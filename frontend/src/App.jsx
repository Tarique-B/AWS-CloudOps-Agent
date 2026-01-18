import React, { useState, useEffect, useRef } from 'react';
import ChatInput from './components/ChatInput';
import ChatMessage from './components/ChatMessage';
import Sidebar from './components/Sidebar';
import WelcomeScreen from './components/WelcomeScreen';
import { Terminal, Menu, ChevronsLeft, ChevronsRight, Copy, Loader2 } from 'lucide-react';

// Helper to generate IDs
const generateId = () => Math.random().toString(36).substring(2, 15);

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi there! I'm ready to help you manage your cloud infrastructure. What's on your mind today?"
    }
  ]);
  
  
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [latency, setLatency] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);
  
  // Session State
  const [sessionInfo, setSessionInfo] = useState({
    actorId: null, // Start as null to trigger WelcomeScreen
    sessionId: `session_${generateId()}`
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleNewSession = () => {
    const newSessionId = `session_${generateId()}`;
    setSessionInfo(prev => ({ ...prev, sessionId: newSessionId }));
    setMessages([{
      role: 'assistant',
      content: "New session started. How can I assist you?"
    }]);
  };

  const handleUpdateActorId = (newActorId) => {
    if (newActorId && newActorId.trim() !== '') {
      setSessionInfo(prev => ({ ...prev, actorId: newActorId.trim() }));
    }
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Check status on mount
    fetch('/api/ping')
      .then(res => res.json())
      .then(data => setStatus(data))
      .catch(err => console.error("Failed to fetch status:", err));
  }, []);

  const handleSendMessage = async (text) => {
    if (!text.trim()) return;

    // Add user message
    const userMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    const startTime = performance.now();

    try {
      // Create a placeholder for assistant message
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      const response = await fetch('/api/invocations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: text,
          stream: true,
          session_id: sessionInfo.sessionId,
          actor_id: sessionInfo.actorId
        }),
      });

      const endTime = performance.now();
      setLatency(Math.round(endTime - startTime));

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantResponse = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.chunk) {
                assistantResponse += data.chunk;
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg.role === 'assistant') {
                    lastMsg.content = assistantResponse;
                  }
                  return newMessages;
                });
              } else if (data.error) {
                console.error('Stream error:', data.error);
                // Optionally handle error in UI
              }
            } catch (e) {
              console.error('Error parsing SSE:', e);
            }
          }
        }
      }

    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `**Error:** Failed to communicate with the agent. \n\nDetails: ${error.message}` 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {!sessionInfo.actorId && (
        <WelcomeScreen onJoin={handleUpdateActorId} />
      )}
      
      <div className={`flex h-screen bg-stealth-bg overflow-hidden font-sans ${!sessionInfo.actorId ? 'blur-sm pointer-events-none' : ''}`}>
        <div className={`${isSidebarOpen ? 'w-72 border-r border-white/5' : 'w-0'} transition-all duration-300 overflow-hidden relative`}>
        <div className="w-72 h-full absolute top-0 left-0">
          <Sidebar 
            onQuickAction={handleSendMessage} 
            status={status} 
            sessionInfo={sessionInfo}
            onNewSession={handleNewSession}
            latency={latency}
            onUpdateActorId={handleUpdateActorId}
            onCloseSidebar={toggleSidebar}
          />
        </div>
      </div>
      
      <main className="flex-1 flex flex-col relative">
        {/* Toggle Sidebar Button - Only show when closed */}
        {!isSidebarOpen && (
          <button 
            onClick={toggleSidebar}
            className="absolute top-4 left-4 z-50 p-2 text-gray-400 hover:text-white bg-stealth-bg/50 hover:bg-white/10 rounded-lg transition-colors border border-white/5 md:flex hidden"
            title="Open Sidebar"
          >
            <ChevronsRight size={20} />
          </button>
        )}

        {/* Background Effects */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
          <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-neon-primary/5 rounded-full blur-[100px]" />
          <div className="absolute bottom-[-10%] left-[-5%] w-[500px] h-[500px] bg-neon-secondary/5 rounded-full blur-[100px]" />
        </div>

        {/* Header - Mobile Only or minimalist */}
        <div className="md:hidden flex items-center p-4 border-b border-white/5 z-10 bg-stealth-bg/80 backdrop-blur-md">
          <Terminal className="text-neon-primary mr-2" size={20} />
          <span className="font-bold text-gray-100">AWS CloudOps Assistant</span>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 z-10 scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent">
          <div className="max-w-6xl mx-auto">
            {messages.map((msg, idx) => (
              <ChatMessage key={idx} message={msg} />
            ))}
            {isLoading && (
              <div className="flex justify-start mb-6">
                <div className="bg-stealth-surface border border-white/5 px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-2 text-gray-400">
                  <Loader2 size={16} className="animate-spin text-neon-primary" />
                  <span className="text-xs">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 z-20 bg-gradient-to-t from-stealth-bg via-stealth-bg to-transparent">
          <div className="max-w-6xl mx-auto w-full">
            <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
          </div>
        </div>
      </main>
    </div>
    </>
  );
}

export default App;

