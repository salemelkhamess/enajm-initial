from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Etudiant


class EtudiantForm(forms.ModelForm):
    # Champ pour les diplômes (multiple choice)
    diplomes = forms.MultipleChoiceField(
        choices=Etudiant.DIPLOME_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Diplômes")
    )

    class Meta:
        model = Etudiant
        fields = [
            'nni', 'matricule', 'nom', 'prenom', 'nom_fr', 'prenom_fr', 'date_naissance',
            'lieu_naissance', 'lieu_naissance_fr', 'sexe', 'telephone', 'email', 'photo',
            'secteur', 'annee', 'niveau', 'situation_amoureuse', 'diplomes', 'nombre_enfants'
        ]

        widgets = {
            'date_naissance': forms.NumberInput(attrs={
                'min': 1900,
                'max': 2100,
                'placeholder': 'Date de naissance'
            }),            'sexe': forms.Select(choices=Etudiant.SEXE_CHOICES),
            'situation_amoureuse': forms.Select(choices=Etudiant.SITUATION_AMOUREUSE_CHOICES),
            'photo': forms.ClearableFileInput(),
            'secteur': forms.Select(attrs={'class': 'form-control select'}),
            'annee': forms.Select(attrs={'class': 'form-control select'}),
            'nombre_enfants': forms.NumberInput(attrs={'min': 0}),
        }

        error_messages = {
            'matricule': {'unique': _("Ce matricule est déjà attribué à un autre élève."),
                          'required': _("Le matricule est obligatoire.")},
            'nni': {'unique': _("Ce NNI est déjà attribué à un autre élève.")},
            'nom': {'required': _("Le nom en arabe est obligatoire.")},
            'secteur': {'required': _("Choisissez la classe de l'élève.")},
            'annee': {'required': _("Choisissez l'année.")},
            'date_naissance': {'invalid': _("Saisissez une année de naissance valide (ex. 1990).")},
            'email': {'invalid': _("Saisissez une adresse email valide.")},
        }

        labels = {
            'secteur': _('Département'),
            'niveau': _('Niveau'),
            'nni': _('NNI'),
            'nom': _('Nom (arabe)'),
            'prenom': _('Prénom (arabe)'),
            'nom_fr': _('Nom (français)'),
            'prenom_fr': _('Prénom (français)'),
            'lieu_naissance_fr': _('Lieu de naissance (français)'),
            'date_naissance': _('Date de naissance'),
            'lieu_naissance': _('Lieu de naissance (arabe)'),
            'sexe': _('Sexe'),
            'telephone': _('Téléphone'),
            'email': _('Email'),
            'photo': _('Photo'),
            'situation_amoureuse': _('Situation amoureuse'),
            'nombre_enfants': _("Nombre d'enfants"),
        }

    def _deja_utilise(self, champ, valeur):
        """Élève (de n'importe quelle année) qui utilise déjà cette valeur, en dehors de l'élève modifié."""
        qs = Etudiant._base_manager.filter(**{f'{champ}__iexact': valeur}).select_related('annee')
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        return qs.first()

    def clean_matricule(self):
        matricule = (self.cleaned_data.get('matricule') or '').strip()
        autre = self._deja_utilise('matricule', matricule)
        if autre:
            raise forms.ValidationError(
                _("Ce matricule (%(matricule)s) est déjà attribué à un autre élève : %(nom)s (année %(annee)s)."),
                code='matricule_unique',
                params={'matricule': matricule, 'nom': f"{autre.nom} {autre.prenom or ''}".strip(), 'annee': autre.annee})
        return matricule

    def clean_nni(self):
        nni = (self.cleaned_data.get('nni') or '').strip()
        if not nni:
            return None
        autre = self._deja_utilise('nni', nni)
        if autre:
            raise forms.ValidationError(
                _("Ce NNI (%(nni)s) est déjà attribué à un autre élève : %(nom)s (matricule %(matricule)s)."),
                code='nni_unique',
                params={'nni': nni, 'nom': f"{autre.nom} {autre.prenom or ''}".strip(), 'matricule': autre.matricule})
        return nni

    def __init__(self, *args, **kwargs):
        super(EtudiantForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            # Ne pas rendre tous les champs obligatoires
            self.fields['prenom'].required = False
            self.fields['prenom_fr'].required = False
            self.fields['nom_fr'].required = False

            if field.required:
                field.widget.attrs['required'] = 'required'

        # Nouvelle inscription : l'année proposée par défaut est l'année affichée en haut (année active)
        if not self.instance.pk and not self.is_bound:
            from parametres.utils import get_annee_courante
            annee_courante = get_annee_courante()
            if annee_courante:
                self.initial.setdefault('annee', annee_courante.pk)

        # Exceptions pour les widgets spéciaux
        self.fields['secteur'].widget.attrs['class'] += ' select'
        self.fields['annee'].widget.attrs['class'] += ' select'
        self.fields['situation_amoureuse'].widget.attrs['class'] += ' select'
        # Niveau : facultatif, uniquement les niveaux actifs (+ le niveau actuel de l'élève s'il est devenu inactif)
        from django.db.models import Q
        from niveaux.models import Niveau
        niveaux = Niveau.objects.filter(Q(actif=True) | Q(pk=self.instance.niveau_id)) if self.instance.pk and self.instance.niveau_id else Niveau.actifs()
        self.fields['niveau'].queryset = niveaux
        self.fields['niveau'].required = False
        self.fields['niveau'].label_from_instance = lambda n: n.libelle
        self.fields['niveau'].widget.attrs.pop('required', None)
        self.fields['niveau'].widget.attrs['class'] += ' select'
        self.fields['diplomes'].widget.attrs['class'] = ''
        # les diplômes sont stockés sous forme de texte : on les relit en liste pour recocher les cases à l'édition
        if self.instance.pk and not self.is_bound:
            self.initial['diplomes'] = Etudiant.diplomes_liste(self.instance.diplomes)