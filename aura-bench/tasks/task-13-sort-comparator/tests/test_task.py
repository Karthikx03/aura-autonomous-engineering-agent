from sorter import sort_by_score_desc

RECORDS = [
    {"name": "a", "score": 10},
    {"name": "b", "score": 30},
    {"name": "c", "score": 20},
]


def test_sorted_by_score_descending():
    result = sort_by_score_desc(RECORDS)
    assert [r["name"] for r in result] == ["b", "c", "a"]


def test_scores_are_non_increasing():
    result = sort_by_score_desc(RECORDS)
    scores = [r["score"] for r in result]
    assert scores == sorted(scores, reverse=True)
