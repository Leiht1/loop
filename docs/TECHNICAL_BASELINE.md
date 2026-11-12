# 技术基线

2026-11-12 实测 Godot 4.7.2.stable.official.ed1daf0bf，Blender 5.2.2 LTS。沿用安装版本，不升级。Forward+，Windows x86_64，GDScript，GodotPhysics3D，60 Hz 物理。1 单位为 1 米，Y 向上，角色正面 -Z，脚底中心为模型原点。交换格式 GLB，Blender 源文件单独保留。

材质采用 StandardMaterial3D，按身体、服装、金属、发光分槽。文件 snake_case，类型 PascalCase。资源按 assets 下角色、环境、动画、材质、纹理分类。InputMap 管理动作，鼠标运动事件驱动 camera_look。目标 1080p 60 FPS，参考硬件和预算待确认，尚未性能验收。Git 忽略 .godot 和导出产物，不提交推送，阶段用 ZIP 与 SHA256 恢复。Windows 导出模板可用性待确认。

官方核查入口 https://godotengine.org/download/windows/ 与 https://www.blender.org/download/ 。官方页面动态更新，未将搜索摘要中的补丁号作为升级依据。

## 项目远端

用户于 2026-11-12 提供项目远端地址 https://github.com/Leiht1/loop.git 。用户已于 2026-11-12 授权将项目推送至此远端，本地 remote 名称为 origin。后续提交和推送仍按各次授权执行。
