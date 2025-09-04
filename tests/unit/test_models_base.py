"""Comprehensive tests for base models."""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any

from src.models.base import (
    BaseModelWithConfig,
    TimestampedModel,
    APIResponse,
    PaginatedResponse,
)


class TestBaseModelWithConfig:
    """Test BaseModelWithConfig functionality."""

    def test_should_create_model_with_valid_data(self):
        """Test that model creation works with valid data."""
        
        class TestModel(BaseModelWithConfig):
            name: str
            value: int
        
        model = TestModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

    def test_should_strip_whitespace_from_strings(self):
        """Test that string fields are automatically stripped."""
        
        class TestModel(BaseModelWithConfig):
            name: str
        
        model = TestModel(name="  test  ")
        assert model.name == "test"

    def test_should_forbid_extra_fields(self):
        """Test that extra fields are forbidden."""
        
        class TestModel(BaseModelWithConfig):
            name: str
        
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            TestModel(name="test", extra_field="should_fail")

    def test_should_validate_on_assignment(self):
        """Test that validation occurs on field assignment."""
        
        class TestModel(BaseModelWithConfig):
            value: int
        
        model = TestModel(value=42)
        
        with pytest.raises(ValueError):
            model.value = "not_an_int"

    def test_should_validate_default_values(self):
        """Test that default values are validated."""
        
        with pytest.raises(ValueError):
            class TestModel(BaseModelWithConfig):
                value: int = "invalid_default"


class TestTimestampedModel:
    """Test TimestampedModel functionality."""

    def test_should_create_with_automatic_timestamp(self):
        """Test that created_at is automatically set."""
        before = datetime.now(timezone.utc)
        model = TimestampedModel()
        after = datetime.now(timezone.utc)
        
        assert before <= model.created_at <= after
        assert model.updated_at is None

    def test_should_accept_custom_created_at(self):
        """Test that custom created_at can be provided."""
        custom_time = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        model = TimestampedModel(created_at=custom_time)
        
        assert model.created_at == custom_time

    def test_should_mark_updated_correctly(self):
        """Test that mark_updated sets updated_at timestamp."""
        model = TimestampedModel()
        original_created = model.created_at
        
        # Small delay to ensure different timestamps
        import time
        time.sleep(0.01)
        
        model.mark_updated()
        
        assert model.created_at == original_created
        assert model.updated_at is not None
        assert model.updated_at > model.created_at

    def test_should_update_timestamp_on_multiple_calls(self):
        """Test that multiple mark_updated calls update the timestamp."""
        model = TimestampedModel()
        model.mark_updated()
        first_update = model.updated_at
        
        import time
        time.sleep(0.01)
        
        model.mark_updated()
        
        assert model.updated_at > first_update

    def test_should_inherit_base_config(self):
        """Test that TimestampedModel inherits base configuration."""
        
        class TestTimestampedModel(TimestampedModel):
            name: str
        
        model = TestTimestampedModel(name="  test  ")
        assert model.name == "test"  # Whitespace stripped


class TestAPIResponse:
    """Test APIResponse functionality."""

    def test_should_create_success_response_with_defaults(self):
        """Test creating success response with default values."""
        response = APIResponse.success_response()
        
        assert response.success is True
        assert response.message == "Request successful"
        assert response.data is None
        assert response.errors is None

    def test_should_create_success_response_with_data(self):
        """Test creating success response with custom data."""
        data = {"key": "value"}
        message = "Custom success"
        
        response = APIResponse.success_response(data=data, message=message)
        
        assert response.success is True
        assert response.message == message
        assert response.data == data
        assert response.errors is None

    def test_should_create_error_response_with_string_error(self):
        """Test creating error response with single error string."""
        error = "Something went wrong"
        
        response = APIResponse.error_response(error)
        
        assert response.success is False
        assert response.message == "Request failed"
        assert response.data is None
        assert response.errors == [error]

    def test_should_create_error_response_with_list_errors(self):
        """Test creating error response with list of errors."""
        errors = ["Error 1", "Error 2"]
        message = "Multiple errors occurred"
        
        response = APIResponse.error_response(errors, message=message)
        
        assert response.success is False
        assert response.message == message
        assert response.data is None
        assert response.errors == errors

    def test_should_validate_response_structure(self):
        """Test that APIResponse validates its structure."""
        # Valid response
        response = APIResponse(
            success=True,
            message="Test",
            data={"test": True},
            errors=None
        )
        assert response.success is True

        # Test that required fields are enforced
        with pytest.raises(ValueError):
            APIResponse(success=True)  # Missing required message field

    def test_should_serialize_to_dict(self):
        """Test that APIResponse serializes correctly."""
        response = APIResponse.success_response(
            data={"test": "value"},
            message="Success"
        )
        
        response_dict = response.model_dump()
        
        expected = {
            "success": True,
            "message": "Success",
            "data": {"test": "value"},
            "errors": None
        }
        
        assert response_dict == expected


class TestPaginatedResponse:
    """Test PaginatedResponse functionality."""

    def test_should_create_paginated_response_with_defaults(self):
        """Test creating paginated response with default pagination."""
        items = [1, 2, 3]
        total = 50
        
        response = PaginatedResponse.create(items=items, total=total)
        
        assert response.items == items
        assert response.total == total
        assert response.page == 1
        assert response.size == 20
        assert response.pages == 3  # ceil(50/20)

    def test_should_create_paginated_response_with_custom_pagination(self):
        """Test creating paginated response with custom page and size."""
        items = list(range(10))
        total = 100
        page = 2
        size = 10
        
        response = PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size
        )
        
        assert response.items == items
        assert response.total == total
        assert response.page == page
        assert response.size == size
        assert response.pages == 10  # ceil(100/10)

    def test_should_calculate_pages_correctly_for_exact_division(self):
        """Test page calculation when total divides evenly."""
        response = PaginatedResponse.create(
            items=[],
            total=40,
            size=10
        )
        
        assert response.pages == 4

    def test_should_calculate_pages_correctly_for_partial_last_page(self):
        """Test page calculation with partial last page."""
        response = PaginatedResponse.create(
            items=[],
            total=41,
            size=10
        )
        
        assert response.pages == 5

    def test_should_handle_zero_total(self):
        """Test handling of zero total items."""
        response = PaginatedResponse.create(
            items=[],
            total=0,
            size=10
        )
        
        assert response.items == []
        assert response.total == 0
        assert response.pages == 1  # Always at least 1 page

    def test_should_validate_pagination_constraints(self):
        """Test that pagination validates constraints."""
        # Valid pagination
        response = PaginatedResponse(
            items=[1, 2, 3],
            total=3,
            page=1,
            size=10,
            pages=1
        )
        assert response.page == 1

        # Test validation constraints
        with pytest.raises(ValueError):
            PaginatedResponse(
                items=[],
                total=-1,  # Invalid: negative total
                page=1,
                size=10,
                pages=1
            )

        with pytest.raises(ValueError):
            PaginatedResponse(
                items=[],
                total=10,
                page=0,  # Invalid: page must be >= 1
                size=10,
                pages=1
            )

        with pytest.raises(ValueError):
            PaginatedResponse(
                items=[],
                total=10,
                page=1,
                size=101,  # Invalid: size too large
                pages=1
            )

    def test_should_serialize_correctly(self):
        """Test that PaginatedResponse serializes correctly."""
        items = ["item1", "item2"]
        response = PaginatedResponse.create(
            items=items,
            total=25,
            page=2,
            size=5
        )
        
        response_dict = response.model_dump()
        
        expected = {
            "items": items,
            "total": 25,
            "page": 2,
            "size": 5,
            "pages": 5
        }
        
        assert response_dict == expected