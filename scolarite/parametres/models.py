from django.db import models

# parametres/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from annee.models import Annee
from trimestre.models import Trimestre


class Parametres(models.Model):
    class Meta:
        verbose_name = _("Paramètres généraux")
        verbose_name_plural = _("Paramètres généraux")

    annee_courante = models.ForeignKey(
        Annee,
        on_delete=models.PROTECT,
        verbose_name=_("Année courante"),
        related_name='parametres_annee'
    )

    trimestre_courant = models.ForeignKey(
        Trimestre,
        on_delete=models.PROTECT,
        verbose_name=_("Trimestre courant"),
        related_name='parametres_trimestre'
    )

    alertes_absences_actives = models.BooleanField(
        default=True,
        verbose_name=_("Alertes d'absences activées")
    )

    date_mise_a_jour = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Date de mise à jour")
    )

    def __str__(self):
        return f"Paramètres ({self.date_mise_a_jour.date()})"

    @classmethod
    def get_real_instance(cls):
        """Paramètres tels qu'enregistrés (année active réelle). À utiliser pour modifier/sauvegarder."""
        from .middleware import cached_real_instance
        def charger():
            obj = cls.objects.select_related('annee_courante', 'trimestre_courant').get_or_create(pk=1)[0]
            return obj
        return cached_real_instance(charger)

    @classmethod
    def get_instance(cls):
        """
        Retourne l'instance unique des paramètres.
        Si l'utilisateur a choisi une autre année à consulter, l'année (et son
        premier trimestre) remplacent, en mémoire seulement, l'année active.
        Ne pas sauvegarder cette instance : utiliser get_real_instance().
        """
        from .middleware import get_annee_consultee_id
        obj = cls.get_real_instance()
        annee_id = get_annee_consultee_id()
        if annee_id and annee_id != obj.annee_courante_id:
            import copy
            real = obj
            obj = copy.copy(real)  # ne pas altérer l'instance mise en cache (cache des FK compris)
            obj._state = copy.copy(real._state)
            obj._state.fields_cache = dict(real._state.fields_cache)
            from .middleware import cached_periode
            annee, trimestre = cached_periode(annee_id, lambda: (
                Annee.objects.filter(pk=annee_id).first(),
                Trimestre.objects.filter(annee_id=annee_id).order_by('numero_trimestre').first()))
            if annee:
                obj.annee_courante = annee
                if trimestre:
                    obj.trimestre_courant = trimestre
        return obj
