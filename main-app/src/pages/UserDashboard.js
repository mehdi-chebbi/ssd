import React, { useState, useEffect } from 'react';
import { LogOut, Cpu, MessageSquare, Settings, User, Clock, Zap, AlertTriangle, Wrench } from 'lucide-react';

const UserDashboard = ({ user, onLogout }) => {
  const [greeting, setGreeting] = useState('');

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

  const features = [
    {
      icon: MessageSquare,
      title: 'Chat Interface',
      description: 'Natural language conversation with your Kubernetes infrastructure',
      status: 'coming-soon',
      color: 'text-k8s-blue'
    },
    {
      icon: Zap,
      title: 'Quick Commands',
      description: 'Execute common kubectl commands with one click',
      status: 'coming-soon',
      color: 'text-k8s-cyan'
    },
    {
      icon: Clock,
      title: 'History',
      description: 'View your past interactions and conversations',
      status: 'coming-soon',
      color: 'text-k8s-orange'
    },
    {
      icon: Settings,
      title: 'Preferences',
      description: 'Customize your AI assistant behavior and responses',
      status: 'coming-soon',
      color: 'text-k8s-purple'
    }
  ];

  const comingSoonFeatures = [
    {
      icon: Wrench,
      title: 'Automated Troubleshooting',
      description: 'AI-powered automatic problem detection and resolution'
    },
    {
      icon: AlertTriangle,
      title: 'Real-time Alerts',
      description: 'Instant notifications for cluster issues and anomalies'
    },
    {
      icon: MessageSquare,
      title: 'Multi-turn Conversations',
      description: 'Context-aware conversations with follow-up questions'
    },
    {
      icon: Zap,
      title: 'Command Suggestions',
      description: 'Smart kubectl command suggestions based on your intent'
    }
  ];

  return (
    <div className="k8s-container min-h-screen">
      {/* Header */}
      <div className="k8s-glass border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Cpu className="w-8 h-8 text-k8s-blue" />
              <div>
                <h1 className="text-2xl font-bold text-white">User Dashboard</h1>
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
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-3 mb-4">
            <User className="w-8 h-8 text-k8s-cyan" />
            <h2 className="text-4xl font-bold text-white">
              Welcome, {user.username}!
            </h2>
          </div>
          <p className="text-xl text-k8s-gray max-w-2xl mx-auto">
            Your AI-powered Kubernetes assistant is ready to help you manage and investigate your infrastructure.
          </p>
        </div>

        {/* Main Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <div key={index} className="k8s-card p-6 hover:scale-105 transition-all duration-300 relative overflow-hidden">
                <div className="absolute top-0 right-0">
                  <span className="bg-k8s-orange text-k8s-darker text-xs px-2 py-1 rounded-bl-lg font-medium">
                    Coming Soon
                  </span>
                </div>
                
                <div className="w-12 h-12 bg-k8s-blue/20 rounded-lg flex items-center justify-center mb-4">
                  <Icon className={`w-6 h-6 ${feature.color}`} />
                </div>
                
                <h3 className="text-lg font-bold text-white mb-3">{feature.title}</h3>
                <p className="text-k8s-gray text-sm leading-relaxed">{feature.description}</p>
                
                <div className="mt-4 pt-4 border-t border-k8s-blue/10">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-k8s-orange rounded-full animate-k8s-pulse"></div>
                    <span className="text-k8s-orange text-xs font-medium">Under Development</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Chat Interface - Under Construction */}
        <div className="mb-12">
          <div className="text-center mb-8">
            <h3 className="text-2xl font-bold text-white mb-4">Chat Interface</h3>
            <p className="text-k8s-gray mb-6">
              The AI chat interface is currently under construction. 
              This will be your main interaction point with the Kubernetes assistant.
            </p>
          </div>
          
          <div className="k8s-card p-8 relative">
            <div className="absolute inset-0 flex items-center justify-center bg-k8s-darker/90 backdrop-blur-sm">
              <div className="text-center">
                <MessageSquare className="w-16 h-16 text-k8s-blue mx-auto mb-4 animate-k8s-bounce" />
                <h4 className="text-xl font-bold text-white mb-2">Under Construction</h4>
                <p className="text-k8s-gray mb-4">
                  We're building an amazing chat experience for you.
                </p>
                <div className="flex items-center justify-center gap-2 text-k8s-cyan">
                  <Zap className="w-4 h-4" />
                  <span className="text-sm font-medium">Coming Soon</span>
                </div>
              </div>
            </div>
            
            {/* Mock Chat Interface Preview */}
            <div className="opacity-20">
              <div className="space-y-4 mb-6">
                <div className="flex justify-end">
                  <div className="bg-k8s-blue/20 rounded-lg px-4 py-2 max-w-xs">
                    <p className="text-white text-sm">Show me all pods in the default namespace</p>
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className="bg-k8s-dark/50 rounded-lg px-4 py-2 max-w-xs">
                    <p className="text-k8s-gray text-sm">I found 3 pods running in the default namespace...</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Coming Soon Features */}
        <div className="mb-12">
          <h3 className="text-2xl font-bold text-white text-center mb-8">What's Coming Next</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {comingSoonFeatures.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div key={index} className="k8s-card p-6 flex gap-4">
                  <div className="w-10 h-10 bg-k8s-blue/20 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Icon className="w-5 h-5 text-k8s-blue" />
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-white mb-2">{feature.title}</h4>
                    <p className="text-k8s-gray text-sm">{feature.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Progress Indicator */}
        <div className="text-center">
          <div className="k8s-glass p-6 rounded-lg inline-block">
            <h4 className="text-lg font-semibold text-white mb-4">Development Progress</h4>
            <div className="w-64 bg-k8s-dark/50 rounded-full h-3 mb-2">
              <div className="bg-gradient-to-r from-k8s-blue to-k8s-cyan h-3 rounded-full" style={{width: '35%'}}></div>
            </div>
            <p className="text-k8s-gray text-sm">Core Infrastructure Complete • AI Chat in Development</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserDashboard;