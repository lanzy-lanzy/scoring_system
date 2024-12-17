from django import template
from competition_app.models import Participant

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_participant(competition, participant_id):
    return competition.participants.filter(id=participant_id).first()

@register.filter
def format_score(value):
    if value is None:
        return "-"
    return "{:.2f}".format(float(value))
