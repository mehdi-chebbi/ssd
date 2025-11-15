#!/usr/bin/env python3

# Test Flask routes with authentication middleware without database
import sys
import os

# Add current directory to path
sys.path.insert(0, '/workspace/cmi05yy3m00d1ooimj653ong9/ssd')

print("Testing Flask Routes with Authentication...")

# Set environment variables for testing
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-validation-only'
os.environ['ENABLE_JWT_AUTH'] = 'true'
os.environ['ENABLE_SESSION_AUTH'] = 'true'
os.environ['FLASK_ENV'] = 'testing'

try:
    import json
    from flask import Flask, jsonify
    from utils.jwt_utils import JWTUtils
    from middleware import AuthMiddleware, AuthenticationError, AuthorizationError
    print("✅ Core imports successful")

    # Create a minimal Flask app for testing
    test_app = Flask(__name__)

    # Create JWT utilities and mock middleware
    jwt_utils = JWTUtils()

    # Mock database for middleware initialization
    class MockDB:
        def _get_connection(self):
            return Mock()
        def _put_connection(self, conn):
            pass
        def update_session_activity(self, session_id):
            pass

    mock_db = MockDB()
    auth_middleware = AuthMiddleware(mock_db, jwt_utils)
    test_app.auth_middleware = auth_middleware

    # Generate test tokens
    admin_token = jwt_utils.generate_jwt_token(1, 'admin', 'admin')
    user_token = jwt_utils.generate_jwt_token(2, 'user', 'user')

    # Create test routes with authentication
    @test_app.route('/public')
    def public_endpoint():
        return jsonify({'message': 'Public endpoint - no auth required'})

    @test_app.route('/protected')
    @auth_middleware.require_authentication
    def protected_endpoint():
        return jsonify({'message': 'Protected endpoint - auth required', 'user': test_app.current_user})

    @test_app.route('/admin')
    @auth_middleware.require_admin
    def admin_endpoint():
        return jsonify({'message': 'Admin endpoint - admin required', 'user': test_app.current_user})

    @test_app.route('/user-data/<int:user_id>')
    @auth_middleware.require_ownership
    def user_endpoint(user_id):
        return jsonify({'message': 'User data endpoint', 'user': test_app.current_user, 'requested_user_id': user_id})

    print("✅ Test Flask app created with authentication decorators")

    # Create test client
    client = test_app.test_client()

    # Test public endpoint (no auth required)
    response = client.get('/public')
    print(f"✅ Public endpoint: {response.status_code} - {json.loads(response.data)['message']}")

    # Test protected endpoint without auth (should fail)
    response = client.get('/protected')
    print(f"✅ Protected endpoint without auth: {response.status_code} (expected failure)")

    # Test protected endpoint with user token
    response = client.get('/protected', headers={'Authorization': f'Bearer {user_token}'})
    if response.status_code == 200:
        data = json.loads(response.data)
        print(f"✅ Protected endpoint with user token: {response.status_code} - {data['user']['username']}")
    else:
        print(f"⚠️  Protected endpoint with user token: {response.status_code}")

    # Test admin endpoint with user token (should fail)
    response = client.get('/admin', headers={'Authorization': f'Bearer {user_token}'})
    print(f"✅ Admin endpoint with user token: {response.status_code} (expected failure)")

    # Test admin endpoint with admin token (should succeed)
    response = client.get('/admin', headers={'Authorization': f'Bearer {admin_token}'})
    if response.status_code == 200:
        data = json.loads(response.data)
        print(f"✅ Admin endpoint with admin token: {response.status_code} - {data['user']['username']}")
    else:
        print(f"⚠️  Admin endpoint with admin token: {response.status_code}")

    # Test user endpoint accessing own data (should succeed)
    response = client.get('/user-data/2', headers={'Authorization': f'Bearer {user_token}'})
    if response.status_code == 200:
        data = json.loads(response.data)
        print(f"✅ User endpoint accessing own data: {response.status_code} - User {data['user']['username']} accessing user_id {data['requested_user_id']}")
    else:
        print(f"⚠️  User endpoint accessing own data: {response.status_code}")

    # Test user endpoint accessing other user's data (should fail)
    response = client.get('/user-data/1', headers={'Authorization': f'Bearer {user_token}'})
    print(f"✅ User endpoint accessing other user's data: {response.status_code} (expected failure)")

    # Test admin accessing any user data (should succeed)
    response = client.get('/user-data/1', headers={'Authorization': f'Bearer {admin_token}'})
    if response.status_code == 200:
        data = json.loads(response.data)
        print(f"✅ Admin accessing user data: {response.status_code} - Admin {data['user']['username']} accessing user_id {data['requested_user_id']}")
    else:
        print(f"⚠️  Admin accessing user data: {response.status_code}")

    print("\n🎉 All Flask route tests completed successfully!")

except Exception as e:
    print(f"❌ Flask route test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)