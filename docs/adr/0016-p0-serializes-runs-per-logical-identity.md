# P0 按逻辑执行身份串行运行

P0 对 `environment + targetRef + actorRef` 使用排他身份租约，同一 Run 的 API 与 Browser 步骤共享租约，其他 Run 排队；不提供提高同一身份并发数的配置。Compiler 从完整确定性计划中枚举包括展开后 Flow、Suite 成员在内的全部租约键，控制面按规范顺序一次性原子获取：任一不可用时 Run 保持 `queued` 且不持有任何部分租约，全部成功后才进入 `running`，执行中禁止追加。共享同一身份键的请求按该键上的 `queuedAt` FIFO，Run 只有在全部所需键上都是最早等待者时才能获取，无关身份的 Run 不受全局队首阻塞；P0 不提供优先级或人工插队。需要并行时配置 `buyer.primary`、`buyer.secondary` 等不同确定性身份。该方式避免多身份 Run 部分占有造成死锁和后到请求造成饥饿，并降低共享账号的订单和服务端会话互相干扰，但不替代稳定业务 ID，也不能防止平台外人工登录；Worker 失联后的租约回收不得重放原 Run。
