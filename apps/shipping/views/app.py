# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Views centric around AppVersion data.
"""

from collections import defaultdict
from django.shortcuts import render, get_object_or_404
from shipping.models import (Milestone, AppVersion, Milestone_Signoffs,
                             Action, Signoff)
from shipping.api import flags4appversions


def changes(request, app_code):
    """Show which milestones on the given appversion took changes for which
    locale
    """
    av = get_object_or_404(AppVersion, code=app_code)
    ms_names = {}
    ms_codes = {}
    for ms in (Milestone.objects
               .filter(appver=av)
               .select_related('appver__app')):
        ms_names[ms.id] = str(ms)
        ms_codes[ms.id] = ms.code
    rows = []
    changes = None
    ms_id = None
    latest = {}
    current = {}
    ms_name = None
    # get historic data that enters this appversion
    # get that in fallback order, we'll reverse afterwards
    flags4av = flags4appversions(appversions={"id": av.id})
    flags4loc = flags4av[av]
    locs4av = defaultdict(dict)  # av -> loc -> ACCEPTED
    notaccepted = {}  # av -> flags
    for loc, (real_av, flags) in flags4loc.iteritems():
        if Action.ACCEPTED in flags:
            locs4av[real_av][loc] = flags[Action.ACCEPTED]
        else:
            notaccepted[loc] = flags
    # for not accepted locales on the current appver,
    # check for accepted on fallbacks
    if av.fallback and notaccepted:
        flags4fallback = flags4av[av.fallback]
        for loc in notaccepted:
            if loc in flags4fallback:
                # if the loc isn't here, it's never been accepted so far
                real_av, flags = flags4fallback[loc]
                if Action.ACCEPTED in flags:
                    locs4av[real_av] = flags[Action.ACCEPTED]
    # let's keep the current appver data around for later,
    # and order the fallbacks
    accepted = locs4av.pop(av.code, {})
    av_ = av
    ng_groups = []
    #T=0
    pointer = 0
    count=0
    this_cycle = None
    last_cycle = None
    buckets = {}
    pointers = {}
    rowspans = defaultdict(int)
    counts = {}
    while av_ and locs4av:
        count += 1
        print av_.code
        if count == 1:
            # "current cycle"
            buckets[1] = {'av' :[av_.code], 'count': []}
            pointers[av_.code] = 1
        elif count == 2:
            # "last cycle"
            buckets[2] = {'av': [av_.code], 'count': []}
            pointers[av_.code] = 2
        elif count == 3 or count == 4:
            prev = buckets.get(3, {'av': [], 'count': []})
            prev['av'].append(av_.code)
            buckets[3] = prev
            pointers[av_.code] = 3
        else:
            prev = buckets.get(4, {'av': [], 'count': []})
            prev['av'].append(av_.code)
            buckets[4] = prev
            pointers[av_.code] = 4

        if av_.code in locs4av:
            #print (av_.code, locs4av)
            #pointer+=1
            accepted4loc = locs4av.pop(av_.code)
            bucket = pointers[av_.code]
            buckets[bucket]['count'] += [len(accepted4loc)]

            #T+=len(accepted4loc)
            #print "\t", (av_.code, len(accepted4loc))

            #print accepted4loc
            #print (pointer, count)
            #if pointer == 1:
            #    bucket2['count'] = len(accepted4loc)
            #elif pointer == 2:
            #    bucket3['count'] = len(accepted4loc)
            #elif pointer in (3,4):
            #    bucket4['count']+= len(accepted4loc)

            #print accepted4loc.keys()
            #print "\n"

            # store actions for now, we'll get the push_ids later
            current.update(accepted4loc)
            row = {
                'name': str(av_),
                'code': av_.code,
                'isAppVersion': True,
                'changes': [(loc, 'added') for loc in sorted(accepted4loc)]
            }
            counts[av_.code] = sum(buckets[bucket]['count'])
            print "\t", av_.code, sum(buckets[bucket]['count'])
            #if bucket not in rowspans:
            #    rowspans[bucket] = len(buckets[bucket]['count'])
            #rowspans[bucket] += len(buckets[bucket]['count'])
            rows.append(row)
        av_ = av_.fallback
    from pprint import pprint
    print "BUCKETS"
    pprint( buckets)
    print "POINTERS"
    pprint(pointers)
#    print "COUNTS"
#    pprint(counts)
    rows.reverse()
    for loc, pid in (Signoff.objects
                     .filter(action__in=current.values())
                     .values_list('locale__code',
                                  'push__id')):
        current[loc] = pid
    for loc, pid in (Signoff.objects
                     .filter(action__in=accepted.values())
                     .values_list('locale__code',
                                  'push__id')):
        accepted[loc] = pid

    for _mid, loc, pid in (Milestone_Signoffs.objects
                           .filter(milestone__appver=av)
                           .order_by('milestone__id',
                                     'signoff__locale__code')
                           .values_list('milestone__id',
                                        'signoff__locale__code',
                                        'signoff__push__id')):
        if _mid != ms_id:
            ms_id = _mid
            # next milestone, bootstrap new row
            if latest:
                # previous milestone has locales left, update previous changes
                changes += [(_loc, 'dropped') for _loc in latest.iterkeys()]
                changes.sort()
            latest = current
            current = {}
            ms_name = ms_names[ms_id]
            changes = []
#            print "LAST CODE", ms_codes[ms_id]
#            print changes
#            print
            rows.append({'name': ms_name,
                         'code': ms_codes[ms_id],
                         'changes': changes})
        if loc not in latest:
            changes.append((loc, 'added'))
        else:
            lpid = latest.pop(loc)
            if lpid != pid:
                changes.append((loc, 'changed'))
        current[loc] = pid

    def _count_group_locales(group):
        locales = set()
        changes = [x['changes'] for x in group if x['changes']]
        for change in changes:
            locales.update(set(x[0] for x in change))
        return len(locales)

    groups = []
    group = []
    code = None

    last = True
    for row in reversed(rows):
        if code is None:
            code = row['code']
        elif row['code'].startswith(code) or not row.get('isAppVersion'):
            pass
        elif len(groups) >= 3:
            pass
        else:
            code = row['code']
            # last item,
            group[-1]['rowspan'] = len(group)
            group[-1]['rowspan_last'] = last
            last = False
            group[-1]['group_locales_count'] = _count_group_locales(group)
            groups.append(group)
            group = []
        group.append(row)

    if group:
        # append the left-overs from the loop
        group[-1]['rowspan'] = len(group)
        group[-1]['rowspan_last'] = last
        group[-1]['group_locales_count'] = _count_group_locales(group)
        groups.append(group)

    from pprint import pprint

    #pprint(groups[0])
#    pprint(groups)
#    pprint(rows)

    # see if we have some locales dropped in the last milestone
    if latest:
        # previous milestone has locales left, update previous changes
        changes += [(loc, 'dropped') for loc in latest.iterkeys()]
        changes.sort()
    # finally, check if there's more signoffs after the last shipped milestone
    newso = [(loc, loc in current and 'changed' or 'added')
        for loc, pid in accepted.iteritems()
        if current.get(loc) != pid]
    for loc, flags in notaccepted.iteritems():
        if Action.PENDING in flags:
            newso.append((loc, 'pending'))
        elif Action.REJECTED in flags:
            newso.append((loc, 'rejected'))
        elif Action.OBSOLETED in flags:
            newso.append((loc, 'obsoleted'))
    if newso:
        newso.sort()
        rows.append({
            'name': '%s .next' % str(av),
            'changes': newso
        })

    return render(request, 'shipping/app-changes.html', {
                    'appver': av,
                    'rows': rows,
                  })
