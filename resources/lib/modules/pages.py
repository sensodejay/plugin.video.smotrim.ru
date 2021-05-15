# -*- coding: utf-8 -*-
# Module: pages
# Author: Alex Bratchik
# Created on: 03.04.2021
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import json
import os
import time

import xbmc
import xbmcgui
import xbmcplugin

from ..utils import remove_files_by_pattern, upnext_signal, kodi_version_major
import resources.lib.kodiplayer as kodiplayer


class Page(object):

    def __init__(self, site):
        self.site = site
        self.data = {}
        self.params = site.params
        self.action = site.action
        self.context = site.context
        self.list_items = []
        self.offset = 0
        self.limit = 0
        self.pages = 0

        self.cache_enabled = False
        self.cache_file = ""
        self.cache_expire = int(self.params['cache_expire']) if 'cache_expire' in self.params else 0

    def load(self):

        self.offset = self.params['offset'] if 'offset' in self.params else 0
        self.limit = self.get_limit_setting()

        xbmc.log("Items per page: %s" % self.limit, xbmc.LOGDEBUG)

        self.cache_file = self.get_cache_filename()

        self.data = self.get_data_query()

        self.set_context_title()

        self.set_limit_offset_pages()

        if 'data' in self.data:
            for element in self.data['data']:
                self.append_li_for_element(element)

            if self.cache_enabled and len(self.data['data']) > 0 and \
                    not (os.path.exists(self.cache_file) and not self.is_cache_expired()):
                with open(self.cache_file, 'w+') as f:
                    json.dump(self.data, f)

        if self.pages > 1:
            self.list_items.append({'id': "home",
                                    'label': "[COLOR=FF00FF00][B]%s[/B][/COLOR]" % self.site.language(30020),
                                    'is_folder': True,
                                    'is_playable': False,
                                    'url': self.site.url,
                                    'info': {'plot': self.site.language(30021)},
                                    'art': {'icon': self.site.get_media("home.png")}
                                    })
            if self.offset < self.pages - 1:
                self.list_items.append({'id': "forward",
                                        'label': "[COLOR=FF00FF00][B]%s[/B][/COLOR]" % self.site.language(30030),
                                        'is_folder': True,
                                        'is_playable': False,
                                        'url': self.get_nav_url(offset=self.offset + 1),
                                        'info': {'plot': self.site.language(30031) % (self.offset + 1, self.pages)},
                                        'art': {'icon': self.site.get_media("next.png")}
                                        })
        self.show_list_items()

    def play(self):
        pass

    def play_url(self, url, this_episode=None, next_episode=None, stream_type="video"):
        if next_episode is None:
            next_episode = {}
        if self.site.addon.getSettingBool("addhistory") and 'brands' in self.params:
            resp = self.site.request(self.site.api_url + '/brands/' + self.params['brands'], output="json")
            self.save_brand_to_history(resp['data'])

        play_item = xbmcgui.ListItem(path=url)
        if '.m3u8' in url:
            play_item.setMimeType('application/x-mpegURL')
            if kodi_version_major() >= 19:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
            else:
                play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')

        if not (this_episode is None) and 'duration' in this_episode:
            play_item.addStreamInfo(stream_type, {'duration': this_episode['duration']})

        xbmcplugin.setResolvedUrl(self.site.handle, True, listitem=play_item)

        if not self.site.addon.getSettingBool("upnext"):
            return

        # Wait for playback to start
        kodi_player = kodiplayer.KodiPlayer()
        if not kodi_player.waitForPlayBack(url=url):
            # Playback didn't start
            return

        if not (next_episode is None) and 'combinedTitle' in next_episode:
            upnext_signal(sender=self.site.id, next_info=self.get_next_info(this_episode, next_episode))

    def get_this_and_next_episode(self, episode_id):
        self.offset = self.params['offset'] if 'offset' in self.params else 0
        self.limit = self.get_limit_setting()

        self.cache_file = self.get_cache_filename()

        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r+') as f:
                self.data = json.load(f)
            for i, episode in enumerate(self.data['data']):
                if str(episode['id']) == episode_id:
                    return episode, self.data['data'][i + 1] if i < min(self.limit, len(self.data['data'])) - 1 else {}

            xbmc.log("Reached page bottom, loading next page?")
            return {}, {}
        else:
            return {}, {}

    def get_next_info(self, this_episode, next_episode):
        return {'current_episode': self.create_next_info(this_episode),
                'next_episode': self.create_next_info(next_episode),
                'play_url': self.get_play_url(next_episode)}

    def get_play_url(self, element):
        return ""

    def create_next_info(self, episode):
        """
        Returns the structure needed for service.upnext addon for playback of next episode.
        Called by get_next_info method.
        This method is to be overridden in case if the episode structure is not compatible

        @param episode:
        @return: nex_info structure for the specified episode
        """
        return {'episodeid': episode['id'],
                'tvshowid': self.params['brands'],
                'title': episode['episodeTitle'],
                'art': {'thumb': self.get_pic_from_plist(episode['pictures'], 'lw'),
                        'fanart': self.get_pic_from_plist(episode['pictures'], 'hd'),
                        'icon': self.get_pic_from_plist(episode['pictures'], 'lw'),
                        'poster': self.get_pic_from_plist(episode['pictures'], 'vhdr')
                        },
                'episode': episode['series'],
                'showtitle': episode['brandTitle'],
                'plot': episode['anons'],
                'playcount': 0,
                'runtime': episode['duration']
                }

    def create_element_li(self, element):
        return element

    def create_root_li(self):
        """
        This method can be optionally overridden if the the module class wants to expose a root-level menu.
        Usage is mainly from the lib.modules.home module.

        @return: the structure defining the list item
        """
        return {}

    def get_load_url(self):
        """
        This method is to be overridden in the child class to provide the url for querying the site. It is used in the
        get_data_query method and can be ignored if get_data_query is overriden in the child class.
        @return:
        """
        return ""

    def set_context_title(self):
        """
        This method is setting the title of the context by setting self.site.context_title attribute. Override if
        you want to create custom title, otherwise the context name will be used by default.
        """
        self.site.context_title = self.context.title()

    def get_data_query(self):
        is_refresh = 'refresh' in self.params and self.params['refresh'] == "true"

        if is_refresh:
            remove_files_by_pattern(os.path.join(self.site.data_path, "%s*.json" % self.get_cache_filename_prefix()))

        if not is_refresh and self.cache_enabled and \
                os.path.exists(self.cache_file) and not (self.is_cache_expired()):
            with open(self.cache_file, 'r+') as f:
                return json.load(f)
        else:
            return self.site.request(self.get_load_url(), output="json")

    def is_cache_expired(self):

        if self.cache_expire == 0:
            # cache never expires
            return False

        mod_time = os.path.getmtime(self.cache_file)
        now = time.time()
        delta = now - mod_time

        return delta > self.cache_expire

    def get_nav_url(self, offset=0):
        return self.site.get_url(self.site.url,
                                 action=self.site.action,
                                 context=self.site.context,
                                 limit=self.limit, offset=offset, url=self.site.url)

    def append_li_for_element(self, element):
        self.list_items.append(self.create_element_li(element))

    def get_limit_setting(self):
        return (self.site.addon.getSettingInt('itemsperpage') + 1) * 10

    def set_limit_offset_pages(self):
        if 'pagination' in self.data:
            self.offset = self.data['pagination']['offset'] if 'offset' in self.data['pagination'] else 0
            self.limit = self.data['pagination']['limit'] if 'limit' in self.data['pagination'] else 0
            self.pages = self.data['pagination']['pages'] if 'pages' in self.data['pagination'] else 0

    @staticmethod
    def get_pic_from_plist(plist, res):
        try:
            ep_pics = plist[0]['sizes'] if type(plist) is list else plist['sizes']
            pic = next(p for p in ep_pics if p['preset'] == res)
            return pic['url']
        except StopIteration:
            return ""
        except IndexError:
            return ""

    @staticmethod
    def format_date(s):
        if s:
            return "%s-%s-%s %s:%s:%s" % (s[6:10], s[3:5], s[0:2], s[11:13], s[14:16], s[17:19])
        else:
            return ""

    @staticmethod
    def get_mpaa(age):
        if age == u'':
            return 'G'
        elif age == 6:
            return 'PG'
        elif age == 12:
            return 'PG-13'
        elif age == 16:
            return 'R'
        elif age == 18:
            return 'NC-17'
        else:
            return ''

    @staticmethod
    def get_country(countries):
        if type(countries) is list and len(countries) > 0:
            return countries[0]['title']
        else:
            return ""

    @staticmethod
    def get_logo(ch, res="xxl"):
        try:
            return ch['logo'][res]['url']
        except KeyError:
            return ""

    def show_list_items(self):

        xbmcplugin.setPluginCategory(self.site.handle, self.site.context_title)

        if self.context == "home":
            xbmcplugin.setContent(self.site.handle, "files")
        else:
            xbmcplugin.setContent(self.site.handle, self.params['content'] if "content" in self.params else "videos")

        # Iterate through categories
        for category in self.list_items:
            # Create a list item with a text label and a thumbnail image.
            list_item = xbmcgui.ListItem(label=category['label'])

            url = category['url']

            is_folder = category['is_folder']
            list_item.setProperty('IsPlayable', str(category['is_playable']).lower())

            if self.cache_enabled:
                list_item.addContextMenuItems([(self.site.language(30001),
                                                "ActivateWindow(Videos, %s&refresh=true)" %
                                                self.get_nav_url(offset=0)), ])

            if 'info' in category:
                list_item.setInfo(category['type'] if 'type' in category else "video", category['info'])

            if 'art' in category:
                list_item.setArt(category['art'])

            xbmcplugin.addDirectoryItem(self.site.handle, url, list_item, is_folder)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.site.handle)

    def save_brand_to_history(self, brand):
        with open(os.path.join(self.site.history_path, "brand_%s.json" % brand['id']), 'w+') as f:
            json.dump(brand, f)

    def get_cache_filename(self):
        return os.path.join(self.site.data_path,
                            "%s_%s_%s.json" % (self.get_cache_filename_prefix(),
                                               self.limit,
                                               self.offset))

    def get_cache_filename_prefix(self):
        return self.context