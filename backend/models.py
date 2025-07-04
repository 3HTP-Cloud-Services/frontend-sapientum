# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from sqlalchemy.sql import func
import enum


db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(50), default='user')
    is_admin = db.Column(db.Boolean, default=False)
    is_catalog_editor = db.Column(db.Boolean, default=False)
    chat_access = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'chatAccess': self.chat_access,
            'isAdmin': self.is_admin,
            'isCatalogEditor': self.is_catalog_editor,
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
    s3Id = db.Column(db.String(1024), default='')
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
    NOT_ALLOWED = "NOT_ALLOWED"
    CHAT_ONLY = "CHAT_ONLY"
    READ_ONLY = "READ_ONLY"
    FULL = "FULL"

class CatalogPermission(db.Model):
    __tablename__ = 'catalog_users'
    catalog_id = db.Column(db.Integer, db.ForeignKey('catalogs.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    catalog = db.relationship('Catalog', backref='users', lazy=True)
    user = db.relationship('User', backref=db.backref('permissions', lazy=True))
    permission = db.Column(db.Enum(PermissionType), default=PermissionType.NOT_ALLOWED)

    def __repr__(self):
        return f'<CatalogPermission {self.user.email if self.user else "No User"} - {self.catalog.name if self.catalog else "No Catalog"} - {self.permission.value}>'

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
            'original_file': self.file.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(1024), default='', nullable=False)
    # should be set by the AI afterwards to group conversations.
    speaker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    speaker = db.relationship('User', backref='sent_messages', lazy=True)
    catalog_id = db.Column(db.Integer, db.ForeignKey('catalogs.id'), nullable=False)
    catalog = db.relationship('Catalog', backref='messages', lazy=True)
    session_id = db.Column(db.String(1024), default='', nullable=False)
    # do note that the session_id may change later if the conversation is old enough
    # are we interested in old session ids? I gather we are not
    __table_args__ = (UniqueConstraint('speaker_id', 'catalog_id', name='unique_user_catalog_conversation'),)

class Message(db.Model):
    __tablename__ = 'messages'
    def __repr__(self):
        return f"Message(id={self.id}, conversation='{self.conversation_id}')"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    conversation = db.relationship('Conversation', backref='messages', lazy=True)
    is_request = db.Column(db.Boolean, default=False, nullable=False) # false for responses from the AI
    prompt = db.Column(db.Text, default='', nullable=True)
    # should be null for requests, save the prompt that generated the response for responses
    message = db.Column(db.Text, default='', nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)


class EventType(enum.Enum):
    PERMISSION_VIOLATION = "permission_violation"
    USER_LOGIN = "user_login"
    USER_CREATION = "user_creation"
    USER_DELETION = "user_deletion"
    USER_EDITION = "user_edition"
    USER_PERMISSION = "user_permission"
    CATALOG_CREATION = "catalog_creation"
    CATALOG_EDITION = "catalog_edition"
    CATALOG_DELETION = "catalog_deletion"
    FILE_UPLOAD = "file_upload"
    FILE_DELETION = "file_deletion"
    FILE_VERSION = "file_new_version"
    CHAT_INTERACTION = "chat_interaction"

class ActivityLog(db.Model):
    __tablename__ = 'activitylogs'
    def __repr__(self):
        return f"Activity"
    id = db.Column(db.Integer, primary_key=True)
    activity = db.Column(db.String(1024), default='', nullable=False)
    message = db.Column(db.Text, default='', nullable=True)
    event = db.Column(db.Enum(EventType), nullable=True)
    user_email = db.Column(db.String(255), nullable=False)
    other_user_email = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    catalog_id = db.Column(db.Integer, db.ForeignKey('catalogs.id'), nullable=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=True)
    version_id = db.Column(db.Integer, db.ForeignKey('versions.id'), nullable=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'activity': self.activity,
            'message': self.message,
            'event': self.event.value if self.event else None,
            'user_email': self.user_email,
            'other_user_email': self.other_user_email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'catalog_id': self.catalog_id,
            'file_id': self.file_id,
            'version_id': self.version_id,
            'message_id': self.message_id
        }
