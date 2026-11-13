# Tripo 校正骨架动作对比 · 2026-11-13

## 当前推荐测试入口：融合版

打开 `scenes/characters/player/tripo_hybrid_comparison.tscn` 按 F6。默认正面左侧 HYBRID - 41 bones 为融合版，右侧 OLD - 18 bones 为旧版。原先 `tripo_rig_comparison.tscn` 入口、`tripo_corrected.glb` 与对应 Blender 源文件保留。

融合版沿用新版身体比例、41 骨结构、左右对称关节与 Tripo 原蒙皮。从旧版 `comparison_triangles.blend` 实际采样六动作的脚踝位移、上臂/前臂方向、骨盆高度与胸腔方向，按新版骨段长度重新求解；周期恢复到旧版（待机/压力姿态 2 秒、行走 1 秒、奔跑约 0.73 秒）。保留轻微骨盆/胸腔反向摆动与减弱的脚踝着地变化。

修正屈膝平面，避免膝盖朝身体中线内收；保持原脚距，脚掌在原朝向上额外外展 4°。实际靴底前后端连线逐帧测得外展约 5.2～6.3°，没有脚尖内转。走路膝盖相对同侧踝点的最大向内偏移约 6mm、跑步约 3mm（以全局横向衡量，仅为塌膝诊断指标）。

生成：`build_tripo_corrected.py -- --hybrid`（通过 Blender 的 `--python` 运行）。验证：`verify_tripo_corrected.py -- --hybrid`。独立源文件 `comparison_tripo_hybrid.blend`，运行模型 `tripo_hybrid.glb`。本地数值和正侧背 90 张关键帧位于 `local_previews/tripo_hybrid/`。

检查：左右对称、六动作循环首尾网格连续、关节夹角、支撑脚接地、步态前后方向、脚掌朝向和膝内收范围；支撑脚误差小于 0.1mm。Godot 双播放器完整循环与多视角画面检查通过。保留原版供主观自然程度比较，不据数值断言正式动画定稿。

以下为前一轮 41 骨校正版记录。

打开 Loopbound/project.godot，在 Godot 打开 scenes/characters/player/tripo_rig_comparison.tscn，按 F6。

默认正面画面左侧为 TRIPO corrected - 41 bones，右侧为 OLD - 18 bones。两者使用同一三角面角色进行对照，旧版模型、动作和旧拓扑对比入口保留。两套动作按归一化周期同步，旧版播放速率会为比较节奏调整，源动作不改写。

1～6：待机、行走、奔跑、双臂举过头、屈肘、下蹲；7/8/9：正面/侧面/背面；空格：暂停；G/T：灰模/原材质。

## 骨架调整

保留用户提供 Tripo 文件的 41 根骨骼、父子关系、顶点权重和材质。原文件复制保存为 assets_source/characters/ranger/animation_inputs/tripo_rigged_original.glb，下载文件不改写。

统一前方与 1.8m 对比身高，对左右对应骨骼头尾求镜像平均，调整肩、肘、腕、髋、膝、踝及扭转骨位置；中轴骨骼居中。保留侧面脊柱曲线与关节前后差异。Root/Hip 辅助骨的异常骨尾改为短竖向，避免显示成穿出身体的斜线。没有强行把四肢排成直线，也没有重建简化骨架。

可编辑源文件：assets_source/characters/ranger/comparison_tripo_corrected.blend。
运行模型：Loopbound/assets/characters/ranger/action_comparison/tripo_corrected.glb。
生成脚本：assets_source/characters/ranger/build_tripo_corrected.py。

## 新动作

新增六动作，按原骨架关节位置计算腿部两骨段目标，膝向前折叠。走路区分支撑与摆动阶段，跑步缩短支撑时间并抬高摆腿；加入反向摆臂、肘部屈曲、骨盆与胸腔反向转动、脚跟着地和脚尖蹬离的脚踝过渡。抬臂包含锁骨抬升，屈肘向前，下蹲包含髋后移、膝前屈和躯干前倾。扭转骨随父骨继承运动，当前动作不包含专门的前臂旋前/旋后。

## 检查与边界

Godot 4.7.2 / RTX 3060 / Forward+：两套 AnimationPlayer 的六个动作完整循环运行通过。实际截图含正侧背 × 六动作 × 五阶段共 90 张，逐组查看。

verify_tripo_corrected.py 检查 41 骨数量、左右镜像误差、六动作逐帧肘膝夹角、支撑脚接地、循环首尾网格、走跑摆动脚前进和支撑脚后移。结果保存在 local_previews/tripo_corrected/verification.json，截图同目录。数值结果证明连续性和约束，不替代动作观感验收。

当前仍为程序化原地动作比较，不是动作捕捉或正式动画定稿。保持 Tripo 原有蒙皮，因此原衣服分件及极限肩袖变形仍会保留；没有手指骨骼、布料模拟或主场景移动接入。没有修改原始衣服造型或替换用户骨架。
