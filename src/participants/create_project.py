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

"""Used to create a new OBS (sub)project if needed for trigger_service :

:term:`Workitem` fields IN:

:Parameters:
   :ev.namespace (string):
      Used to contact the right OBS instance.
   :project (string):
      Optional OBS project to create
   
:term:`Workitem` params IN

:Parameters:
   :project (string):
      Optional OBS project in which the package lives, overrides the project field

:term:`Workitem` fields OUT:

:Returns:
   :result (Boolean):
      True if the everything went OK, False otherwise

"""

from boss.obs import BuildServiceParticipant
import osc
from urlparse import urlparse
import os
from lxml import etree

os.environ['DJANGO_SETTINGS_MODULE'] = 'webhook_launcher.settings'

from webhook_launcher.app.models import WebHookMapping

class ParticipantHandler(BuildServiceParticipant):
    """ Participant class as defined by the SkyNET API """

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    @BuildServiceParticipant.get_oscrc
    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        pass

    def get_repolinks(self, wid, project):
        """Get a description of the repositories to link to.
           Returns a dictionary where the repository names are keys
           and the values are lists of architectures."""
        exclude_repos = wid.fields.exclude_repos or []
        exclude_archs = wid.fields.exclude_archs or []
    
        repolinks = {}
        prjmeta = etree.fromstring(self.obs.getProjectMeta(project))

        for repoelem in prjmeta.findall('repository'):
            repo = repoelem.get('name')
            if repo in exclude_repos:
                continue
            repolinks[repo] = []
            for archelem in repoelem.findall('arch'):
                arch = archelem.text
                if arch in exclude_archs:
                    continue
                repolinks[repo].append(arch)
            if not repolinks[repo]:
                del repolinks[repo]
        return repolinks

    @BuildServiceParticipant.setup_obs
    def handle_wi(self, wid):
        """ Workitem handling function """
        wid.result = True
        f = wid.fields
        p = wid.params

        project = p.project or f.project
        package = p.package or f.package
        maintainers = []
        links = []
        repos = []
        paths = []
        repolinks = {}

        project_list = self.obs.getProjectList()
        if project:
            if project in project_list:
                # project already exists, don't do anything
                return

            prj_parts = project.split(":")
            if prj_parts[0] == "home" and len(prj_parts) > 1:
                maintainers.append(project.split(":")[1])
                #TODO: construct repos and build paths for a devel build

            # support "updateX" subprojects by creating a link to the parent
            if prj_parts[-1].startswith("update"):
                link = ":".join(prj_parts[0:-1])
                if link in project_list:
                    links.append(link)
                    repolinks.update(self.get_repolinks(wid, link))
                    #TODO: append link maintaianers ?

        #else:
        #TODO: deduce project name from "official" mappings of the same repo

        result = self.obs.createProject(project, repolinks, 
                                        links=links, maintainers=maintainers)

        if not result:
            raise RuntimeError("Something went wrong while creating project %s" % project)

        wid.result = True