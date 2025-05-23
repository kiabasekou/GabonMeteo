# app/error_handlers.py
from flask import render_template, jsonify, request
import logging

def register_error_handlers(app):
    """Enregistre les gestionnaires d'erreurs globaux"""
    
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint non trouvé'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logging.error(f'Erreur serveur: {error}')
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Erreur interne du serveur'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Accès interdit'}), 403
        return render_template('errors/403.html'), 403