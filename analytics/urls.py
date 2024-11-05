from django.urls import path
from . import views, home_views, tdml_ml_views,ai_models

urlpatterns = [
    path('predict/',ai_models.PredictedModel, name="PredictedModel"),
    path("advanced_analytics/", home_views.analytics_home_page , name='advanced_analytics'),
    path("advanced_analytics/traditional_ml_hp/", home_views.traditional_ml_home_page, name='traditional_ml'),
    path('list_datasources/', views.list_datasources, name='list_datasources'),
    path('CreateDataFrame/',views.CreateDataFrame,name='CreateDataFrame'),
    path('traditional_ml_hp/batch_list_files/', tdml_ml_views.batch_list_files, name='batch_list_files'),
    path('traditional_ml_hp/real_list_files/', tdml_ml_views.real_list_files, name='real_list_files'),
    path('predictModel/', tdml_ml_views.predictModel, name = 'predictModel'), 
    path('readModel/', tdml_ml_views.getModelRespons,name='readModel'),
    path('uploadModel/',tdml_ml_views.upload_ml,name='uploadModel'),
    path('wms_usecase_data/',home_views.tml_wms_usecase_data, name = 'WMS_data'),
    path('list_files/', tdml_ml_views.listfiles, name='list_files'),
    path('data_from_file/',tdml_ml_views.data_from_file, name="data_from_file"),
    path('analytics/models_upload_s3_view/',tdml_ml_views.models_upload_s3_view, name="models_upload_s3_view"),
] 