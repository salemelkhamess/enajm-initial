import datetime as dt

from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import translation

from annee.models import Annee
from branches.models import Secteur
from formations.models import Formation
from matiers.models import Matiere
from parametres.models import Parametres
from professeur.models import Professeur
from salle.models import Salle
from trimestre.models import Trimestre
from users.models import User

from . import modifications
from .models import EmploiDuTemps, ModificationEmploi

MERCREDI = dt.date(2026, 11, 25)  # lundi 23/11, dimanche 29/11


def c(jour, debut, fin, matiere=1, professeur=1, salle=1, emploi_id=None):
    return modifications.creneau(jour, debut, fin, matiere, professeur, salle, emploi_id)


def grille(*creneaux):
    return {modifications.position(x): x for x in creneaux}


class ComparerTests(SimpleTestCase):
    def test_rien_ne_change(self):
        etat = grille(c('Lundi', '08:00', '10:00'))
        self.assertEqual(modifications.comparer(etat, grille(c('Lundi', '08:00', '10:00'))), [])

    def test_changement_de_professeur_a_la_meme_position(self):
        avant, apres = c('Lundi', '08:00', '10:00', professeur=1), c('Lundi', '08:00', '10:00', professeur=2)
        self.assertEqual(modifications.comparer(grille(avant), grille(apres)), [(avant, apres)])

    def test_deplacement_de_la_meme_matiere_est_un_seul_changement(self):
        avant, apres = c('Lundi', '08:00', '10:00', matiere=5), c('Mardi', '10:00', '12:00', matiere=5)
        self.assertEqual(modifications.comparer(grille(avant), grille(apres)), [(avant, apres)])

    def test_le_deplacement_prefere_le_meme_professeur(self):
        a1, a2 = c('Lundi', '08:00', '10:00', matiere=5, professeur=1), c('Mardi', '08:00', '10:00', matiere=5, professeur=2)
        n1 = c('Jeudi', '08:00', '10:00', matiere=5, professeur=2)
        changements = modifications.comparer(grille(a1, a2), grille(a1, n1))
        self.assertEqual(changements, [(a2, n1)])

    def test_ajout_et_retrait_de_matieres_differentes(self):
        retire, ajoute = c('Lundi', '08:00', '10:00', matiere=1), c('Mardi', '08:00', '10:00', matiere=2)
        changements = modifications.comparer(grille(retire), grille(ajoute))
        self.assertCountEqual(changements, [(retire, None), (None, ajoute)])

    def test_heures_saisies_en_texte_ou_en_time_sont_equivalentes(self):
        self.assertEqual(modifications.position(c('Lundi', '08:00', '10:00')),
                         modifications.position(c('Lundi', dt.time(8), dt.time(10, 0, 0))))
        self.assertEqual(modifications.heure('08:00:00'), dt.time(8))


class BaseEmploi(TestCase):
    def setUp(self):
        formation = Formation.objects.create(nom='Formation')
        self.annee = Annee.objects.create(formation=formation, numero_annee=2026)
        self.trimestre = Trimestre.objects.create(annee=self.annee, numero_trimestre=1,
                                                  debut=dt.date(2026, 9, 1), fin=dt.date(2027, 1, 31))
        self.secteur = Secteur.objects.create(nom='Classe A', formation=formation)
        self.autre_secteur = Secteur.objects.create(nom='Classe B', formation=formation)
        self.maths = Matiere.objects.create(nom='Maths', coefficient=1, secteur=self.secteur)
        self.droit = Matiere.objects.create(nom='Droit', coefficient=1, secteur=self.secteur)
        self.prof1 = Professeur.objects.create(nom='Ali', prenom='Ahmed', email='a@x.mr', telephone='1', specialite='M')
        self.prof2 = Professeur.objects.create(nom='Sidi', prenom='Omar', email='b@x.mr', telephone='2', specialite='D')
        self.salle1 = Salle.objects.create(nom='S1', capacite=30)
        self.salle2 = Salle.objects.create(nom='S2', capacite=30)
        Parametres.objects.create(pk=1, annee_courante=self.annee, trimestre_courant=self.trimestre)
        self.classe = dict(annee_id=self.annee.pk, trimestre_id=self.trimestre.pk, secteur_id=self.secteur.pk)

    def emploi(self, jour='Lundi', debut='08:00', fin='10:00', matiere=None, prof=None, salle=None, secteur=None):
        return EmploiDuTemps.objects.create(
            annee=self.annee, trimestre=self.trimestre, secteur=secteur or self.secteur, jour=jour,
            heure_debut=debut, heure_fin=fin, matiere=matiere or self.maths, professeur=prof or self.prof1,
            salle=salle or self.salle1)

    def creneau(self, jour='Lundi', debut='08:00', fin='10:00', matiere=None, prof=None, salle=None):
        return c(jour, debut, fin, (matiere or self.maths).pk, (prof or self.prof1).pk, (salle or self.salle1).pk)


class EnregistrerGrilleTests(BaseEmploi):
    def enregistrer(self, nouveaux, portee=None):
        return modifications.enregistrer_grille(nouveaux, portee=portee, par='agent', aujourdhui=MERCREDI,
                                                **self.classe)

    def test_premiere_saisie_sans_confirmation_ni_journal(self):
        statut, changements = self.enregistrer(grille(self.creneau(), self.creneau('Mardi')))
        self.assertEqual((statut, changements), ('initial', []))
        self.assertEqual(EmploiDuTemps.objects.count(), 2)
        self.assertEqual(ModificationEmploi.objects.count(), 0)

    def test_sans_changement_rien_n_est_demande(self):
        self.emploi()
        statut, _ = self.enregistrer(grille(self.creneau()))
        self.assertEqual(statut, 'inchange')
        self.assertEqual(ModificationEmploi.objects.count(), 0)

    def test_un_changement_sans_portee_demande_confirmation_et_ne_change_rien(self):
        self.emploi()
        statut, changements = self.enregistrer(grille(self.creneau(prof=self.prof2)))
        self.assertEqual(statut, 'confirmer')
        self.assertEqual(len(changements), 1)
        self.assertEqual(EmploiDuTemps.objects.get().professeur, self.prof1)
        self.assertEqual(ModificationEmploi.objects.count(), 0)

    def test_semaines_suivantes_modifie_le_modele_sur_place_et_journalise(self):
        ligne = self.emploi()
        statut, _ = self.enregistrer(grille(self.creneau(prof=self.prof2, salle=self.salle2)), 'suivantes')
        self.assertEqual(statut, 'applique')
        ligne.refresh_from_db()  # même identifiant : la ligne est mise à jour, pas recréée
        self.assertEqual((ligne.professeur, ligne.salle), (self.prof2, self.salle2))
        m = ModificationEmploi.objects.get()
        self.assertEqual((m.portee, m.date_effet, m.date_fin, m.cree_par), ('suivantes', MERCREDI, None, 'agent'))
        self.assertEqual((m.avant_professeur_id, m.apres_professeur_id), (self.prof1.pk, self.prof2.pk))
        self.assertEqual((m.avant_professeur_nom, m.apres_professeur_nom), ('Ali Ahmed', 'Sidi Omar'))
        self.assertEqual((m.avant_salle_nom, m.apres_salle_nom), ('S1', 'S2'))
        self.assertEqual((m.apres_jour, m.apres_heure_debut, m.apres_heure_fin), ('Lundi', dt.time(8), dt.time(10)))
        self.assertFalse(m.est_ajout or m.est_retrait)

    def test_cette_semaine_seulement_laisse_le_modele_et_journalise_jusqu_au_dimanche(self):
        self.emploi()
        statut, _ = self.enregistrer(grille(self.creneau(prof=self.prof2)), 'semaine')
        self.assertEqual(statut, 'applique')
        self.assertEqual(EmploiDuTemps.objects.get().professeur, self.prof1)  # modèle hebdomadaire inchangé
        m = ModificationEmploi.objects.get()
        self.assertEqual((m.portee, m.date_effet, m.date_fin), ('semaine', MERCREDI, dt.date(2026, 11, 29)))

    def test_deplacement_est_un_changement_et_garde_une_seule_ligne(self):
        self.emploi('Lundi', '08:00', '10:00')
        self.enregistrer(grille(self.creneau('Mardi', '10:00', '12:00')), 'suivantes')
        ligne = EmploiDuTemps.objects.get()
        self.assertEqual((ligne.jour, ligne.heure_debut), ('Mardi', dt.time(10)))
        m = ModificationEmploi.objects.get()
        self.assertEqual((m.avant_jour, m.apres_jour, m.apres_heure_debut), ('Lundi', 'Mardi', dt.time(10)))

    def test_retrait_et_ajout_de_matieres_differentes(self):
        self.emploi('Lundi', matiere=self.maths)
        self.enregistrer(grille(self.creneau('Jeudi', matiere=self.droit)), 'suivantes')
        self.assertEqual(list(EmploiDuTemps.objects.values_list('jour', 'matiere__nom')), [('Jeudi', 'Droit')])
        self.assertEqual(sorted((m.est_ajout, m.est_retrait) for m in ModificationEmploi.objects.all()),
                         [(False, True), (True, False)])

    def test_les_autres_classes_ne_sont_pas_touchees(self):
        autre = self.emploi(secteur=self.autre_secteur)
        self.emploi()
        self.enregistrer(grille(self.creneau(prof=self.prof2)), 'suivantes')
        autre.refresh_from_db()
        self.assertEqual(autre.professeur, self.prof1)

    def test_une_ligne_refusee_annule_tout_et_porte_le_creneau_fautif(self):
        self.emploi()
        mauvais = self.creneau('Mardi', '10:00', '09:00')  # fin avant le début
        with self.assertRaises(ValidationError) as ctx:
            self.enregistrer(grille(self.creneau(prof=self.prof2), mauvais), 'suivantes')
        self.assertEqual(ctx.exception.slot['jour'], 'Mardi')
        self.assertEqual(EmploiDuTemps.objects.get().professeur, self.prof1)  # rien n'a été modifié
        self.assertEqual(ModificationEmploi.objects.count(), 0)

    def test_grille_depuis_post(self):
        post = QueryDict(mutable=True)
        post.setlist('creneau_debut[]', ['08:00', '10:00'])
        post.setlist('creneau_fin[]', ['10:00', '12:00'])
        post['matiere_Lundi_08:00_10:00'] = str(self.maths.pk)
        post['professeur_Lundi_08:00_10:00'] = str(self.prof1.pk)
        post['salle_Lundi_08:00_10:00'] = str(self.salle1.pk)
        post['matiere_Mardi_10:00_12:00'] = str(self.droit.pk)  # sans professeur ni salle : case vide
        etat = modifications.grille_depuis_post(post)
        self.assertEqual(list(etat), [('Lundi', dt.time(8), dt.time(10))])


class VuesTests(BaseEmploi):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.create_superuser('admin@x.mr', 'x'))

    def donnees(self, emploi, **changes):
        valeurs = {
            'annee': emploi.annee_id, 'trimestre': emploi.trimestre_id, 'niveau': '', 'langue': '',
            'secteur': emploi.secteur_id, 'matiere': emploi.matiere_id, 'professeur': emploi.professeur_id,
            'salle': emploi.salle_id, 'jour': emploi.jour, 'heure_debut': f"{emploi.heure_debut:%H:%M}",
            'heure_fin': f"{emploi.heure_fin:%H:%M}",
        }
        valeurs.update(changes)
        return valeurs

    def test_modifier_un_creneau_demande_la_portee(self):
        ligne = self.emploi()
        reponse = self.client.post(reverse('emploi_update', args=[ligne.pk]),
                                   self.donnees(ligne, professeur=self.prof2.pk))
        self.assertEqual(reponse.status_code, 200)
        self.assertTemplateUsed(reponse, 'emploi/confirmer_portee.html')
        self.assertContains(reponse, 'name="portee"')
        self.assertContains(reponse, 'name="professeur" value="%d"' % self.prof2.pk)  # le formulaire est rejoué
        ligne.refresh_from_db()
        self.assertEqual(ligne.professeur, self.prof1)
        self.assertEqual(ModificationEmploi.objects.count(), 0)

    def test_modifier_cette_semaine_seulement(self):
        ligne = self.emploi()
        reponse = self.client.post(reverse('emploi_update', args=[ligne.pk]),
                                   {**self.donnees(ligne, professeur=self.prof2.pk), 'portee': 'semaine'})
        self.assertEqual(reponse.status_code, 302)
        ligne.refresh_from_db()
        self.assertEqual(ligne.professeur, self.prof1)  # le modèle hebdomadaire ne change pas
        self.assertEqual(ModificationEmploi.objects.get().portee, 'semaine')

    def test_modifier_les_semaines_suivantes(self):
        ligne = self.emploi()
        reponse = self.client.post(reverse('emploi_update', args=[ligne.pk]),
                                   {**self.donnees(ligne, professeur=self.prof2.pk), 'portee': 'suivantes'})
        self.assertEqual(reponse.status_code, 302)
        ligne.refresh_from_db()
        self.assertEqual(ligne.professeur, self.prof2)
        m = ModificationEmploi.objects.get()
        self.assertEqual((m.portee, m.avant_professeur_id, m.apres_professeur_id),
                         ('suivantes', self.prof1.pk, self.prof2.pk))

    def test_enregistrer_sans_rien_changer_ne_demande_rien(self):
        ligne = self.emploi()
        reponse = self.client.post(reverse('emploi_update', args=[ligne.pk]), self.donnees(ligne))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(ModificationEmploi.objects.count(), 0)

    def valeurs(self, **changes):
        """Champs du formulaire d'un créneau (lundi 8h-10h, maths, professeur 1, salle 1)."""
        valeurs = {'annee': self.annee.pk, 'trimestre': self.trimestre.pk, 'niveau': '', 'langue': '',
                   'secteur': self.secteur.pk, 'matiere': self.maths.pk, 'professeur': self.prof1.pk,
                   'salle': self.salle1.pk, 'jour': 'Lundi', 'heure_debut': '08:00', 'heure_fin': '10:00'}
        valeurs.update(changes)
        return valeurs

    def test_ajouter_un_creneau_a_une_classe_qui_a_deja_un_emploi_demande_la_portee(self):
        self.emploi()
        reponse = self.client.post(reverse('emploi_create'), self.valeurs(jour='Jeudi'))
        self.assertTemplateUsed(reponse, 'emploi/confirmer_portee.html')
        self.assertEqual(EmploiDuTemps.objects.count(), 1)

    def test_ajouter_cette_semaine_seulement_ne_cree_pas_de_ligne(self):
        self.emploi()
        self.client.post(reverse('emploi_create'), {**self.valeurs(jour='Jeudi'), 'portee': 'semaine'})
        self.assertEqual(EmploiDuTemps.objects.count(), 1)
        m = ModificationEmploi.objects.get()
        self.assertEqual((m.portee, m.est_ajout, m.apres_jour), ('semaine', True, 'Jeudi'))

    def test_ajouter_le_premier_creneau_d_une_classe_ne_demande_rien(self):
        reponse = self.client.post(reverse('emploi_create'), self.valeurs())
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(EmploiDuTemps.objects.count(), 1)
        self.assertEqual(ModificationEmploi.objects.count(), 0)

    def test_supprimer_cette_semaine_seulement_garde_la_ligne(self):
        ligne = self.emploi()
        self.client.post(reverse('emploi_delete', args=[ligne.pk]), {'portee': 'semaine'})
        self.assertTrue(EmploiDuTemps.objects.filter(pk=ligne.pk).exists())
        m = ModificationEmploi.objects.get()
        self.assertEqual((m.portee, m.est_retrait, m.avant_jour), ('semaine', True, 'Lundi'))

    def test_supprimer_les_semaines_suivantes_retire_la_ligne(self):
        ligne = self.emploi()
        self.client.post(reverse('emploi_delete', args=[ligne.pk]), {'portee': 'suivantes'})
        self.assertFalse(EmploiDuTemps.objects.filter(pk=ligne.pk).exists())
        self.assertEqual(ModificationEmploi.objects.get().portee, 'suivantes')

    def grille_post(self, **extra):
        donnees = {'secteur_id': self.secteur.pk, 'creneau_debut[]': ['08:00'], 'creneau_fin[]': ['10:00'],
                   'matiere_Lundi_08:00_10:00': self.maths.pk, 'professeur_Lundi_08:00_10:00': self.prof2.pk,
                   'salle_Lundi_08:00_10:00': self.salle1.pk}
        donnees.update(extra)
        return self.client.post(reverse('sauvegarder_grille'), donnees)

    def test_grille_premiere_saisie(self):
        reponse = self.grille_post()
        self.assertEqual(reponse.json()['success'], True)
        self.assertEqual(EmploiDuTemps.objects.count(), 1)
        self.assertEqual(ModificationEmploi.objects.count(), 0)

    def test_grille_demande_la_portee_puis_applique(self):
        ligne = self.emploi()
        reponse = self.grille_post().json()
        self.assertEqual((reponse['success'], reponse['confirmation']), (False, True))
        self.assertIn('Sidi Omar', reponse['changements'][0]['texte'])
        ligne.refresh_from_db()
        self.assertEqual(ligne.professeur, self.prof1)
        with translation.override('fr'):  # le message est traduit : on le lit en français
            reponse = self.grille_post(portee='semaine').json()
        self.assertEqual(reponse['success'], True)
        self.assertIn('semaine actuelle seulement', reponse['message'])
        ligne.refresh_from_db()
        self.assertEqual(ligne.professeur, self.prof1)
        self.assertEqual(ModificationEmploi.objects.get().portee, 'semaine')

    def test_grille_garde_l_identifiant_des_creneaux(self):
        ligne = self.emploi()
        self.grille_post(portee='suivantes')
        self.assertEqual(EmploiDuTemps.objects.get().pk, ligne.pk)
        ligne.refresh_from_db()
        self.assertEqual(ligne.professeur, self.prof2)
