# ゲーム・アニメ制作のための生成AIまとめ

**ゲーム・アニメ制作**に役立つ生成AI / MLの **タスク** を厳選してまとめた、**自動更新型**のカタログです。
「領域 → タスク」のツリーで整理し、各タスクにはオープンソースのモデル・論文に加え、スタジオが実際に
使っている商用ツールも掲載しています。

[カタログを見る :material-arrow-right:](catalog/index.md){ .md-button .md-button--primary }
[仕組み :material-arrow-right:](about.md){ .md-button }

## 収録領域

- :material-image: **画像・2Dアート** — コンセプトアート、線画着色、アニメのアップスケーリング
- :material-cube-outline: **3D生成** — テキスト/画像からの3D、メッシュ、テクスチャ、シーン
- :material-account: **キャラクター・アバター** — 生成、自動リギング、スキニング
- :material-run: **アニメーション・モーション** — モーションキャプチャ、リターゲティング、フレーム補間・中割り
- :material-movie-open: **動画** — 生成、復元、ロトスコープ
- :material-music: **音声・オーディオ** — TTS、ボイスクローン、歌声合成、音楽・効果音
- :material-script-text: **テキスト・物語・デザイン** — NPC対話、クエスト、ローカライズ
- :material-book-open-page-variant: **漫画・コミック** — コマ・ページ生成、コマ割り、着色

## 鮮度を保つ仕組み

週次のGitHub Actionsジョブが、LLMリサーチエージェント（arXiv・Hugging Face・GitHub・DuckDuckGo）を
実行して新しい項目を発見し、検証・重複排除のうえでレビュー用のプルリクエストを作成します。スキーマと
リンクのチェックを通過し、人によるマージを経るまで、サイトには反映されません。詳しくは[概要](about.md)を
ご覧ください。

!!! tip "貢献について"
    不足・誤りを見つけたら、`data/entries.yml`（オープンソース）または `data/services.yml`（商用）を
    編集してPRを送ってください。エージェントのマージは、人が編集した項目を上書きしません。
