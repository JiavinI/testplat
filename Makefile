PYTHON ?= python3
CONTRACTS_TOOL := tools/contracts.py
# 清空同名 make-level 变量，阻止命令行 `TARGET=$(shell ...)` 在解析阶段执行。
override TARGET :=
# TARGET 只从 shell 环境读取，避免 GNU Make 先展开命令行变量中的函数。

.PHONY: contracts-check contracts-compat contracts-test

contracts-check:
	@if [ -n "$$CONTRACTS_TARGET" ]; then $(PYTHON) $(CONTRACTS_TOOL) check --root contracts --target "$$CONTRACTS_TARGET"; else $(PYTHON) $(CONTRACTS_TOOL) check --root contracts; fi

contracts-compat:
	@if [ -n "$$CONTRACTS_TARGET" ]; then $(PYTHON) $(CONTRACTS_TOOL) compat --root contracts --target "$$CONTRACTS_TARGET"; else $(PYTHON) $(CONTRACTS_TOOL) compat --root contracts; fi

contracts-test:
	$(PYTHON) -m unittest discover -s tests/contracts -p 'test_*.py'
