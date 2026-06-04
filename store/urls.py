from django.urls import path
from . import views

urlpatterns = [
    path('', views.store, name='store'),
    path('category/<slug:catagory_slug>/', views.store, name='products_by_catagory'),
    path('category/<slug:catagory_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('search', views.search, name='search'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_wishlist, name='add_wishlist'),
]