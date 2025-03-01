import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import *
from django.shortcuts import *
from django.template import Context
from django.template.loader import get_template
from gamesoup.library.forms import *
from gamesoup.library.local_editing import pack_types, unpack_types
from gamesoup.library.models import *
from gamesoup.library.code import TypeCode


###############################################################################
# DOCUMENTATION


@staff_member_required
def multiple_interface_documentation(request):
    query = {}
    if request.GET:
        g = lambda value: ',' in value and map(str, value.split(',')) or str(value)
        query = dict([(str(key), g(value)) for key, value in request.GET.items()])
    try:
        qs = Interface.objects.filter(**query).order_by('name')
    except Exception:
        qs = Interface.objects.all()
    context = {
        'title': 'Interface Documentation',
        'interfaces': qs,
    }
    return render_to_response('admin/library/interface/multiple_docs.html', context)


@staff_member_required
def interface_documentation(request, interface_id):
    interface = get_object_or_404(Interface, pk=interface_id)
    context = {
        'title': '%s Documentation' % interface.name,
        'interface': interface,
    }
    return render_to_response('admin/library/interface/doc.html', context)


@staff_member_required
def generate_type_code(request, type_id):
    type = get_object_or_404(Type, pk=type_id)
    if request.method == 'POST':
        form = GenerateCodeForm(request.POST)
        if form.is_valid():
            type.code = form.cleaned_data['new_code']
            type.save()
            return HttpResponseRedirect(reverse('admin:library_type_change', args=[type.id]))
    else:
        form = GenerateCodeForm({
            'new_code': type.generated_code(),
        })
    context = {
        'title': 'Generate %s code' % type,
        'form': form,
        'type': type,
    }
    return render_to_response('admin/library/type/generate-code.html', context)


@staff_member_required
def parsed_type_code(request, type_id):
    type = get_object_or_404(Type, pk=type_id)
    code = TypeCode(type)
    im = Method.objects.filter(interface__implemented_by=type)
    context = {
        'title': 'Parsed code for %s' % type,
        'type': type,
        'methods': im,
        'im_code': [code.interface_method(m.name) for m in im],
    }
    return render_to_response('admin/library/type/parsed.html', context)


###############################################################################
# LOCAL EDITING


@staff_member_required
def local_editing(request):
    context = {
        'title': 'Local editing',
    }
    return render_to_response('admin/library/local-editing/index.html', context)


@staff_member_required
def bulk_download(request):
    response = HttpResponse(mimetype='application/x-tar')
    pack_types(request.user.username, response)
    return response


@staff_member_required
def bulk_upload(request):
    if request.method == 'POST':
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            error = False
            tarball = form.cleaned_data['tarball']
            try:
                messages = unpack_types(request.user.username, tarball)
            except ValueError, e:
                messages = [str(e)]
                error = True
            context = {
                'title': 'Bulk upload',
                'bu_messages': messages,
                'error': error,
            }
            return render_to_response('admin/library/local-editing/bulk-upload-done.html', context)
    else:
        form = BulkUploadForm()
    context = {
        'title': 'Bulk upload',
        'form': form,
    }
    return render_to_response('admin/library/local-editing/bulk-upload.html', context)


###############################################################################
# TEMPLATION


def possible_template_parameters(request, klass, query):
    ids = map(int, filter(bool, request.POST['ids'].split(',')))
    qs = klass.objects.filter(**{query: ids})
    x = {
        'possibilities': [
            {
                'name': unicode(param),
                'id': param.id,
            }
            for param in qs
        ]
    }
    response = HttpResponse(mimetype='application/json')
    response.write(json.dumps(x))
    return response

@staff_member_required
def possible_method_template_parameters(request):
    return possible_template_parameters(request, MethodTemplateParameter, 'of_method__id__in')

@staff_member_required
def possible_interface_template_parameters(request):
    return possible_template_parameters(request, InterfaceTemplateParameter, 'of_interface__id__in')
