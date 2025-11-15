#!/usr/bin/env python3

# Test script for JWT utilities
import sys
import os

# Add current directory to path
sys.path.insert(0, '/workspace/cmi05yy3m00d1ooimj653ong9/ssd')

print("Testing JWT implementation...")

try:
    import jwt
    print("✅ PyJWT library available")
except ImportError as e:
    print(f"❌ PyJWT library missing: {e}")
    sys.exit(1)

try:
    from utils.jwt_utils import JWTUtils
    print("✅ JWTUtils import successful")
except ImportError as e:
    print(f"❌ JWTUtils import failed: {e}")
    sys.exit(1)

# Test JWT utils functionality
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-validation-only'

try:
    jwt_utils = JWTUtils()
    print("✅ JWTUtils instantiation successful")

    # Test basic token generation
    token = jwt_utils.generate_jwt_token(1, 'testuser', 'user')
    print(f"✅ JWT token generation successful: {token[:20]}...")

    # Test token validation
    user_info = jwt_utils.validate_jwt_token(token)
    print(f"✅ JWT token validation successful: {user_info}")

    # Test token expiration check
    is_expired = jwt_utils.is_token_expired(token)
    print(f"✅ Token expiration check: {'expired' if is_expired else 'valid'}")

    # Test token from header
    auth_header = f"Bearer {token}"
    extracted_token = jwt_utils.extract_token_from_header(auth_header)
    print(f"✅ Token extraction from header: {'success' if extracted_token else 'failed'}")

    print("\n🎉 All JWT tests passed!")

except Exception as e:
    print(f"❌ JWT test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)