# -*- coding: utf-8 -*-
"""Orange France"""
from datetime import date, datetime
import json
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from lib.providers.provider_interface import ProviderInterface
from lib.types import DRM
from lib.utils import log, random_ua

class OrangeFranceProvider(ProviderInterface):
    """Orange France provider"""
    chunks_per_day: int = 2
    drm: DRM = DRM.WIDEVINE
    groups: dict = {
        'TNT': [192, 4, 80, 34, 47, 118, 111, 445, 119, 195, 446, 444, 234, 78, 481, 226, 458, 482, 3163, 1404, 1401,
                1403, 1402, 1400, 1399, 112, 2111],
        'Généralistes': [205, 191, 145, 115, 225]
    }

    # pylint: disable=line-too-long
    def get_stream_info(self, channel_id: int) -> dict:
        endpoint = 'https://mediation-tv.orange.fr/all/live/v3/applications/PC/users/me/channels/{channel_id}/stream?terminalModel=WEB_PC'

        req = Request(endpoint.format(channel_id=channel_id), headers={
            'User-Agent': random_ua(),
            'Host': urlparse(endpoint).netloc
        })

        try:
            res = urlopen(req)
            stream_info = json.loads(res.read())
        except HTTPError as error:
            if error.code == 403:
                return False

        license_server_url = None
        for system in stream_info.get('protectionData'):
            if system.get('keySystem') == self.drm.value:
                license_server_url = system.get('laUrl')

        headers = 'Content-Type=&User-Agent={}&Host={}'.format(random_ua(), urlparse(license_server_url).netloc)
        post_data = 'R{SSM}'
        response = ''

        stream_info = {
            'path': stream_info['url'],
            'mime_type': 'application/xml+dash',
            'manifest_type': 'mpd',
            'drm': self.drm.name.lower(),
            'license_type': self.drm.value,
            'license_key': '{}|{}|{}|{}'.format(license_server_url, headers, post_data, response)
        }

        log(stream_info, 'debug')
        return stream_info

    def get_streams(self) -> list:
        endpoint = 'https://mediation-tv.orange.fr/all/live/v3/applications/PC/channels'

        req = Request(endpoint, headers={
            'User-Agent': random_ua(),
            'Host': urlparse(endpoint).netloc
        })

        res = urlopen(req)
        channels = json.loads(res.read())
        streams = []

        for channel in channels:
            streams.append({
                'id': channel['id'],
                'name': channel['name'],
                'preset': channel['zappingNumber'],
                'logo': channel['logos']['square'],
                'stream': 'plugin://plugin.video.orange.fr/channel/{id}'.format(id=channel['id']),
                'group': [group_name for group_name in self.groups if int(channel['id']) in self.groups[group_name]]
            })

        return streams

    def get_epg(self, days: int) -> dict:
        today = datetime.timestamp(datetime.combine(date.today(), datetime.min.time()))
        chunk_duration = 24 * 60 * 60 / self.chunks_per_day

        programs = []

        for chunk in range(0, days * self.chunks_per_day):
            programs.extend(self._get_programs(
                period_start=(today + chunk_duration * chunk) * 1000,
                period_end=(today + chunk_duration * (chunk + 1)) * 1000
            ))

        epg = {}

        for program in programs:
            if not program['channelId'] in epg:
                epg[program['channelId']] = []

            start = datetime.fromtimestamp(program['diffusionDate']).astimezone().replace(microsecond=0)
            stop = datetime.fromtimestamp(program['diffusionDate'] + program['duration']).astimezone()

            if program['programType'] != 'EPISODE':
                title = program['title']
                subtitle = None
                episode = None
            else:
                title = program['season']['serie']['title']
                subtitle = program['title']
                episode = 'S{s}E{e}'.format(s=program['season']['number'], e=program['episodeNumber'])

            image = None
            if isinstance(program['covers'], list):
                for cover in program['covers']:
                    if cover['format'] == 'RATIO_16_9':
                        image = program['covers'][0]['url']

            epg[program['channelId']].append({
                'start': start.isoformat(),
                'stop': stop.isoformat(),
                'title': title,
                'subtitle': subtitle,
                'episode': episode,
                'description': program['synopsis'],
                'genre': program['genre'] if program['genreDetailed'] is None else program['genreDetailed'],
                'image': image
            })

        return epg

    # pylint: disable=no-self-use
    def _get_programs(self, period_start: int = None, period_end: int = None) -> list:
        """Returns the programs for today (default) or the specified period"""
        endpoint = 'https://mediation-tv.orange.fr/all/live/v3/applications/PC/programs?period={period}&mco=OFR'

        if period_start is int and period_end is int:
            period = '{start},{end}'.format(start=period_start, end=period_end)
        else:
            period = 'today'

        req = Request(endpoint.format(period=period), headers={
            'User-Agent': random_ua(),
            'Host': urlparse(endpoint).netloc
        })

        res = urlopen(req)
        return json.loads(res.read())