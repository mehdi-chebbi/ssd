import React, { useState, useEffect, useRef } from 'react';
import { LogOut, Cpu, MessageSquare, Send, Loader2 } from 'lucide-react';
import { apiService } from '../services/apiService';

const UserDashboard = ({ user, onLogout }) => {
  const [greeting, setGreeting] = useState('');
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) {
      setGreeting('Good morning');
    } else if (hour < 18) {
      setGreeting('Good afternoon');
    } else {
      setGreeting('Good evening');
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!message.trim() || isLoading) {
      return;
    }

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: message.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setMessage('');
    setIsLoading(true);
    setError('');

    try {
      const response = await apiService.chat(message.trim(), user.id);
      
      if (response.success) {
        const assistantMessage = {
          id: Date.now() + 1,
          role: 'assistant',
          content: response.data.response,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const errorMessage = {
          id: Date.now() + 1,
          role: 'assistant',
          content: `Error: ${response.error}`,
          timestamp: new Date().toISOString(),
          isError: true
        };
        
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="k8s-container min-h-screen">
      {/* Header */}
      <div className="k8s-glass border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Cpu className="w-8 h-8 text-k8s-blue" />
              <div>
                <h1 className="text-2xl font-bold text-white">Kubernetes Assistant</h1>
                <p className="text-k8s-gray text-sm">
                  {greeting}, {user.username}!
                </p>
              </div>
            </div>
            <button
              onClick={onLogout}
              className="k8s-button-secondary flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <MessageSquare className="w-8 h-8 text-k8s-cyan" />
            <h2 className="text-4xl font-bold text-white">
              Chat with Your K8s Assistant
            </h2>
          </div>
          <p className="text-xl text-k8s-gray max-w-2xl mx-auto">
            Ask questions about your Kubernetes infrastructure in natural language.
          </p>
        </div>

        {/* Chat Interface */}
        <div className="k8s-card h-[600px] flex flex-col">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 k8s-chat-scroll">
            {messages.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="w-12 h-12 text-k8s-blue mx-auto mb-4 opacity-50" />
                <p className="text-k8s-gray">
                  Start a conversation by asking about your Kubernetes cluster.
                </p>
                <p className="text-k8s-gray text-sm mt-2">
                  Try: "Show me all pods" or "What's the status of my deployments?"
                </p>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-2' : 'order-1'}`}>
                    <div className={`px-4 py-3 rounded-lg ${
                      msg.role === 'user' 
                        ? 'bg-k8s-blue text-white ml-4' 
                        : msg.isError 
                          ? 'bg-red-500/20 text-red-400 mr-4 border border-red-500/30'
                          : 'bg-k8s-dark/50 text-k8s-gray mr-4 border border-k8s-blue/20'
                    }`}>
                      {msg.role === 'assistant' && (
                        <div className="flex items-center gap-2 mb-2">
                          <Cpu className="w-4 h-4 text-k8s-blue" />
                          <span className="text-xs font-medium text-k8s-blue">K8s Assistant</span>
                        </div>
                      )}
                      <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                      <div className="text-xs text-k8s-gray/60 mt-2">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-k8s-dark/50 text-k8s-gray mr-4 border border-k8s-blue/20 px-4 py-3 rounded-lg max-w-[80%]">
                  <div className="flex items-center gap-2 mb-2">
                    <Cpu className="w-4 h-4 text-k8s-blue" />
                    <span className="text-xs font-medium text-k8s-blue">K8s Assistant</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-k8s-spin" />
                    <span className="text-sm">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        
          {/* Chat Input */}
          <div className="border-t border-k8s-blue/20 p-4">
            <form onSubmit={handleSendMessage} className="flex gap-3">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Ask about your Kubernetes cluster..."
                className="flex-1 k8s-input"
                disabled={isLoading}
              />
              <button
                type="submit"
                className="k8s-button-primary px-6 py-3"
                disabled={isLoading || !message.trim()}
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-k8s-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserDashboard;