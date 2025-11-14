import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

class AuthService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
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
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
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
}

export const authService = new AuthService();