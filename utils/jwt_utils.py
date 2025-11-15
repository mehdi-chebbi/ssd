"""
JWT Utilities for K8s Audit Bot
Handles JWT token generation, validation, and management
"""

import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class JWTUtils:
    """Utility class for JWT token operations"""

    def __init__(self):
        """Initialize JWT utilities with configuration"""
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable is required for JWT authentication")

        self.algorithm = 'HS256'
        self.default_expiration_hours = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
        self.issuer = 'k8s-audit-bot'

    def generate_jwt_token(self, user_id: int, username: str, role: str,
                          expires_in_hours: Optional[int] = None) -> str:
        """
        Generate a JWT token for a user

        Args:
            user_id: User ID from database
            username: Username
            role: User role (admin/user)
            expires_in_hours: Custom expiration time in hours

        Returns:
            JWT token string
        """
        try:
            expiration_hours = expires_in_hours or self.default_expiration_hours
            expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)

            payload = {
                'user_id': user_id,
                'username': username,
                'role': role,
                'iat': datetime.utcnow(),
                'exp': expires_at,
                'iss': self.issuer,
                'type': 'access'
            }

            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

            logger.info(f"Generated JWT token for user {username} (ID: {user_id}), expires: {expires_at}")
            return token

        except Exception as e:
            logger.error(f"Failed to generate JWT token: {str(e)}")
            raise

    def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate and decode a JWT token

        Args:
            token: JWT token string

        Returns:
            Token payload if valid, None if invalid
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]

            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Validate token type and issuer
            if payload.get('type') != 'access':
                logger.warning("Invalid token type: expected 'access'")
                return None

            if payload.get('iss') != self.issuer:
                logger.warning("Invalid token issuer")
                return None

            # Check if token is expired
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                logger.warning("Token has expired")
                return None

            logger.info(f"Validated JWT token for user {payload.get('username')} (ID: {payload.get('user_id')})")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error validating JWT token: {str(e)}")
            return None

    def is_token_expired(self, token: str) -> bool:
        """
        Check if a JWT token is expired

        Args:
            token: JWT token string

        Returns:
            True if expired, False if not expired or invalid
        """
        try:
            if token.startswith('Bearer '):
                token = token[7:]

            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})

            # If token doesn't have exp claim, consider it not expired (but invalid)
            if 'exp' not in payload:
                return True

            return datetime.utcnow() > datetime.fromtimestamp(payload['exp'])

        except Exception as e:
            logger.warning(f"Error checking token expiration: {str(e)}")
            return True  # Treat invalid tokens as expired

    def refresh_jwt_token(self, token: str) -> Optional[str]:
        """
        Refresh a JWT token if it's not too old

        Args:
            token: JWT token string

        Returns:
            New JWT token if refreshable, None if not
        """
        try:
            payload = self.validate_jwt_token(token)
            if not payload:
                return None

            # Only refresh if token expires within the next hour
            expires_at = datetime.fromtimestamp(payload['exp'])
            if datetime.utcnow() > expires_at - timedelta(hours=1):
                logger.info("Token too old for refresh")
                return None

            # Generate new token with same claims but new expiration
            return self.generate_jwt_token(
                user_id=payload['user_id'],
                username=payload['username'],
                role=payload['role']
            )

        except Exception as e:
            logger.error(f"Error refreshing JWT token: {str(e)}")
            return None

    def extract_token_from_header(self, auth_header: str) -> Optional[str]:
        """
        Extract JWT token from Authorization header

        Args:
            auth_header: Authorization header value

        Returns:
            JWT token string or None
        """
        if not auth_header:
            return None

        if auth_header.startswith('Bearer '):
            return auth_header[7:]

        return None

    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Extract user information from a valid JWT token

        Args:
            token: JWT token string

        Returns:
            User information dict or None
        """
        payload = self.validate_jwt_token(token)
        if not payload:
            return None

        return {
            'user_id': payload['user_id'],
            'username': payload['username'],
            'role': payload['role']
        }

    def is_jwt_enabled(self) -> bool:
        """
        Check if JWT authentication is enabled

        Returns:
            True if JWT secret key is configured
        """
        return os.getenv('ENABLE_JWT_AUTH', 'true').lower() == 'true'

    def verify_admin_role(self, token: str) -> bool:
        """
        Verify if token belongs to an admin user

        Args:
            token: JWT token string

        Returns:
            True if admin, False otherwise
        """
        user_info = self.get_user_from_token(token)
        if not user_info:
            return False

        return user_info['role'] == 'admin'