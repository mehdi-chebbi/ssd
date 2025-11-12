import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
import bcrypt
from datetime import datetime
from typing import Optional, Dict, Any, List
import json

logger = logging.getLogger(__name__)

class Database:
    """Database manager for K8s Audit Bot using PostgreSQL"""
    
    def __init__(self, host='localhost', port=5432, database='k8s_bot', 
                 user='bot_user', password='bot_password_123', min_conn=1, max_conn=10):
        """Initialize database connection pool"""
        self.connection_pool = None
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                min_conn,
                max_conn,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            
            if self.connection_pool:
                logger.info(f"Connected to PostgreSQL database: {database}")
                self._init_tables()
            else:
                raise Exception("Failed to create connection pool")
                
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def _get_connection(self):
        """Get a connection from the pool"""
        return self.connection_pool.getconn()
    
    def _put_connection(self, conn):
        """Return a connection to the pool"""
        self.connection_pool.putconn(conn)
    
    def _init_tables(self):
        """Initialize database tables if they don't exist"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Drop and recreate users table to ensure correct schema
            cursor.execute("DROP TABLE IF EXISTS activity_logs CASCADE")
            cursor.execute("DROP TABLE IF EXISTS chat_history CASCADE")
            cursor.execute("DROP TABLE IF EXISTS sessions CASCADE")
            cursor.execute("DROP TABLE IF EXISTS user_preferences CASCADE")
            cursor.execute("DROP TABLE IF EXISTS users CASCADE")
            
            # Users table
            cursor.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    is_banned BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL,
                    last_login TIMESTAMP,
                    CONSTRAINT role_check CHECK (role IN ('admin', 'user'))
                )
            """)
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    tone VARCHAR(100) DEFAULT 'casual',
                    response_style VARCHAR(100) DEFAULT 'detailed',
                    personality VARCHAR(100) DEFAULT 'friendly',
                    max_commands_preference INTEGER DEFAULT 3,
                    auto_investigate BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Activity logs table (for admin - NO message content)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    action_type VARCHAR(100) NOT NULL,
                    command TEXT,
                    classification_type VARCHAR(100),
                    success BOOLEAN,
                    error_message TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Chat history table (for users - contains actual messages)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_id VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    message TEXT NOT NULL,
                    commands_executed JSONB,
                    classification_info JSONB,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT role_check CHECK (role IN ('user', 'assistant'))
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            """)
            
            conn.commit()
            logger.info("Database tables initialized successfully")
            
            # Create default admin if no users exist
            self._create_default_admin()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to initialize database tables: {str(e)}")
            raise
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def _create_default_admin(self):
        """Create default admin user if no users exist"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result = cursor.fetchone()
            
            if result['count'] == 0:
                # Create default admin
                default_password = "admin123"  # Should be changed on first login
                password_hash = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())
                
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, ("admin", "admin@localhost", password_hash.decode('utf-8'), "admin", datetime.now()))
                
                conn.commit()
                logger.info("Default admin user created (username: admin, password: admin123)")
                logger.warning("IMPORTANT: Change the default admin password immediately!")
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create default admin: {str(e)}")
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, username: str, email: str, password: str, role: str = 'user') -> Optional[int]:
        """Create a new user"""
        conn = None
        try:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (username, email, password_hash.decode('utf-8'), role, datetime.now()))
            
            user_id = cursor.fetchone()[0]
            
            # Create default preferences
            cursor.execute("""
                INSERT INTO user_preferences (user_id, updated_at)
                VALUES (%s, %s)
            """, (user_id, datetime.now()))
            
            conn.commit()
            logger.info(f"User created: {username} (ID: {user_id})")
            return user_id
        
        except psycopg2.IntegrityError as e:
            if conn:
                conn.rollback()
            logger.error(f"User creation failed - duplicate username/email: {str(e)}")
            return None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create user: {str(e)}")
            return None
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return user info"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, username, email, password_hash, role, is_banned
                FROM users
                WHERE username = %s
            """, (username,))
            
            user = cursor.fetchone()
            
            if not user:
                logger.warning(f"Authentication failed - user not found: {username}")
                return None
            
            if user['is_banned']:
                logger.warning(f"Authentication failed - user is banned: {username}")
                return None
            
            # Verify password
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                # Update last login
                cursor.execute("""
                    UPDATE users SET last_login = %s WHERE id = %s
                """, (datetime.now(), user['id']))
                conn.commit()
                
                logger.info(f"User authenticated: {username}")
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role']
                }
            else:
                logger.warning(f"Authentication failed - invalid password: {username}")
                return None
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, username, email, role, is_banned, created_at, last_login
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            return dict(user) if user else None
        
        except Exception as e:
            logger.error(f"Failed to get user: {str(e)}")
            return None
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (for admin dashboard)"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, username, email, role, is_banned, created_at, last_login
                FROM users
                ORDER BY created_at DESC
            """)
            
            users = cursor.fetchall()
            return [dict(user) for user in users]
        
        except Exception as e:
            logger.error(f"Failed to get users: {str(e)}")
            return []
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Update user role"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET role = %s WHERE id = %s
            """, (new_role, user_id))
            
            conn.commit()
            logger.info(f"User role updated: ID {user_id} -> {new_role}")
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to update user role: {str(e)}")
            return False
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET is_banned = TRUE WHERE id = %s
            """, (user_id,))
            
            conn.commit()
            logger.info(f"User banned: ID {user_id}")
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to ban user: {str(e)}")
            return False
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET is_banned = FALSE WHERE id = %s
            """, (user_id,))
            
            conn.commit()
            logger.info(f"User unbanned: ID {user_id}")
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to unban user: {str(e)}")
            return False
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def change_password(self, user_id: int, new_password: str) -> bool:
        """Change user password"""
        conn = None
        try:
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET password_hash = %s WHERE id = %s
            """, (password_hash.decode('utf-8'), user_id))
            
            conn.commit()
            logger.info(f"Password changed for user ID: {user_id}")
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to change password: {str(e)}")
            return False
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    # ==================== USER PREFERENCES ====================
    
    def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT tone, response_style, personality, max_commands_preference, auto_investigate
                FROM user_preferences
                WHERE user_id = %s
            """, (user_id,))
            
            prefs = cursor.fetchone()
            return dict(prefs) if prefs else None
        
        except Exception as e:
            logger.error(f"Failed to get user preferences: {str(e)}")
            return None
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build dynamic update query
            fields = []
            values = []
            
            for key in ['tone', 'response_style', 'personality', 'max_commands_preference', 'auto_investigate']:
                if key in preferences:
                    fields.append(f"{key} = %s")
                    values.append(preferences[key])
            
            if not fields:
                return False
            
            fields.append("updated_at = %s")
            values.append(datetime.now())
            values.append(user_id)
            
            query = f"UPDATE user_preferences SET {', '.join(fields)} WHERE user_id = %s"
            cursor.execute(query, values)
            
            conn.commit()
            logger.info(f"User preferences updated: ID {user_id}")
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to update user preferences: {str(e)}")
            return False
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    # ==================== ACTIVITY LOGS ====================
    
    def log_activity(self, user_id: int, action_type: str, command: str = None,
                    classification_type: str = None, success: bool = True,
                    error_message: str = None):
        """Log user activity (for admin visibility)"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO activity_logs 
                (user_id, timestamp, action_type, command, classification_type, success, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, datetime.now(), action_type, command,
                  classification_type, success, error_message))
            
            conn.commit()
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to log activity: {str(e)}")
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def get_activity_logs(self, user_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get activity logs (for admin dashboard)"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if user_id:
                cursor.execute("""
                    SELECT l.*, u.username
                    FROM activity_logs l
                    JOIN users u ON l.user_id = u.id
                    WHERE l.user_id = %s
                    ORDER BY l.timestamp DESC
                    LIMIT %s
                """, (user_id, limit))
            else:
                cursor.execute("""
                    SELECT l.*, u.username
                    FROM activity_logs l
                    JOIN users u ON l.user_id = u.id
                    ORDER BY l.timestamp DESC
                    LIMIT %s
                """, (limit,))
            
            logs = cursor.fetchall()
            return [dict(log) for log in logs]
        
        except Exception as e:
            logger.error(f"Failed to get activity logs: {str(e)}")
            return []
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    # ==================== CHAT HISTORY ====================
    
    def save_chat_message(self, user_id: int, session_id: str, role: str, message: str,
                         commands_executed: List[str] = None, classification_info: Dict = None):
        """Save chat message to history"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO chat_history 
                (user_id, session_id, timestamp, role, message, commands_executed, classification_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, session_id, datetime.now(), role, message,
                  json.dumps(commands_executed) if commands_executed else None,
                  json.dumps(classification_info) if classification_info else None))
            
            conn.commit()
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save chat message: {str(e)}")
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def get_chat_history(self, user_id: int, session_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a user"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if session_id:
                cursor.execute("""
                    SELECT id, session_id, timestamp, role, message, commands_executed, classification_info
                    FROM chat_history
                    WHERE user_id = %s AND session_id = %s
                    ORDER BY timestamp ASC
                    LIMIT %s
                """, (user_id, session_id, limit))
            else:
                cursor.execute("""
                    SELECT id, session_id, timestamp, role, message, commands_executed, classification_info
                    FROM chat_history
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (user_id, limit))
            
            history = cursor.fetchall()
            return [dict(msg) for msg in history]
        
        except Exception as e:
            logger.error(f"Failed to get chat history: {str(e)}")
            return []
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT DISTINCT session_id, MIN(timestamp) as started_at, MAX(timestamp) as last_message
                FROM chat_history
                WHERE user_id = %s
                GROUP BY session_id
                ORDER BY last_message DESC
            """, (user_id,))
            
            sessions = cursor.fetchall()
            return [dict(session) for session in sessions]
        
        except Exception as e:
            logger.error(f"Failed to get user sessions: {str(e)}")
            return []
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def delete_chat_history(self, user_id: int, session_id: str = None) -> bool:
        """Delete chat history for a user"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute("""
                    DELETE FROM chat_history WHERE user_id = %s AND session_id = %s
                """, (user_id, session_id))
            else:
                cursor.execute("""
                    DELETE FROM chat_history WHERE user_id = %s
                """, (user_id,))
            
            conn.commit()
            logger.info(f"Chat history deleted for user ID: {user_id}")
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to delete chat history: {str(e)}")
            return False
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    # ==================== SESSIONS ====================
    
    def create_session(self, user_id: int, session_id: str) -> bool:
        """Create a new session"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.now()
            
            cursor.execute("""
                INSERT INTO sessions (user_id, session_id, created_at, last_activity)
                VALUES (%s, %s, %s, %s)
            """, (user_id, session_id, now, now))
            
            conn.commit()
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create session: {str(e)}")
            return False
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sessions SET last_activity = %s WHERE session_id = %s
            """, (datetime.now(), session_id))
            
            conn.commit()
            return True
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to update session activity: {str(e)}")
            return False
        finally:
            if conn:
                cursor.close()
                self._put_connection(conn)
    
    def close_all(self):
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("All database connections closed")