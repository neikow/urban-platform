import pytest

from about.blocks import UserBlock, UserListBlock, MemberBlock, MembersListBlock


@pytest.mark.django_db
class TestUserBlock:
    def test_user_block_fields(self) -> None:
        block = UserBlock()
        assert "name" in block.declared_blocks
        assert "image" in block.declared_blocks
        assert "role" in block.declared_blocks
        assert "description" in block.declared_blocks
        assert "facebook_url" in block.declared_blocks

    def test_user_block_template(self) -> None:
        block = UserBlock()
        assert block.meta.template == "about/blocks/user_block.html"


@pytest.mark.django_db
class TestUserListBlock:
    def test_user_list_block_child_is_user_block(self) -> None:
        block = UserListBlock()
        assert isinstance(block.child_block, UserBlock)

    def test_user_list_block_template(self) -> None:
        block = UserListBlock()
        assert block.meta.template == "about/blocks/user_list_block.html"


@pytest.mark.django_db
class TestMemberBlock:
    def test_member_block_fields(self) -> None:
        block = MemberBlock()
        assert "name" in block.declared_blocks
        assert "image" in block.declared_blocks
        assert "role" in block.declared_blocks
        assert "description" in block.declared_blocks
        assert "github_url" in block.declared_blocks
        assert "facebook_url" in block.declared_blocks
        assert "personal_website_url" in block.declared_blocks

    def test_member_block_template(self) -> None:
        block = MemberBlock()
        assert block.meta.template == "about/blocks/member_block.html"


@pytest.mark.django_db
class TestMembersListBlock:
    def test_members_list_block_child_is_member_block(self) -> None:
        block = MembersListBlock()
        assert isinstance(block.child_block, MemberBlock)

    def test_members_list_block_template(self) -> None:
        block = MembersListBlock()
        assert block.meta.template == "about/blocks/members_list_block.html"
