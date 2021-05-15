# -*- coding: utf-8 -*-
# Module: audios
# Author: Alex Bratchik
# Created on: 03.04.2021
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import resources.lib.modules.pages as pages

from ..utils import clean_html


class Audio(pages.Page):
    def __init__(self, site):
        super(Audio, self).__init__(site)
        self.cache_enabled = True

    def get_load_url(self):
        return self.site.get_url(self.site.api_url + '/audios',
                                 brands=self.params['brands'],
                                 limit=self.limit,
                                 offset=self.offset,
                                 sort="dasc")

    def set_context_title(self):
        if 'data' in self.data:
            self.site.context_title = self.data['data'][0]['brandTitle'] \
                if len(self.data['data']) > 0 else self.site.language(30040)

    def get_nav_url(self, offset=0):
        return self.site.get_url(self.site.url,
                                 action="load",
                                 context="audios",
                                 content=self.params['content'],
                                 brands=self.params['brands'],
                                 limit=self.limit, offset=offset, url=self.site.url)

    def create_element_li(self, element):
        return {'id': element['id'],
                'label': element['title'],
                'is_folder': False,
                'is_playable': True,
                'url': self.get_play_url(element),
                'type': "video",
                'info': {'title': element['title'],
                         'originaltitle': element['title'],
                         'sorttitle': element['title'],
                         'tvshowtitle': element['brandTitle'],
                         'mediatype': "episode",
                         'episode': element['series'],
                         'dateadded': self.format_date(element['datePub']),
                         'duration': element['duration'],
                         'plot': "%s[CR]%s" % (element['title'], element['anons'])},
                'art': {'fanart': self.get_pic_from_plist(element['pictures'], 'hd'),
                        'icon': self.get_pic_from_plist(element['pictures'], 'lw'),
                        'thumb': self.get_pic_from_plist(element['pictures'], 'lw'),
                        'poster': self.get_pic_from_plist(element['pictures'], 'vhdr')
                        }
                }

    def play(self):
        spath = self.params['spath']

        this_audio, next_audio = self.get_this_and_next_episode(self.params['audios'])

        self.play_url(spath, this_audio, next_audio, stream_type="audio")

    def get_play_url(self, element):
        return self.site.get_url(self.site.url,
                                 action="play",
                                 context="audios",
                                 brands=element['brandId'],
                                 audios=element['id'],
                                 offset=self.offset,
                                 limit=self.limit,
                                 spath=element['sources']['mp3'],
                                 url=self.site.url)

    def get_cache_filename_prefix(self):
        return "brand_audios_%s" % self.params['brands']

