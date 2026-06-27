from flask import Blueprint, render_template, request, jsonify

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET"])
def index():
    """Home page"""
    return render_template("index.html")

@main_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Heroku"""
    return jsonify({"status": "healthy"}), 200


@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Not found"}), 404


@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500
