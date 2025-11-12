import React, { useState, useEffect } from 'react';
import { Users, Activity, LogOut, Settings, Database, Shield, Cpu, AlertCircle, TrendingUp, Eye, EyeOff, UserPlus, Loader2 } from 'lucide-react';
import { apiService } from '../services/apiService';

const AdminDashboard = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [health, setHealth] = useState(null);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [createUserForm, setCreateUserForm] = useState({
    username: '',
    email: '',
    password: '',
    role: 'user'
  });
  const [loading, setLoading] = useState({
    users: false,
    logs: false,
    health: false,
    create: false
  });
  const [error, setError] = useState('');

  useEffect(() => {
    loadHealth();
    loadUsers();
    loadLogs();
  }, []);

  const loadHealth = async () => {
    setLoading(prev => ({ ...prev, health: true }));
    try {
      const result = await apiService.getHealth();
      if (result.success) {
        setHealth(result.data);
      } else {
        setError('Failed to load health data');
      }
    } catch (error) {
      setError('Error loading health data');
    } finally {
      setLoading(prev => ({ ...prev, health: false }));
    }
  };

  const loadUsers = async () => {
    setLoading(prev => ({ ...prev, users: true }));
    try {
      const result = await apiService.getUsers();
      if (result.success) {
        setUsers(result.users);
      } else {
        setError(result.error);
      }
    } catch (error) {
      setError('Error loading users');
    } finally {
      setLoading(prev => ({ ...prev, users: false }));
    }
  };

  const loadLogs = async () => {
    setLoading(prev => ({ ...prev, logs: true }));
    try {
      const result = await apiService.getActivityLogs(null, 50);
      if (result.success) {
        setLogs(result.logs);
      } else {
        setError(result.error);
      }
    } catch (error) {
      setError('Error loading logs');
    } finally {
      setLoading(prev => ({ ...prev, logs: false }));
    }
  };

  const handleBanUser = async (userId) => {
    try {
      const result = await apiService.banUser(userId);
      if (result.success) {
        loadUsers(); // Refresh users list
      } else {
        setError(result.error);
      }
    } catch (error) {
      setError('Error banning user');
    }
  };

  const handleUnbanUser = async (userId) => {
    try {
      const result = await apiService.unbanUser(userId);
      if (result.success) {
        loadUsers(); // Refresh users list
      } else {
        setError(result.error);
      }
    } catch (error) {
      setError('Error unbanning user');
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    
    if (!createUserForm.username || !createUserForm.email || !createUserForm.password) {
      setError('Please fill in all fields');
      return;
    }

    setLoading(prev => ({ ...prev, create: true }));
    setError('');

    try {
      const result = await apiService.createUser(createUserForm);
      
      if (result.success) {
        setShowCreateUser(false);
        setCreateUserForm({ username: '', email: '', password: '', role: 'user' });
        loadUsers(); // Refresh users list
      } else {
        setError(result.error);
      }
    } catch (error) {
      setError('Error creating user');
    } finally {
      setLoading(prev => ({ ...prev, create: false }));
    }
  };

  const handleCreateUserChange = (e) => {
    const { name, value } = e.target;
    setCreateUserForm(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError('');
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
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
                <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
                <p className="text-k8s-gray text-sm">Welcome back, {user.username}</p>
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

      {/* Error Display */}
      {error && (
        <div className="max-w-7xl mx-auto px-6 pt-4">
          <div className="k8s-card p-4 border-red-500/30 bg-red-500/10 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Navigation Tabs */}
        <div className="flex gap-1 mb-8 bg-k8s-dark/30 p-1 rounded-lg w-fit">
          {['overview', 'users', 'logs', 'settings'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 rounded-md font-medium transition-all duration-200 ${
                activeTab === tab
                  ? 'bg-k8s-blue text-white shadow-lg'
                  : 'text-k8s-gray hover:text-white hover:bg-white/5'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-white mb-6">System Overview</h2>
            
            {health && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="k8s-card p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">Database</h3>
                    <Database className="w-6 h-6 text-k8s-blue" />
                  </div>
                  <p className={`text-sm font-medium ${
                    health.database?.status === 'healthy' ? 'text-k8s-green' : 'text-k8s-orange'
                  }`}>
                    {health.database?.status || 'Unknown'}
                  </p>
                  {health.database?.stats && (
                    <div className="mt-2 text-k8s-gray text-sm">
                      <p>Users: {health.database.stats.users}</p>
                      <p>Sessions: {health.database.stats.sessions}</p>
                      <p>Messages: {health.database.stats.messages}</p>
                    </div>
                  )}
                </div>

                <div className="k8s-card p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">Kubernetes</h3>
                    <Shield className="w-6 h-6 text-k8s-cyan" />
                  </div>
                  <p className={`text-sm font-medium ${
                    health.kubernetes?.status === 'connected' ? 'text-k8s-green' : 'text-k8s-orange'
                  }`}>
                    {health.kubernetes?.status || 'Unknown'}
                  </p>
                </div>

                <div className="k8s-card p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">AI Classifier</h3>
                    <Cpu className="w-6 h-6 text-k8s-purple" />
                  </div>
                  <p className={`text-sm font-medium ${
                    health.classifier?.status === 'healthy' ? 'text-k8s-green' : 'text-k8s-orange'
                  }`}>
                    {health.classifier?.status || 'Unknown'}
                  </p>
                </div>

                <div className="k8s-card p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">System Status</h3>
                    <Activity className="w-6 h-6 text-k8s-green" />
                  </div>
                  <p className={`text-sm font-medium ${
                    health.status === 'healthy' ? 'text-k8s-green' : 'text-k8s-orange'
                  }`}>
                    {health.status || 'Unknown'}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-white">User Management</h2>
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setShowCreateUser(true)}
                  className="k8s-button-primary flex items-center gap-2"
                >
                  <UserPlus className="w-4 h-4" />
                  Create User
                </button>
                <Users className="w-6 h-6 text-k8s-blue" />
              </div>
            </div>

            {/* Create User Modal */}
            {showCreateUser && (
              <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                <div className="k8s-card p-6 w-full max-w-md mx-4">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-xl font-bold text-white">Create New User</h3>
                    <button
                      onClick={() => setShowCreateUser(false)}
                      className="text-k8s-gray hover:text-white transition-colors"
                    >
                      ×
                    </button>
                  </div>

                  {error && (
                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                      <span className="text-red-300 text-sm">{error}</span>
                    </div>
                  )}

                  <form onSubmit={handleCreateUser} className="space-y-4">
                    {/* Username Field */}
                    <div>
                      <label htmlFor="create-username" className="block text-sm font-medium text-k8s-gray mb-2">
                        Username
                      </label>
                      <input
                        type="text"
                        id="create-username"
                        name="username"
                        value={createUserForm.username}
                        onChange={handleCreateUserChange}
                        className="k8s-input w-full"
                        placeholder="Enter username"
                        disabled={loading.create}
                      />
                    </div>

                    {/* Email Field */}
                    <div>
                      <label htmlFor="create-email" className="block text-sm font-medium text-k8s-gray mb-2">
                        Email
                      </label>
                      <input
                        type="email"
                        id="create-email"
                        name="email"
                        value={createUserForm.email}
                        onChange={handleCreateUserChange}
                        className="k8s-input w-full"
                        placeholder="Enter email"
                        disabled={loading.create}
                      />
                    </div>

                    {/* Password Field */}
                    <div>
                      <label htmlFor="create-password" className="block text-sm font-medium text-k8s-gray mb-2">
                        Password
                      </label>
                      <input
                        type="password"
                        id="create-password"
                        name="password"
                        value={createUserForm.password}
                        onChange={handleCreateUserChange}
                        className="k8s-input w-full"
                        placeholder="Enter password"
                        disabled={loading.create}
                      />
                    </div>

                    {/* Role Field */}
                    <div>
                      <label htmlFor="create-role" className="block text-sm font-medium text-k8s-gray mb-2">
                        Role
                      </label>
                      <select
                        id="create-role"
                        name="role"
                        value={createUserForm.role}
                        onChange={handleCreateUserChange}
                        className="k8s-input w-full"
                        disabled={loading.create}
                      >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                      </select>
                    </div>

                    {/* Submit Button */}
                    <div className="flex gap-3 pt-4">
                      <button
                        type="button"
                        onClick={() => setShowCreateUser(false)}
                        className="k8s-button-secondary flex-1"
                        disabled={loading.create}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={loading.create}
                        className="k8s-button-primary flex-1 flex items-center justify-center gap-2"
                      >
                        {loading.create ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-k8s-spin" />
                            Creating...
                          </>
                        ) : (
                          <>
                            <UserPlus className="w-4 h-4" />
                            Create User
                          </>
                        )}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
            
            {loading.users ? (
              <div className="text-center py-12">
                <div className="k8s-loader mx-auto"></div>
                <p className="text-k8s-gray mt-4">Loading users...</p>
              </div>
            ) : (
              <div className="k8s-card overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-k8s-dark/50 border-b border-k8s-blue/20">
                      <tr>
                        <th className="text-left py-4 px-6 text-k8s-gray font-semibold">User</th>
                        <th className="text-left py-4 px-6 text-k8s-gray font-semibold">Role</th>
                        <th className="text-left py-4 px-6 text-k8s-gray font-semibold">Status</th>
                        <th className="text-left py-4 px-6 text-k8s-gray font-semibold">Created</th>
                        <th className="text-left py-4 px-6 text-k8s-gray font-semibold">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user) => (
                        <tr key={user.id} className="border-b border-k8s-blue/10 hover:bg-k8s-blue/5 transition-colors">
                          <td className="py-4 px-6">
                            <div>
                              <p className="text-white font-medium">{user.username}</p>
                              <p className="text-k8s-gray text-sm">{user.email}</p>
                            </div>
                          </td>
                          <td className="py-4 px-6">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              user.role === 'admin' 
                                ? 'bg-k8s-purple/20 text-k8s-purple' 
                                : 'bg-k8s-blue/20 text-k8s-blue'
                            }`}>
                              {user.role}
                            </span>
                          </td>
                          <td className="py-4 px-6">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              user.is_banned 
                                ? 'bg-red-500/20 text-red-400' 
                                : 'bg-k8s-green/20 text-k8s-green'
                            }`}>
                              {user.is_banned ? 'Banned' : 'Active'}
                            </span>
                          </td>
                          <td className="py-4 px-6 text-k8s-gray text-sm">
                            {formatDate(user.created_at)}
                          </td>
                          <td className="py-4 px-6">
                            <div className="flex gap-2">
                              {user.is_banned ? (
                                <button
                                  onClick={() => handleUnbanUser(user.id)}
                                  className="px-3 py-1 bg-k8s-green/20 text-k8s-green rounded text-sm hover:bg-k8s-green/30 transition-colors"
                                >
                                  Unban
                                </button>
                              ) : (
                                <button
                                  onClick={() => handleBanUser(user.id)}
                                  className="px-3 py-1 bg-red-500/20 text-red-400 rounded text-sm hover:bg-red-500/30 transition-colors"
                                >
                                  Ban
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Logs Tab */}
        {activeTab === 'logs' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-white">System Logs</h2>
              <Activity className="w-6 h-6 text-k8s-orange" />
            </div>
            
            {loading.logs ? (
              <div className="text-center py-12">
                <div className="k8s-loader mx-auto"></div>
                <p className="text-k8s-gray mt-4">Loading logs...</p>
              </div>
            ) : (
              <div className="k8s-card">
                <div className="max-h-96 overflow-y-auto k8s-chat-scroll">
                  {logs.map((log, index) => (
                    <div key={index} className="border-b border-k8s-blue/10 pb-4 mb-4 last:border-0">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            log.success 
                              ? 'bg-k8s-green/20 text-k8s-green' 
                              : 'bg-red-500/20 text-red-400'
                          }`}>
                            {log.action_type}
                          </span>
                          <span className="text-k8s-gray text-sm">
                            {formatDate(log.timestamp)}
                          </span>
                        </div>
                      </div>
                      {log.command && (
                        <p className="text-k8s-gray font-mono text-sm bg-k8s-dark/30 p-2 rounded mb-2">
                          {log.command}
                        </p>
                      )}
                      {log.error_message && (
                        <p className="text-red-400 text-sm">{log.error_message}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-white mb-6">Settings</h2>
            <div className="k8s-card p-8">
              <p className="text-k8s-gray text-center">
                Settings panel coming soon... This will include system configuration, 
                backup settings, and administrative preferences.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;