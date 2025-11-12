from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from datetime import datetime

from k8s_client import K8sClient
from command_verifier import CommandVerifier
from openrouter_client import OpenRouterClient
from question_classifier import HybridQuestionClassifier, QuestionType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Initialize components
k8s_client = K8sClient()
hybrid_classifier = HybridQuestionClassifier()
# OpenRouter client will be initialized per request with API key

# Store conversation history (simple in-memory for now)
conversation_history = {}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'k8s-audit-bot'
    })

@app.route('/chat', methods=['POST'])
def chat():
    """
    Enhanced intelligent chat endpoint with hybrid classification:
    1. Classify question using hybrid approach
    2. Use classification to determine command strategy
    3. Execute commands based on strategy
    4. Analyze results and generate response
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message']
        session_id = data.get('session_id', 'default')
        api_key = data.get('api_key')  # Get API key from request
        
        logger.info(f"Received message: {user_message} from session: {session_id}")
        
        # Initialize conversation history for new session
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        
        # Add user message to history
        conversation_history[session_id].append({
            'role': 'user',
            'message': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Initialize OpenRouter client with provided API key
        openrouter_client = OpenRouterClient(api_key)
        
        # Step 1: Classify question using hybrid approach
        logger.info("Step 1: Classifying question with hybrid approach...")
        classification = hybrid_classifier.classify_question(
            message=user_message,
            conversation_history=conversation_history[session_id],
            ai_client=openrouter_client
        )
        
        logger.info(f"Classification result: {classification.question_type.value} "
                   f"(score: {classification.complexity_score:.2f}, "
                   f"confidence: {classification.confidence:.2f}, "
                   f"method: {classification.classification_method})")
        
        # Step 2: Determine command strategy based on classification
        max_commands = classification.suggested_max_commands
        follow_up_allowed = classification.follow_up_allowed
        
        # Step 3: Ask model to suggest appropriate commands based on classification
        logger.info("Step 3: Requesting command suggestions from model...")
        suggested_commands = openrouter_client.suggest_commands(
            user_question=user_message,
            conversation_history=conversation_history[session_id]
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
                conversation_history=conversation_history[session_id]
            )
            
            # Add response to history
            conversation_history[session_id].append({
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
        
        # Step 4: Verify and execute safe commands
        logger.info("Step 4: Verifying and executing commands...")
        command_outputs = {}
        executed_commands = []
        rejected_commands = []
        
        for cmd in suggested_commands:
            # First check for placeholders before even checking safety
            has_placeholder, placeholder_reason = CommandVerifier.has_placeholders(cmd)
            if has_placeholder:
                logger.warning(f"Command rejected for placeholders: {cmd} - {placeholder_reason}")
                rejected_commands.append({'command': cmd, 'reason': placeholder_reason})
                continue
            
            # Verify command is safe
            is_safe, reason = CommandVerifier.is_safe_command(cmd)
            
            if is_safe:
                logger.info(f"Executing safe command: {cmd}")
                # Execute the command (remove 'kubectl' prefix for the k8s_client)
                cmd_parts = cmd.split()[1:]  # Remove 'kubectl'
                output = k8s_client._run_kubectl_command(cmd_parts)
                command_outputs[cmd] = output
                executed_commands.append(cmd)
                
                # Log command execution result
                if output.get('success'):
                    logger.info(f"Command succeeded: {cmd}")
                else:
                    logger.warning(f"Command failed: {cmd} - {output.get('stderr', 'Unknown error')}")
            else:
                logger.warning(f"Command rejected: {cmd} - {reason}")
                rejected_commands.append({'command': cmd, 'reason': reason})
        
        # Step 5: Generate follow-up commands if allowed and appropriate
        follow_up_commands = []
        if (follow_up_allowed and command_outputs and 
            classification.question_type in [QuestionType.MODERATE_INVESTIGATION, QuestionType.DEEP_ANALYSIS]):
            
            logger.info("Step 5: Generating follow-up commands...")
            follow_up_commands = openrouter_client.suggest_follow_up_commands(
                original_question=user_message,
                discovery_outputs=command_outputs,
                conversation_history=conversation_history[session_id]
            )
            
            # Limit follow-up commands based on classification
            if follow_up_commands and len(follow_up_commands) > 2:  # Conservative limit for follow-ups
                follow_up_commands = follow_up_commands[:2]
            
            if follow_up_commands:
                logger.info(f"Model suggested follow-up commands: {follow_up_commands}")
                
                for cmd in follow_up_commands:
                    # Check for placeholders again
                    has_placeholder, placeholder_reason = CommandVerifier.has_placeholders(cmd)
                    if has_placeholder:
                        logger.warning(f"Follow-up command rejected for placeholders: {cmd} - {placeholder_reason}")
                        rejected_commands.append({'command': cmd, 'reason': placeholder_reason})
                        continue
                    
                    # Verify command is safe
                    is_safe, reason = CommandVerifier.is_safe_command(cmd)
                    
                    if is_safe:
                        logger.info(f"Executing safe follow-up command: {cmd}")
                        cmd_parts = cmd.split()[1:]  # Remove 'kubectl'
                        output = k8s_client._run_kubectl_command(cmd_parts)
                        command_outputs[cmd] = output
                        executed_commands.append(cmd)
                        
                        # Log command execution result
                        if output.get('success'):
                            logger.info(f"Follow-up command succeeded: {cmd}")
                        else:
                            logger.warning(f"Follow-up command failed: {cmd} - {output.get('stderr', 'Unknown error')}")
                    else:
                        logger.warning(f"Follow-up command rejected: {cmd} - {reason}")
                        rejected_commands.append({'command': cmd, 'reason': reason})
        
        # Step 6: Send command outputs to model for analysis
        logger.info("Step 6: Analyzing command outputs...")
        if command_outputs:
            bot_response = openrouter_client.analyze_command_outputs(
                user_question=user_message,
                command_outputs=command_outputs,
                conversation_history=conversation_history[session_id]
            )
        else:
            # No commands were executed (all were rejected)
            bot_response = f"I couldn't execute any of the suggested commands for your question. All commands were rejected for safety reasons.\n\n**Rejected commands:**\n"
            for rejected in rejected_commands:
                bot_response += f"- {rejected['command']}: {rejected['reason']}\n"
            
            bot_response += "\nPlease try rephrasing your question or ask about specific Kubernetes resources in a different way."
        
        # Add bot response to history
        conversation_history[session_id].append({
            'role': 'assistant',
            'message': bot_response,
            'timestamp': datetime.now().isoformat(),
            'commands_executed': executed_commands,
            'rejected_commands': rejected_commands,
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
            'rejected_commands': rejected_commands,
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

@app.route('/safe-commands-info', methods=['GET'])
def safe_commands_info():
    """Get information about safe commands for user reference"""
    return jsonify(CommandVerifier.get_safe_commands_info())

@app.route('/sessions/<session_id>/history', methods=['GET'])
def get_session_history(session_id):
    """Get conversation history for a session"""
    if session_id not in conversation_history:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify({
        'session_id': session_id,
        'history': conversation_history[session_id]
    })

@app.route('/sessions/<session_id>/clear', methods=['DELETE'])
def clear_session_history(session_id):
    """Clear conversation history for a session"""
    if session_id in conversation_history:
        del conversation_history[session_id]
    
    return jsonify({
        'message': 'Session history cleared',
        'session_id': session_id
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting K8s Audit Bot Flask Server with Intelligent Flow...")
    app.run(debug=True, host='0.0.0.0', port=5000)