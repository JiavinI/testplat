# Contracts 贡献规则

1. 先修改父仓库 `contracts/` 中的权威内容，再让组件仓库更新固定引用；禁止复制文件形成第二份事实来源。
2. 每个登记项必须有全局唯一的 `id`、整数 `major.minor` 版本、相对 `payload` 路径和 `sha256:` 摘要。
3. ID 一旦发布不得复用；语义不兼容使用新 ID 或新的主版本，兼容扩展使用已声明的次版本和 feature。
4. `requiredFeatures` 表示消费者不能忽略的语义；未知必需 feature 必须拒绝。`optionalFeatures` 可被旧消费者忽略，但不能借此改变既有字段语义。
5. 任何契约变更都必须同时更新兼容矩阵、正反向样本和 `make contracts-check`/`make contracts-compat` 结果。
6. 摘要由工具根据规范化 JSON 载荷计算，不手工编辑。载荷路径必须留在 `contracts/` 内，不允许通过 `..` 或符号链接逃逸。

本规则只约束契约资产的登记和演进方式，不在 P0-001 中增加 DSL、S1、S2、S3 的字段或运行时职责。
