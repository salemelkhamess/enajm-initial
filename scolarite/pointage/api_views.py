# pointages/api_views.py
from rest_framework import viewsets
from .models import Pointage
from .serializers import PointageSerializer
from rest_framework import generics

class PointageViewSet(viewsets.ModelViewSet):
    queryset = Pointage.objects.all()
    serializer_class = PointageSerializer

class PointageListAPIView(generics.ListAPIView):
    queryset = Pointage.objects.all()
    serializer_class = PointageSerializer