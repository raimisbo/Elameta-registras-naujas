from __future__ import annotations

"""
Service layer for business logic
Separates complex operations from views and models
"""

from typing import Any, Dict, Iterable, Optional

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, FieldDoesNotExist, ObjectDoesNotExist
from django.db.models import Count, Q

from .models import Klientas, Projektas, Detale, Uzklausa, Kaina
import logging

logger = logging.getLogger(__name__)


def _normalize_path(value: Any) -> Optional[str]:
    r"""
    Konvertuoja tinklo kelią (\\server\dir\file) į HTTP-like kelią (server/dir/file).
    Jei jau http(s) – palieka. Jei None/tuščia – grąžina None.
    """
    if not value:
        return None
    s = str(value)
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return s.strip("\\").replace("\\", "/")


def _extract(data: Optional[Dict[str, Any]], keys: Iterable[str]) -> Dict[str, Any]:
    """Grąžina naują dict tik su nurodytais raktais (jei yra)."""
    if not data:
        return {}
    return {k: data.get(k) for k in keys if k in data}


class UzklausaService:
    """Service for handling complex Uzklausa operations"""

    @staticmethod
    @transaction.atomic
    def create_full_request(
        form_data: Dict[str, Any],
        projektas_data: Optional[Dict[str, Any]] = None,
        detale_data: Optional[Dict[str, Any]] = None,
    ) -> Uzklausa:
        """
        Sukuria pilną užklausą (Klientas/Projektas/Detale/Uzklausa).
        Atgalinis suderinamumas su senu parašu (ignoruoja papildomus argumentus, jei jų nėra).

        Tikėtini raktai form_data (senas kelias):
          - existing_klientas | new_klientas_vardas
          - existing_projektas | projekto_pavadinimas, uzklausos_data, pasiulymo_data
          - existing_detale | detale_fields (dict)
        Naujieji (pasirinktinai):
          - projektas_data (dict) – papildomi Projektas laukai
          - detale_data (dict) – papildomi Detale laukai
        """
        try:
            klientas = UzklausaService._get_or_create_klientas(form_data)
            projektas = UzklausaService._get_or_create_projektas(form_data, klientas, projektas_data)
            detale = UzklausaService._get_or_create_detale(form_data, projektas, detale_data)

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
    def _resolve_instance_or_pk(model_cls, value, field_name: str = "id"):
        """Leidžia paduoti arba instancą, arba PK – grąžina instancą."""
        if value is None:
            return None
        if isinstance(value, model_cls):
            return value
        return model_cls.objects.get(**{field_name: value})

    @staticmethod
    def _get_or_create_klientas(form_data: Dict[str, Any]) -> Klientas:
        """Naudoja esamą klientą (obj/pk) arba sukuria naują iš vardo."""
        existing_kl = form_data.get("existing_klientas")
        new_kl_vardas = form_data.get("new_klientas_vardas")

        if existing_kl:
            return UzklausaService._resolve_instance_or_pk(Klientas, existing_kl)
        if new_kl_vardas:
            return Klientas.objects.create(
                vardas=new_kl_vardas,
                telefonas=form_data.get("klientas_telefonas", ""),
                el_pastas=form_data.get("klientas_el_pastas", ""),
            )
        raise ValidationError("Klientas privalomas (pasirinkite esamą arba nurodykite naują vardą).")

    @staticmethod
    def _get_or_create_projektas(
        form_data: Dict[str, Any],
        klientas: Klientas,
        projektas_data: Optional[Dict[str, Any]] = None,
    ) -> Projektas:
        """
        Naudoja esamą projektą arba sukuria naują.
        Papildomi laukai (pasirinktinai): projekto_pradzia, projekto_pabaiga, kaina_galioja_iki,
        apmokejimo_salygos, transportavimo_salygos.
        """
        existing_pr = form_data.get("existing_projektas")
        if existing_pr:
            return UzklausaService._resolve_instance_or_pk(Projektas, existing_pr)

        pavadinimas = (
            form_data.get("projekto_pavadinimas")
            or form_data.get("projekto_pavadinimas_default")
            or "Projektas"
        )
        uzklausos_data = form_data.get("uzklausos_data")
        pasiulymo_data = form_data.get("pasiulymo_data")

        if uzklausos_data and pasiulymo_data:
            ValidationService.validate_project_dates(uzklausos_data, pasiulymo_data)

        extra = _extract(
            projektas_data,
            ["projekto_pradzia", "projekto_pabaiga", "kaina_galioja_iki", "apmokejimo_salygos", "transportavimo_salygos"],
        )

        return Projektas.objects.create(
            klientas=klientas,
            pavadinimas=pavadinimas,
            uzklausos_data=uzklausos_data,
            pasiulymo_data=pasiulymo_data,
            **extra,
        )

    @staticmethod
    def _get_or_create_detale(
        form_data: Dict[str, Any],
        projektas: Projektas,
        detale_data: Optional[Dict[str, Any]] = None,
    ) -> Detale:
        """
        Naudoja esamą detalę arba sukuria naują.
        Sujungia seną `detale_fields` + naują `detale_data`. Sutvarko M2M `danga` ir nuorodų normalizavimą.
        """
        existing_det = form_data.get("existing_detale")
        if existing_det:
            return UzklausaService._resolve_instance_or_pk(Detale, existing_det)

        payload: Dict[str, Any] = {}
        payload.update(form_data.get("detale_fields") or {})
        payload.update(detale_data or {})

        # Normalizuojam nuorodas
        if "nuoroda_brezinio" in payload:
            payload["nuoroda_brezinio"] = _normalize_path(payload.get("nuoroda_brezinio"))
        if "nuoroda_pasiulymo" in payload:
            payload["nuoroda_pasiulymo"] = _normalize_path(payload.get("nuoroda_pasiulymo"))

        # ManyToMany 'danga' atskirai (jei egzistuoja toks laukas)
        danga_values = payload.pop("danga", None)

        # Sukuriam Detale (bent projektas privalomas)
        detale = Detale.objects.create(projektas=projektas, **payload)

        # Pririšam dangas (jei laukas yra ir pateikta reikšmių)
        if danga_values:
            try:
                field = detale._meta.get_field("danga")  # ManyToManyField?
            except FieldDoesNotExist:
                logger.warning("Detale neturi M2M lauko 'danga' – praleidžiama.")
            else:
                related_model = getattr(field.remote_field, "model", None)
                if related_model is None:
                    logger.warning("Nepavyko nustatyti 'danga' susijusio modelio – praleidžiama.")
                else:
                    ids = []
                    for v in danga_values:
                        # bandome kaip ID
                        try:
                            iv = int(v)
                            if related_model.objects.filter(pk=iv).exists():
                                ids.append(iv)
                                continue
                        except (TypeError, ValueError):
                            pass
                        # bandome pagal pavadinimą (dažnas tavo atvejis)
                        for name_field in ("pavadinimas", "name", "title"):
                            try:
                                obj = related_model.objects.filter(**{name_field: v}).first()
                                if obj:
                                    ids.append(obj.pk)
                                    break
                            except Exception:
                                continue
                        else:
                            logger.warning("Danga '%s' nerasta – praleidžiama", v)
                    if ids:
                        getattr(detale, "danga").set(ids)

        return detale

    @staticmethod
    @transaction.atomic
    def update_prices(detale: Detale, formset) -> None:
        """
        Atnaujina visas detalės kainas:
          - jeigu yra `yra_aktuali`: esamą → False
          - priešingu atveju, jei yra `busena`: „aktuali“ → „sena“
          - sukuria naujas ir pažymi kaip „aktuali“ / `yra_aktuali=True`
        """
        try:
            # Nustatom „seno“ statusą esamoms
            fields = {f.name for f in Kaina._meta.get_fields()}
            if "yra_aktuali" in fields:
                detale.kainos.filter(yra_aktuali=True).update(yra_aktuali=False, galioja_iki=timezone.localdate())
            elif "busena" in fields:
                detale.kainos.filter(busena="aktuali").update(busena="sena")

            # Įrašom naujas kainas
            for form in formset:
                cd = getattr(form, "cleaned_data", None)
                if not cd or cd.get("DELETE"):
                    continue

                # Jei ModelForm – commit=False
                try:
                    kaina = form.save(commit=False)
                except Exception:
                    # fallback – rankinis konstravimas
                    fields_to_copy = ("suma", "kiekis_nuo", "kiekis_iki", "fiksuotas_kiekis", "kainos_matas", "tipas")
                    data = {k: cd.get(k) for k in fields_to_copy if k in cd}
                    kaina = Kaina(**data)

                kaina.detale = detale

                if "yra_aktuali" in fields:
                    kaina.yra_aktuali = True
                    if hasattr(kaina, "galioja_nuo") and not getattr(kaina, "galioja_nuo", None):
                        kaina.galioja_nuo = timezone.localdate()
                elif "busena" in fields:
                    kaina.busena = "aktuali"

                if hasattr(kaina, "tipas") and not getattr(kaina, "tipas", None):
                    try:
                        kaina.tipas = "VIENETO"
                    except Exception:
                        pass

                kaina.save()

            logger.info("Kainos atnaujintos detalei id=%s", getattr(detale, "id", None))

        except ValidationError:
            raise
        except Exception as e:
            logger.exception("Klaida atnaujinant kainas: %s", e)
            raise ValidationError(f"Nepavyko atnaujinti kainų: {e}")

    @staticmethod
    def get_active_price(detale: Detale, quantity: int) -> Optional[Kaina]:
        """
        Grąžina „aktyvią“ kainą pagal kiekį.
        Jei nustatytas `fiksuotas_kiekis` – tikslus atitikmuo.
        Kitu atveju – tikrina intervalą [kiekis_nuo; kiekis_iki].
        """
        fields = {f.name for f in Kaina._meta.get_fields()}
        if "yra_aktuali" in fields:
            active_prices = detale.kainos.filter(yra_aktuali=True)
        else:
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
        """Skaičiuoja užklausas per Uzklausa ir projektus per Projektas."""
        uzk_counts = {
            row["klientas_id"]: row["c"]
            for row in Uzklausa.objects.values("klientas_id").annotate(c=Count("id"))
        }
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
        """Statistika pagal dangas (jei ryšys yra)."""
        try:
            Detale._meta.get_field("danga")
        except FieldDoesNotExist:
            return []
        # dažniausiai danga turi 'pavadinimas'
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
        """Pasiūlymo data negali būti ankstesnė už užklausos datą."""
        if uzklausos_data and pasiulymo_data and uzklausos_data > pasiulymo_data:
            raise ValidationError("Pasiūlymo data negali būti ankstesnė už užklausos datą")
        return True


class KainosService:
    @staticmethod
    @transaction.atomic
    def nustatyti_nauja_kaina(
        *,
        uzklausa_id: int,
        suma,
        valiuta: str = 'EUR',
        detale_id: Optional[int] = None,
        priezastis: str = '',
        user=None,
    ) -> Kaina:
        """
        Nustato naują kainą: uždaro seną „aktualią“ ir sukuria naują.
        Palaiko modelio versiją su `yra_aktuali` (rekomenduojama).
        """
        # rasti esamą aktualią
        qs = Kaina.objects.filter(uzklausa_id=uzklausa_id)
        if detale_id:
            qs = qs.filter(detale_id=detale_id)

        fields = {f.name for f in Kaina._meta.get_fields()}
        if "yra_aktuali" in fields:
            qs = qs.filter(yra_aktuali=True)
        else:
            qs = qs.filter(busena="aktuali")

        sena = qs.select_for_update().first()
        today = timezone.localdate()

        # jei kaina nesikeičia – grąžinam esamą
        if sena and str(getattr(sena, "suma", None)) == str(suma) and getattr(sena, "valiuta", None) == valiuta:
            return sena

        # uždaryti seną
        if sena:
            if "yra_aktuali" in fields:
                sena.yra_aktuali = False
                if hasattr(sena, "galioja_iki"):
                    sena.galioja_iki = today
                sena.save(update_fields=[f for f in ("yra_aktuali", "galioja_iki") if hasattr(sena, f)])
            else:
                sena.busena = "sena"
                sena.save(update_fields=["busena"])

        # sukurti naują
        create_kwargs = dict(
            uzklausa_id=uzklausa_id,
            detale_id=detale_id,
            suma=suma,
            valiuta=valiuta,
        )
        if "yra_aktuali" in fields:
            create_kwargs.update(
                yra_aktuali=True,
                galioja_nuo=today if "galioja_nuo" in fields else None,
                keitimo_priezastis=priezastis or '' if "keitimo_priezastis" in fields else None,
            )
        else:
            create_kwargs.update(busena="aktuali")

        # remove None-valued keys (if field not present)
        create_kwargs = {k: v for k, v in create_kwargs.items() if v is not None}

        if "pakeite" in fields and user is not None and getattr(user, "is_authenticated", False):
            create_kwargs["pakeite"] = user

        nauja = Kaina.objects.create(**create_kwargs)
        return nauja
