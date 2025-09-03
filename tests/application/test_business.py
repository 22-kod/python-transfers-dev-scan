import pytest
from unittest.mock import patch, Mock
# Importando desde src.application
from src.application import business
from result import Ok, Err, Result


def test_get_use_case(): 
    mock_id = "some_id"
    result = business.user_get(mock_id) 
    match result:
        case Ok(user):
            assert user == {"id": mock_id}
        case Err(e):
            assert False, e


def test_user_create(): 
    mock_data = {"key": "value"}
    
    result = business.user_create(mock_data) 
    assert result.is_ok()