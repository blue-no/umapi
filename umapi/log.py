"""モジュール間共通のロガーを生成し, ログを記録するプログラム."""

import logging
import logging.config
import os

from . import utils


LOG_CONFIG = utils.abspath("./json/logconfig.json", __file__)


def create_logger(savedir: str, verbose: int = 0) -> logging.Logger:
    """loggerにカスタム設定を適用し, モジュール共通のロガーを新規に生成する.

    Parameters
    ----------
        savedir: ログを保存するディレクトリ
        verbose: ログの詳細度(0~2)
            verbose=0: INFO以上をコンソールに出力
            verbose=1: INFO以上をコンソールとファイルに出力
            verbose=2: INFO以上をコンソール, DEBUG以上をファイルに出力

    Returns
    -------
        新規のロガー
    """
    config = utils.read_json(LOG_CONFIG)

    if verbose == 0:
        config['loggers']['main']['handlers'] = ['console']
        del config['handlers']['file']
    else:
        filepath = os.path.join(savedir, 'apilog.log')
        os.makedirs(savedir, exist_ok=True)
        if os.path.isfile(filepath):
            os.remove(filepath)
        config['loggers']['main']['handlers'] = ['console', 'file']
        config['handlers']['file']['filename'] = filepath

    if verbose <= 1:
        config['loggers']['main']['level'] = 'INFO'
    else:
        config['loggers']['main']['level'] = 'DEBUG'

    logging.config.dictConfig(config)
    logger = get_logger()
    logger.info('Created logger')
    return logger


def get_logger() -> logging.Logger:
    """モジュール共通のロガーを取得する. create_loggerが実行されなければ, 取得した
    ロガーは機能しない.

    Returns
    -------
        既存のロガー
    """
    return logging.getLogger('main')
