"""
Authentication Middleware for K8s Audit Bot
Provides authentication and authorization decorators for Flask routes
"""

import os
import logging
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable

from utils.jwt_utils import JWTUtils

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom authentication error"""
    def __init__(self, message: str, status_code: int = 401, error_code: str = "AUTH_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class AuthorizationError(Exception):
    """Custom authorization error"""
    def __init__(self, message: str, status_code: int = 403, error_code: str = "INSUFFICIENT_PERMISSIONS"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class AuthMiddleware:
    """Main authentication middleware class"""

    def __init__(self, db, jwt_utils: JWTUtils):
        """Initialize authentication middleware

        Args:
            db: Database instance
            jwt_utils: JWT utilities instance
        """
        self.db = db
        self.jwt_utils = jwt_utils
        self.session_enabled = os.getenv('ENABLE_SESSION_AUTH', 'true').lower() == 'true'
        self.jwt_enabled = jwt_utils.is_jwt_enabled()

        logger.info(f"AuthMiddleware initialized - Session auth: {self.session_enabled}, JWT auth: {self.jwt_enabled}")

    def extract_session_id(self, request_obj) -> Optional[str]:
        """Extract session ID from request"""
        # Try header first
        session_id = request_obj.headers.get('X-Session-ID')
        if session_id:
            return session_id

        # Try request body (for POST requests)
        if request_obj.is_json:
            data = request_obj.get_json(silent=True)
            if data and 'session_id' in data:
                return data['session_id']

        # Try query parameter
        return request_obj.args.get('session_id')

    def extract_jwt_token(self, request_obj) -> Optional[str]:
        """Extract JWT token from request"""
        # Try Authorization header first
        auth_header = request_obj.headers.get('Authorization')
        if auth_header:
            return self.jwt_utils.extract_token_from_header(auth_header)

        return None

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate session against database

        Args:
            session_id: Session ID to validate

        Returns:
            User information if valid, None otherwise
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # Get session and user info
            cursor.execute("""
                SELECT s.user_id, s.last_activity, s.is_active,
                       u.username, u.role, u.is_banned
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_id = %s
            """, (session_id,))

            result = cursor.fetchone()
            cursor.close()
            self.db._put_connection(conn)

            if not result:
                logger.warning(f"Session not found: {session_id}")
                return None

            user_id, last_activity, is_active, username, role, is_banned = result

            # Check if session is active
            if not is_active:
                logger.warning(f"Inactive session: {session_id}")
                return None

            # Check if user is banned
            if is_banned:
                logger.warning(f"Banned user attempting access: {username}")
                return None

            # Check session expiration (7 days by default)
            session_exp_days = int(os.getenv('SESSION_EXPIRATION_DAYS', '7'))
            if datetime.utcnow() > last_activity + timedelta(days=session_exp_days):
                logger.warning(f"Expired session: {session_id}")
                return None

            # Update last activity
            self.db.update_session_activity(session_id)

            logger.info(f"Valid session: {session_id} for user {username} (ID: {user_id})")
            return {
                'user_id': user_id,
                'username': username,
                'role': role,
                'session_id': session_id
            }

        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return None

    def authenticate_request(self, request_obj) -> Optional[Dict[str, Any]]:
        """
        Authenticate request using JWT or session

        Args:
            request_obj: Flask request object

        Returns:
            User information if authenticated, None otherwise
        """
        # Try JWT authentication first
        if self.jwt_enabled:
            jwt_token = self.extract_jwt_token(request_obj)
            if jwt_token:
                user_info = self.jwt_utils.get_user_from_token(jwt_token)
                if user_info:
                    logger.info(f"JWT authenticated: {user_info['username']} (ID: {user_info['user_id']})")
                    return user_info

        # Fall back to session authentication
        if self.session_enabled:
            session_id = self.extract_session_id(request_obj)
            if session_id:
                user_info = self.validate_session(session_id)
                if user_info:
                    return user_info

        logger.warning("No valid authentication found")
        return None

    def require_authentication(self, f: Callable) -> Callable:
        """Decorator requiring authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Authenticate request
                user_info = self.authenticate_request(request)
                if not user_info:
                    raise AuthenticationError(
                        message="Please provide valid session_id or JWT token",
                        error_code="AUTH_REQUIRED"
                    )

                # Add user info to request context
                request.current_user = user_info

                return f(*args, **kwargs)

            except AuthenticationError as e:
                return jsonify({
                    'error': e.error_code,
                    'message': e.message,
                    'timestamp': datetime.utcnow().isoformat()
                }), e.status_code

            except Exception as e:
                logger.error(f"Unexpected authentication error: {str(e)}")
                return jsonify({
                    'error': 'INTERNAL_ERROR',
                    'message': 'Authentication service unavailable',
                    'timestamp': datetime.utcnow().isoformat()
                }), 500

        return decorated_function

    def require_admin(self, f: Callable) -> Callable:
        """Decorator requiring admin role"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # First authenticate
                user_info = self.authenticate_request(request)
                if not user_info:
                    raise AuthenticationError(
                        message="Please provide valid session_id or JWT token",
                        error_code="AUTH_REQUIRED"
                    )

                # Check admin role
                if user_info['role'] != 'admin':
                    raise AuthorizationError(
                        message="Admin role required for this endpoint",
                        error_code="INSUFFICIENT_PERMISSIONS"
                    )

                # Add user info to request context
                request.current_user = user_info

                return f(*args, **kwargs)

            except (AuthenticationError, AuthorizationError) as e:
                return jsonify({
                    'error': e.error_code,
                    'message': e.message,
                    'timestamp': datetime.utcnow().isoformat()
                }), e.status_code

            except Exception as e:
                logger.error(f"Unexpected authentication error: {str(e)}")
                return jsonify({
                    'error': 'INTERNAL_ERROR',
                    'message': 'Authentication service unavailable',
                    'timestamp': datetime.utcnow().isoformat()
                }), 500

        return decorated_function

    def require_ownership(self, user_id_param: str = 'user_id') -> Callable:
        """
        Decorator requiring user ownership verification

        Args:
            user_id_param: Name of the parameter containing the target user ID
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    # First authenticate
                    user_info = self.authenticate_request(request)
                    if not user_info:
                        raise AuthenticationError(
                            message="Please provide valid session_id or JWT token",
                            error_code="AUTH_REQUIRED"
                        )

                    # Get target user ID from various sources
                    target_user_id = None

                    # Try request body
                    if request.is_json:
                        data = request.get_json(silent=True)
                        if data and user_id_param in data:
                            target_user_id = data[user_id_param]

                    # Try query parameters
                    if not target_user_id:
                        target_user_id = request.args.get(user_id_param)

                    # Try URL parameters (for Flask routes)
                    if not target_user_id and user_id_param in kwargs:
                        target_user_id = kwargs[user_id_param]

                    if target_user_id:
                        target_user_id = int(target_user_id)

                    # Check ownership - admin can access any user data
                    if user_info['role'] != 'admin' and user_info['user_id'] != target_user_id:
                        raise AuthorizationError(
                            message="You can only access your own data",
                            error_code="INSUFFICIENT_PERMISSIONS"
                        )

                    # Add user info to request context
                    request.current_user = user_info

                    return f(*args, **kwargs)

                except (AuthenticationError, AuthorizationError) as e:
                    return jsonify({
                        'error': e.error_code,
                        'message': e.message,
                        'timestamp': datetime.utcnow().isoformat()
                    }), e.status_code

                except Exception as e:
                    logger.error(f"Unexpected authentication error: {str(e)}")
                    return jsonify({
                        'error': 'INTERNAL_ERROR',
                        'message': 'Authentication service unavailable',
                        'timestamp': datetime.utcnow().isoformat()
                    }), 500

            return decorated_function
        return decorator

# Decorator functions for direct use (without middleware instance)
def require_auth(f: Callable) -> Callable:
    """Decorator requiring authentication (uses app context)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(current_app, 'auth_middleware'):
            return jsonify({
                'error': 'CONFIGURATION_ERROR',
                'message': 'Authentication middleware not configured',
                'timestamp': datetime.utcnow().isoformat()
            }), 500

        return current_app.auth_middleware.require_authentication(f)(*args, **kwargs)

    return decorated_function

def require_admin(f: Callable) -> Callable:
    """Decorator requiring admin role (uses app context)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(current_app, 'auth_middleware'):
            return jsonify({
                'error': 'CONFIGURATION_ERROR',
                'message': 'Authentication middleware not configured',
                'timestamp': datetime.utcnow().isoformat()
            }), 500

        return current_app.auth_middleware.require_admin(f)(*args, **kwargs)

    return decorated_function

def require_ownership(user_id_param: str = 'user_id') -> Callable:
    """Decorator requiring user ownership (uses app context)"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(current_app, 'auth_middleware'):
                return jsonify({
                    'error': 'CONFIGURATION_ERROR',
                    'message': 'Authentication middleware not configured',
                    'timestamp': datetime.utcnow().isoformat()
                }), 500

            return current_app.auth_middleware.require_ownership(user_id_param)(f)(*args, **kwargs)

        return decorated_function
    return decorator