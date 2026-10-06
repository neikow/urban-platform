from urllib.robotparser import RobotFileParser

import pytest


@pytest.fixture
def robots(client) -> RobotFileParser:
    response = client.get("/robots.txt")
    assert response.status_code == 200
    parser = RobotFileParser()
    parser.parse(response.content.decode().splitlines())
    return parser


@pytest.mark.django_db
@pytest.mark.parametrize("agent", ["*", "Googlebot", "GPTBot", "ClaudeBot", "PerplexityBot"])
def test_private_paths_are_disallowed_for_every_agent(robots, agent):
    for path in ("/admin/", "/django-admin/", "/auth/login/", "/api/projects/1/vote/"):
        assert not robots.can_fetch(agent, path), (agent, path)


@pytest.mark.django_db
@pytest.mark.parametrize("agent", ["*", "GPTBot"])
def test_public_pages_are_allowed(robots, agent):
    assert robots.can_fetch(agent, "/")
    assert robots.can_fetch(agent, "/actualites/some-project/")
