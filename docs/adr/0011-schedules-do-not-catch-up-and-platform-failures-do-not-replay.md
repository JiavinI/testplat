# 定时触发不补跑且平台故障不自动重放

P0 默认使用 `Asia/Shanghai` 中国时区展示和新建任务，但每个定时任务显式保存 IANA 时区并以 UTC 固化触发时刻，以 `scheduleRef + scheduledFireTime` 去重。同一任务串行且最多保留一个待执行实例；停机或夏令时不存在的本地时间默认跳过而不补跑，回拨产生的重复本地时间只取较早 UTC 时刻一次。进入队列前的平台不可用记录为 `rejected + platform`，运行中的 Worker 租约丢失记录为 `failed + platform`，恢复后都不得自动重放原 Scenario。这个取舍牺牲自动追赶，避免恢复过程重复执行支付、结算、退款等外部影响。
