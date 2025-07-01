import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import Flask and create a completely separate test app
from flask import Flask
from models import db, User, Catalog, CatalogPermission, PermissionType


class TestCatalogCreation(unittest.TestCase):
    """Test suite for catalog creation and permission assignment"""
    
    def setUp(self):
        """Set up test fixtures with isolated test app"""
        # Create a completely separate Flask app for testing
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize the database with our test app
        db.init_app(self.app)
        
        with self.app.app_context():
            db.create_all()
            
            # Create a test user
            self.test_user = User(
                email='test@example.com',
                role='user',
                is_admin=False,
                chat_access=True
            )
            db.session.add(self.test_user)
            db.session.commit()
            
            # Store the user ID for later reference
            self.test_user_id = self.test_user.id
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    @patch('catalog.get_bucket_name')
    @patch('catalog.list_s3_folder_contents')
    @patch('catalog.create_s3_folder')
    @patch('aws_utils.get_client_with_assumed_role')
    @patch('cognito.get_user_from_token')
    @patch('activity.create_activity_catalog_log')
    def test_catalog_creation_adds_full_permission_to_creator(self, 
                                                              mock_activity_log,
                                                              mock_get_user_token,
                                                              mock_s3_client,
                                                              mock_create_s3_folder,
                                                              mock_list_s3_contents,
                                                              mock_get_bucket):
        """Test that creating a catalog automatically grants FULL permission to the creator"""
        
        with self.app.app_context():
            # Mock all external dependencies
            mock_get_bucket.return_value = 'test-bucket'
            mock_list_s3_contents.return_value = ['s3_folder']
            mock_create_s3_folder.return_value = 'test/path'
            
            # Mock S3 client
            mock_s3 = MagicMock()
            mock_s3_client.return_value = mock_s3
            
            # Mock user token validation to return our test user
            mock_get_user_token.return_value = (True, {'email': 'test@example.com'})
            
            # Mock activity logging
            mock_activity_log.return_value = None
            
            # Test data
            catalog_name = 'Test Catalog'
            description = 'Test Description'
            catalog_type = 's3_folder'
            
            # Import create_catalog here to avoid loading production config
            from catalog import create_catalog
            
            # Act: Create the catalog
            result = create_catalog(catalog_name, description, catalog_type)
            
            # Assert: Catalog was created successfully
            self.assertIsNotNone(result, "Catalog creation should return a result")
            self.assertIsInstance(result, dict, "Result should be a dictionary")
            self.assertIn('name', result, "Result should contain catalog name")
            self.assertEqual(result['name'], catalog_name, "Catalog name should match input")
            
            # Assert: Catalog exists in database
            created_catalog = Catalog.query.filter_by(name=catalog_name).first()
            self.assertIsNotNone(created_catalog, "Catalog should exist in database")
            
            # Assert: Catalog has correct properties
            self.assertEqual(created_catalog.name, catalog_name, "Catalog name should match")
            self.assertEqual(created_catalog.description, description, "Catalog description should match")
            self.assertEqual(created_catalog.type, catalog_type, "Catalog type should match")
            self.assertEqual(created_catalog.created_by_id, self.test_user_id, 
                            "Catalog should be created by test user")
            self.assertTrue(created_catalog.is_active, "Catalog should be active")
            
            # Assert: FULL permission was granted to creator
            permission = CatalogPermission.query.filter_by(
                catalog_id=created_catalog.id,
                user_id=self.test_user_id
            ).first()
            
            self.assertIsNotNone(permission, 
                                "Permission should exist for catalog creator")
            self.assertEqual(permission.permission, PermissionType.FULL, 
                            "Creator should have FULL permission on the catalog")
            
            # Assert: Only one permission entry exists for this catalog
            all_permissions = CatalogPermission.query.filter_by(
                catalog_id=created_catalog.id
            ).all()
            
            self.assertEqual(len(all_permissions), 1, 
                            "Only one permission should exist for the new catalog")
            
            # Assert: The permission belongs to the correct user
            self.assertEqual(all_permissions[0].user_id, self.test_user_id,
                            "The permission should belong to the creating user")
            
            # Verify external calls were made correctly
            mock_get_bucket.assert_called_once()
            mock_get_user_token.assert_called_once()
            mock_s3_client.assert_called_once_with('s3')
            mock_activity_log.assert_called_once()
    
    @patch('catalog.get_bucket_name')
    @patch('catalog.list_s3_folder_contents') 
    @patch('catalog.create_s3_folder')
    @patch('aws_utils.get_client_with_assumed_role')
    @patch('cognito.get_user_from_token')
    @patch('activity.create_activity_catalog_log')
    def test_catalog_creation_permission_enum_value(self,
                                                    mock_activity_log,
                                                    mock_get_user_token,
                                                    mock_s3_client,
                                                    mock_create_s3_folder,
                                                    mock_list_s3_contents,
                                                    mock_get_bucket):
        """Test that the permission granted is specifically PermissionType.FULL enum value"""
        
        with self.app.app_context():
            # Mock all external dependencies
            mock_get_bucket.return_value = 'test-bucket'
            mock_list_s3_contents.return_value = ['s3_folder']
            mock_create_s3_folder.return_value = 'test/path'
            
            # Mock S3 client
            mock_s3 = MagicMock()
            mock_s3_client.return_value = mock_s3
            
            # Mock user token validation
            mock_get_user_token.return_value = (True, {'email': 'test@example.com'})
            
            # Mock activity logging
            mock_activity_log.return_value = None
            
            # Import create_catalog here to avoid loading production config
            from catalog import create_catalog
            
            # Create catalog
            result = create_catalog('Permission Test Catalog', 'Test', 's3_folder')
            
            # Get the created catalog and permission
            created_catalog = Catalog.query.filter_by(name='Permission Test Catalog').first()
            permission = CatalogPermission.query.filter_by(
                catalog_id=created_catalog.id,
                user_id=self.test_user_id
            ).first()
            
            # Verify exact enum value
            self.assertEqual(permission.permission, PermissionType.FULL,
                           "Permission should be exactly PermissionType.FULL")
            self.assertEqual(permission.permission.value, 'FULL',
                           "Permission value should be 'FULL' string")
            
            # Verify it's not any other permission type
            self.assertNotEqual(permission.permission, PermissionType.READ_ONLY,
                              "Permission should not be READ_ONLY")
            self.assertNotEqual(permission.permission, PermissionType.CHAT_ONLY,
                              "Permission should not be CHAT_ONLY")
            self.assertNotEqual(permission.permission, PermissionType.NOT_ALLOWED,
                              "Permission should not be NOT_ALLOWED")
            
            # Verify the relationship works correctly
            self.assertEqual(permission.catalog_id, created_catalog.id,
                           "Permission should reference correct catalog")
            self.assertEqual(permission.user_id, self.test_user_id,
                           "Permission should reference correct user")
    
    def test_permission_enum_values(self):
        """Test that PermissionType enum has expected values"""
        with self.app.app_context():
            # Test all enum values exist
            self.assertEqual(PermissionType.NOT_ALLOWED.value, 'NOT_ALLOWED')
            self.assertEqual(PermissionType.CHAT_ONLY.value, 'CHAT_ONLY')
            self.assertEqual(PermissionType.READ_ONLY.value, 'READ_ONLY')
            self.assertEqual(PermissionType.FULL.value, 'FULL')
            
            # Test enum comparison
            self.assertNotEqual(PermissionType.FULL, PermissionType.READ_ONLY)
            self.assertTrue(PermissionType.FULL == PermissionType.FULL)


if __name__ == '__main__':
    unittest.main()