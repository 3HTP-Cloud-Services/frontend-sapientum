#!/usr/bin/env python3
"""
Test script for external catalog creation API integration

This script demonstrates how the external catalog API is called
when creating a new catalog.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from catalog import call_external_catalog_api

def test_external_api_call():
    """
    Test the external catalog creation API call

    Note: This will make an actual API call to the external service.
    You'll need a valid JWT token for authentication.
    """
    print("\n" + "=" * 80)
    print("TESTING EXTERNAL CATALOG API INTEGRATION")
    print("=" * 80 + "\n")

    # Test parameters
    catalog_name = "test_catalog_demo"
    catalog_type = "General"  # Maps to 'general' in the API
    description = "This is a test catalog created via the external API"
    instruction = "Test instruction for catalog creation"
    apply = False  # Set to True to execute complete creation

    # Note: In production, this JWT token comes from the authenticated user
    # For testing, you would need to provide a valid token
    jwt_token = None  # Replace with actual token for testing

    print(f"Test Parameters:")
    print(f"  - catalog_name: {catalog_name}")
    print(f"  - catalog_type: {catalog_type}")
    print(f"  - description: {description}")
    print(f"  - instruction: {instruction}")
    print(f"  - apply: {apply}")
    print(f"  - jwt_token: {'Provided' if jwt_token else 'None (will test without auth)'}")
    print("\n")

    # Call the external API
    success, response = call_external_catalog_api(
        catalog_name=catalog_name,
        catalog_type=catalog_type,
        description=description,
        instruction=instruction,
        apply=apply,
        jwt_token=jwt_token
    )

    # Print results
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    print(f"Success: {success}")
    print(f"Response Data: {response}")
    print("=" * 80 + "\n")

    if success:
        print("✓ External API call succeeded!")
        print("\nThe full JSON response has been printed to the console above.")
    else:
        print("✗ External API call failed")
        print(f"\nError: {response.get('error', 'Unknown error')}")
        if response.get('detail'):
            print(f"Details: {response.get('detail')}")

    return success, response

if __name__ == "__main__":
    print("\n" + "!" * 80)
    print("! WARNING: This script will make an actual API call to the external service")
    print("! Make sure you have the correct permissions and JWT token")
    print("!" * 80 + "\n")

    # Uncomment the line below to run the test
    # test_external_api_call()

    print("To run the test, uncomment the last line in this script.")
    print("Remember to provide a valid JWT token if authentication is required.")
