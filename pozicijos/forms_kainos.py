# pozicijos/forms_kainos.py
from django import forms

from .models import PozicijosKaina


class PozicijosKainaForm(forms.ModelForm):
    class Meta:
        model = PozicijosKaina
        fields = [
            "suma",
            "kainos_matas",
            "busena",
            "kiekis_nuo",
            "kiekis_iki",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")
        self.fields["suma"].label = "Kaina / suma"
        self.fields["kainos_matas"].label = "Kainos matas (vnt., komplektas...)"
        self.fields["busena"].label = "Būsena"
        self.fields["kiekis_nuo"].label = "Kiekis nuo"
        self.fields["kiekis_iki"].label = "Kiekis iki"
