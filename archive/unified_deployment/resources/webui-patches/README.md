# WebUI Patches

这个目录包含用于修改 OpenMemory UI 的 patch 文件，以适配 Mem0 API 并移除不需要的功能。

## Patch 文件

### 1. `remove-apps-navbar.patch`
移除导航栏中的 Apps 链接和相关路由处理。

**修改内容：**
- 移除 `/apps` 和 `/apps/[appId]` 路由配置
- 移除 Apps 链接按钮
- 移除 app_id 相关的路由处理逻辑

### 2. `remove-install-component.patch`
移除 Dashboard 页面中的 "Install OpenMemory" 组件。

**修改内容：**
- 移除 `<Install />` 组件
- 调整 Stats 组件为全宽显示（从 `col-span-1` 改为 `col-span-3`）

## 使用方法

这些 patch 文件会在构建 WebUI Docker 镜像时自动应用（在 `webui.Dockerfile` 中）。

## 验证

要验证 patch 是否正确应用，可以：

1. 检查构建日志中是否有 patch 应用信息
2. 检查运行中的容器内的文件是否已修改
3. 访问 WebUI 确认相关功能已移除

