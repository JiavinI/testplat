# Contracts 单一权威目录

本目录是父仓库维护的跨仓契约权威来源。Control、Engine 和其他组件只能固定引用这里的版本，不得把 Schema、fixture、错误码或兼容矩阵复制到组件仓库。

当前 Ticket 只建立可版本化的目录和校验边界，不提前定义 P0-002～005 的具体协议字段。后续协议包应各自放在对应的版本化子目录，并通过 `manifest.json` 登记。

## 目录约定

- `schemas/`：版本化 JSON Schema；本 Ticket 不添加具体 Schema。
- `fixtures/`：正向和负向协议样本；本 Ticket 只保留目录说明。
- `errors/`：错误码注册表与状态映射；具体内容属于 P0-005。
- `compatibility/`：版本与 feature 兼容矩阵。
- `manifest.json`：当前权威内容的登记清单。清单允许暂时为空，但文件本身必须存在。
- `schemas/manifest.json`、`fixtures/manifest.json`、`errors/registry.json`：三类资产的空元数据外壳，保持格式稳定但不预置协议条目。

三类注册表的每个条目统一要求 `id`、`version`、`payload` 和 `sha256`；ID 在主 manifest、三类注册表和兼容矩阵之间全局不得重复，payload 必须通过同一 contracts 内路径和摘要校验。

所有 JSON 载荷的摘要算法为 RFC 8785 JCS 后的 SHA-256，摘要写成 `sha256:<64 位小写十六进制>`。摘要覆盖载荷正文，不覆盖登记项自身；这样登记项可被重排而不改变被登记内容的身份。为满足 RFC 8785/I-JSON 的跨实现确定性，JSON 整数必须位于 `[-2^53+1, 2^53-1]`，超出范围稳定拒绝，不静默转字符串或改变摘要语义；孤立 UTF-16 surrogate 也会拒绝。

## 校验入口

```shell
make contracts-check
make contracts-compat
CONTRACTS_TARGET=schemas make contracts-check
```

`contracts-check` 检查目录、登记项、ID 唯一性、版本格式、路径边界和载荷摘要。`contracts-compat` 检查登记项是否能被当前矩阵消费，并拒绝未知的必需 feature。Make target 通过环境变量 `CONTRACTS_TARGET` 传入；不读取 make-level `TARGET`，避免 GNU Make 先展开其中的函数。失败时工具使用稳定错误码并返回非零状态，便于 CI 固定消费。

登记项 payload 若是 UTF-8 且内容为 JSON，则无论文件扩展名都使用 JCS 摘要；非 JSON 二进制/文本才按原始字节摘要，`.json` 后缀文件的非法 JSON 会直接拒绝。数字规范化回归覆盖 RFC 8785 Appendix B 向量。
