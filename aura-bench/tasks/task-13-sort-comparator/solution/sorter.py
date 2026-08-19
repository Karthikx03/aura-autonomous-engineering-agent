def sort_by_score_desc(records):
    """Sort records by 'score' descending."""
    return sorted(records, key=lambda r: r["score"], reverse=True)
