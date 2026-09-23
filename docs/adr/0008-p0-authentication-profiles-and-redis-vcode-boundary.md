# P0 认证 Profile 与 Redis 验证码边界

P0 只开放黄金流程需要的认证类型：匿名、API 表单登录提取 Token、API Cookie Session、Browser Cookie/Storage State，以及受控验证码认证 Adapter。验证码 Adapter 可以通过认证专用 Redis 受控连接读取一次性验证码，但普通 Scenario 不得读取验证码或取得连接凭据；每种 Profile 都必须定义成功校验、有效期、失效条件和销毁行为。其他认证方式通过后续版本化 Profile 能力增加。
