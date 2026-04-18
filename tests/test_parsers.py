"""Tests for file parsers."""

from abaqusgpt.parsers.msg_parser import MsgParser


class TestMsgParser:
    """Tests for MsgParser."""

    def test_parse_empty_content(self, tmp_path):
        """Test parsing empty file."""
        msg_file = tmp_path / "empty.msg"
        msg_file.write_text("")

        parser = MsgParser()
        result = parser.parse(msg_file)

        assert result["errors"] == []
        assert result["warnings"] == []

    def test_parse_errors(self, tmp_path):
        """Test parsing error messages."""
        content = """
***ERROR: TOO MANY ATTEMPTS MADE FOR THIS INCREMENT
***WARNING: SOME WARNING MESSAGE
        """
        msg_file = tmp_path / "test.msg"
        msg_file.write_text(content)

        parser = MsgParser()
        result = parser.parse(msg_file)

        assert len(result["errors"]) == 1
        assert "TOO MANY ATTEMPTS" in result["errors"][0]
        assert len(result["warnings"]) == 1

    def test_parse_step_info(self, tmp_path):
        """Test parsing step and increment info."""
        content = """
STEP    1  INCREMENT    10
ITERATION     5
        """
        msg_file = tmp_path / "test.msg"
        msg_file.write_text(content)

        parser = MsgParser()
        result = parser.parse(msg_file)

        assert result["last_step"] == 1
        assert result["last_increment"] == 10
