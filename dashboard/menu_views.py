from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
import csv
import io

from .decorators import staff_required, manager_required
from orders.models import Order
from reservations.models import Reservation
from menu.models import Category, MenuItem, Tag, AddOn


@staff_required
@manager_required
def menu_list(request):
    """All menu items with filters."""
    items = MenuItem.objects.select_related('category').prefetch_related('tags', 'addons').order_by('category__order_position', 'name')

    category_filter = request.GET.get('category', '')
    search = request.GET.get('search', '').strip()
    availability_filter = request.GET.get('available', '')

    if category_filter:
        items = items.filter(category__id=category_filter)
    if search:
        items = items.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if availability_filter == '1':
        items = items.filter(is_available=True)
    elif availability_filter == '0':
        items = items.filter(is_available=False)

    categories = Category.objects.order_by('order_position', 'name')

    context = {
        'items': items,
        'categories': categories,
        'category_filter': category_filter,
        'search': search,
        'availability_filter': availability_filter,
        'total_items': MenuItem.objects.count(),
        'available_items': MenuItem.objects.filter(is_available=True).count(),
        'hidden_items': MenuItem.objects.filter(is_available=False).count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/menu_list.html', context)


@staff_required
@manager_required
def menu_item_add(request):
    """Add a new menu item."""
    categories = Category.objects.order_by('order_position', 'name')
    tags = Tag.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        category_id = request.POST.get('category', '')
        is_available = request.POST.get('is_available') == 'on'
        is_featured = request.POST.get('is_featured') == 'on'
        image = request.FILES.get('image')
        tag_ids = request.POST.getlist('tags')

        if not name or not price or not category_id:
            messages.error(request, 'Name, price, and category are required.')
        else:
            try:
                category = Category.objects.get(id=category_id)
                item = MenuItem.objects.create(
                    name=name,
                    description=description,
                    price=price,
                    category=category,
                    is_available=is_available,
                    is_featured=is_featured,
                    image=image,
                )
                if tag_ids:
                    item.tags.set(tag_ids)
                messages.success(request, f'"{name}" added to the menu.')
                return redirect('dashboard:menu_list')
            except Exception as e:
                messages.error(request, f'Error adding item: {e}')

    context = {
        'categories': categories,
        'tags': tags,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/menu_item_form.html', context)


@staff_required
@manager_required
def menu_item_edit(request, item_id):
    """Edit an existing menu item."""
    item = get_object_or_404(MenuItem, id=item_id)
    categories = Category.objects.order_by('order_position', 'name')
    tags = Tag.objects.all()

    if request.method == 'POST':
        item.name = request.POST.get('name', '').strip()
        item.description = request.POST.get('description', '').strip()
        item.price = request.POST.get('price', '').strip()
        category_id = request.POST.get('category', '')
        item.is_available = request.POST.get('is_available') == 'on'
        item.is_featured = request.POST.get('is_featured') == 'on'
        image = request.FILES.get('image')
        tag_ids = request.POST.getlist('tags')

        if not item.name or not item.price or not category_id:
            messages.error(request, 'Name, price, and category are required.')
        else:
            try:
                item.category = Category.objects.get(id=category_id)
                if image:
                    item.image = image
                item.save()
                item.tags.set(tag_ids)
                messages.success(request, f'"{item.name}" updated.')
                return redirect('dashboard:menu_list')
            except Exception as e:
                messages.error(request, f'Error updating item: {e}')

    context = {
        'item': item,
        'categories': categories,
        'tags': tags,
        'editing': True,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/menu_item_form.html', context)


@staff_required
@manager_required
def menu_item_delete(request, item_id):
    """Delete a menu item."""
    if request.method != 'POST':
        return redirect('dashboard:menu_list')
    item = get_object_or_404(MenuItem, id=item_id)
    name = item.name
    item.delete()
    messages.success(request, f'"{name}" has been deleted.')
    return redirect('dashboard:menu_list')


@staff_required
@manager_required
def menu_item_toggle(request, item_id):
    """Toggle item availability."""
    if request.method != 'POST':
        return redirect('dashboard:menu_list')
    item = get_object_or_404(MenuItem, id=item_id)
    item.is_available = not item.is_available
    item.save()
    status = 'visible' if item.is_available else 'hidden'
    messages.success(request, f'"{item.name}" is now {status}.')
    return redirect('dashboard:menu_list')


@staff_required
@manager_required
def menu_csv_import(request):
    """Bulk import menu items from CSV."""
    categories = Category.objects.order_by('order_position', 'name')

    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            messages.error(request, 'Please select a CSV file.')
            return redirect('dashboard:menu_csv_import')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File must be a .csv file.')
            return redirect('dashboard:menu_csv_import')

        try:
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            updated = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    name = row.get('name', '').strip()
                    if not name:
                        errors.append(f'Row {row_num}: name is required.')
                        continue

                    price = row.get('price', '').strip()
                    if not price:
                        errors.append(f'Row {row_num}: price is required for "{name}".')
                        continue

                    category_name = row.get('category', '').strip()
                    if not category_name:
                        errors.append(f'Row {row_num}: category is required for "{name}".')
                        continue

                    # Get or create category
                    category, _ = Category.objects.get_or_create(
                        name__iexact=category_name,
                        defaults={'name': category_name}
                    )

                    description = row.get('description', '').strip()
                    is_available = row.get('is_available', 'true').strip().lower() in ('true', '1', 'yes')
                    is_featured = row.get('is_featured', 'false').strip().lower() in ('true', '1', 'yes')
                    image_filename = row.get('image', '').strip()

                    # Create or update
                    item, was_created = MenuItem.objects.update_or_create(
                        name__iexact=name,
                        defaults={
                            'name': name,
                            'description': description,
                            'price': price,
                            'category': category,
                            'is_available': is_available,
                            'is_featured': is_featured,
                        }
                    )

                    # Handle tags
                    tag_names = row.get('tags', '').strip()
                    if tag_names:
                        tag_list = [t.strip() for t in tag_names.split('|') if t.strip()]
                        tag_objects = []
                        for tag_name in tag_list:
                            tag, _ = Tag.objects.get_or_create(name__iexact=tag_name, defaults={'name': tag_name})
                            tag_objects.append(tag)
                        item.tags.set(tag_objects)

                    # Handle add-ons
                    addon_data = row.get('addons', '').strip()
                    if addon_data:
                        # Format: "Extra Sauce:20|Extra Rice:15"
                        for addon_str in addon_data.split('|'):
                            if ':' in addon_str:
                                addon_name, addon_price = addon_str.split(':', 1)
                                AddOn.objects.get_or_create(
                                    dish=item,
                                    name__iexact=addon_name.strip(),
                                    defaults={'name': addon_name.strip(), 'additional_price': addon_price.strip()}
                                )

                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append(f'Row {row_num}: {str(e)}')

            # Summary message
            if created or updated:
                messages.success(request, f'Import complete — {created} item(s) created, {updated} item(s) updated.')
            if errors:
                for err in errors[:5]:  # Show first 5 errors
                    messages.error(request, err)
                if len(errors) > 5:
                    messages.error(request, f'...and {len(errors) - 5} more errors.')

            return redirect('dashboard:menu_list')

        except Exception as e:
            messages.error(request, f'Failed to read CSV: {e}')

    context = {
        'categories': categories,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/menu_csv_import.html', context)


@staff_required
@manager_required
def menu_csv_template(request):
    """Download a blank CSV template."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="menu_import_template.csv"'

    writer = csv.writer(response)
    writer.writerow(['name', 'category', 'price', 'description', 'is_available', 'is_featured', 'tags', 'addons', 'image'])

    # Example rows using your actual categories and tag choices
    writer.writerow(['Lobster Bisque', 'Chef Specials', '24.99', 'Rich creamy bisque with fresh lobster', 'true', 'true', 'bestseller|spicy', 'Extra Bread:1.50', ''])
    writer.writerow(['Grilled Ribeye', 'Main Course', '32.00', '12oz ribeye with herb butter', 'true', 'false', 'bestseller', 'Extra Sauce:2.00|Upgrade to Wagyu:15.00', ''])
    writer.writerow(['Spring Rolls', 'Appetizers', '8.50', 'Crispy veggie spring rolls', 'true', 'false', 'vegan', '', ''])
    writer.writerow(['Spaghetti Carbonara', 'Pasta', '14.99', 'Classic carbonara with pancetta', 'true', 'false', '', 'Extra Parmesan:1.00', ''])
    writer.writerow(['Chocolate Lava Cake', 'Desserts', '9.00', 'Warm chocolate cake with vanilla ice cream', 'true', 'false', 'new', '', ''])
    writer.writerow(['Mango Shake', 'Beverages', '5.50', 'Fresh mango blended with milk', 'true', 'false', '', '', ''])

    return response


@staff_required
@manager_required
def categories_list(request):
    """Manage categories."""
    categories = Category.objects.order_by('order_position', 'name')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            name = request.POST.get('name', '').strip()
            order = request.POST.get('order', 0)
            if name:
                Category.objects.create(name=name, order_position=order)
                messages.success(request, f'Category "{name}" added.')
            else:
                messages.error(request, 'Category name is required.')

        elif action == 'delete':
            cat_id = request.POST.get('category_id')
            cat = get_object_or_404(Category, id=cat_id)
            reassign_id = request.POST.get('reassign_to', '').strip()
            item_count = cat.items.count()

            if item_count > 0:
                if not reassign_id:
                    messages.error(request, f'"{cat.name}" has {item_count} item(s). Select a category to move them to first.')
                else:
                    try:
                        new_cat = Category.objects.get(id=reassign_id)
                        cat.items.update(category=new_cat)
                        cat.delete()
                        messages.success(request, f'"{cat.name}" deleted. {item_count} item(s) moved to "{new_cat.name}".')
                    except Category.DoesNotExist:
                        messages.error(request, 'Target category not found.')
            else:
                cat.delete()
                messages.success(request, f'Category "{cat.name}" deleted.')

        return redirect('dashboard:categories_list')

    context = {
        'categories': categories,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/categories_list.html', context)