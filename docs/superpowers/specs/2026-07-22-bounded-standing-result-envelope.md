# Goal Brief: Bounded Standing Result Envelope

## Goal

让owner-preauthorized standing result即使面对超长或恶意provider输出，也只能消耗有上限的本地capture、validation与
durable state资源，并以安全错误码停止后续无人执行。

## In scope

- 固定总字符、criteria/stop/source/list与字符串/path上限。
- charter配置、JSON Schema、Pydantic、Codex Adapter和Orchestrator capture同边界。
- 区分JSON语法、schema/duplicate-key和总长错误。
- raw输出不进IM/proposal，超限后fail closed。

## Out of scope

- provider生成期间的token/cost硬中断。
- Codex进程内部或JSONL整行读取前的内存控制。
- 大附件/对象存储证据协议和真实owner定时dogfood。

## Acceptance

1. 超过32,768字符时，capture最多保留32,769字符并产生`result_too_large`。
2. 字段/数量越界或duplicate key产生`result_schema_invalid`；语法错误仍是`invalid_json`。
3. charter无法配置超过result contract的criteria/stop/text。
4. schema与模型资源常量有同步测试，普通非standing输出不截断。
5. proposal与老板IM不包含oversized raw marker，后续run继续fail closed。

## Stop conditions

- 不把本地接收上限写成provider token/cost上限。
- 不为排障持久化raw provider正文。
- 不扩大standing read-only授权或增加第二次LLM调用。
