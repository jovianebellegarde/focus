"""Phase 6 domain labels — map match, precedence, convention fallback."""

from pathlib import Path

from focus.config import FocusConfig, load_config
from focus.graph import build_graph, downstream_rings
from focus.hud import build_hud
from focus.hud.domains import (
    convention_domain_label,
    domain_for_seeds,
    match_domain,
)
from focus.scan import discover_python_files, parse_module


def test_match_domain_first_glob_wins():
    domains = {
        "billing/**": "Revenue / charge path",
        "billing/charge.py": "Should not win — later",
        "auth/**": "Auth boundary",
    }
    assert match_domain("billing/charge.py", domains) == "Revenue / charge path"
    assert match_domain("auth/utils.py", domains) == "Auth boundary"
    assert match_domain("docs/README.md", domains) is None


def test_match_domain_exact_and_star():
    domains = {"api/routes.py": "Public HTTP surface", "jobs/*": "Background jobs"}
    assert match_domain("api/routes.py", domains) == "Public HTTP surface"
    assert match_domain("jobs/worker.py", domains) == "Background jobs"
    assert match_domain("jobs/nested/x.py", domains) is None


def test_domain_for_seeds_map_over_convention():
    domains = {"auth_utils.py": "Login boundary"}
    # Convention would also fire for auth danger path names, but map wins.
    assert (
        domain_for_seeds(["auth_utils.py"], domains, danger_paths={"auth_utils.py"})
        == "Login boundary"
    )


def test_domain_for_seeds_empty_map_uses_convention_on_auth_danger():
    assert (
        domain_for_seeds(["auth_utils.py"], {}, danger_paths={"auth_utils.py"})
        == "Auth boundary"
    )


def test_domain_for_seeds_nonempty_map_no_match_stays_quiet():
    # Owner declared domains but none match — do not invent via convention.
    assert (
        domain_for_seeds(
            ["auth_utils.py"],
            {"billing/**": "Revenue"},
            danger_paths={"auth_utils.py"},
        )
        is None
    )


def test_convention_billing_and_auth_only_when_dangerish():
    assert convention_domain_label("auth_utils.py") is None  # not danger_path alone
    assert (
        convention_domain_label("auth_utils.py", treat_as_danger=True) == "Auth boundary"
    )
    assert (
        convention_domain_label("billing/charge.py", treat_as_danger=True)
        == "Billing / payment path"
    )
    assert convention_domain_label("helpers/util.py", treat_as_danger=True) is None


def test_load_config_parses_domains(tmp_path: Path):
    (tmp_path / ".focus.toml").write_text(
        '[domains]\n"billing/**" = "Revenue / charge path"\n'
        '"auth/**" = "Auth boundary"\n',
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.domains["billing/**"] == "Revenue / charge path"
    assert list(cfg.domains)[0] == "billing/**"


def test_build_hud_summary_includes_domain_once(glass_box_path: Path):
    facts = [parse_module(f) for f in discover_python_files(glass_box_path)]
    graph = build_graph(facts, glass_box_path)
    rings = downstream_rings(graph, "auth_utils.py")
    hud = build_hud(
        graph,
        "auth_utils.py",
        rings,
        domains={"auth_utils.py": "Login boundary"},
    )
    assert hud.mode == "full"
    assert hud.summary.count("Login boundary") == 1
    assert "touches **Login boundary**" in hud.summary


def test_build_hud_without_domains_keeps_quiet_or_convention(glass_box_path: Path):
    facts = [parse_module(f) for f in discover_python_files(glass_box_path)]
    graph = build_graph(facts, glass_box_path)
    rings = downstream_rings(graph, "auth_utils.py")
    hud = build_hud(graph, "auth_utils.py", rings, domains={})
    # auth_utils.py is a danger hub with "auth" in the name → convention may apply.
    if "Auth boundary" in hud.summary:
        assert hud.summary.count("Auth boundary") == 1
    else:
        assert "touches **" not in hud.summary


def test_focus_config_default_domains_empty():
    assert FocusConfig().domains == {}
