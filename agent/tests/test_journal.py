import pytest

from urban_agent import journal as journal_module
from urban_agent.hints import hint
from urban_agent.journal import Journal


@pytest.fixture
def path(tmp_path):
    return tmp_path / "journal.json"


class TestJournal:
    def test_kept_until_acknowledged(self, path):
        journal = Journal(path)
        journal.record("info", "one")
        journal.record("error", "two", slug="aix", detail="x" * 20_000)

        again = Journal(path)  # after a restart
        assert again.id == journal.id
        assert [(e["seq"], e["message"]) for e in again.pending()] == [(1, "one"), (2, "two")]
        assert len(again.pending()[1]["detail"]) == journal_module.DETAIL_LIMIT

        again.acknowledge({"events_ack": 1})
        assert [e["seq"] for e in Journal(path).pending()] == [2]

    @pytest.mark.parametrize("answer", [None, {}, {"events_ack": "2"}, {"events_ack": True}])
    def test_ignores_other_answers(self, path, answer):
        journal = Journal(path)
        journal.record("info", "one")

        journal.acknowledge(answer)

        assert len(journal.pending()) == 1

    def test_never_acknowledges_what_it_did_not_send(self, path):
        journal = Journal(path)
        journal.record("info", "one")
        journal.acknowledge({"events_ack": 99})
        journal.record("info", "two")

        assert [e["seq"] for e in journal.pending()] == [2]

    def test_oldest_dropped_beyond_the_limit(self, path, monkeypatch):
        monkeypatch.setattr(journal_module, "LIMIT", 3)
        monkeypatch.setattr(journal_module, "BATCH", 2)
        journal = Journal(path)
        for n in range(5):
            journal.record("info", str(n))

        assert [e["message"] for e in journal.pending()] == ["2", "3"]

    def test_a_lost_journal_gets_a_new_id(self, path):
        first = Journal(path).id
        path.write_text("not json")

        assert Journal(path).id != first


class TestHints:
    def test_known_cause(self):
        error = "docker compose -p aix: service migrator didn't complete successfully: exit 1"
        logs = 'FATAL:  password authentication failed for user "urban"'

        assert "same slug" in hint(error, logs)

    def test_unknown_cause(self):
        assert hint("something else") == ""
