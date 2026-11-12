# 动画标准

动画使用 idle、walk、run，骨骼沿角色标准固定命名。首阶段采用原地动画，控制器负责位移，禁止 root motion 叠加。循环首尾姿态与速度连续。按真实水平速度混合，建议 0、2.6、6m/s 作为混合点，过渡约 0.15s。

当前接口通过 AnimationTree 的 parameters/locomotion/blend_position 驱动一维混合空间，正式资产需建立对应节点。无正式素材时只显示占位姿态和状态，不声称完成正式动画或滑步验收。
