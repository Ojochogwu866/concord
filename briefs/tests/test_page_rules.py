from briefs.models import BriefIndexPage, BriefPage, HomePage


def test_home_page_only_holds_brief_index() -> None:
    assert HomePage.allowed_subpage_models() == [BriefIndexPage]


def test_brief_index_only_holds_briefs() -> None:
    assert BriefIndexPage.allowed_parent_page_models() == [HomePage]
    assert BriefIndexPage.allowed_subpage_models() == [BriefPage]


def test_briefs_live_under_index_and_have_no_children() -> None:
    assert BriefPage.allowed_parent_page_models() == [BriefIndexPage]
    assert BriefPage.allowed_subpage_models() == []
