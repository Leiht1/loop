# 当前主角开发模型

2026-11-13，使用用户认可的常规动作第三版作为当前游戏主角，已接入主关卡。

- Godot 工程为 `Loopbound/project.godot`，F5 运行游戏。
- 可复用角色场景为 `Loopbound/scenes/characters/player/ranger_baseline.tscn`。
- 运行模型为 `Loopbound/assets/characters/ranger/action_comparison/locomotion_v3.glb`。
- 可编辑源为 `assets_source/characters/ranger/locomotion_v3.blend`。
- 当前生成依赖为 `assets_source/characters/ranger/locomotion_motion_reference.blend`，保存原始中性姿态和步态采样。
- 原始输入为 `assets_source/characters/ranger/animation_inputs/tripo_rigged_original.glb`。
- 生成脚本为 `build_locomotion_v3.py`，逐帧验证脚本为 `verify_locomotion.py`。
- 独立动作预览为 `Loopbound/scenes/characters/player/locomotion_v3.tscn`，F6 运行。

运行资产包含 96,284 三角面、12 网格、12 材质、36 张内嵌纹理和 71 蒙皮关节，含新增双手 30 根手指骨。角色约 1.8m，Godot 前方为 -Z。八段动作为待机、走路、握拳奔跑、环顾与四向闪避。文件校验记录见 `RANGER_ASSET_REGISTRY.json`。

游戏内闪避距离为前方 3.3m、后方 2.8m、左右各 3.0m，配合动作阶段非线性位移并经过碰撞求解。详细输入与接入逻辑见 `../RANGER_ANIMATION_HANDOFF.md`。

旧测试版本及其生成产物已清理，本地恢复包保存在忽略目录。手指握持、衣摆变形、步幅与速度匹配继续精调。

走跑和环顾参考 `animation_inputs/tripo_motion_reference.glb`，重定向到当前校正骨架。站立 5 秒后触发环顾，移动或闪避淡出环顾。
