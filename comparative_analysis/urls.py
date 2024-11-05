from django.urls import path
from .views import ComparisionOfPRPS, LostAndFoundAnalysis, TransactionBenchMark,getFilesList, uniqueItemByMonth, damageProducts, ShortShippedOrderAnalysis
 
urlpatterns = [
    path('Transaction-BenchMark/', TransactionBenchMark, name='TransactionBenchMark'),
    path('ComparativeFiles/',getFilesList,name='ComparativeFiles'),
    path('LostAndFoundAnalysis/',LostAndFoundAnalysis, name='LostAndFoundAnalysis'),
    path('UniqueitemsReceviedByMonth/',uniqueItemByMonth,name='uniqueItemByMonth'),
    path('ComparisionOfPRPS/',ComparisionOfPRPS,name='ComparisionOfPRPS'),
     path('damageProducts/',damageProducts, name='DamagedProducts'),
    path('ShortShippedOrderAnalysis/',ShortShippedOrderAnalysis,name='ShortShippedOrderAnalysis')
]