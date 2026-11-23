# ROS 2 Arm Tools

[English](../README.md) · 日本語

名前付き関節ポーズの教示・保存・再生と、関節単位の微調整を行うツールです。
ROSのJointStateとFollowJointTrajectoryを使い、PyLoTのRobotクラス・固定モータIDから
切り離しました。モータを直接開かず、機体のドライバとros2_controlを利用します。

## 機体設定

`config/example_arm.yaml` を参考に実機のjoint名・上下限を定義します。
revoluteはrad、prismaticはmです。サンプルの上下限は実機の校正値ではありません。
コントローラに含む関節をすべて指定してください。別コントローラのグリッパーを
操作する場合は別profileとaction名を指定します。

```yaml
joints:
  shoulder: {type: revolute, min: -1.0, max: 1.0}
  slide: {type: prismatic, min: 0.0, max: 0.1}
```

## 教示・再生・微調整

```bash
ros2-arm-tools --profile my_arm.yaml --file poses.yaml teach ready
ros2-arm-tools --file poses.yaml list
ros2-arm-tools --file poses.yaml show ready
ros2-arm-tools --profile my_arm.yaml --file poses.yaml move ready --duration 3 --timeout 10
ros2-arm-tools --profile my_arm.yaml jog shoulder 0.02 --duration 1
```

`teach` は `/joint_states` の最新の値を記録します。手で教示する際のトルク制御は
機体側で行ってください。本ツールはトルクを切り替えません。
`jog` は新しく取得した関節状態にdeltaを加えて送信する1ステップの微調整です。
角度はrad、直動はmです。現在値が取得できない場合に0から動かす処理はありません。

教示・jogは全設定関節の有効で新しいJointStateが必要です。可動域外・NaN/inf・
不明な関節はエラーです。再生も現在のprofileで再検証します。JointStateのheader.stampを
設定してください。既定のactionは `/arm_controller/follow_joint_trajectory`、
`--action` で変更できます。結果を待ち、タイムアウト時はキャンセルを要求します。
`--states` で関節状態トピックを指定できます。durationは0より大きく86400秒以下です。

保存はファイルロックとatomic renameを使用し、壊れたファイルや同名への暗黙の上書きを
拒否します。同名で教示し直す場合は `--replace` を指定します。
保存形式は `{schema_version: 1, poses: {NAME: {JOINT: SI_VALUE}}}`。
旧Luna armポーズファイルは自動読み込みしません。

## 教示専用ROSノード

```bash
ros2 run arm_tools arm_tools_node --ros-args -p profile:=/absolute/my_arm.yaml \
  -p file:=/absolute/poses.yaml -p pose_name:=ready
ros2 service call /arm_tools/record std_srvs/srv/Trigger '{}'
```

常駐ノードは教示と `/arm_tools/list` のみで、起動時に動作指令を出しません。
`profile` は必須です。結合テストでは合成JointStateとテスト用軌道サーバーを使い、
教示値の保存と送信する関節名・位置・結果処理を確認します。実アームは動かしません。

## インストールと検証

Python 3.10+。リポジトリのルートで実行します。通常のPython環境ではROSは不要です。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m arm_tools.cli demo
```

ROS 2 Jazzyで使う場合は通常のワークスペースのsrcに配置し、ROS環境でビルドします。

```bash
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select arm_tools
source install/setup.bash
```

`config/params.yaml` を自分の入出力に合わせて変更してください。パラメータは起動時設定です。
`ros2 launch arm_tools arm_tools.launch.py params_file:=/absolute/path/to/params.yaml` で起動できます。
CIはPython 3.10/3.12でコアテストと合成デモを実行します。ROS結合テストはROS環境で
実行し、それ以外ではスキップします。モデル・実センサ・実アームの性能は認証しません。

## ライセンスと出典

Apache-2.0。元のコミット・ファイルと変更範囲は
[PROVENANCE.md](../PROVENANCE.md) を参照してください。元モノレポへの依存はありません。
