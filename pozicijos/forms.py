# pozicijos/forms.py
from django import forms
from .models import Pozicija


class PozicijaForm(forms.ModelForm):
    class Meta:
        model = Pozicija
        # nerodom techninių laukų
        exclude = ("created", "updated")
        widgets = {
            "pastabos": forms.Textarea(attrs={"rows": 3}),
            "instrukcija": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # padarom, kad kodas ir pavadinimas būtų privalomi
        for name in ("poz_kodas", "poz_pavad"):
            if name in self.fields:
                self.fields[name].required = True

        # visiems uždedam klasę, kad normaliai atrodytų
        for f in self.fields.values():
            cls = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (cls + " form-control").strip()
