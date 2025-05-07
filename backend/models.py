# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
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
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'documentAccess': self.document_access,
            'chatAccess': self.chat_access,
            'isAdmin': self.is_admin,
            'isActive': self.is_active,
            'role': self.role
        }

class Domain(db.Model):
    __tablename__ = 'domains'

    def __repr__(self):
        return f"Domain(id={self.id}, name='{self.name}')"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), default='')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }

class Catalog(db.Model):
    __tablename__ = 'catalogs'
    def __repr__(self):
        return f"Catalog(id={self.id}, name='{self.name}')"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), default='')
    s3Id = db.Column(db.String(356), default='')
    description = db.Column(db.String(255), default='')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.relationship('User', backref=db.backref('catalogs', lazy=True))
    is_active = db.Column(db.Boolean, default=True)
    type = db.Column(db.String(50), default='')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            's3Id': self.s3Id,
            'type': self.type,
            'description': self.description,
            'created_by': self.created_by.email if self.created_by else None,
            'created_by_id': self.created_by_id,
            'is_active': self.is_active
        }