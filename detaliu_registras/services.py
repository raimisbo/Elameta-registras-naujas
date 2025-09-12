"""
Service layer for business logic
Separates complex operations from views and models
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Count
from .models import Klientas, Projektas, Detale, Uzklausa, Kaina
import logging

logger = logging.getLogger(__name__)


class UzklausaService:
    """Service for handling complex Uzklausa operations"""

    @staticmethod
    @transaction.atomic
    def create_full_request(form_data):
        """
        Sukuria pilną užklausą (Klientas/Projektas/Detale/Uzklausa) arba panaudoja jau duotus egzistuojančius objektus.
        Tikslas – nelaužyti projekto, jeigu kai kurie modelių laukai yra privalomi.
        Tikėtini raktai form_data:
          - existing_klientas (obj arba pk) | new_klientas_vardas
          - existing_projektas (obj arba pk) | projekto_pavadinimas, uzklausos_data, pasiulymo_data
          - existing_detale (obj arba pk) | detale_fields (žodynas su laukais)
        """
        try:
            klientas = UzklausaService._get_or_create_klientas(form_data)
            projektas = UzklausaService._get_or_create_projektas(form_data, klientas)
            detale = UzklausaService._get_or_create_detale(form_data, projektas)

            uzklausa = Uzklausa.objects.create(
                klientas=klientas,
                projektas=projektas,
                detale=detale,
            )
            logger.info("Sukurta užklausa id=%s klientui '%s'", uzklausa.id, getattr(klientas, "vardas", klientas))
            return uzklausa

        except ValidationError:
            raise
        except Exception as e:
            logger.exception("Klaida kuriant pilną užklausą: %s", e)
            raise ValidationError(f"Nepavyko sukurti užklausos: {e}")

    @staticmethod
    def _resolve_instance_or_pk(model_cls, value, field_name="id"):
        """Leidžia paduoti arba instancą, arba pirminį raktą; grąžina instancą."""
        if value is None:
            return None
        if isinstance(value, model_cls):
            return value
        return model_cls.objects.get(**{field_name: value})

    @staticmethod
    def _get_or_create_klientas(form_data):
        """Naudoja esamą klientą (obj/pk) arba sukuria naują iš vardo."""
        existing_kl = form_data.get("existing_klientas")
        new_kl_vardas = form_data.get("new_klientas_vardas")

        if existing_kl:
            return UzklausaService._resolve_instance_or_pk(Klientas, existing_kl)
        if new_kl_vardas:
            return Klientas.objects.create(
                vardas=new_kl_vardas,
                # jei turi privalomų laukų – pildyk čia saugiomis reikšmėmis
                telefonas=form_data.get("klientas_telefonas", ""),
                el_pastas=form_data.get("klientas_el_pastas", ""),
            )
        raise ValidationError("Klientas privalomas (pasirinkite esamą arba nurodykite naują vardą).")

    @staticmethod
    def _get_or_create_projektas(form_data, klientas):
        """Naudoja esamą projektą arba sukuria naują; validuoja datas, jei abi pateiktos."""
        existing_pr = form_data.get("existing_projektas")
        if existing_pr:
            return UzklausaService._resolve_instance_or_pk(Projektas, existing_pr)

        pavadinimas = form_data.get("projekto_pavadinimas")
        uzklausos_data = form_data.get("uzklausos_data")
        pasiulymo_data = form_data.get("pasiulymo_data")

        # Jei abi datos pateiktos – validuojam
        if uzklausos_data and pasiulymo_data:
            ValidationService.validate_project_dates(uzklausos_data, pasiulymo_data)

        if not pavadinimas:
            # Jei nepaduotas pavadinimas – bandome su default, kad nesulūžtų (arba keliam ValidationError)
            pavadinimas = form_data.get("projekto_pavadinimas_default") or "Projektas"

        return Projektas.objects.create(
            klientas=klientas,
            pavadinimas=pavadinimas,
            uzklausos_data=uzklausos_data,
            pasiulymo_data=pasiulymo_data,
        )

    @staticmethod
    def _get_or_create_detale(form_data, projektas):
        """Naudoja esamą detalę arba kuria naują iš pateiktų laukų; jei trūksta – kelia klaidą aiškiai."""
        existing_det = form_data.get("existing_detale")
        if existing_det:
            return UzklausaService._resolve_instance_or_pk(Detale, existing_det)

        detale_fields = form_data.get("detale_fields") or {}
        # Jeigu tavo Detale turi privalomų laukų (pvz., pavadinimas, kodas ir pan.) – pasiimk iš detale_fields
        # Jei būtini laukai nepaduoti, kilstelėkim aiškią klaidą:
        required = []  # prireikus: ['pavadinimas', 'kodas']
        missing = [f for f in required if not detale_fields.get(f)]
        if missing:
            raise ValidationError(f"Trūksta Detalės laukų: {', '.join(missing)}")

        # BENT jau projektas turi būti nustatytas
        detale = Detale.objects.create(projektas=projektas, **detale_fields)
        return detale

    @staticmethod
    @transaction.atomic
    def update_prices(detale, formset):
        """
        Atnaujina visas detalės kainas:
          - esamas „aktuali“ → „sena“
          - sukuria naujas ir pažymi kaip „aktuali“
        Veikia tiek su ModelForm, tiek su paprastu Form.
        """
        try:
            # Pažymim senas
            detale.kainos.filter(busena="aktuali").update(busena="sena")

            # Pereinam per naujas formas
            for form in formset:
                cd = getattr(form, "cleaned_data", None)
                if not cd or cd.get("DELETE"):
                    continue

                # Jeigu tai ModelForm – paprasčiau
                try:
                    kaina = form.save(commit=False)  # ModelForm atvejis
                except Exception:
                    # Paprastas Form – kuriam iš cleaned_data
                    fields = {}
                    for key in ("suma", "kiekis_nuo", "kiekis_iki", "fiksuotas_kiekis", "kainos_matas"):
                        if key in cd:
                            fields[key] = cd.get(key)
                    kaina = Kaina(**fields)

                kaina.detale = detale
                kaina.busena = "aktuali"
                kaina.save()

            logger.info("Kainos atnaujintos detalei id=%s", getattr(detale, "id", None))

        except ValidationError:
            raise
        except Exception as e:
            logger.exception("Klaida atnaujinant kainas: %s", e)
            raise ValidationError(f"Nepavyko atnaujinti kainų: {e}")

    @staticmethod
    def get_active_price(detale, quantity):
        """
        Grąžina „aktyvią“ kainą pagal kiekį.
        Jei nustatytas `fiksuotas_kiekis` – tikslus atitikmuo.
        Kitu atveju – tikrina intervalą [kiekis_nuo; kiekis_iki].
        """
        active_prices = detale.kainos.filter(busena="aktuali")
        for price in active_prices:
            fk = getattr(price, "fiksuotas_kiekis", None)
            if fk is not None:
                if quantity == fk:
                    return price
            else:
                nuo = getattr(price, "kiekis_nuo", 0) or 0
                iki = getattr(price, "kiekis_iki", None)
                if iki is None:
                    if quantity >= nuo:
                        return price
                else:
                    if nuo <= quantity <= iki:
                        return price
        return None


class ReportService:
    """Service for generating reports and analytics"""

    @staticmethod
    def get_client_statistics():
        """
        Stabiliai, be related_name prielaidų:
        - skaičiuoja užklausas per Uzklausa
        - skaičiuoja projektus per Projektas
        """
        # Užklausų kiekiai per klientą
        uzk_counts = {
            row["klientas_id"]: row["c"]
            for row in Uzklausa.objects.values("klientas_id").annotate(c=Count("id"))
        }
        # Projektų kiekiai per klientą
        proj_counts = {
            row["klientas_id"]: row["c"]
            for row in Projektas.objects.values("klientas_id").annotate(c=Count("id"))
        }
        out = []
        for kl in Klientas.objects.all().only("id", "vardas"):
            out.append({
                "vardas": kl.vardas,
                "uzklausu_kiekis": uzk_counts.get(kl.id, 0),
                "projektu_kiekis": proj_counts.get(kl.id, 0),
            })
        return out

    @staticmethod
    def get_coating_usage_stats():
        """
        Statistika pagal dangas (jei ryšys yra):
        Grupuoja pagal danga__pavadinimas.
        """
        return list(
            Detale.objects.values("danga__pavadinimas")
            .annotate(usage_count=Count("id"))
            .order_by("-usage_count")
        )


class ValidationService:
    """Service for complex validation logic"""

    @staticmethod
    def validate_price_ranges(prices_data):
        """Validuoja, kad kainų intervalai nepersidengtų."""
        sorted_prices = sorted(prices_data, key=lambda x: x.get("kiekis_nuo", 0))
        for i in range(len(sorted_prices) - 1):
            current = sorted_prices[i]
            next_price = sorted_prices[i + 1]
            current_end = current.get("kiekis_iki")
            next_start = next_price.get("kiekis_nuo")
            if current_end and next_start and current_end >= next_start:
                raise ValidationError(
                    f"Kainų diapazonai persidengia: {current_end} >= {next_start}"
                )
        return True

    @staticmethod
    def validate_project_dates(uzklausos_data, pasiulymo_data):
        """Validuoja projektų datas (pasiūlymas negali būti anksčiau už užklausą)."""
        if uzklausos_data and pasiulymo_data and uzklausos_data > pasiulymo_data:
            raise ValidationError("Pasiūlymo data negali būti ankstesnė už užklausos datą")
        return True
