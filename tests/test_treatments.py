"""Every skill in ``treatments/`` loads: Harbor fails each Trial for a skill
directory without ``SKILL.md``, and Claude Code lists a skill by the ``name``
and ``description`` in its frontmatter."""

import pytest

from weval.run import TREATMENTS

SKILLS = sorted(TREATMENTS.glob("*/skills/*/"))


def test_treatments_exist():
    assert SKILLS


@pytest.mark.parametrize(
    "skill", SKILLS, ids=lambda path: f"{path.parents[1].name}/{path.name}"
)
def test_skill_has_frontmatter_naming_it(skill):
    text = (skill / "SKILL.md").read_text()
    frontmatter, _, _ = text.removeprefix("---\n").partition("\n---\n")
    fields = dict(line.split(": ", 1) for line in frontmatter.splitlines())
    assert fields["name"] == skill.name
    assert fields["description"]
