# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import enum


db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(50), default='user')
    is_admin = db.Column(db.Boolean, default=False)
    chat_access = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
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

class File(db.Model):
    __tablename__ = 'files'
    def __repr__(self):
        return f"File(id={self.id}, name='{self.name}')"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1024), default='')
    s3Id = db.Column(db.String(1024), default='')
    summary = db.Column(db.String(1024), default='')
    catalog_id = db.Column(db.Integer, db.ForeignKey('catalogs.id'))
    catalog = db.relationship('Catalog', backref='files', lazy=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    uploaded_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.relationship('User', backref='files', lazy=True)
    status = db.Column(db.String(16), default='')
    confidentiality = db.Column(db.Boolean, default=False)
    size = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            's3Id': self.s3Id,
            'summary': self.summary,
            'catalog_id': self.catalog_id,
            'catalog_name': self.catalog.name if self.catalog else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'created_by_id': self.created_by_id,
            'created_by': self.created_by.email if self.created_by else None,
            'status': self.status,
            'confidentiality': self.confidentiality,
            'size': self.size,
            'size_formatted': self._format_size(self.size) if self.size else '0 B'
        }

    def _format_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"

        size_names = ("B", "KB", "MB", "GB", "TB")
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1

        return f"{size_bytes:.2f} {size_names[i]}"

class PermissionType(enum.Enum):
    NOT_ALLOWED = "permission-not-allowed"
    READ_ONLY = "permission-read-only"
    FULL = "permission-full"

class CatalogPermission(db.Model):
    __tablename__ = 'catalog_users'
    catalog_id = db.Column(db.Integer, db.ForeignKey('catalogs.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    catalog = db.relationship('Catalog', backref='users', lazy=True)
    user = db.relationship('User', backref=db.backref('permissions', lazy=True))
    permission = db.Column(db.Enum(PermissionType), default=PermissionType.NOT_ALLOWED)

    def __repr__(self):
        return f'<CatalogPermission {self.user.username} - {self.catalog.name} - {self.permission.value}>'

    def to_dict(self):
        return {
            'catalog_id': self.catalog_id,
            'user_id': self.user_id,
            'permission': self.permission.value,
            'catalog': self.catalog.to_dict() if self.catalog else None,
            'user': self.user.to_dict() if self.user else None
        }

class Version(db.Model):
    __tablename__ = 'versions'
    def __repr__(self):
        return f"Version(id={self.id}, name='{self.name}')"
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean, default=False, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    s3Id = db.Column(db.String(1024), default='', nullable=False)
    size = db.Column(db.Integer, default=0, nullable=False)
    filename = db.Column(db.String(1024), default='', nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploader = db.relationship('User', backref='versions', lazy=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False)
    file = db.relationship('File', backref='versions', lazy=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'version': self.version,
            'active': self.active,
            's3Id': self.s3Id,
            'size': self.size,
            'filename': self.filename,
            'uploader': self.uploader.email,
            'original_file': self.file.filename,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
