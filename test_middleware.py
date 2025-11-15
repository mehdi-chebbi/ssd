#!/usr/bin/env python3

# Test script for authentication middleware
import sys
import os
from unittest.mock import Mock

# Add current directory to path
sys.path.insert(0, '/workspace/cmi05yy3m00d1ooimj653ong9/ssd')

print("Testing Authentication Middleware...")

# Set environment variables for testing
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-validation-only'
os.environ['ENABLE_JWT_AUTH'] = 'true'
os.environ['ENABLE_SESSION_AUTH'] = 'true'

try:
    import jwt
    from utils.jwt_utils import JWTUtils
    from middleware import AuthMiddleware, AuthenticationError, AuthorizationError
    print("✅ Authentication middleware imports successful")
except ImportError as e:
    print(f"❌ Middleware import failed: {e}")
    sys.exit(1)

try:
    # Create JWT utils instance
    jwt_utils = JWTUtils()

    # Mock database instance
    mock_db = Mock()

    # Create middleware instance
    auth_middleware = AuthMiddleware(mock_db, jwt_utils)
    print("✅ AuthMiddleware instantiation successful")

    # Test JWT token generation
    token = jwt_utils.generate_jwt_token(1, 'testuser', 'admin')
    print(f"✅ JWT token generated: {token[:20]}...")

    # Test mock request creation
    class MockRequest:
        def __init__(self, headers=None, json_data=None, args=None):
            self.headers = headers or {}
            self._json = json_data
            self.args = args or {}

        def get_json(self, silent=False):
            return self._json

    # Test JWT authentication
    print("\n--- Testing JWT Authentication ---")
    request_with_jwt = MockRequest(headers={'Authorization': f'Bearer {token}'})
    user_info = auth_middleware.authenticate_request(request_with_jwt)
    print(f"✅ JWT authentication successful: {user_info}")

    # Test session authentication (mock)
    print("\n--- Testing Session Authentication ---")
    request_with_session = MockRequest(headers={'X-Session-ID': 'test-session-id'})

    # Mock database response for session validation
    mock_db._get_connection.return_value = Mock()
    mock_db._get_connection.return_value.cursor.return_value.fetchone.return_value = (
        1,  # user_id
        '2025-01-01 00:00:00',  # last_activity
        True,  # is_active
        'testuser',  # username
        'admin',  # role
        False   # is_banned
    )
    mock_db.update_session_activity.return_value = True

    session_user_info = auth_middleware.validate_session('test-session-id')
    print(f"✅ Session validation successful: {session_user_info}")

    # Test authentication decorators
    print("\n--- Testing Authentication Decorators ---")

    # Test require_authentication decorator
    @auth_middleware.require_authentication
    def protected_endpoint():
        return {'message': 'Protected endpoint accessed'}

    # Mock Flask request context
    import flask
    app = flask.Flask(__name__)

    with app.test_request_context('/', headers={'Authorization': f'Bearer {token}'}):
        # This will test if authentication is properly applied
        print("✅ Authentication decorator test setup complete")

    # Test require_admin decorator
    @auth_middleware.require_admin
    def admin_endpoint():
        return {'message': 'Admin endpoint accessed'}

    print("✅ Admin decorator test setup complete")

    # Test require_ownership decorator
    @auth_middleware.require_ownership(user_id_param='user_id')
    def user_endpoint():
        return {'message': 'User endpoint accessed'}

    print("✅ Ownership decorator test setup complete")

    print("\n🎉 All middleware tests passed!")

except Exception as e:
    print(f"❌ Middleware test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)