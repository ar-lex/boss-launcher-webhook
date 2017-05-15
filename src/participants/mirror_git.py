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
        url_replacements = [
            ("jolla/p4903", "jolla-p4903/p4903"),
            ("mer-hybris/ngfd-plugin-pulse", "mer-core/ngfd-plugin-pulse"),
            ("mer-packages/build-compare", "mer-core/build-compare"),
            ("mer-packages/busybox", "mer-core/busybox"),
            ("mer-packages/giflib", "mer-core/giflib"),
            ("mer-packages/icu", "mer-core/icu"),
            ("mer-packages/kmod", "mer-core/kmod"),
            ("mer-packages/libcap", "mer-core/libcap"),
            ("mer-packages/libjpeg-turbo", "mer-core/libjpeg-turbo"),
            ("mer-packages/libpng15-compat", "mer-core/libpng15-compat"),
            ("mer-packages/libsignon-glib", "mer-core/libsignon-glib"),
            ("mer-packages/libsystrace", "mer-core/libsystrace"),
            ("mer-packages/libtheora", "mer-core/libtheora"),
            ("mer-packages/libxkbcommon", "mer-core/libxkbcommon"),
            ("mer-packages/libyaml", "mer-core/libyaml"),
            ("mer-packages/pacrunner", "mer-core/pacrunner"),
            ("mer-packages/pygobject2", "mer-core/pygobject2"),
            ("mer-packages/python-docutils", "mer-core/python-docutils"),
            ("mer-packages/python-jinja2", "mer-core/python-jinja2"),
            ("mer-packages/python-markupsafe", "mer-core/python-markupsafe"),
            ("mer-packages/python-pygments", "mer-core/python-pygments"),
            ("mer-packages/python-sphinx", "mer-core/python-sphinx"),
            ("mer-packages/repomd-pattern-builder", "mer-core/repomd-pattern-builder"),
            ("mer-packages/rfkill", "mer-core/rfkill"),
            ("mer-packages/ruby", "mer-core/ruby"),
            ("mer-packages/sbc", "mer-core/sbc"),
            ("mer-packages/wayland", "mer-core/wayland"),
            ("mer-packages/zlib", "mer-core/zlib"),
            ("nemomobile/buteo-syncml", "mer-core/buteo-syncml"),
            ("nemomobile/eventfeed", "mer-core/eventfeed"),
            ("nemomobile/fftune", "mer-core/fftune"),
            ("nemomobile/git", "mer-core/git"),
            ("nemomobile/libaudioresource", "mer-core/libaudioresource"),
            ("nemomobile/libaudioresource-qt", "mer-core/libaudioresource-qt"),
            ("nemomobile/libbluez-qt", "mer-core/libbluez-qt"),
            ("nemomobile/libprofile-qt", "mer-core/libprofile-qt"),
            ("nemomobile/libprolog", "mer-core/libprolog"),
            ("nemomobile/libshadowutils", "mer-core/libshadowutils"),
            ("nemomobile/libwspcodec", "mer-core/libwspcodec"),
            ("nemomobile/mapplauncherd-booster-qtcomponents", "mer-core/mapplauncherd-booster-qtcomponents"),
            ("nemomobile/nemo-control-panel-applets", "mer-core/nemo-control-panel-applets"),
            ("nemomobile/nemo-gst-interfaces", "mer-core/nemo-gst-interfaces"),
            ("nemomobile/nemo-qml-plugin-accounts", "mer-core/nemo-qml-plugin-accounts"),
            ("nemomobile/nemo-qml-plugin-connectivity", "mer-core/nemo-qml-plugin-connectivity"),
            ("nemomobile/nemo-qml-plugin-signon", "mer-core/nemo-qml-plugin-signon"),
            ("nemomobile/nemo-theme-default", "mer-core/nemo-theme-default"),
            ("nemomobile/obex-capability", "mer-core/obex-capability"),
            ("nemomobile/ohm", "mer-core/ohm"),
            ("nemomobile/ohm-rule-engine", "mer-core/ohm-rule-engine"),
            ("nemomobile-packages/aspell", "mer-core/aspell"),
            ("nemomobile-packages/aspell-en", "mer-core/aspell-en"),
            ("nemomobile-packages/bluez-hcidump", "mer-core/bluez-hcidump"),
            ("nemomobile-packages/btrfs-progs", "mer-core/btrfs-progs"),
            ("nemomobile-packages/calligra-extra-cmake-modules", "mer-core/calligra-extra-cmake-modules"),
            ("nemomobile-packages/dbus-python3", "mer-core/dbus-python3"),
            ("nemomobile-packages/eigen2", "mer-core/eigen2"),
            ("nemomobile-packages/enchant", "mer-core/enchant"),
            ("nemomobile-packages/fbset", "mer-core/fbset"),
            ("nemomobile-packages/geoclue", "mer-core/geoclue"),
            ("nemomobile-packages/hunspell", "mer-core/hunspell"),
            ("nemomobile-packages/iotop", "mer-core/iotop"),
            ("nemomobile-packages/libcanberra", "mer-core/libcanberra"),
            ("nemomobile-packages/libenca", "mer-core/libenca"),
            ("nemomobile-packages/libgdata", "mer-core/libgdata"),
            ("nemomobile-packages/libgee", "mer-core/libgee"),
            ("nemomobile-packages/liboauth", "mer-core/liboauth"),
            ("nemomobile-packages/libopenal", "mer-core/libopenal"),
            ("nemomobile-packages/libquazip", "mer-core/libquazip"),
            ("nemomobile-packages/libquvi", "mer-core/libquvi"),
            ("nemomobile-packages/libquvi-scripts", "mer-core/libquvi-scripts"),
            ("nemomobile-packages/librest", "mer-core/librest"),
            ("nemomobile-packages/libsdl-gfx", "mer-core/libsdl-gfx"),
            ("nemomobile-packages/libsdl-image", "mer-core/libsdl-image"),
            ("nemomobile-packages/libsdl-mixer", "mer-core/libsdl-mixer"),
            ("nemomobile-packages/libsdl-net", "mer-core/libsdl-net"),
            ("nemomobile-packages/libsdl-ttf", "mer-core/libsdl-ttf"),
            ("nemomobile-packages/libwbxml2", "mer-core/libwbxml2"),
            ("nemomobile-packages/lsof", "mer-core/lsof"),
            ("nemomobile-packages/maliit-plugins", "mer-core/maliit-plugins"),
            ("nemomobile-packages/openobex", "mer-core/openobex"),
            ("nemomobile-packages/polkit-qt-1", "mer-core/polkit-qt-1"),
            ("nemomobile-packages/protobuf", "mer-core/protobuf"),
            ("nemomobile-packages/python3", "mer-core/python3"),
            ("nemomobile-packages/python3-cairo", "mer-core/python3-cairo"),
            ("nemomobile-packages/python3-gobject", "mer-core/python3-gobject"),
            ("nemomobile-packages/python-openssl", "mer-core/python-openssl"),
            ("nemomobile-packages/python-twisted", "mer-core/python-twisted"),
            ("nemomobile-packages/python-zope-interface", "mer-core/python-zope-interface"),
            ("nemomobile-packages/recode", "mer-core/recode"),
            ("nemomobile-packages/screen", "mer-core/screen"),
            ("nemomobile-packages/signon-plugin-oauth2", "mer-core/signon-plugin-oauth2"),
            ("nemomobile-packages/smpeg", "mer-core/smpeg"),
            ("nemomobile-packages/sound-theme-freedesktop", "mer-core/sound-theme-freedesktop"),
            ("nemomobile-packages/swi-prolog", "mer-core/swi-prolog"),
            ("nemomobile-packages/telepathy-gabble", "mer-core/telepathy-gabble"),
            ("nemomobile-packages/telepathy-mission-control", "mer-core/telepathy-mission-control"),
            ("nemomobile-packages/telepathy-rakia", "mer-core/telepathy-rakia"),
            ("nemomobile-packages/uthash", "mer-core/uthash"),
            ("nemomobile-packages/vala", "mer-core/vala"),
            ("nemomobile/pacrunner-cutes", "mer-core/pacrunner-cutes"),
            ("nemomobile/profiled", "mer-core/profiled"),
            ("nemomobile/qml-rpm-macros", "mer-core/qml-rpm-macros"),
            ("nemomobile/qmsystem", "mer-core/qmsystem"),
            ("nemomobile/qt-components", "mer-core/qt-components"),
            ("nemomobile/statefs", "mer-core/statefs"),
            ("nemomobile/systemd-user-session-targets", "mer-core/systemd-user-session-targets"),
            ("nemomobile/telepathy-accounts-signon", "mer-core/telepathy-accounts-signon"),
            ("nemomobile/the-vault", "mer-core/the-vault"),
            ("nemomobile/tone-generator", "mer-core/tone-generator"),
            ("nemomobile/tumbler", "mer-core/tumbler"),
            ("nemomobile/tut", "mer-core/tut"),
            ("nemomobile/vmtouch", "mer-core/vmtouch"),
            ("sailfishos/vo-aacenc", "mer-core/vo-aacenc")
        ]
        if upstream_url.startswith("git@"):
            upstream_url = "ssh://" + upstream_url[::-1].replace(':','/',1)[::-1]
        upstream_parsed_url = urlparse.urlparse(upstream_url)
        mirror_parsed_url = upstream_parsed_url._replace(
            scheme = "https",
            netloc = "git.omprussia.ru",
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
