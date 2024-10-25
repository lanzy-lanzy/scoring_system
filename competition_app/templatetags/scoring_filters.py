from django import template

register = template.Library()

@register.filter
def get_score(score_lookup, ids):
    """Gets score from lookup dictionary using participant and criterion IDs"""
    participant_id, criterion_id = ids.split(',')
    return score_lookup.get((int(participant_id), int(criterion_id)), '')

@register.filter
def get_remarks(score_lookup, key_pair):
    """Get remarks value from lookup dictionary"""
    participant_id, criterion_id = key_pair
    key = f"{participant_id}_{criterion_id}"
    score = score_lookup.get(key)
    return score.remarks if score else ''

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get item from dictionary"""
    if dictionary is None:
        return None
    return dictionary.get(key)
    return score_lookup.get((participant_id, criterion_id), '')