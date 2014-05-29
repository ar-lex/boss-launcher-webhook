# Copyright (C) 2013 Jolla Ltd.
# Contact: Islam Amer <islam.amer@jollamobile.com>
# All rights reserved.
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from django.conf import settings
from django.contrib.auth.models import User
from RuoteAMQP import Launcher

import urlparse
import pycurl
import json

from models import WebHookMapping, BuildService, LastSeenRevision, QueuePeriod

def launch(process, fields):
    """ BOSS process launcher

    :param process: process definition
    :param fields: dict of workitem fields
    """

    launcher = Launcher(amqp_host = settings.BOSS_HOST,
                        amqp_user = settings.BOSS_USER,
                        amqp_pass = settings.BOSS_PASS,
                        amqp_vhost = settings.BOSS_VHOST)

    launcher.launch(process, fields)

def launch_notify(fields):
    with open(settings.VCSCOMMIT_NOTIFY, mode='r') as process_file:
        process = process_file.read()
    launch(process, fields)

def launch_build(fields):
    with open(settings.VCSCOMMIT_BUILD, mode='r') as process_file:
        process = process_file.read()
    launch(process, fields)

def handle_payload(data):
    url = None
    func = None
    repo = data.get('repository', None)
    gh_pull_request = data.get('pull_request', None)
    bb_pr_keys = ["pullrequest_created"]
    bburl = "https://bitbucket.org"
    # https://bitbucket.org/site/master/issue/8340/pull-request-post-hook-does-not-include
    # "pullrequest_merged", "pullrequest_declined","pullrequest_updated"

    #TODO: support more payload types
    for key in bb_pr_keys:
        bb_pull_request = data.get(key, None)
        if bb_pull_request:
            break

    if bb_pull_request:
        func = bitbucket_pull_request
        url = urlparse.urljoin(bburl, data[key]['destination']['repository']['full_name']) + '.git'

    elif gh_pull_request:
        # Github pull request event
        func = github_pull_request
        url = data['pull_request']['base']['repo']['clone_url']

    elif repo:
        if repo.get('absolute_url', None):
            # bitbucket type payload
            url = repo.get('absolute_url', None)
            canon_url = data.get('canon_url', None)
            if canon_url and url:
                print "bitbucket payload"
                if url.endswith('/'):
                    url = url[:-1]
                url = urlparse.urljoin(canon_url, url)
                if not url.endswith(".git"):
                    url = url + ".git"
                func = bitbucket_webhook_launch
        elif repo.get('url', None):
            # github type payload
            url = repo.get('url', None)
            if url:
                print "github payload"
                if not url.endswith(".git"):
                    url = url + ".git"
                func = github_webhook_launch

    if not url or not func:

        if data.get('zen', None) and data.get('hook_id', None):
            # Github ping event, do nothing
            print "Github says hi!"
        else:
            print "unknown payload"

        #TODO: move to DB based service whitelist
    if ((not settings.SERVICE_WHITELIST) or
        (settings.SERVICE_WHITELIST and
         urlparse.urlparse(url).netloc in settings.SERVICE_WHITELIST)):
        func(url, data)

def handle_commit(mapobj, user, payload):
    message = "%s commit(s) pushed by %s to %s branch of %s" % (len(payload["commits"]), user, mapobj.branch, mapobj.repourl)
    if not mapobj.mapped:
        message = "%s, which is not mapped yet. Please map it." % message

    fields = mapobj.to_fields()
    fields['msg'] = message
    fields['payload'] = payload
    print message
    launch_notify(fields)

    mapobj.untag()

def handle_tag(mapobj, user, payload, tag, webuser=None):

    build = mapobj.build and mapobj.mapped
    delayed = False
    skipped = False

    if build:
        if not webuser:
            if mapobj.handled and mapobj.tag == tag:
                print "build already handled, skipping"
                build = False
                skipped = True

        # Find possible queue period objects
        qps = QueuePeriod.objects.filter(projects__name = mapobj.project,
                                         projects__obs__pk = mapobj.obs.pk)
        for qp in qps:
            if qp.delay() and not qp.override(webuser=webuser):
                print "Build trigger for %s delayed by %s" % (mapobj, qp)
                print qp.comment
                mapobj.tag = tag
                mapobj.handled = False
                build = False
                delayed = True
                break

    if mapobj.notify:

        message = "Tag %s" % tag
        if webuser:
            message = "Forced build trigger for %s" % tag

        message = "%s by %s in %s branch of %s" % (message, user, mapobj.branch,
                                                   mapobj.repourl)
        if not mapobj.mapped:
            message = "%s, which is not mapped yet. Please map it." % message
        elif build:
            message = ("%s, which will trigger build in project %s package "
                       "%s (%s/package/show?package=%s&project=%s)" % (message,
                        mapobj.project, mapobj.package, mapobj.obs.weburl,
                        mapobj.package, mapobj.project))

        elif skipped:
            message = "%s, which was already handled; skipping" % message
        elif delayed:
            message = "%s, which will be delayed by %s" % (message, qp)
            if qp.comment:
                message = "%s\n%s" % (message, qp.comment)

        fields = mapobj.to_fields()
        fields['msg'] = message
        fields['payload'] = payload
        print message
        launch_notify(fields)
        
    if build:
        fields = mapobj.to_fields()
        fields['branch'] = mapobj.branch
        fields['revision'] = mapobj.rev_or_head
        fields['payload'] = payload
        print "build"
        launch_build(fields)
        mapobj.tag = tag

def create_placeholder(repourl, branch):

    if not settings.DEFAULT_PROJECT:
        return []

    print "no mapping, create placeholder"
    mapobj = WebHookMapping()
    mapobj.repourl = repourl
    mapobj.branch = branch
    mapobj.user = User.objects.get(id=1)
    mapobj.obs = BuildService.objects.all()[0]
    mapobj.notify = False
    mapobj.save()
    return WebHookMapping.objects.filter(repourl=repourl, branch=branch)

def github_webhook_launch(repourl, payload):
    # github performs one POST per ref (tag/branch) touched even if they are pushed together
    refsplit = payload['ref'].split("/", 2)
    if len(refsplit) > 1:
        reftype, refname = refsplit[1:]
    else:
        print "Couldn't figure out reftype or refname"
        return

    if reftype == "tags":
    # tag
        if 'base_refs' in payload:
            branches = payload['base_refs']
        elif 'base_ref' in payload:
            branches =  [payload['base_ref'].split("/")[2]]
        else:
            # unfortunately github doesn't send info about the branch that an annotated tag is in
            # nor the commit sha1 it points at. The tag itself is enough to tell what to pull and build
            # but we wouldn't know which project / package to trigger
            # try to use the head sha1sum to detect
            print "annotated tag on %s" % repourl
            branches = []

    elif reftype == "heads":
    # commit to branch
        branches = [refname]
    else:
        print "Couldn't use payload"
        return

    print repourl
    print branches
    mapobj = None
    mapobjs = WebHookMapping.objects.filter(repourl=repourl)
    if branches:
        mapobjs = mapobjs.filter(branch__in=branches)
    print mapobjs

    zerosha = '0000000000000000000000000000000000000000'
    # action
    if payload.get('after', '') == zerosha:
        #deleted
        if reftype == "heads":
            for mapobj in mapobjs:
                # branch was deleted
                # FIXME: Notify
                # NOTE: do related objects get removed ?
                mapobj.delete()
    else:
        #created or changed
        #the head commit is either the branch's HEAD or what the tag is pointing at
        revision = None
        name = None
        if 'head_commit' in payload:
            revision = payload['head_commit']['id']
            name =  payload["pusher"]["name"]
        else:
            revision = payload['after']
            name =  payload["user_name"]

        if not revision or not name:
            return

        if not len(mapobjs):
            mapobjs = []
            for branch in branches:
                mapobjs.extend(list(create_placeholder(repourl, branch)))

        for mapobj in mapobjs:
            seenrev, created = LastSeenRevision.objects.get_or_create(mapping=mapobj)
            if created or seenrev.revision != revision:
                if branches:
                    print "%s in %s was not seen before, notify it if enabled" % (revision, mapobj.branch)
                    seenrev.revision = revision
                    seenrev.save()
                else:
                    # annotated tag. only continue if we already had a mapping with a matching
                    # revision
                    continue

            # notify new branch created or commit in branch
            if reftype == "heads":
                notified = False
                if mapobj.notify and not notified:
                    handle_commit(mapobj, name, payload)
                    notified = True

            elif reftype == "tags":
                print "Tag %s for %s in %s/%s, notify and build it if enabled" % (refname, revision, repourl, mapobj.branch)
                handle_tag(mapobj, name, payload, refname)

class bbAPIcall(object):
    def __init__(self, slug):
        self.contents = ''
        self.base = "https://api.bitbucket.org/1.0"
        self.slug = slug

    def body_callback(self, buf):
        self.contents += buf

    def api_call(self, endpoint, call):
        c = pycurl.Curl()
        c.setopt(pycurl.SSL_VERIFYPEER, 0)
        c.setopt(pycurl.SSL_VERIFYHOST, 0)
        if settings.OUTGOING_PROXY:
            c.setopt(pycurl.PROXY, settings.OUTGOING_PROXY)
            c.setopt(pycurl.PROXYPORT, settings.OUTGOING_PROXY_PORT)
        c.setopt(pycurl.NETRC, 1)
        url = str("/%s/%s/%s" % (endpoint, self.slug, call)).replace("//","/")
        url = self.base + url
        c.setopt(pycurl.URL, url)
        c.setopt(c.WRITEFUNCTION, self.body_callback)
        c.perform()
        c.close()

    def branches_tags(self):
        self.api_call('repositories', 'branches-tags')
        return json.loads(self.contents)

def bitbucket_webhook_launch(repourl, payload):
    mapobj = None
    tips = {}

    #generate pairs of branch : commits in this commit
    for comm in payload['commits']:
        if not comm['branch']:
            print "Dangling commit !" 
        else:
            if not comm['branch'] in tips:
                tips[comm['branch']] = []
            tips[comm['branch']].append(comm['raw_node'])

    if not len(tips.keys()):
        print "no tips due to empty event, calling api"
        bbcall = bbAPIcall(payload['repository']['absolute_url'])
        bts = bbcall.branches_tags()
        for branch in bts['branches']:
            print branch
            for tag in bts['tags']:
                print tag
                if tag['changeset'] == branch['changeset']:
                    print "found tagged branch"
                    tips[branch['name']] = ([branch['changeset']], tag['name'])

    print tips

    for branch, ct in tips.items():
        if isinstance(ct, tuple):
            commits = ct[0]
            tag = ct[1]
        else:
            commits = ct
            tag = None

        mapobjs = WebHookMapping.objects.filter(repourl=repourl, branch=branch)

        if not len(mapobjs):
            mapobjs = create_placeholder(repourl, branch)

        notified = False
        for mapobj in mapobjs:
            print "found or created mapping"

            seenrev, created = LastSeenRevision.objects.get_or_create(mapping=mapobj)

            if created or seenrev.revision != commits[-1]:

                print "%s in %s was not seen before, notify it if enabled" % (commits[-1], branch)
                seenrev.revision = commits[-1]
                seenrev.save()

                if mapobj.notify and not notified:
                    handle_commit(mapobj, payload["user"], payload)
                    notified = True

            else:
                print "%s in %s was seen before, notify and build it if enabled" % (commits[-1], branch)
                handle_tag(mapobj, payload["user"], payload, tag)

def github_pull_request(repourl, payload):

    branch = payload['pull_request']['base']['ref']
    data = { "url" : payload['pull_request']['html_url'],
             "source_repourl" : payload['pull_request']['head']['repo']['clone_url'],
             "source_branch" : payload['pull_request']['head']['ref'],
             "username" : payload['pull_request']['user']['login'],
             "action" : payload['action'],
             "id" : payload['number'],
         }

    for mapobj in WebHookMapping.objects.filter(repourl=repourl, branch=branch):
        handle_pr(mapobj, data, payload)

def bitbucket_pull_request(repourl, payload):
    bburl = "https://bitbucket.org"

    for key, values in payload.items():
        branch = values['destination']['branch']['name']
        source = urlparse.urljoin(bburl, values['source']['repository']['full_name'])

        data = { "url" : urlparse.urljoin(source + '/', "pull-request/%s" % values['id']),
                 "source_repourl" : source + ".git",
                 "source_branch" : values['source']['branch']['name'],
                 "username" : values['author']['username'],
                 "action" : key.replace("pullrequest_",""),
                 "id" : values['id'],
             }

    for mapobj in WebHookMapping.objects.filter(repourl=repourl, branch=branch):
        handle_pr(mapobj, data, payload)

def handle_pr(mapobj, data, payload):

    message = "Pull request #%s by %s from %s / %s to %s %s (%s)" % (
        data['id'], data['username'], data['source_repourl'],
        data['source_branch'], mapobj, data['action'], data['url'])

    if mapobj.notify:

        fields = mapobj.to_fields()
        fields['msg'] = message
        fields['payload'] = payload
        print message
        launch_notify(fields)
