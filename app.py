from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import sys
from datetime import datetime
import uuid

from k8s_client import K8sClient
from openrouter_client import OpenRouterClient
from question_classifier import HybridQuestionClassifier, QuestionType
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application with proper error handling"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for frontend integration
    
    # Initialize components with error handling
    k8s_client = None
    hybrid_classifier = None
    db = None
    
    # Initialize K8s client
    try:
        k8s_client = K8sClient()
        logger.info("K8s client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize K8s client: {e}")
        # Continue without K8s - will be handled in endpoints
    
    # Initialize question classifier
    try:
        hybrid_classifier = HybridQuestionClassifier()
        logger.info("Question classifier initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize question classifier: {e}")
        sys.exit(1)  # This is critical - exit if we can't initialize
    
    # Initialize database with proper error handling
    try:
        db = Database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.error("This is a critical component - application cannot start without database")
        sys.exit(1)  # Exit if we can't connect to database
    
    # Store components in app context
    app.k8s_client = k8s_client
    app.hybrid_classifier = hybrid_classifier
    app.db = db
    
    # Store in-memory conversation history (will be synced with DB)
    app.conversation_history = {}
    
    return app

# Create application instance
app = create_app()

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint with comprehensive status"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'k8s-audit-bot',
        'version': 'v0.1'
    }
    
    # Check database health
    try:
        if app.db:
            db_health = app.db.health_check()
            health_status['database'] = db_health
            if db_health['status'] != 'healthy':
                health_status['status'] = 'degraded'
        else:
            health_status['database'] = {'status': 'not_initialized'}
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['database'] = {'status': 'error', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Check K8s client health
    try:
        if app.k8s_client:
            # Basic kubectl check
            result = app.k8s_client._run_kubectl_command(['version', '--client'], timeout=5)
            if result['success']:
                health_status['kubernetes'] = {'status': 'connected', 'kubectl_available': True}
            else:
                health_status['kubernetes'] = {'status': 'kubectl_error', 'error': result.get('error', 'Unknown error')}
        else:
            health_status['kubernetes'] = {'status': 'not_initialized'}
    except Exception as e:
        health_status['kubernetes'] = {'status': 'error', 'error': str(e)}
    
    # Check classifier health
    try:
        if app.hybrid_classifier:
            health_status['classifier'] = {'status': 'healthy'}
        else:
            health_status['classifier'] = {'status': 'not_initialized'}
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['classifier'] = {'status': 'error', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Determine appropriate HTTP status code
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return jsonify(health_status), status_code

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password are required'}), 400
        
        username = data['username']
        password = data['password']
        
        # Authenticate user
        user = app.db.authenticate_user(username, password)
        
        if not user:
            return jsonify({'error': 'Invalid credentials or user is banned'}), 401
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        app.db.create_session(user['id'], session_id)
        
        # Log activity
        app.db.log_activity(user['id'], 'login', success=True)
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            },
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id:
            # Clear in-memory conversation history
            if session_id in app.conversation_history:
                del app.conversation_history[session_id]
        
        return jsonify({'message': 'Logout successful'})
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

# ==================== ADMIN ENDPOINTS ====================

@app.route('/admin/users', methods=['GET'])
def get_users():
    """Get all users (admin only)"""
    try:
        # TODO: Add authentication middleware to verify admin role
        users = app.db.get_all_users()
        return jsonify({'users': users})
        
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Failed to get users'}), 500

@app.route('/admin/users', methods=['POST'])
def create_user():
    """Create new user (admin only)"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Username, email, and password are required'}), 400
        
        username = data['username']
        email = data['email']
        password = data['password']
        role = data.get('role', 'user')
        
        user_id = app.db.create_user(username, email, password, role)
        
        if user_id:
            return jsonify({
                'message': 'User created successfully',
                'user_id': user_id
            }), 201
        else:
            return jsonify({'error': 'Failed to create user - username or email already exists'}), 400
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({'error': 'Failed to create user'}), 500

@app.route('/admin/users/<int:user_id>/ban', methods=['POST'])
def ban_user(user_id):
    """Ban a user (admin only)"""
    try:
        success = app.db.ban_user(user_id)
        
        if success:
            return jsonify({'message': f'User {user_id} banned successfully'})
        else:
            return jsonify({'error': 'Failed to ban user'}), 500
        
    except Exception as e:
        logger.error(f"Error banning user: {str(e)}")
        return jsonify({'error': 'Failed to ban user'}), 500

@app.route('/admin/users/<int:user_id>/unban', methods=['POST'])
def unban_user(user_id):
    """Unban a user (admin only)"""
    try:
        success = app.db.unban_user(user_id)
        
        if success:
            return jsonify({'message': f'User {user_id} unbanned successfully'})
        else:
            return jsonify({'error': 'Failed to unban user'}), 500
        
    except Exception as e:
        logger.error(f"Error unbanning user: {str(e)}")
        return jsonify({'error': 'Failed to unban user'}), 500

@app.route('/admin/users/<int:user_id>/role', methods=['PUT'])
def update_user_role(user_id):
    """Update user role (admin only)"""
    try:
        data = request.get_json()
        
        if not data or 'role' not in data:
            return jsonify({'error': 'Role is required'}), 400
        
        new_role = data['role']
        
        if new_role not in ['admin', 'user']:
            return jsonify({'error': 'Invalid role'}), 400
        
        success = app.db.update_user_role(user_id, new_role)
        
        if success:
            return jsonify({'message': f'User {user_id} role updated to {new_role}'})
        else:
            return jsonify({'error': 'Failed to update role'}), 500
        
    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}")
        return jsonify({'error': 'Failed to update role'}), 500

@app.route('/admin/users/<int:user_id>/password', methods=['PUT'])
def change_user_password(user_id):
    """Change user password (admin only)"""
    try:
        data = request.get_json()
        
        if not data or 'new_password' not in data:
            return jsonify({'error': 'New password is required'}), 400
        
        new_password = data['new_password']
        success = app.db.change_password(user_id, new_password)
        
        if success:
            return jsonify({'message': f'Password changed for user {user_id}'})
        else:
            return jsonify({'error': 'Failed to change password'}), 500
        
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return jsonify({'error': 'Failed to change password'}), 500

@app.route('/admin/logs', methods=['GET'])
def get_activity_logs():
    """Get activity logs (admin only)"""
    try:
        user_id = request.args.get('user_id', type=int)
        limit = request.args.get('limit', default=100, type=int)
        
        logs = app.db.get_activity_logs(user_id=user_id, limit=limit)
        return jsonify({'logs': logs})
        
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return jsonify({'error': 'Failed to get logs'}), 500

# ==================== USER ENDPOINTS ====================

@app.route('/user/preferences', methods=['GET'])
def get_preferences():
    """Get user preferences"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        preferences = app.db.get_user_preferences(user_id)
        
        if preferences:
            return jsonify({'preferences': preferences})
        else:
            return jsonify({'error': 'Preferences not found'}), 404
        
    except Exception as e:
        logger.error(f"Error getting preferences: {str(e)}")
        return jsonify({'error': 'Failed to get preferences'}), 500

@app.route('/user/preferences', methods=['PUT'])
def update_preferences():
    """Update user preferences"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Extract preference fields
        preferences = {
            key: data[key]
            for key in ['tone', 'response_style', 'personality', 'max_commands_preference', 'auto_investigate']
            if key in data
        }
        
        success = app.db.update_user_preferences(user_id, preferences)
        
        if success:
            return jsonify({'message': 'Preferences updated successfully'})
        else:
            return jsonify({'error': 'Failed to update preferences'}), 500
        
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        return jsonify({'error': 'Failed to update preferences'}), 500

@app.route('/user/sessions', methods=['GET'])
def get_user_sessions():
    """Get all chat sessions for a user"""
    try:
        user_id = request.args.get('user_id', type=int)
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        sessions = app.db.get_user_sessions(user_id)
        return jsonify({'sessions': sessions})
        
    except Exception as e:
        logger.error(f"Error getting sessions: {str(e)}")
        return jsonify({'error': 'Failed to get sessions'}), 500

@app.route('/user/history', methods=['GET'])
def get_user_history():
    """Get chat history for a user"""
    try:
        user_id = request.args.get('user_id', type=int)
        session_id = request.args.get('session_id')
        limit = request.args.get('limit', default=50, type=int)
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        history = app.db.get_chat_history(user_id, session_id=session_id, limit=limit)
        return jsonify({'history': history})
        
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({'error': 'Failed to get history'}), 500

@app.route('/user/history', methods=['DELETE'])
def delete_user_history():
    """Delete chat history for a user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        session_id = data.get('session_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        success = app.db.delete_chat_history(user_id, session_id=session_id)
        
        if success:
            return jsonify({'message': 'Chat history deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete history'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting history: {str(e)}")
        return jsonify({'error': 'Failed to delete history'}), 500

# ==================== CHAT ENDPOINT ====================

@app.route('/chat', methods=['POST'])
def chat():
    """
    Enhanced intelligent chat endpoint with hybrid classification and database integration
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message']
        session_id = data.get('session_id', 'default')
        user_id = data.get('user_id')  # User ID from authentication
        api_key = data.get('api_key')  # API key provided by user each time
        
        if not user_id:
            return jsonify({'error': 'User ID is required (please login)'}), 401
        
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
        
        logger.info(f"Received message from user {user_id}: {user_message}")
        
        # Get user preferences
        user_prefs = app.db.get_user_preferences(user_id)
        
        # Initialize conversation history for session
        if session_id not in app.conversation_history:
            # Load from database
            db_history = app.db.get_chat_history(user_id, session_id=session_id)
            app.conversation_history[session_id] = [
                {
                    'role': msg['role'],
                    'message': msg['message'],
                    'timestamp': msg['timestamp']
                }
                for msg in db_history
            ]
        
        # Add user message to history
        app.conversation_history[session_id].append({
            'role': 'user',
            'message': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Initialize OpenRouter client with provided API key
        openrouter_client = OpenRouterClient(api_key)
        
        # Step 1: Classify question using hybrid approach
        logger.info("Step 1: Classifying question with hybrid approach...")
        classification = app.hybrid_classifier.classify_question(
            message=user_message,
            conversation_history=app.conversation_history[session_id],
            ai_client=openrouter_client
        )
        
        logger.info(f"Classification result: {classification.question_type.value} "
                   f"(score: {classification.complexity_score:.2f}, "
                   f"confidence: {classification.confidence:.2f}, "
                   f"method: {classification.classification_method})")
        
        # Step 2: Determine command strategy based on classification
        max_commands = classification.suggested_max_commands
        follow_up_allowed = classification.follow_up_allowed
        
        # Apply user preferences if they exist
        if user_prefs and user_prefs.get('max_commands_preference'):
            max_commands = min(max_commands, user_prefs['max_commands_preference'])
        
        # Step 3: Ask model to suggest appropriate commands based on classification
        logger.info("Step 3: Requesting command suggestions from model...")
        suggested_commands = openrouter_client.suggest_commands(
            user_question=user_message,
            conversation_history=app.conversation_history[session_id]
        )
        
        # Limit commands based on classification
        if suggested_commands and len(suggested_commands) > max_commands:
            logger.info(f"Limiting commands from {len(suggested_commands)} to {max_commands} based on classification")
            suggested_commands = suggested_commands[:max_commands]
        
        if not suggested_commands:
            logger.info("No commands needed - providing direct advice response")
            # Use analysis method directly without command outputs
            bot_response = openrouter_client.analyze_command_outputs(
                user_question=user_message,
                command_outputs={},  # Empty command outputs
                conversation_history=app.conversation_history[session_id]
            )
            
            # Save to database
            app.db.save_chat_message(
                user_id=user_id,
                session_id=session_id,
                role='user',
                message=user_message
            )
            
            app.db.save_chat_message(
                user_id=user_id,
                session_id=session_id,
                role='assistant',
                message=bot_response,
                commands_executed=[],
                classification_info={
                    'type': classification.question_type.value,
                    'complexity_score': classification.complexity_score,
                    'confidence': classification.confidence,
                    'method': classification.classification_method
                }
            )
            
            # Log activity
            app.db.log_activity(
                user_id=user_id,
                action_type='advice_query',
                classification_type=classification.question_type.value,
                success=True
            )
            
            # Add response to history
            app.conversation_history[session_id].append({
                'role': 'assistant',
                'message': bot_response,
                'timestamp': datetime.now().isoformat(),
                'commands_executed': [],
                'classification': {
                    'type': classification.question_type.value,
                    'complexity_score': classification.complexity_score,
                    'confidence': classification.confidence,
                    'method': classification.classification_method
                },
                'analysis_type': 'advice_only'
            })
            
            return jsonify({
                'response': bot_response,
                'commands_executed': [],
                'classification': {
                    'type': classification.question_type.value,
                    'complexity_score': classification.complexity_score,
                    'confidence': classification.confidence,
                    'method': classification.classification_method,
                    'reasoning': classification.reasoning
                },
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'advice_only'
            })
        
        logger.info(f"Model suggested commands: {suggested_commands}")
        
        # Step 4: Execute safe commands (no verification needed now)
        logger.info("Step 4: Executing commands...")
        command_outputs = {}
        executed_commands = []
        
        for cmd in suggested_commands:
            logger.info(f"Executing command: {cmd}")
            # Execute the command (remove 'kubectl' prefix for the k8s_client)
            cmd_parts = cmd.split()[1:]  # Remove 'kubectl'
            output = app.k8s_client._run_kubectl_command(cmd_parts)
            command_outputs[cmd] = output
            executed_commands.append(cmd)
            
            # Log command execution
            app.db.log_activity(
                user_id=user_id,
                action_type='command_executed',
                command=cmd,
                classification_type=classification.question_type.value,
                success=output.get('success'),
                error_message=output.get('stderr') if not output.get('success') else None
            )
            
            # Log command execution result
            if output.get('success'):
                logger.info(f"Command succeeded: {cmd}")
            else:
                logger.warning(f"Command failed: {cmd} - {output.get('stderr', 'Unknown error')}")
        
        # Step 5: Generate follow-up commands if allowed and appropriate
        follow_up_commands = []
        if (follow_up_allowed and command_outputs and 
            classification.question_type in [QuestionType.MODERATE_INVESTIGATION, QuestionType.DEEP_ANALYSIS]):
            
            logger.info("Step 5: Generating follow-up commands...")
            follow_up_commands = openrouter_client.suggest_follow_up_commands(
                original_question=user_message,
                discovery_outputs=command_outputs,
                conversation_history=app.conversation_history[session_id]
            )
            
            # Limit follow-up commands based on classification
            if follow_up_commands and len(follow_up_commands) > 2:  # Conservative limit for follow-ups
                follow_up_commands = follow_up_commands[:2]
            
            if follow_up_commands:
                logger.info(f"Model suggested follow-up commands: {follow_up_commands}")
                
                for cmd in follow_up_commands:
                    logger.info(f"Executing follow-up command: {cmd}")
                    cmd_parts = cmd.split()[1:]  # Remove 'kubectl'
                    output = app.k8s_client._run_kubectl_command(cmd_parts)
                    command_outputs[cmd] = output
                    executed_commands.append(cmd)
                    
                    # Log follow-up command
                    app.db.log_activity(
                        user_id=user_id,
                        action_type='followup_command_executed',
                        command=cmd,
                        classification_type=classification.question_type.value,
                        success=output.get('success'),
                        error_message=output.get('stderr') if not output.get('success') else None
                    )
                    
                    # Log command execution result
                    if output.get('success'):
                        logger.info(f"Follow-up command succeeded: {cmd}")
                    else:
                        logger.warning(f"Follow-up command failed: {cmd} - {output.get('stderr', 'Unknown error')}")
        
        # Step 6: Send command outputs to model for analysis
        logger.info("Step 6: Analyzing command outputs...")
        bot_response = openrouter_client.analyze_command_outputs(
            user_question=user_message,
            command_outputs=command_outputs,
            conversation_history=app.conversation_history[session_id]
        )
        
        # Save to database
        app.db.save_chat_message(
            user_id=user_id,
            session_id=session_id,
            role='user',
            message=user_message
        )
        
        app.db.save_chat_message(
            user_id=user_id,
            session_id=session_id,
            role='assistant',
            message=bot_response,
            commands_executed=executed_commands,
            classification_info={
                'type': classification.question_type.value,
                'complexity_score': classification.complexity_score,
                'confidence': classification.confidence,
                'method': classification.classification_method
            }
        )
        
        # Add bot response to history
        app.conversation_history[session_id].append({
            'role': 'assistant',
            'message': bot_response,
            'timestamp': datetime.now().isoformat(),
            'commands_executed': executed_commands,
            'classification': {
                'type': classification.question_type.value,
                'complexity_score': classification.complexity_score,
                'confidence': classification.confidence,
                'method': classification.classification_method,
                'reasoning': classification.reasoning
            },
            'analysis_type': 'command_based'
        })
        
        return jsonify({
            'response': bot_response,
            'commands_executed': executed_commands,
            'classification': {
                'type': classification.question_type.value,
                'complexity_score': classification.complexity_score,
                'confidence': classification.confidence,
                'method': classification.classification_method,
                'reasoning': classification.reasoning,
                'strategy': classification.strategy_type.value,
                'max_commands_suggested': classification.suggested_max_commands,
                'follow_up_allowed': classification.follow_up_allowed
            },
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'command_based'
        })
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to process your request. Please try again.'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting K8s Audit Bot Flask Server with Database Integration...")
    logger.info("=" * 60)
    logger.info("DEFAULT ADMIN CREDENTIALS:")
    logger.info("Username: admin")
    logger.info("Password: admin123")
    logger.info("PLEASE CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")
    logger.info("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)