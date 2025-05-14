"""
URL configuration for sharedgoals project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.urls import path,include
from rest_framework.routers import DefaultRouter
from expenses.views import (GroupViewSet, GroupExpenseViewSet,
                            GroupBalancesView,GroupRepaymentViewSet,
                            GroupSummaryView)
from users.views import RegisterationViewSet, LoginViewSet

router = DefaultRouter()
router.register(r'groups', GroupViewSet)
router.register(r"register", RegisterationViewSet, basename="register")
router.register(r"login", LoginViewSet, basename="login")

urlpatterns = [

    path("admin/", admin.site.urls),
    path('api/', include(router.urls)),
    path('groups/<int:group_id>/expenses/', GroupExpenseViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='group-expenses-list'),
    
    path('groups/<int:group_id>/expenses/<int:pk>/', GroupExpenseViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='group-expenses-detail'),
    
    path('groups/<int:group_id>/repayments/', GroupRepaymentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='group-repayments-list'),
    
    path('groups/<int:group_id>/repayments/<int:pk>/', GroupRepaymentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='group-repayments-detail'),
    

    path('groups/<int:group_id>/summary/', GroupSummaryView.as_view(), name='group-summary'),
    path('groups/<int:group_id>/balances/', GroupBalancesView.as_view(), name='group-balances'),

]
