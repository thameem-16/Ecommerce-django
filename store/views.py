from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages

from carts.models import Cart, CartItem
from carts.views import _cart_id
from .models import Product, Order, OrderItem
from .models import Wishlist
from catagory.models import Catagory
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.contrib.auth.decorators import login_required


def store(request, catagory_slug=None):
    catagories = None
    products = None
    # base queryset
    if catagory_slug:
        catagories = get_object_or_404(Catagory, slug=catagory_slug)
        products = Product.objects.filter(catagory=catagories, is_available=True)
    else:
        products = Product.objects.filter(is_available=True).order_by('id')

    # filters from GET
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    color = request.GET.get('color')
    size = request.GET.get('size')
    sort = request.GET.get('sort')

    if min_price:
        try:
            products = products.filter(price__gte=min_price)
        except:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=max_price)
        except:
            pass
    if color:
        products = products.filter(variation__variation_category__iexact='color', variation__variation_value__iexact=color).distinct()
    if size:
        products = products.filter(variation__variation_category__iexact='size', variation__variation_value__iexact=size).distinct()

    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')

    paginator = Paginator(products, 3)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    product_count = products.count()

    context = {
        'products': paged_products,
        'product_count': product_count,
        'available_colors': Product.objects.filter(is_available=True).filter(variation__variation_category='color').values_list('variation__variation_value', flat=True).distinct(),
        'available_sizes': Product.objects.filter(is_available=True).filter(variation__variation_category='size').values_list('variation__variation_value', flat=True).distinct(),
    }
    return render(request, 'store/store.html', context)


def product_detail(request, catagory_slug, product_slug):
    try:
        single_product = Product.objects.get(catagory__slug=catagory_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e
    
    context={
        'single_product': single_product,
        'in_cart' : in_cart,
    }

    return render(request, 'store/product_detail.html', context)


def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()
    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)



@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):
    try:
        total = Decimal('0.00')
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += (Decimal(cart_item.product.price) * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (Decimal('2') * total) / Decimal('100')
        grand_total = total + tax
    except ObjectDoesNotExist:
        return redirect('cart')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', request.user.first_name)
        last_name = request.POST.get('last_name', request.user.last_name)
        phone = request.POST.get('phone', getattr(request.user, 'phone_number', ''))
        email = request.POST.get('email', request.user.email)
        address_line_1 = request.POST.get('address_line_1')
        address_line_2 = request.POST.get('address_line_2', '')
        city = request.POST.get('city')
        state = request.POST.get('state', '')
        postal_code = request.POST.get('postal_code')
        country = request.POST.get('country')

        import uuid
        order_number = str(uuid.uuid4()).split('-')[0].upper()
        order = Order.objects.create(
            user=request.user,
            order_number=order_number,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            order_total=grand_total,
            tax=tax,
            is_ordered=True,
        )

        for item in cart_items:
            oi = OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                product_price=item.product.price,
                ordered=True,
            )
            if item.variations.exists():
                oi.variations.set(item.variations.all())
            # decrement stock
            item.product.stock -= item.quantity
            item.product.save()
            # remove cart item
            item.delete()

        cart.delete()
        messages.success(request, f'Order placed successfully. Order no: {order.order_number}')
        return redirect('order_history')

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/checkout.html', context)


@login_required(login_url='login')
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'store/order_history.html', context)


@login_required(login_url='login')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'store/order_detail.html', context)


@login_required(login_url='login')
def add_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    from account.models import Account
    user = request.user
    if not user.is_authenticated:
        return redirect('login')
    Wishlist.objects.get_or_create(user=user, product=product)
    messages.success(request, 'Added to wishlist')
    return redirect('product_detail', catagory_slug=product.catagory.slug, product_slug=product.slug)


@login_required(login_url='login')
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product')
    context = {
        'wishlist_items': items,
    }
    return render(request, 'store/wishlist.html', context)