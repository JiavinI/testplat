# 页面实例使用显式句柄且 BrowserContext 只属于单个 Run

`pageRef` 只表示静态 PageContract，不能唯一识别运行时标签页；因此 `browser.open` 和产生新页面的动作返回 `pageHandle` 类型的当前 Run 页面能力，后续 Browser Step 必须通过 `pageHandleRef` 显式传递，多个新页面视为歧义失败。`pageHandle` 不是 string 或其他可序列化资产值，只能在同一 Run、同一 BrowserContext 内经 Step/Flow 输入输出传递，不能进入 DataSet、Scenario 外部输入、JSON、模板、转换或持久化恢复。BrowserContext 以 `(runId, environment, targetRef, actorRef)` 隔离，同一 Run 内可以复用但绝不跨 Run 复用；Cookie/Storage State 只能初始化新 Context，Run 结束后销毁全部页面和 Context。这个模型避免“当前页面”隐式状态和跨身份、跨运行会话泄漏。
