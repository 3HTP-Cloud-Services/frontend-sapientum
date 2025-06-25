from functools import wraps
from flask import jsonify, request
from cognito import get_user_from_token
from models import User, CatalogPermission, PermissionType

def token_required(f):
    """
    Decorator for routes that require JWT token authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        success, user_data = get_user_from_token()
        
        if not success:
            return jsonify({"error": "Authentication required", "details": user_data.get("error")}), 401
        
        # Check if user exists in local database
        user_email = user_data.get("email")
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({
                "error": "User not found in system",
                "details": "User authenticated but not found in local database"
            }), 401
        
        # Add user information to kwargs for the route function
        kwargs['current_user'] = user
        kwargs['token_user_data'] = user_data
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """
    Decorator for routes that require admin privileges
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        success, user_data = get_user_from_token()
        
        if not success:
            return jsonify({"error": "Authentication required", "details": user_data.get("error")}), 401
        
        # Check if user exists in local database
        user_email = user_data.get("email")
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({
                "error": "User not found in system",
                "details": "User authenticated but not found in local database"
            }), 401
        
        # Check admin privileges
        if not user.is_admin:
            return jsonify({
                "error": "Admin privileges required",
                "details": "This operation requires administrator privileges"
            }), 403
        
        # Add user information to kwargs for the route function
        kwargs['current_user'] = user
        kwargs['token_user_data'] = user_data
        
        return f(*args, **kwargs)
    
    return decorated_function

def chat_access_required(f):
    """
    Decorator for routes that require chat access
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        success, user_data = get_user_from_token()
        
        if not success:
            return jsonify({"error": "Authentication required", "details": user_data.get("error")}), 401
        
        # Check if user exists in local database
        user_email = user_data.get("email")
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({
                "error": "User not found in system",
                "details": "User authenticated but not found in local database"
            }), 401
        
        # Check chat access
        if not user.chat_access:
            return jsonify({
                "error": "Chat access required",
                "details": "This operation requires chat access privileges"
            }), 403
        
        # Add user information to kwargs for the route function
        kwargs['current_user'] = user
        kwargs['token_user_data'] = user_data
        
        return f(*args, **kwargs)
    
    return decorated_function

def catalog_admin_required(f):
    """
    Decorator for routes that require admin privileges OR FULL permissions on a specific catalog.
    The catalog_id should be available in the route parameters.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        success, user_data = get_user_from_token()
        
        if not success:
            return jsonify({"error": "Authentication required", "details": user_data.get("error")}), 401
        
        # Check if user exists in local database
        user_email = user_data.get("email")
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({
                "error": "User not found in system",
                "details": "User authenticated but not found in local database"
            }), 401
        
        # Check if user is a general admin (has access to all catalogs)
        if user.is_admin:
            kwargs['current_user'] = user
            kwargs['token_user_data'] = user_data
            return f(*args, **kwargs)
        
        # Check if user has FULL permission on the specific catalog
        catalog_id = kwargs.get('catalog_id') or request.view_args.get('catalog_id')
        if not catalog_id:
            return jsonify({
                "error": "Catalog ID required",
                "details": "Unable to determine catalog for permission check"
            }), 400
        
        catalog_permission = CatalogPermission.query.filter_by(
            catalog_id=catalog_id,
            user_id=user.id
        ).first()
        
        if not catalog_permission or catalog_permission.permission != PermissionType.FULL:
            return jsonify({
                "error": "Insufficient privileges",
                "details": "This operation requires admin privileges or full access to this catalog"
            }), 403
        
        # Add user information to kwargs for the route function
        kwargs['current_user'] = user
        kwargs['token_user_data'] = user_data
        
        return f(*args, **kwargs)
    
    return decorated_function