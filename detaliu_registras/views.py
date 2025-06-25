from django.shortcuts import render
from .forms import ImportCSVForm
from .utils import import_csv

def index(request):
    return render(request, 'detaliu_registras/index.html')

def import_csv_view(request):
    preview_data = None
    errors_exist = False
    csv_error = None

    if request.method == 'POST':
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            result = import_csv(file)
            preview_data = result.get('preview')
            errors_exist = result.get('errors_exist')
            csv_error = result.get('csv_error')
    else:
        form = ImportCSVForm()

    return render(request, 'detaliu_registras/import_csv.html', {
        'form': form,
        'preview_data': preview_data,
        'errors_exist': errors_exist,
        'csv_error': csv_error,
    })