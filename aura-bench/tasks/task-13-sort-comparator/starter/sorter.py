def sort_by_score_desc(records):
    """Sort records by 'score' descending."""
    # BUG: wrong key ('name' instead of 'score') and wrong direction (ascending)
    return sorted(records, key=lambda r: r["name"])
