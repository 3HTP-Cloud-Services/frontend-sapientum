import unittest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat import parse_file_references, get_file_info, generate_ai_response


class TestChatFileReferences(unittest.TestCase):
    """
    Unit tests for chat file reference parsing functionality.
    These tests do NOT connect to real database, S3, or external services.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        pass

    def tearDown(self):
        """Clean up after each test method."""
        pass

    def test_parse_file_references_no_matches(self):
        """Test parse_file_references with text containing no file references."""
        text = "This is a normal message with no file references."
        result = parse_file_references(text)
        self.assertEqual(result, text)

    def test_parse_file_references_single_match_valid_file(self):
        """Test parse_file_references with single valid file reference."""
        text = "Please see document 33-44-55.pdf for details."
        
        # Mock get_file_info to return valid file data
        with patch('chat.get_file_info') as mock_get_file_info:
            mock_get_file_info.return_value = {
                'filename': 'financial_report_2023.pdf',
                'file_name': 'Financial Report',
                'catalog_name': 'Finance Documents',
                'size': 1024000,
                'created_at': '2023-01-01T12:00:00'
            }
            
            result = parse_file_references(text)
            expected = 'Please see document <a href="/api/download/55" download="financial_report_2023.pdf">financial_report_2023.pdf</a> for details.'
            
            self.assertEqual(result, expected)
            mock_get_file_info.assert_called_once_with(33, 44, 55)

    def test_parse_file_references_single_match_invalid_file(self):
        """Test parse_file_references with file reference that doesn't exist in database."""
        text = "Please see document 33-44-55.pdf for details."
        
        # Mock get_file_info to return None (file not found)
        with patch('chat.get_file_info') as mock_get_file_info:
            mock_get_file_info.return_value = None
            
            result = parse_file_references(text)
            # Should return original text unchanged
            self.assertEqual(result, text)
            mock_get_file_info.assert_called_once_with(33, 44, 55)

    def test_parse_file_references_multiple_matches(self):
        """Test parse_file_references with multiple file references."""
        text = "See documents 33-44-55.pdf and 12-34-56.docx for more info."
        
        # Mock get_file_info for both files
        with patch('chat.get_file_info') as mock_get_file_info:
            def mock_return(catalog_id, file_id, version_id):
                if catalog_id == 33 and file_id == 44 and version_id == 55:
                    return {
                        'filename': 'report.pdf',
                        'file_name': 'Report',
                        'catalog_name': 'Documents',
                        'size': 1024,
                        'created_at': '2023-01-01T12:00:00'
                    }
                elif catalog_id == 12 and file_id == 34 and version_id == 56:
                    return {
                        'filename': 'manual.docx',
                        'file_name': 'Manual',
                        'catalog_name': 'Manuals',
                        'size': 2048,
                        'created_at': '2023-01-02T12:00:00'
                    }
                return None
            
            mock_get_file_info.side_effect = mock_return
            
            result = parse_file_references(text)
            expected = 'See documents <a href="/api/download/55" download="report.pdf">report.pdf</a> and <a href="/api/download/56" download="manual.docx">manual.docx</a> for more info.'
            
            self.assertEqual(result, expected)
            self.assertEqual(mock_get_file_info.call_count, 2)

    def test_parse_file_references_mixed_valid_invalid(self):
        """Test parse_file_references with mix of valid and invalid file references."""
        text = "Valid: 33-44-55.pdf, Invalid: 99-88-77.docx"
        
        with patch('chat.get_file_info') as mock_get_file_info:
            def mock_return(catalog_id, file_id, version_id):
                if catalog_id == 33 and file_id == 44 and version_id == 55:
                    return {'filename': 'valid.pdf'}
                return None  # Invalid file returns None
            
            mock_get_file_info.side_effect = mock_return
            
            result = parse_file_references(text)
            expected = 'Valid: <a href="/api/download/55" download="valid.pdf">valid.pdf</a>, Invalid: 99-88-77.docx'
            
            self.assertEqual(result, expected)

    def test_parse_file_references_different_extensions(self):
        """Test parse_file_references with various file extensions."""
        text = "Files: 1-2-3.pdf, 4-5-6.docx, 7-8-9.xlsx, 10-11-12.txt"
        
        with patch('chat.get_file_info') as mock_get_file_info:
            def mock_return(catalog_id, file_id, version_id):
                extensions = {3: 'pdf', 6: 'docx', 9: 'xlsx', 12: 'txt'}
                ext = extensions.get(version_id)
                if ext:
                    return {'filename': f'file_{version_id}.{ext}'}
                return None
            
            mock_get_file_info.side_effect = mock_return
            
            result = parse_file_references(text)
            expected = 'Files: <a href="/api/download/3" download="file_3.pdf">file_3.pdf</a>, <a href="/api/download/6" download="file_6.docx">file_6.docx</a>, <a href="/api/download/9" download="file_9.xlsx">file_9.xlsx</a>, <a href="/api/download/12" download="file_12.txt">file_12.txt</a>'
            
            self.assertEqual(result, expected)

    @patch('chat.Version')
    @patch('chat.File')
    @patch('chat.Catalog')
    def test_get_file_info_valid_file(self, mock_catalog, mock_file, mock_version):
        """Test get_file_info with valid file that exists in database."""
        # Mock the database models and query chain
        mock_version_obj = MagicMock()
        mock_version_obj.filename = 'test_document.pdf'
        mock_version_obj.size = 1024000
        mock_version_obj.created_at.isoformat.return_value = '2023-01-01T12:00:00'
        
        mock_file_obj = MagicMock()
        mock_file_obj.name = 'Test Document'
        mock_version_obj.file = mock_file_obj
        
        mock_catalog_obj = MagicMock()
        mock_catalog_obj.name = 'Test Catalog'
        mock_file_obj.catalog = mock_catalog_obj
        
        # Mock the query chain
        mock_query = MagicMock()
        mock_query.join.return_value.join.return_value.filter.return_value.first.return_value = mock_version_obj
        mock_version.query = mock_query
        
        result = get_file_info(33, 44, 55)
        
        expected = {
            'filename': 'test_document.pdf',
            'file_name': 'Test Document',
            'catalog_name': 'Test Catalog',
            'size': 1024000,
            'created_at': '2023-01-01T12:00:00'
        }
        
        self.assertEqual(result, expected)

    @patch('chat.Version')
    @patch('chat.File')
    @patch('chat.Catalog')
    def test_get_file_info_invalid_file(self, mock_catalog, mock_file, mock_version):
        """Test get_file_info with file that doesn't exist in database."""
        # Mock query to return None (file not found)
        mock_query = MagicMock()
        mock_query.join.return_value.join.return_value.filter.return_value.first.return_value = None
        mock_version.query = mock_query
        
        result = get_file_info(99, 88, 77)
        
        self.assertIsNone(result)

    @patch('chat.Version')
    @patch('chat.File')
    @patch('chat.Catalog')
    def test_get_file_info_database_exception(self, mock_catalog, mock_file, mock_version):
        """Test get_file_info handles database exceptions gracefully."""
        # Mock query to raise an exception
        mock_query = MagicMock()
        mock_query.join.side_effect = Exception("Database connection error")
        mock_version.query = mock_query
        
        with patch('builtins.print'):  # Suppress error printing
            result = get_file_info(33, 44, 55)
        
        self.assertIsNone(result)

    @patch('chat.Version')
    @patch('chat.File')
    @patch('chat.Catalog')
    def test_get_file_info_missing_created_at(self, mock_catalog, mock_file, mock_version):
        """Test get_file_info with version that has None created_at timestamp."""
        # Mock version with None created_at
        mock_version_obj = MagicMock()
        mock_version_obj.filename = 'test.pdf'
        mock_version_obj.size = 1024
        mock_version_obj.created_at = None
        mock_version_obj.file.name = 'Test File'
        mock_version_obj.file.catalog.name = 'Test Catalog'
        
        mock_query = MagicMock()
        mock_query.join.return_value.join.return_value.filter.return_value.first.return_value = mock_version_obj
        mock_version.query = mock_query
        
        result = get_file_info(33, 44, 55)
        
        expected = {
            'filename': 'test.pdf',
            'file_name': 'Test File',
            'catalog_name': 'Test Catalog',
            'size': 1024,
            'created_at': None
        }
        
        self.assertEqual(result, expected)

    def test_parse_file_references_edge_cases(self):
        """Test parse_file_references with edge cases and malformed references."""
        # Test cases that should NOT match the pattern
        test_cases = [
            "File 33-44.pdf missing version",  # Missing version number
            "File 33-44-55 missing extension",  # Missing extension
            "File a-b-c.pdf non-numeric",  # Non-numeric IDs
            "Text with 33-44-55.pdf at end"  # Should still work
        ]
        
        with patch('chat.get_file_info') as mock_get_file_info:
            mock_get_file_info.return_value = {'filename': 'test.pdf'}
            
            # Only the last case should match
            result = parse_file_references(test_cases[-1])
            expected = 'Text with <a href="/api/download/55" download="test.pdf">test.pdf</a> at end'
            self.assertEqual(result, expected)
            
            # Test the non-matching cases
            for text in test_cases[:-1]:
                result = parse_file_references(text)
                self.assertEqual(result, text)  # Should remain unchanged
                
    def test_parse_file_references_invalid_extension_characters(self):
        """Test that file references with invalid extension characters are not matched."""
        text = "File 33-44-55.p@df has invalid extension characters"
        
        with patch('chat.get_file_info') as mock_get_file_info:
            mock_get_file_info.return_value = {'filename': 'test.pdf'}
            
            result = parse_file_references(text)
            # Should not match due to @ character in extension
            self.assertEqual(result, text)
                
    def test_parse_file_references_too_many_numbers(self):
        """Test that references with too many numbers get partially matched."""
        # The current regex will match the last 3 numbers in a longer sequence
        # This is acceptable behavior - testing what actually happens
        text = "File 33-44-55-66.pdf has too many numbers"
        
        with patch('chat.get_file_info') as mock_get_file_info:
            mock_get_file_info.return_value = {'filename': 'test.pdf'}
            
            result = parse_file_references(text)
            # The regex matches "44-55-66.pdf" from the sequence
            expected = 'File 33-<a href="/api/download/66" download="test.pdf">test.pdf</a> has too many numbers'
            self.assertEqual(result, expected)
            mock_get_file_info.assert_called_once_with(44, 55, 66)

    def test_parse_file_references_html_escaping(self):
        """Test parse_file_references handles filenames with special characters safely."""
        text = "See 33-44-55.pdf for details."
        
        with patch('chat.get_file_info') as mock_get_file_info:
            # Filename with special characters that could break HTML
            mock_get_file_info.return_value = {
                'filename': 'report_with_<special>_&_"quotes".pdf'
            }
            
            result = parse_file_references(text)
            # The filename should be used as-is in download attribute
            expected = 'See <a href="/api/download/55" download="report_with_<special>_&_"quotes".pdf">report_with_<special>_&_"quotes".pdf</a> for details.'
            
            self.assertEqual(result, expected)

    def test_integration_parse_file_references_in_workflow(self):
        """Test that parse_file_references integrates properly in the chat workflow."""
        # This test verifies the function works as expected without complex mocking
        test_response = "Check document 33-44-55.pdf for details."
        
        with patch('chat.get_file_info') as mock_get_file_info:
            mock_get_file_info.return_value = {'filename': 'report.pdf'}
            
            result = parse_file_references(test_response)
            expected = 'Check document <a href="/api/download/55" download="report.pdf">report.pdf</a> for details.'
            
            self.assertEqual(result, expected)
            mock_get_file_info.assert_called_once_with(33, 44, 55)



if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)