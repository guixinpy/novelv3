CHAPTER_SCOPED_TRUTH_PREDICATES = {"presence_count"}


def is_chapter_scoped_truth_predicate(predicate: str) -> bool:
    return predicate in CHAPTER_SCOPED_TRUTH_PREDICATES
