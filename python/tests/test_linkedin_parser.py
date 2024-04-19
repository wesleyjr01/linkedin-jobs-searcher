import json
from python_package.lambda_function import LinkedinJobParser
from unittest.mock import patch, PropertyMock, mock_open


def test_epoch_to_timestamp():
    epoch_time = 1712878212000
    expected = "2024-04-11 23:30:12"
    assert LinkedinJobParser.epoch_to_timestamp(epoch_time) == expected


def test_epoch_to_date():
    epoch_time = 1712878212000
    expected = "2024-04-11"
    assert LinkedinJobParser.epoch_to_date(epoch_time) == expected


@patch.object(
    LinkedinJobParser,
    "get_jobs",
    new_callable=PropertyMock,
)
@patch("python_package.lambda_function.LinkedinJobParser.get_api_client")
def test_get_job_ids(p_client, p_get_jobs):
    p_client.return_value = None
    p_get_jobs.return_value = [
        {"trackingUrn": "urn:li:jobPosting:3895256357"},
        {"trackingUrn": "urn:li:jobPosting:3894466400"},
    ]
    jobs_searcher = LinkedinJobParser(
        login_email="",
        login_password="",
        keywords="",
        days_old_listed_job="",
    )
    assert jobs_searcher._job_ids == ["3895256357", "3894466400"]


def test_export_as_jsonl():
    # Prepare the data to be tested
    data_to_test = [
        {"name": "Alice", "age": 25, "city": "New York"},
        {"name": "Bob", "age": 30, "city": "Los Angeles"},
        {"name": "Charlie", "age": 35, "city": "Chicago"},
    ]

    # Expected JSON Lines output as a string
    expected_output = "".join(json.dumps(item) + "\n" for item in data_to_test)

    # Use mock_open to simulate file operations
    with patch("builtins.open", mock_open()) as mocked_file:
        # Call the function
        LinkedinJobParser.export_list_of_dict_as_jsonl(data_to_test, "dummy_file.jsonl")

        # Check that open was called correctly
        mocked_file.assert_called_once_with("dummy_file.jsonl", "w", encoding="utf-8")

        # Ensure all data was written correctly
        written_data = "".join(
            call.args[0] for call in mocked_file().write.call_args_list
        )
        assert (
            written_data == expected_output
        ), "The data written to the file does not match the expected output."


def test_is_word_in_info():
    word = "AWS"
    text1 = "We are looking for a Cloud Engineer with experience in aWs."
    text2 = "We are looking for a Cloud Engineer with experience in asdgAWSgasf."
    text3 = "We are looking for a Cloud Engineer with experience in Azure."

    assert LinkedinJobParser.is_word_in_text(word, text1) is True
    assert LinkedinJobParser.is_word_in_text(word, text2) is False
    assert LinkedinJobParser.is_word_in_text(word, text3) is False

    word_2 = "Pessoa"
    text4 = "Pessoa Engenheira de Dados."
    assert LinkedinJobParser.is_word_in_text(word_2, text4) is True


def test_get_information_from_job():
    pass
