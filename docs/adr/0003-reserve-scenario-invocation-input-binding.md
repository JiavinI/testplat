# P0 保留统一调用输入绑定但只接受空输入

P0 不开放 Scenario 外部输入，也不在 DSL 或 Web 中制造未实现的 `spec.inputs` 功能；所有非空 Scenario 输入绑定都在快照形成前拒绝。同时，手动运行、定时任务、Suite 及后续 API/MCP 统一经过 `ExecutableInvocation -> InputBinder -> RunSnapshot`，并固化空的 `ResolvedScenarioInputs`。这个边界使未来增加类型化 Scenario 输入时只扩展声明与输入来源，而不需要让 Compiler 或 Worker 理解各入口的原始参数。
