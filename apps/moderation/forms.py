from django import forms
from .models import ModerationAction, Region


class ModerationDecisionForm(forms.Form):
    """
    One generic decision form used for all event actions.
    """
    region = forms.ChoiceField(choices=Region.choices)
    event_id = forms.IntegerField(min_value=1)
    action = forms.ChoiceField(choices=ModerationAction.choices)
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note (rejection reason, cancellation note, etc.)"}),
        max_length=2000,
    )

    def clean(self):
        cleaned = super().clean()

        # Optional: enforce note for reject/cancel (common policy)
        action = cleaned.get("action")
        note = (cleaned.get("note") or "").strip()

        if action in {ModerationAction.REJECT, ModerationAction.CANCEL} and not note:
            self.add_error("note", "Please add a short note for this action.")

        return cleaned
