# Copyright (C) 2017 Jolla Ltd.
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
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""Used to mirror a git repository

:term:`Workitem` fields IN:

:Parameters:
   :mirror_repourl (str):
      Url of git repository to mirror

:term:`Workitem` fields OUT:

:Returns:
   :result (Boolean):
      True if the everything went OK, False otherwise

"""


import os
import urlparse

from mirror_git_data import *

class ParticipantHandler(object):
    """ Participant class as defined by the SkyNET API """

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        pass

    def handle_wi(self, wid):
        """ Workitem handling function """
        wid.result = False

        if wid.fields.mirror_repourl is None:
            raise RuntimeError("Missing mandatory field: mirror_repourl")

        upstream_url = wid.fields.mirror_repourl
        self.log.info("Mirroring %s" % upstream_url)
        GITBASE = os.environ["HOME"] + "/mirror_git"
        if upstream_url.startswith("git@"):
            upstream_url = "ssh://" + upstream_url[::-1].replace(':','/',1)[::-1]
        upstream_parsed_url = urlparse.urlparse(upstream_url)
        mirror_parsed_url = upstream_parsed_url._replace(
            scheme = mirror_scheme,
            netloc = mirror_netloc,
            path = reduce(lambda a, b: a.replace(*b), url_replacements, upstream_parsed_url.path)
        )
        mirror_url = mirror_parsed_url.geturl()
        mirror_path = os.path.join(
            GITBASE,
            upstream_parsed_url.netloc,
            upstream_parsed_url.path.strip("/")
        )

        if not os.system("git ls-remote %s" % upstream_url) == 0:
            raise RuntimeError("Failed to read mirroring source: %s" % upstream_url)

        if not os.system("git ls-remote %s" % mirror_url) == 0:
            raise RuntimeError("Failed to read mirroring target: %s" % mirror_url)

        if not os.path.exists(mirror_path):
            os.makedirs(mirror_path)
            os.chdir(mirror_path)
            os.system("git --bare init")
            os.system("git remote add mirror %s" % mirror_url)
            os.system("git remote add upstream %s" % upstream_url)
        else:
            os.chdir(mirror_path)
            os.system("git remote set-url mirror %s" % mirror_url)
            os.system("git remote set-url upstream %s" % upstream_url)

        os.system("git remote update mirror")
        os.system("git remote update upstream")
        os.system("cp -rf refs/remotes/upstream/* refs/heads/")

        if not os.system("git push mirror 'refs/tags/*' 'refs/heads/*'") == 0:
            raise RuntimeError("Failed to push to mirroring target: %s" % mirror_url)

        wid.result = True
