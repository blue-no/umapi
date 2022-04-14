"""プリンタとのHTTP通信及び取得データ蓄積のためのバックエンドプログラム.

HttpSenderクラス経由で取得したデータをRecordクラスに蓄積する. HttpSenderクラスメソッ
ドで指定可能なURLはUltimaker API Swagger UIを参照.
"""

import json
import os
from typing import Any, Dict

import pandas as pd
import requests
from requests.auth import HTTPDigestAuth

from . import log
from . import utils


logger = log.get_logger()


class Record:
    """プリンタ本体から取得したセンサ値を蓄積する. 一定通信回数毎に記録をcsv形式で書
    き出す.

    Parameters
    ----------
        sender: 通信を確立したHttpSenderインスタンス
        savedir: 記録を書き出すディレクトリ
        push_lines: csvに書き出すデータ数のインターバル
    """
    def __init__(
        self, sender: 'HttpSender', savedir: str, push_lines: int = 10
    ) -> None:
        self.sender = sender
        self.savedir = savedir
        self.push_lines = push_lines
        self.autopush_enabled = True
        self._push_count = 0
        self._is_first_push = True

    def read_watchlist(self, watchlist_file: str) -> None:
        """プリンタ本体のセンサ値のうち, 監視対象を読み込み登録する.

        Parameters
        ----------
            watchlist_file: 監視対象とそのURLが記載されたjsonファイル名
        """
        self.watchlist = utils.read_json(watchlist_file)
        self._init_values()

    def update(self) -> None:
        """最新のセンサ値を取得し, 一定回数毎に記録を書き出す."""
        logger.debug('Updating record...')
        self._fetch_latest_values()
        if self.autopush_enabled:
            self._push_count += 1
        if self._push_count > self.push_lines:
            self.push()
            self._push_count = 0
        logger.debug('Updated record')

    def push(self) -> None:
        """蓄積したセンサ値をcsvファイルに書き出す."""
        logger.debug('Pushing record...')
        data = self._pop_values()
        self._export(data)
        logger.debug('Pushed record')

    def _init_values(self) -> None:
        values = {'time': []}
        for target in self.watchlist:
            for item in target['items']:
                values[item['name']] = []
        self.values = values
        logger.debug('Initialized record')

    def _fetch_latest_values(self) -> None:
        curtime = utils.timestamp()
        self.values['time'].append()
        for target in self.watchlist:
            value = self.sender.get(target['url'])
            for item in target['items']:
                key, name = item['key'], item['name']
                if self.autopush_enabled:
                    self._append(value, key, name)
                else:
                    self._replace(value, key, name)
        logger.debug(f'Fetched latest values at {curtime}')

    def _append(self, value: Any, key: str, name: str) -> None:
        if key is None:
            self.values[name].append(value)
        else:
            self.values[name].append(value[key])

    def _replace(self, value: Any, key: str, name: str) -> None:
        try:
            if key is None:
                self.values[name][-1] = value
            else:
                self.values[name][-1] = value[key]
        except IndexError:
            self._append(value, key, name)

    def _pop_values(self) -> None:
        popped = {}
        poplen = self.push_lines - 1
        for name, history in self.values.items():
            popped[name] = history[:poplen]
            del history[:poplen]
        logger.debug(f'Popped values: length={poplen}')
        return popped

    def _export(self, data: Dict[str, list]) -> None:
        if self._is_first_push:
            mode = 'w'
            header = True
            self._is_first_push = False
        else:
            mode = 'a'
            header = False
        os.makedirs(self.savedir, exist_ok=True)
        path = os.path.join(self.savedir, 'sensor_record.csv')
        pd.DataFrame(data).to_csv(path, mode=mode, header=header, index=False)
        logger.debug('Exported values as csv')


class HttpSender:
    """プリンタにHTTPリクエストを送信し, 情報を受信する."""

    def __init__(self) -> None:
        self.headers = {'Content-type': 'application/json'}

    def read_config(self, config_file: str) -> None:
        """通信情報を読み込む.

        Parameters
        ----------
            config_file: プリンタ本体との接続情報が書かれたjsonファイル名
        """
        config = utils.read_json(config_file)
        self.base_url = config['base_url']
        self.auth = HTTPDigestAuth(config['id'], config['key'])

    def verify(self) -> bool:
        """プリンタ本体との接続の可否を検証する.

        Returns
        -------
            認証の可否を示すbool値
                Falseの場合Swagger UI上で認証プロセスをやり直し, idとpassを書き換え
                る必要がある.
        """
        res = self.get('auth/verify')
        if res['message'] == 'ok':
            logger.info('Access permitted')
            return True
        logger.warning('Access denied')
        return False

    def get(self, url: str) -> requests.Response:
        """GETリクエスト. 情報取得に使用する."""
        logger.debug(f'Get: "{url}"')
        res = requests.get(self.base_url + url, auth=self.auth)
        return self._response(res)

    def put(self, url: str, data: Dict[str, Any]) -> requests.Response:
        """PUTリクエスト. プリンタ本体の設定変更に使用する."""
        logger.debug(f'Put: "{url}"')
        res = requests.put(
            self.base_url + url, data=json.dumps(data), auth=self.auth,
            headers=self.headers)
        return self._response(res)

    def post(self, url: str, data: Any) -> requests.Response:
        """POSTリクエスト. ファイル送信に使用する."""
        logger.debug(f'Post: "{url}"')
        res = requests.post(
            self.base_url + url, files=data, auth=self.auth)
        return self._response(res)

    def _response(self, res: requests.Response) -> dict:
        errorcode = str(res.status_code).startswith('4')
        if errorcode or not res.content:
            return None
        resj = res.json()
        return resj
