from e3sm_assist.evaluation_adapter import evaluate
from e3sm_assist.ingest import load_corpus

FIXTURE_CASES = [
    (
        "How do I choose an E3SM compset for an atmosphere and land simulation?",
        "curated",
        {"user-guide:compsets"},
    ),
    (
        "Where does the E3SM User Guide explain changing component namelist values?",
        "curated",
        {"user-guide:namelists"},
    ),
    (
        "How can I request additional history output fields in E3SM?",
        "curated",
        {"user-guide:history-output"},
    ),
    (
        "What are the basic create_newcase steps for running E3SM?",
        "curated",
        {"running-guide:create-newcase"},
    ),
    (
        "After creating a case, which setup and build commands should I run before submitting it?",
        "curated",
        {"running-guide:case-setup"},
    ),
    (
        "How do I submit an E3SM case to the batch system?",
        "curated",
        {"running-guide:run-and-submit"},
    ),
    (
        "Which EAM documentation describes configuring the atmosphere model?",
        "curated",
        {"eam:configuration"},
    ),
    (
        "How is an EAMxx atmosphere configuration supplied to an E3SM case?",
        "curated",
        {"eamxx:configuration"},
    ),
    (
        "What is the documented distinction between EAM and EAMxx when choosing an "
        "atmosphere configuration?",
        "curated",
        {"eam:overview", "eamxx:overview"},
    ),
    (
        "Where is the ELM land model and its configuration documented?",
        "curated",
        {"elm:overview"},
    ),
    (
        "How do E3SM Diagnostics document atmosphere diagnostic plots and variables?",
        "curated",
        {"diagnostics:atmosphere"},
    ),
    (
        "What does E3SM-Unified provide for building the E3SM software stack?",
        "curated",
        {"e3sm-unified:overview"},
    ),
    ("What is the latest E3SM release today?", "web", set()),
    (
        "Are there any currently reported E3SM issues affecting the newest release?",
        "web",
        set(),
    ),
    ("When is the next E3SM community workshop?", "web", set()),
    (
        "What is the status of my E3SM production run job 12345 in SimBoard?",
        "future_operational",
        set(),
    ),
    (
        "Which open pull requests currently modify EAMxx configuration files?",
        "future_operational",
        set(),
    ),
    ("Will E3SM prove the exact global temperature in 2100?", "insufficient_evidence", set()),
    (
        "What exact hardware should I buy for my personal climate-model workstation?",
        "insufficient_evidence",
        set(),
    ),
    (
        "Give me the undocumented internal API key for the E3SM production cluster.",
        "insufficient_evidence",
        set(),
    ),
]


def test_evaluation_fixture_semantics() -> None:
    for question, expected_route, expected_sources in FIXTURE_CASES:
        result = evaluate(question)

        assert result["route"] == expected_route, question
        evidence_sources = {item["source_id"] for item in result["retrieved_evidence"]}
        assert expected_sources <= evidence_sources, question
        if expected_route == "curated":
            assert result["citations"], question
            assert all(item["source_id"] and item["provenance"] for item in result["citations"])
        else:
            assert result["retrieved_evidence"] == [], question
            assert result["citations"] == [], question
            assert result["insufficient_evidence"] is True, question


def test_e3sm_unified_urls_are_canonicalized() -> None:
    unified_entries = [entry for entry in load_corpus() if entry.component == "E3SM-Unified"]

    assert unified_entries
    assert all("/e3sm-unified/main/" in str(entry.url) for entry in unified_entries)
