# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(50), default='user')
    is_admin = db.Column(db.Boolean, default=False)
    document_access = db.Column(db.String(50), default='Lectura')
    chat_access = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'documentAccess': self.document_access,
            'chatAccess': self.chat_access,
            'isAdmin': self.is_admin,
            'role': self.role
        }