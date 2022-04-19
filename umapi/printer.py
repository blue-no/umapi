"""backend.pyのプログラムをラップし, プリンタ本体の操作及びモニタリングを行うための
インターフェースプログラム.
"""

from contextlib import contextmanager
import os
import threading
import time
from typing import List, Tuple, Union

import numpy as np

from . import log
from .backend import HttpSender, Record
from . import utils
from .exceptions import ConnectionError, SensingError, MonitoringError


UMCONFIG = utils.abspath("./json/umconfig.json", __file__)
WATCHLIST = utils.abspath("./json/watchlist.json", __file__)
sender = HttpSender()
logger = log.get_logger()


def establish_connection() -> None:
    """プリンタ本体との通信を確立する(一番初めに実行).

    Raises
    ------
        接続エラー
            プリンタに接続できなかった場合. 同じネットワーク内かどうか要確認.
    """
    sender.read_config(UMCONFIG)
    if not sender.verify():
        raise ConnectionError('Unable to access the printer')
    logger.info('Established connection')


def send_job(job_file: str) -> None:
    """手元のufpまたはgcodeファイルを送信し印刷を開始する.

    Parameters
    ----------
        job_file: 造形物ファイルのパス
    """
    logger.info(f'Sending {job_file} ...')
    ext = os.path.splitext(job_file)[1]
    if ext not in ('.gcode', '.ufp'):
        raise Exception(
            'Invalid file format. Extention must be ".gcode" or ".ufp"')

    with open(job_file, 'rb') as obj:
        data = {
            'job_name': os.path.basename(job_file),
            'file': obj
        }
        sender.post('print_job', data)


def pause() -> None:
    """印刷を一時中断する."""
    logger.info('Pausing job...')
    sender.put('print_job/state', {'target': 'pause'})


def abort() -> None:
    """印刷を止めジョブを破棄する."""
    logger.info('Aborting job...')
    sender.put('print_job/state', {'target': 'abort'})


def resume() -> None:
    logger.info('Resuming job...')
    """印刷を再開する（印刷が一時中断中の場合に限る）."""
    sender.put('print_job/state', {'target': 'print'})


def change_hotendtemp(target: float) -> None:
    """ホットエンドの温度を変更する.

    Parameters
    ----------
        target: 目標温度 [C]
    """
    sender.put(
        'printer/heads/0/extruders/0/hotend/temperature/target', target)
    logger.info(f'Changed hotend target temperature to {target}')


def change_bedtemp(target: float) -> None:
    """ビルドプレートの温度を変更する.

    Parameters
    ----------
        target: 目標温度 [C]
    """
    sender.put('printer/bed/temperature', target)
    logger.info(f'Changed bed target temperature to {target}')


def change_brightness(target: int) -> None:
    """LEDの明るさを変更する.

    Parameters
    ----------
        target: 変更後の明度 [%]
    """
    sender.put('printer/led/brightness', target)
    logger.info(f'Changed led brightness to {target}')


def change_maxspeed(target: int) -> None:
    """速さの最大値を変更する.

    Parameters
    ----------
        target: 速さの最大値 [mm/s]
    """
    sender.put('printer/heads/0/max_speed', {"x": target, "y": target})
    logger.info(f'Changed max speed to {target}')


class SensingLoop:
    """プリンタ情報及びセンサ値をループ取得する.

    Parameters
    ----------
        record: Recordインスタンス
        watch_interval: 取得する時間間隔 [sec]
    """
    def __init__(self, record: 'Record', watch_interval: float) -> None:
        self.record = record
        self.watch_interval = watch_interval
        self._is_alive_thread = True
        self._is_updated = False

    @contextmanager
    def start(self) -> None:
        """ループを開始する. with文から抜けると終了処理を行うので注意"""
        try:
            self._setup()
            self._is_alive_thread = True
            self._thread.start()
            logger.info('Entered acquisition loop')
            yield

        finally:
            self._is_alive_thread = False
            logger.info('Exiting acquisition loop...')
            while self._thread.is_alive():
                self._thread.join()
            self.record.push()
            logger.info('Exited acquisition loop')

    def fetch_latest(
        self, *args: Union[List[str], str]
    ) -> Union[Tuple[Union[float, int, str]], Union[float, int, str], None]:
        """最新の情報及びセンサ値を返す. 値が古い場合は更新を待機する.

        Parameters
        ----------
            args: 取得するセンサ値の名前
                複数列挙可能. json/watchlist.jsonのitems内のnameを指定

        Returns
        -------
            最新の情報及び値
                argsにおいて複数指定した場合は, 同順のタプル
        """
        logger.debug(f'Fetching sensor values: {args}')
        while not self._is_updated:
            time.sleep(0.1)
        values = self.record.values
        self._is_updated = False

        vlist = []
        for key in args:
            try:
                vlist.append(values[key][-1])
            except KeyError:
                raise SensingError(f'"{key}" not in watchlist')

        length = len(vlist)
        if length == 0:
            return None
        elif length == 1:
            return vlist[0]
        else:
            return tuple(vlist)

    def _setup(self) -> None:
        self.record.read_watchlist(WATCHLIST)

        def _mainloop() -> None:
            while self._is_alive_thread:
                t1 = time.perf_counter()
                self.record.update()
                self._is_updated = True
                t2 = time.perf_counter()
                logger.debug(f'Acquisition time: {t2-t1:.3f} s')
                time.sleep(max(self.watch_interval-(t2-t1), 0))

        self._thread = threading.Thread(target=_mainloop)


class Monitor(SensingLoop):
    """プリンタのモニタリングを行う.

    モニタリング対象を変更する場合は, "watchlist.json"を編集.

    Parameters
    ----------
        savedir: センサ値を保存するディレクトリ
    """
    def __init__(self, savedir: str) -> None:
        self.record = Record(sender, savedir)
        super().__init__(self.record, watch_interval=1.0)
        self.layer_pitch = 0.2  # [mm]
        self.hotendtemp_diff_thresh = 2.0  # [C]
        self.record.autopush_enabled = False
        self._z_pre = 0.0

    def start_recording(self) -> None:
        """センサ値のファイル出力を有効化する."""
        self.record.autopush_enabled = True
        logger.info('Started sensor history output')

    def stop_recording(self) -> None:
        """センサ値のファイル出力を無効化する."""
        self.record.autopush_enabled = False
        logger.info('Stopped sensor history output')

    def wait_printstart(self) -> None:
        """プリンタが印刷を開始するまで待機する."""
        logger.info('Waiting for printing to start...')
        is_preparing = False
        while True:
            state = self.fetch_latest('state')
            if is_preparing and state == 'none':
                raise MonitoringError('Active leveling failed')
            elif not is_preparing and state == 'pre_print':
                is_preparing = True
            elif state == 'printing':
                time.sleep(6)
                break
        logger.info('Started')

    def count_layers(self, n: int = np.inf) -> int:
        """指定した層数に渡り, 新しい層の印刷が始まったタイミングで層カウントを返す.

        Parameters
        ----------
            n: 層カウント数
                デフォルトは無制限.
        """
        logger.info(f'Counting layers: {n}')
        i = 0
        while True:
            state, z_cur = self.fetch_latest('state', 'z')
            if state != 'printing':
                raise MonitoringError('Not printing')

            if abs(self._z_pre - z_cur) > 1e-4:
                logger.info(f'Layer: {i}')
                yield i
                i += 1
                if i >= n:
                    break
            self._z_pre = z_cur

    def wait_hotendtemp_reach(self, target: float) -> None:
        """ホットエンドが目標温度に近づくまで待機する.

        正確には現在温度と目標温度の差の絶対値が閾値以内になるまで待機する.

        Parameters
        ----------
            target: 目標温度 [C]
        """
        logger.info(f'Waiting for hotend temperature to reach {target}')
        while True:
            state, temp = self.fetch_latest('state', 'hotendtemp_current')
            if state != 'printing':
                raise MonitoringError('Not printing')

            if abs(temp - target) < self.hotendtemp_diff_thresh:
                break
        logger.info('Temperature reached')

    def wait_layer_reach(self, target: int) -> None:
        """印刷層が目標の層に到達するまで待機する.

        Parameters
        ----------
            target: 目標の層
        """
        logger.info(f'Waiting for layer to reach {target}')
        while True:
            state, z = self.fetch_latest('state', 'z')
            if state != 'printing':
                raise MonitoringError('Not printing')

            layer = int(z / self.layer_pitch)
            if layer >= target:
                break
        logger.info('Layer reached')
