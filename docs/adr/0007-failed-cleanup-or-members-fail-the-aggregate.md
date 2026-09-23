# cleanup 或成员失败会使聚合结果失败

Scenario 只有主步骤与全部 cleanup 都通过时才为 `passed`；主步骤成功但 cleanup 失败仍为 `failed`，并保留主成功与 `phase: cleanup` 事实。Suite 即使选择继续执行，任一成员失败也使最终 Run 失败；ApiCheckSet 默认执行全部变体，任一变体失败也使整体失败，同时保留每个成员或变体的独立结果。这个判定避免“部分失败却显示成功”污染通知和趋势。
