# Adapter 只能随受控平台部署安装

P0 的 HTTP、Playwright Chromium、MySQL、Redis 验证码和钉钉 Adapter 由部署管理员随平台版本安装，每个 Adapter 以稳定 ID、版本、兼容协议和内容摘要进入 Worker 能力声明及运行快照。Web、YAML 和资产 Git 仓库不得上传、热加载或执行 Adapter 代码；缺少兼容版本时在运行前拒绝。这个边界牺牲用户即时扩展能力，避免通用测试资产演变为绕过发布、权限和隔离边界的任意代码入口。
