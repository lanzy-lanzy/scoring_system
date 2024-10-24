from django import template

register = template.Library()

@register.filter
def get_score(scores_dict, participant_id):
    return {k: v for k, v in scores_dict.items() if k.startswith(f"{participant_id}_")}

@register.filter
def get_criterion(participant_scores, criterion_id):
    key = next((k for k in participant_scores.keys() if k.endswith(f"_{criterion_id}")), None)
    return participant_scores[key].score if key else ""

@register.filter
def get_remarks(scores_dict, participant_id):
    scores = [v for k, v in scores_dict.items() if k.startswith(f"{participant_id}_")]
    return scores[0].remarks if scores else ""

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)