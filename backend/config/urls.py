from django.urls import include, path

from ledger import lender, views

urlpatterns = [
    path("", views.index), path("api/", include("ledger.urls")),
    path("lender/", lender.dashboard), path("lender/export.csv", lender.export_csv),
    path("lender/<str:ent_id>/", lender.borrower_page), path("lender/<str:ent_id>/decide/", lender.decide),
    path("lender/<str:ent_id>/kfs.pdf", lender.kfs_pdf),
]
