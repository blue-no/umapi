"""カメラストリーミングを別スレッドで起動し, フレームの取得と保存を行うプログラム."""

from contextlib import contextmanager
import os
from PIL import Image

import cv2
import numpy as np
from threading import Thread
from typing import Optional

from . import log
from . import utils


CALIBPARAM_FILE = utils.abspath("./calibparams.npz", __file__)
logger = log.get_logger()


class CameraStream:
    """カメラフレームを連続的に取得, 表示する.

    Parameters
    ----------
        savedir: 取得フレームを保存するディレクトリ
        cam_id: カメラID
            インカメと外付けカメラで番号が違う.
    """
    def __init__(self, savedir: str, cam_id: int = 0) -> None:
        logger.info('Launching camera...')
        self.savedir = savedir
        self.capture = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
        self.is_stream_alive = True
        self._stream_thread = True

    @contextmanager
    def start(self, undistort: bool = False) -> None:
        """新規ウィンドウにてストリーミングを開始する. with文から抜けると終了処理を
        行うので注意.

        Parameters
        ----------
            undistort: 歪み補正を行うか否か
        """
        if undistort:
            calib = Calibration(CALIBPARAM_FILE)
            logger.info('Enabled undistortion')
        try:
            def stream() -> None:
                logger.info('Streaming started')

                while self.is_stream_alive:
                    frame = self.capture.read()[1]
                    if frame is not None and undistort:
                        frame = calib.undistort(frame)
                    cv2.imshow(f'stream', frame)
                    self.frame = frame
                    cv2.waitKey(10)

                logger.info('Closing camera...')
                self.is_stream_alive = False

            self.is_stream_alive = True
            self._stream_thread = Thread(target=stream)
            self._stream_thread.start()
            yield

        finally:
            self.is_stream_alive = False
            self._stream_thread.join()
            self.capture.release()
            cv2.destroyAllWindows()
            logger.info('Closed camera')

    def fetch(self, label: Optional[str] = None) -> np.ndarray:
        """現在のフレームを取得, 保存する.

        Parameters
        ----------
            label: 画像の保存名
                指定しなければ取得時刻となる.

        Returns
        -------
            取得フレーム
        """
        logger.info(f'Fetching frame...')
        frame = self.frame
        if label is None:
            label = utils.formatted_now()
        self._save(frame, label)
        return frame

    def _save(self, frame: np.ndarray, label: str) -> None:
        os.makedirs(self.savedir, exist_ok=True)
        path = os.path.join(self.savedir, f"cam-{label}.png")
        Image.fromarray(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).save(path)
        logger.debug('Saved frame')


class Calibration:
    """カメラ画像の歪みを補正する.

    Parameters
    ----------
        fpath: 補正パラメータのnpzファイルパス
    """
    def __init__(self, fpath: str) -> None:
        npz = np.load(fpath)
        self.mtx = npz['mtx']
        self.dist = npz['dist']
        self.newcameramtx = npz['newcameramtx']
        self.roi = npz['roi']

    def undistort(self, src: np.ndarray) -> np.ndarray:
        """画像周辺の湾曲を補正する.

        Parameters
        ----------
            src: 元画像

        Returns
        -------
            補正画像
        """
        dst = cv2.undistort(src, self.mtx, self.dist, None, self.newcameramtx)
        x, y, w, h = self.roi
        return dst[y:y+h, x:x+w]
