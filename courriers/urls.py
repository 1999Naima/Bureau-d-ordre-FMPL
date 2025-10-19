from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_courrier, name='add_courrier'),
    path('process-ocr/', views.ProcessOCRView.as_view(), name='process_ocr'),
    path('list/', views.courrier_list, name='courrier_list'),  # Optional list view
]