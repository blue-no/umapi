# UM-Api
3Dプリンタ Ultimaker S3 の監視, 操作をまとめたAPIです.

## Setup
### 1. プリンタとの接続設定
プリンタ本体の "developer mode" をオンにし, ローカルネットワークに接続後します(PC接続を容易にするため, 固定IPを割り当てます). PCのブラウザからそのIPアドレスにアクセスすると, Swagger UI が開きます.

"API Documentation" -> "Authentication" をクリックし, 項目を上から順に "Try it out!" で実行して認証設定を行います. 最後の "/auth/verify" を実行し, {"message": "ok"} が返ってくれば本体設定の完了です.

次に本ライブラリ内 umapi\json\umconfig.json に, 下の例のようにプリンタの接続情報を記入します.
* toplevel_url: Swagger UI 各項目実行時の"Request URL" に表示されるアドレスの共通部分.
* id: 取得したid.
* key: パスキー.

```json
{
    "toplevel_url": "http://192.168.x.x/api/v1/",
    "id": "2bfe3xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "key": "6c1980xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

### 2. センサ値履歴設定(Optional)
Monitor クラスで監視し履歴を記録するセンサ値を設定します. 対象は Swagger UI 上の GET リクエストで取得できる値です.

umapi\json\watchlist.json を開き, 下の例のように編集します.
* url: Swagger UI の GET コマンド.
* items: 上記コマンドで取得した値(辞書型構造)のうち, 取り出したい値のキー(key)と取得名(name)のペアの配列. 値が1つの場合は key に null を設定.

(例)ノズル温度の現在値と目標値を取得
```json
[
    {
        "url": "printer/heads/0/extruders/0/hotend/temperature",
        "items": [
            {
                "key": "current",
                "name": "hotendtemp_current"
            },
            {
                "key": "target",
                "name": "hotendtemp_target"
            }
        ]
    }
]
```

## Examples
● スクリプトからプリンタ本体のLEDの明るさを変更する例.<br>
**※プリンタとPCが同じネットワークに接続されている必要あり.**
```python
import printer

printer.establish_connection()  # 初めに1回実行
printer.change_brightness(10)  # 明るさを10%に変更
```

● プリンタが特定の層を印刷し始めた際に外付けカメラで写真を撮る例(ログ付き).
```python
import printer

LAYERS = [10, 20, 30]  # 撮影時の層数
SAVE_DIR = 'tests'  # ログ, センサ値履歴, 画像の出力先

printer.create_logger(SAVE_DIR)  # ログ設定

printer.establish_connection()
monitor = printer.Monitor(SAVE_DIR)
camera = printer.CameraStream(SAVE_DIR, cam_id=0)

printer.send_job('sample.ufp')  # ローカルの.ufpファイルの送信, 印刷開始

with monitor.start(), camera.start():
    monitor.wait_printstart()  # アクティブレベリングを終え, 印刷が始まるまで待機
    monitor.start_recording()  # センサ値履歴の取得開始

    for layer in LAYERS:
        monitor.wait_layer_reach(layer)  # layer番目の層を印刷し始めるまで待機
        camera.fetch(tag=f'layer-{layer}')  # 画像保存

    monitor.stop_recording()  # センサ値履歴の取得終了

printer.abort()  # 印刷中断
```

## Installation
```
pip install git+https://github.com/ut-hnl-lab/umapi.git
```