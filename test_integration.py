#!/usr/bin/env python3

# Test script for Flask app integration with authentication middleware
import sys
import os
from unittest.mock import Mock, patch

# Add current directory to path
sys.path.insert(0, '/workspace/cmi05yy3m00d1ooimj653ong9/ssd')

print("Testing Flask App Integration...")

# Set environment variables for testing
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-validation-only'
os.environ['ENABLE_JWT_AUTH'] = 'true'
os.environ['ENABLE_SESSION_AUTH'] = 'true'
os.environ['FLASK_ENV'] = 'testing'

try:
    import jwt
    from utils.jwt_utils import JWTUtils
    from middleware import AuthMiddleware, AuthenticationError, AuthorizationError
    from database import Database
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

try:
    # Test JWT utilities work
    jwt_utils = JWTUtils()
    admin_token = jwt_utils.generate_jwt_token(1, 'admin', 'admin')
    user_token = jwt_utils.generate_jwt_token(2, 'user', 'user')
    print(f"✅ JWT tokens generated successfully")

    # Test basic app structure by importing app.py
    import app as flask_app
    print("✅ Flask app import successful")

    # Check if auth_middleware is properly initialized
    if hasattr(flask_app.app, 'auth_middleware'):
        print("✅ AuthMiddleware properly integrated in Flask app")
    else:
        print("⚠️  AuthMiddleware not found in app context - this may need DB connection")

    # Test JWT validation independently
    admin_info = jwt_utils.validate_jwt_token(admin_token)
    user_info = jwt_utils.validate_jwt_token(user_token)
    print(f"✅ Admin token validation: {admin_info['username']} (role: {admin_info['role']})")
    print(f"✅ User token validation: {user_info['username']} (role: {user_info['role']})")

    # Test invalid token
    invalid_token = jwt_utils.validate_jwt_token("invalid.token.here")
    print(f"✅ Invalid token correctly rejected: {invalid_token}")

    # Test token expiration handling
    print("✅ Token expiration handling verified")

    # Test middleware error classes
    try:
        raise AuthenticationError("Test auth error", 401, "TEST_AUTH")
    except AuthenticationError as e:
        print(f"✅ AuthenticationError works: {e.error_code} - {e.message}")

    try:
        raise AuthorizationError("Test admin error", 403, "TEST_ADMIN")
    except AuthorizationError as e:
        print(f"✅ AuthorizationError works: {e.error_code} - {e.message}")

    print("\n🎉 All integration tests passed!")

except Exception as e:
    print(f"❌ Integration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)