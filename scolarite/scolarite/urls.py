"""
URL configuration for scolarite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('login_page.urls')),
    path('home/', include('home.urls')),
    re_path(r'^formations/', include('formations.urls')),
    path('annees/', include('annee.urls')),
    re_path(r'^etudiants/', include('etudiant.urls')),
    re_path(r'^matiers/', include('matiers.urls')),
    re_path(r'^presence/etudiant/', include('presenceetudiant.urls')),
    re_path(r'^pvs/', include('pv.urls')),
    re_path(r'^proffesseur/', include('professeur.urls')),
    re_path(r'^proffesseur/absence/', include('presenceprof.urls')),
    re_path(r'^entete/', include('entete.urls')),
    re_path(r'^trimestre/', include('trimestre.urls')),
    re_path(r'^emploie/', include('emploie.urls')),
    re_path(r'^evaluations/', include('evaluation.urls')),
    re_path(r'^notes/', include('notes.urls')),
    re_path(r'^users/', include('users.urls')),
    re_path(r'^branches/', include('branches.urls')),
    re_path(r'^slaees/', include('salle.urls')),
    re_path(r'^pointages/', include('pointage.urls')),
    re_path(r'^language/', include('languages.urls')),
    re_path(r'^pointage-matiere/', include('pointagematiere.urls')),
    re_path(r'^parametres/', include('parametres.urls')),
    re_path(r'^rapports/', include('rapports.urls')),
    re_path(r'^espace-prof/', include('espace_prof.urls')),
    re_path(r'^roles/', include('roles.urls')),
    re_path(r'^documents/', include('documents.urls')),

    path('i18n/', include('django.conf.urls.i18n')),
    path('api/pointages/', include('pointage.urls')),  # ← assure-toi que cette ligne existe

)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)