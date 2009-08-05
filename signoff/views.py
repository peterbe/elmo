from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from life.models import Locale, Push, Tree
from signoff.models import Milestone, Signoff, Snapshot, AppVersion, Action, SignoffForm, ActionForm
from l10nstats.models import Run
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import simplejson
from django.core import serializers
from django.db import connection

from collections import defaultdict
from ConfigParser import ConfigParser
import datetime
from difflib import SequenceMatcher

from Mozilla.Parser import getParser, Junk
from Mozilla.CompareLocales import AddRemove, Tree


def index(request):
    locales = Locale.objects.all().order_by('code')
    avs = AppVersion.objects.all().order_by('code')

    for i in avs:
        statuses = Milestone.objects.filter(appver=i.id).values_list('status', flat=True).distinct()
        if 1 in statuses:
            i.status = 'open'
        elif 0 in statuses:
            i.status = 'upcoming'
        elif 2 in statuses:
            i.status = 'shipped'
        else:
            i.status = 'unknown' 

    return render_to_response('signoff/index.html', {
        'locales': locales,
        'avs': avs,
    })

def pushes(request):
    if request.GET.has_key('locale'):
        locale = Locale.objects.get(code=request.GET['locale'])
    if request.GET.has_key('ms'):
        mstone = Milestone.objects.get(code=request.GET['ms'])
    if request.GET.has_key('av'):
        mstone = Milestone.objects.filter(appver__code=request.GET['av']).order_by('-pk')[0]
    enabled = mstone.status<2
    if enabled:
        current = _get_current_signoff(locale, mstone)
    else:
        current = _get_accepted_signoff(locale, mstone)
    user = request.user
    anonymous = user.is_anonymous()
    staff = user.is_staff
    if request.method == 'POST': # we're going to process forms
        offset_id = request.POST['first_row']
        if not enabled: # ... but we're not logged in. Panic!
            request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s</span> could not be added - <strong>Milestone is not open for edits</strong>' % (mstone, locale)
        elif anonymous: # ... but we're not logged in. Panic!
            request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s</span> could not be added - <strong>User not logged in</strong>' % (mstone, locale)
        else:
            if request.POST.has_key('accepted'): # we're in AcceptedForm mode
                if not staff: # ... but we have no privileges for that!
                    request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s</span> could not be accepted/rejected - <strong>User has not enough privileges</strong>' % (mstone, locale)
                else:
                    # hack around AcceptForm not taking strings, fixed in
                    # django 1.1
                    bval = {"true": 1, "false": 2}[request.POST['accepted']]
                    form = ActionForm({'signoff': current.id, 'flag': bval, 'author': user.id, 'comment': request.POST['comment']})
                    if form.is_valid():
                        form.save()
                        if request.POST['accepted'] == "False":
                            request.session['signoff_info'] = '<span style="font-style: italic">Rejected'
                        else:
                            request.session['signoff_info'] = '<span style="font-style: italic">Accepted'
                    else:
                        request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> could not be added' % (mstone, locale, user.username)
            else:
                instance = Signoff(appversion=mstone.appver, locale=locale, author=user)
                form = SignoffForm(request.POST, instance=instance)
                if form.is_valid():
                    form.save()
                    
                    #add a snapshot of the current test results
                    pushobj = Push.objects.get(id=request.POST['push'])
                    lastrun = _get_compare_locales_result(pushobj.tip, mstone.appver.tree)
                    if lastrun:
                        Snapshot.objects.create(signoff_id=form.instance.id, test=Run, tid=lastrun.id)
                    Action.objects.create(signoff_id=form.instance.id, flag=0, author=user)

                    request.session['signoff_info'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> added' % (mstone, locale, user.username)
                else:
                    request.session['signoff_error'] = '<span style="font-style: italic">Signoff for %s %s by %s</span> could not be added' % (mstone, locale, user.username)
        return HttpResponseRedirect('%s?locale=%s&ms=%s&offset=%s' % (reverse('signoff.views.pushes'), locale.code ,mstone.code, offset_id))

    form = SignoffForm()
    
    forest = mstone.appver.tree.l10n
    repo_url = '%s%s/' % (forest.url, locale.code)
    notes = _get_notes(request.session)
    accepted = _get_accepted_signoff(locale, mstone)

    max_pushes = _get_total_pushes(locale, mstone)
    if max_pushes > 50:
        max_pushes = 50

    if request.GET.has_key('center'):
        offset = _get_push_offset(request.GET['center'],-5)
    elif request.GET.has_key('offset'):
        offset = _get_push_offset(request.GET['offset'])
    else:
        offset = 0
    return render_to_response('signoff/pushes.html', {
        'mstone': mstone,
        'locale': locale,
        'form': form,
        'notes': notes,
        'current': current,
        'accepted': accepted,
        'user': user,
        'user_type': 0 if user.is_anonymous() else 2 if user.is_staff else 1,
        'pushes': (simplejson.dumps(_get_api_items(locale, mstone, current, offset=offset+20)), 0, min(max_pushes,offset+10)),
        'max_pushes': max_pushes,
        'offset': offset,
        'current_js': simplejson.dumps(_get_current_js(current)),
    })


def diff_app(request):
    reponame = request.GET['repo']
    repopath = settings.REPOSITORY_BASE + '/' + reponame
    from mercurial.ui import ui as _ui
    from mercurial.hg import repository
    ui = _ui()
    repo = repository(ui, repopath)
    ctx1 = repo.changectx(request.GET['from'])
    ctx2 = repo.changectx(request.GET['to'])
    match = None # maybe get something from l10n.ini and cmdutil
    changed, added, removed = repo.status(ctx1, ctx2, match=match)[:3]
    diffs = Tree(dict)
    for path in changed:
        lines = []
        try:
            p = getParser(path)
        except UserWarning:
            diffs[path].update({'path': path,
                                'lines': [{'class': 'issue',
                                           'oldval': '',
                                           'newval': '',
                                           'entity': 'cannot parse ' + path}]})
            continue
        data1 = ctx1.filectx(path).data()
        data2 = ctx2.filectx(path).data()
        p.readContents(data1)
        a_entities, a_map = p.parse()
        p.readContents(data2)
        c_entities, c_map = p.parse()
        del p
        a_list = sorted(a_map.keys())
        c_list = sorted(c_map.keys())
        ar = AddRemove()
        ar.set_left(a_list)
        ar.set_right(c_list)
        for action, item_or_pair in ar:
            if action == 'delete':
                lines.append({'class': 'removed',
                              'oldval': [{'value':a_entities[a_map[item_or_pair]].val}],
                              'newval': '',
                              'entity': item_or_pair})
            elif action == 'add':
                lines.append({'class': 'added',
                              'oldval': '',
                              'newval':[{'value': c_entities[c_map[item_or_pair]].val}],
                              'entity': item_or_pair})
            else:
                oldval = a_entities[a_map[item_or_pair[0]]].val
                newval = c_entities[c_map[item_or_pair[1]]].val
                if oldval == newval:
                    continue
                sm = SequenceMatcher(None, oldval, newval)
                oldhtml = []
                newhtml = []
                for op, o1, o2, n1, n2 in sm.get_opcodes():
                    if o1 != o2:
                        oldhtml.append({'class':op, 'value':oldval[o1:o2]})
                    if n1 != n2:
                        newhtml.append({'class':op, 'value':newval[n1:n2]})
                lines.append({'class':'changed',
                              'oldval': oldhtml,
                              'newval': newhtml,
                              'entity': item_or_pair[0]})
        container_class = lines and 'file' or 'empty-diff'
        diffs[path].update({'path': path,
                            'class': container_class,
                            'lines': lines})
    diffs = diffs.toJSON().get('children', [])
    return render_to_response('signoff/diff.html',
                              {'locale': request.GET['locale'],
                               'added': added,
                               'removed': removed,
                               'repo_url': request.GET['url'],
                               'old_rev': request.GET['from'],
                               'new_rev': request.GET['to'],
                               'diffs': diffs})


def dashboard(request):
    if 'ms' in request.GET:
        mstone = Milestone.objects.get(code=request.GET['ms'])
        tree = mstone.appver.tree
        obj = mstone
        query = 'ms'
    else:
        appver = AppVersion.objects.get(code=request.GET['av'])
        tree = appver.tree
        obj = appver
        query = 'av'
    args = ["tree=%s" % tree.code]
    return render_to_response('signoff/dashboard.html', {
            'obj': obj,
            'query': query,
            'args': args,
            })

def l10n_changesets(request):
    if request.GET.has_key('ms'):
        mstone = Milestone.objects.get(code=request.GET['ms'])
        sos = _get_signoffs(ms=mstone)
    elif request.GET.has_key('av'):
        appver = AppVersion.objects.get(code=request.GET['av'])
        sos = _get_signoffs(av=appver)
    else:
        return HttpResponse('No milestone or appversion given')
    
    r = HttpResponse(('%s %s\n' % (k, sos[k].push.tip.shortrev)
                      for k in sorted(sos.keys())),
                     content_type='text/plain; charset=utf-8')
    r['Content-Disposition'] = 'inline; filename=l10n-changesets'
    return r

def shipped_locales(request):
    if request.GET.has_key('ms'):
        mstone = Milestone.objects.get(code=request.GET['ms'])
        sos = _get_signoffs(ms=mstone)
    elif request.GET.has_key('av'):
        appver = AppVersion.objects.get(code=request.GET['av'])
        sos = _get_signoffs(av=appver)
    else:
        return HttpResponse('No milestone or appversion given')

    locales = sos.keys() + ['en-US']
    def withPlatforms(loc):
        if loc == 'ja':
            return 'ja linux win32\n'
        if loc == 'ja-JP-mac':
            return 'ja-JP-mac osx\n'
        return loc + '\n'
    
    r = HttpResponse(map(withPlatforms, sorted(locales)),
                      content_type='text/plain; charset=utf-8')
    r['Content-Disposition'] = 'inline; filename=shipped-locales'
    return r

def signoff_json(request):
    if request.GET.has_key('ms'):
        mstone = Milestone.objects.get(code=request.GET['ms'])
        lsd = _get_signoff_statuses(ms=mstone)
    elif request.GET.has_key('av'):
        appver = AppVersion.objects.get(code=request.GET['av'])
        lsd = _get_signoff_statuses(av=appver)
    items = defaultdict(list)
    values = dict(Action._meta.get_field('flag').flatchoices)
    for loc, sol in lsd.iteritems():
        items[loc] = [values[so] for so in sol]
    # make a list now
    items = [{"type": "SignOff", "label": locale, 'signoff': list(values)}
             for locale, values in items.iteritems()]
    return HttpResponse(simplejson.dumps({'items': items}, indent=2))


def pushes_json(request):
    loc = request.GET.get('locale', None)
    ms = request.GET.get('mstone', None)
    start = int(request.GET.get('from', 0))
    to = int(request.GET.get('to', 20))
    
    locale = None
    mstone = None
    current = None
    if loc:
        locale = Locale.objects.get(code=loc)
    if ms:
        mstone = Milestone.objects.get(code=ms)
    if loc and ms:
        cur = _get_current_signoff(locale, mstone)
    
    pushes = _get_api_items(locale, mstone, cur, start=start, offset=start+to)
    return HttpResponse(simplejson.dumps({'items': pushes}, indent=2))


def milestones(request):
    """Administrate milestones.

    Opens an exhibit that offers the actions below depending on 
    milestone status and user permissions.
    """
    return render_to_response('signoff/milestones.html',
                              {},
                              context_instance=RequestContext(request))

def stones_data(request):
    """JSON data to be used by milestones
    """
    stones = Milestone.objects.order_by('-pk').select_related(depth=1)[:5]
    items = [{'label': str(stone),
              'appver': str(stone.appver),
              'status': stone.status,
              'code': stone.code}
             for stone in stones]
    return HttpResponse(simplejson.dumps({'items': items}, indent=2))

def open_mstone(request):
    """Open a milestone.

    Only available to POST, and requires signoff.can_open permissions.
    Redirects to milestones().
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        request.user.has_perm('signoff.can_open')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            mstone.status = 1
            # XXX create event
            mstone.save()
        except:
            pass
    return HttpResponseRedirect(reverse('signoff.views.milestones'))

def clear_mstone(request):
    """Clear a milestone, reset all sign-offs.

    Only available to POST, and requires signoff.can_open permissions.
    Redirects to dasboard() for the milestone.
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        request.user.has_perm('signoff.can_open')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            if mstone.status is 2:
                return HttpResponseRedirect(reverse('signoff.views.milestones'))
            # get all signoffs, independent of state, and file an obsolete
            # action
            for loc, so in _get_signoffs(ms=mstone, status=None).iteritems():
                so.action_set.create(flag=4, author=request.user)
            return HttpResponseRedirect(reverse('signoff.views.dashboard')
                                        + "?ms=" + mstone.code)
        except:
            pass
    return HttpResponseRedirect(reverse('signoff.views.milestones'))

def confirm_ship_mstone(request):
    """Intermediate page when shipping a milestone.

    Gathers all data to verify when shipping.
    Ends up in ship_mstone if everything is fine.
    Redirects to milestones() in case of trouble.
    """
    if not ("ms" in request.GET and
            request.user.has_perm('signoff.can_ship')):
        return HttpResponseRedirect(reverse('signoff.views.milestones'))
    try:
        mstone = Milestone.objects.get(code=request.GET['ms'])
    except:
        return HttpResponseRedirect(reverse('signoff.views.milestones'))
    if mstone.status is not 1:
        return HttpResponseRedirect(reverse('signoff.views.milestones'))
    pendings = _get_signoffs(ms=mstone, status=0)
    pending_locs = sorted(pendings.keys())
    good = _get_signoffs(ms=mstone)
    good_locs = sorted(good.keys())
    return render_to_response('signoff/confirm-ship.html',
                              {'mstone': mstone,
                               'pendings': pendings,
                               'pending_locs': pending_locs,
                               'good': good,
                               'good_locs': good_locs},
                              context_instance=RequestContext(request))
        
def ship_mstone(request):
    """The actual worker method to ship a milestone.

    Only avaible to POST.
    Redirects to milestones().
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        request.user.has_perm('signoff.can_ship')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            cs = _get_signoffs(ms=mstone)      # get current signoffs
            mstone.signoffs.add(*cs.values())  # add them
            mstone.status = 2
            # XXX create event
            mstone.save()
        except:
            pass
    return HttpResponseRedirect(reverse('signoff.views.milestones'))

#
#  Internal functions
#

def _get_current_signoff(locale, mstone):
    sos = Signoff.objects.filter(locale=locale, appversion=mstone.appver)
    try:
        return sos.order_by('-pk')[0]
    except IndexError:
        return None

def _get_total_pushes(locale=None, mstone=None):
    if mstone:
        forest = mstone.appver.tree.l10n
        repo_url = '%s%s/' % (forest.url, locale.code) 
        return Push.objects.filter(changesets__repository__url=repo_url).count()
    else:
        return Push.objects.count()

def _get_compare_locales_result(rev, tree):
        try:
            return Run.objects.filter(revisions=rev,
                                      tree=tree).order_by('-build__id')[0]
        except:
            return None

def _get_api_items(locale=None, mstone=None, current=None, start=0, offset=10):
    if mstone:
        forest = mstone.appver.tree.l10n
        repo_url = '%s%s/' % (forest.url, locale.code) 
        pushobjs = Push.objects.filter(changesets__repository__url=repo_url).order_by('-push_date')[start:start+offset]
    else:
        pushobjs = Push.objects.order_by('-push_date')[start:start+offset]
    
    pushes = []
    for pushobj in pushobjs:
        if mstone:
            signoff_trees = [mstone.appver.tree]
        else:
            signoff_trees = Tree.objects.filter(l10n__repositories=pushobj.tip.repository, appversion__milestone__isnull=False)
        name = '%s on [%s]' % (pushobj.user, pushobj.push_date)
        date = pushobj.push_date.strftime("%Y-%m-%d")
        cur = current and current.push.id == pushobj.id

        # check compare-locales
        runs2 = Run.objects.filter(revisions=pushobj.tip)
        for tree in signoff_trees:
            try:
                lastrun = runs2.filter(tree=tree).order_by('-build__id')[0]
                missing = lastrun.missing + lastrun.missingInFiles
                if missing:
                    compare = '%d missing' % missing
                elif lastrun.obsolete:
                    compare = '%d obsolete' % lastrun.obsolete
                else:
                    compare = 'green (%d%%)' % lastrun.completion
            except:
                compare = 'no build'

            pushes.append({'name': name,
                           'date': date,
                           'time': pushobj.push_date.strftime("%H:%M:%S"),
                           'id': pushobj.id,
                           'user': pushobj.user,
                           'revision': pushobj.tip.shortrev,
                           'revdesc': pushobj.tip.description,
                           'status': 'green',
                           'build': 'green',
                           'compare': compare,
                           'signoff': cur,
                           'url': '%spushloghtml?changeset=%s' % (pushobj.tip.repository.url, pushobj.tip.shortrev),
                           'accepted': current.accepted if cur else None})
    return pushes

def _get_current_js(cur):
    current = {}
    if cur:
        current['when'] = cur.when.strftime("%Y-%m-%d %H:%M")
        current['author'] = str(cur.author)
        current['status'] = None if cur.status==0 else cur.accepted
        current['id'] = str(cur.id)
        current['class'] = cur.flag
    return current

def _get_notes(session):
    notes = {}
    for i in ('info','warning','error'):
        notes[i] = session.get('signoff_%s' % (i,), None)
        if notes[i]:
            del session['signoff_%s' % (i,)]
        else:
            del notes[i]
    return notes

def _get_push_offset(id, shift=0):
    """returns an offset of the push for signoff slider"""
    if not id:
        return 0
    push = Push.objects.get(changesets__revision__startswith=id)
    num = Push.objects.filter(pk__gt=push.pk, changesets__repository__url=push.tip.repository.url).count()
    if num+shift<0:
        return 0
    return num+shift

def _get_accepted_signoff(locale, ms):
    '''this function gets the latest accepted signoff
    for a milestone/locale
    '''

    if ms.status==2: # shipped
        try:
            return ms.signoffs.get(locale=locale)
        except:
            return None

    cursor = connection.cursor()
    cursor.execute("SELECT a.flag,s.id FROM signoff_action \
                    AS a,signoff_signoff AS s WHERE a.signoff_id=s.id AND \
                    s.appversion_id=%s AND s.locale_id=%s GROUP BY a.signoff_id ORDER BY a.id DESC;", [ms.appver.id, locale.id])
    items = cursor.fetchall()
    for item in items:
        if item[0] is not 1:
            # if action.flag is not Accepted, skip
            continue
        if item[0] is 4:
            return None
        return Signoff.objects.get(pk=item[1])
    return None

def _get_signoff_statuses(ms=None, av=None):
    '''this function gets the latest signoff flags
    for a milestone or appversion
    '''
    if ms and ms.status==2: # shipped
        return dict([(so.locale.code, so) for so in ms.signoffs.all()])
    
    if ms:
        aid = ms.appver.id
    else:
        aid = av.id
    
    cursor = connection.cursor()
    stmnt = (("SELECT s.locale_id,s.id,a.flag FROM %s as s " +
              ",%s as a WHERE s.appversion_id=%%s AND a.signoff_id=s.id" +
              " GROUP BY a.signoff_id ORDER BY a.id DESC")
             % (Signoff._meta.db_table, Action._meta.db_table))
    cursor.execute(stmnt, [aid])
    # filter signoffs if wanted, strip obsolete and just get the ids

    def items():
        for item in cursor.fetchall():
            yield item

    locales = Locale.objects.all()

    lf = defaultdict(list)
    for i in items():
        lf[i[0]].append(i[2])

    for code,flags in lf.items():
        for i,flag in enumerate(flags):
            if flag==1:          # stop on accepted
              del lf[code][i+1:]
              break
            if flag==4:          # stop on obsoleted
              del lf[code][i:]
              break

    lcd = dict(Locale.objects.filter(pk__in=lf.keys()).values_list('id','code'))
    return dict(map(lambda v: (lcd[v[0]],v[1]), lf.iteritems()))


def _get_signoffs(ms=None, av=None, status=1):
    '''this function gets the latest accepted signoffs
    for a milestone or appversion
    '''
    if ms and ms.status==2: # shipped
        return dict([(so.locale.code, so) for so in ms.signoffs.all()])
    
    if ms:
        aid = ms.appver.id
    else:
        aid = av.id
    
    cursor = connection.cursor()
    stmnt = (("SELECT a.flag,s.id FROM %s " +
              "AS a,%s AS s WHERE a.signoff_id=s.id AND " +
              "s.appversion_id=%%s GROUP BY a.signoff_id ORDER BY a.id;")
             % (Action._meta.db_table, Signoff._meta.db_table))
    cursor.execute(stmnt, [aid])
    items = cursor.fetchall()
    # filter signoffs if wanted, strip obsolete and just get the ids
    if status is not None:
        items = filter(lambda t: t[0] is status, items)
    else:
        items = filter(lambda t: t[0] is not 4, items)
    so_ids = map(lambda t: t[1], items)
    so_q = Signoff.objects.filter(pk__in=so_ids).select_related('locale__code',
                                                                'push__changesets')
    sos = dict((so.locale.code, so) for so in so_q)
    return sos

