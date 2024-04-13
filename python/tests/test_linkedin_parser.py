from python_package.linkedin_parser import LinkedinJobParser


def test_epoch_to_timestamp():
    epoch_time = 1712878212000
    expected = "2024-04-11 23:30:12"
    assert LinkedinJobParser.epoch_to_timestamp(epoch_time) == expected
