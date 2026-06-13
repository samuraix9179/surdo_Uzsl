import pytest
from scripts.validate_agent_tasks import validate_manifest, ValidationError


@pytest.fixture
def valid_manifest():
    return {
        "schema_version": 1,
        "project": "surdo",
        "task_source_priority": ["agent_tasks.json"],
        "risk_levels": ["low", "medium", "high", "critical"],
        "merge_policy": {
            "low": "auto",
            "medium": "auto",
            "high": "human",
            "critical": "manual"
        },
        "replenishment_policy": {
            "minimum_todo_tasks": 2,
            "batch_size": 2,
            "allowed_risks_for_generated_tasks": ["low", "medium"],
            "instruction": "Test instruction"
        },
        "tasks": [
            {
                "id": "task-1",
                "status": "todo",
                "area": "test",
                "risk": "low",
                "title": "Test task",
                "description": "Test description",
                "allowed_paths": ["test.py"],
                "acceptance": ["test passes"]
            },
            {
                "id": "task-2",
                "status": "todo",
                "area": "test",
                "risk": "low",
                "title": "Test task 2",
                "description": "Test description 2",
                "allowed_paths": ["test.py"],
                "acceptance": ["test passes"]
            }
        ]
    }


def test_valid_manifest(valid_manifest):
    warnings = validate_manifest(valid_manifest)
    assert isinstance(warnings, list)


def test_missing_schema_version(valid_manifest):
    del valid_manifest["schema_version"]
    with pytest.raises(ValidationError, match="schema_version must be 1"):
        validate_manifest(valid_manifest)


def test_invalid_schema_version(valid_manifest):
    valid_manifest["schema_version"] = 2
    with pytest.raises(ValidationError, match="schema_version must be 1"):
        validate_manifest(valid_manifest)


def test_missing_tasks(valid_manifest):
    del valid_manifest["tasks"]
    with pytest.raises(ValidationError, match="tasks must be a non-empty array"):
        validate_manifest(valid_manifest)


def test_empty_tasks(valid_manifest):
    valid_manifest["tasks"] = []
    with pytest.raises(ValidationError, match="tasks must be a non-empty array"):
        validate_manifest(valid_manifest)


def test_invalid_task_status(valid_manifest):
    valid_manifest["tasks"][0]["status"] = "unknown_status"
    with pytest.raises(ValidationError, match="unknown status 'unknown_status'"):
        validate_manifest(valid_manifest)


def test_missing_task_fields(valid_manifest):
    del valid_manifest["tasks"][0]["title"]
    with pytest.raises(ValidationError, match="missing fields"):
        validate_manifest(valid_manifest)


def test_duplicate_task_id(valid_manifest):
    valid_manifest["tasks"][1]["id"] = "task-1"
    with pytest.raises(ValidationError, match="duplicate task id: task-1"):
        validate_manifest(valid_manifest)
