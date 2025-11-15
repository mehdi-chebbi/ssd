import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

class AuthService {
  constructor() {
    // Create base API instance
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to include session ID for auth calls
    this.api.interceptors.request.use(
      (config) => {
        const sessionId = localStorage.getItem('sessionId');
        if (sessionId) {
          config.headers['X-Session-ID'] = sessionId;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );
  }

  async signup(userData) {
    try {
      const response = await this.api.post('/auth/signup', {
        username: userData.username,
        email: userData.email,
        password: userData.password,
      });

      return {
        success: response.data.success,
        message: response.data.message,
        error: response.data.error,
        userId: response.data.user_id,
      };
    } catch (error) {
      console.error('Signup error:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Registration failed. Please try again.',
      };
    }
  }

  async login(username, password) {
    try {
      const response = await this.api.post('/auth/login', {
        username,
        password,
      });

      if (response.data.user) {
        // Store session and user data
        localStorage.setItem('sessionId', response.data.session_id);
        localStorage.setItem('userData', JSON.stringify(response.data.user));
        
        return {
          success: true,
          user: response.data.user,
          sessionId: response.data.session_id,
        };
      }
      return { success: false, error: 'Invalid response from server' };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Login failed. Please try again.',
      };
    }
  }

  async logout(sessionId) {
    try {
      await this.api.post('/auth/logout', {
        session_id: sessionId,
      });
      
      // Clear local storage
      localStorage.removeItem('sessionId');
      localStorage.removeItem('userData');
      
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      // Still clear local storage even if API call fails
      localStorage.removeItem('sessionId');
      localStorage.removeItem('userData');
      return { success: false, error: 'Logout failed' };
    }
  }

  isAuthenticated() {
    const sessionId = localStorage.getItem('sessionId');
    const userData = localStorage.getItem('userData');
    return !!(sessionId && userData);
  }

  getCurrentUser() {
    const userData = localStorage.getItem('userData');
    return userData ? JSON.parse(userData) : null;
  }

  getSessionId() {
    return localStorage.getItem('sessionId');
  }

  isAdmin() {
    const user = this.getCurrentUser();
    return user && user.role === 'admin';
  }
}

export const authService = new AuthService();