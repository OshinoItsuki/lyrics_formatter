歌詞改行ツール 分割版

起動:
  python main.py

構成:
  main.py                         起動処理
  app/config.py                   定数・正規表現
  app/main_window.py              メイン画面と編集機能
  app/settings_store.py           settings.jsonの読み書き
  app/dialogs/settings_dialog.py  設定画面
  app/dialogs/time_tag_inspector.py タイムタグ検査画面
  app/dialogs/auto_allocation_dialog.py 自動割付結果画面
  app/dialogs/auto_allocation_settings_dialog.py 自動割付専用設定画面
  app/services/update_service.py  GitHub Release確認
  app/services/part_extractor.py  パート分け抽出
  app/services/nicokara_settings.py ニコカラメーカー設定読込
  app/services/display_timing.py 表示時間計算
  app/services/page_optimizer.py 行割付最適化

追加した設定:
  part_start_char / part_end_char
  初期値は ( と )
  設定画面の「パート分け抽出設定」から変更可能

自動割付設定:
  auto_allocation_base_lines / max_page_lines
  pre_wipe_ms / post_wipe_ms / interval_ms
  manual_protection_enabled / manual_protection_ms
  自動割付画面の「割付設定」から変更可能
