from django.urls import path

from .views import UsageView, CostEstimateView, ProjectCostView, ScenarioEstimateView

urlpatterns = [
    path(
        "usage/scenario-estimate/",
        ScenarioEstimateView.as_view(),
        name="ai_scenario_estimate",
    ),
    path("usage/", UsageView.as_view(), name="ai_usage"),
    path("usage/estimate/", CostEstimateView.as_view(), name="ai_cost_estimate"),
    path(
        "usage/projects/<uuid:video_id>/",
        ProjectCostView.as_view(),
        name="ai_project_cost",
    ),
]
