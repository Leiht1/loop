# 主角开发基准模型 V1

2026-11-13，用户确认当前融合版明显改善并要求将此主角入库。登记为唯一主角开发基准，不新增主角候选；敌人后续单独登记。确认的是当前模型与制作流程，六个动作仍需细调。

- 可复用 Godot 场景：`Loopbound/scenes/characters/player/ranger_baseline.tscn`。
- 运行模型：`Loopbound/assets/characters/ranger/action_comparison/tripo_hybrid.glb`。
- 可编辑源文件：`assets_source/characters/ranger/comparison_tripo_hybrid.blend`。
- Tripo 原始绑定文件：`assets_source/characters/ranger/animation_inputs/tripo_rigged_original.glb`。
- 动作参考源：`assets_source/characters/ranger/comparison_triangles.blend`。
- 重建：Blender 后台运行 `build_tripo_corrected.py -- --hybrid`；验证同方式运行 `verify_tripo_corrected.py -- --hybrid`。
- 检查入口：`Loopbound/scenes/characters/player/tripo_hybrid_comparison.tscn`，F6，左侧融合版、右侧旧版。

实测数据：96,284 三角面、56,842 个导出顶点、12 个网格、12 个材质、36 张内嵌纹理、41 个蒙皮关节、6 个测试动作；统一对比身高 1.8m，Godot 前方 -Z。导出顶点可能因 UV/法线分离而重复，不等同于建模软件中未拆分顶点数。GLB 内嵌纹理，Godot 生成的对应图片副本和 .import 设置一并保留，便于复现当前材质。

准确路径、骨名与 SHA-256 校验记录见 `RANGER_ASSET_REGISTRY.json`。入库不代表性能预算、主场景接入、武器握持或正式动作验收完成。当前独立场景不会自动替换主场景角色，避免把未细调动作提前接入控制器。

后续从此版本派生手指绑定与动作精修版本，保留此基准及旧版对照文件。原有 41 骨名称、父子关系和静止姿态应保持稳定；新增骨骼优先作为现有节点子骨，降低已有动画失效风险。手指完成后仍需实际重新导出与验证，不保证只加骨就能正确握持。
