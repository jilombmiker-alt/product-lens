# 阶段交接与用户检验

下述结构为SOP设计，不是被拆产品、模型或云平台的真实字段。用共同外壳索引各步原有文档，专业字段放payload，避免重新维护两份事实。

## 外壳

| 字段 | 语义 |
|---|---|
| schema_version / record_kind | 本协议schema标识；project为实际项目，fixture为测试替身，template为空模板 |
| project_id / artifact_id / artifact_version | 稳定项目与交接身份，内容变化升版本 |
| mode / stage / scope / environment | 实际模式、内部阶段、当前闭环范围及证据环境 |
| upstream_refs | 上游交接ID、所消费版本；入口可为空，但不得伪造前序已完成 |
| artifacts | 本交接的产物ID、版本、相对路径、摘要；路径须在交付目录内 |
| checks | 检查ID、必需性、状态、实际证据产物ID、不适用理由 |
| review_decision | 阶段评审：pass/conditional_pass/return_for_revision；人工语义判断，不能由脚本替代 |
| human_review | 必需性、检查点、状态、绑定版本/范围/环境、用户原始反馈来源 |
| allowed_uses / blocked_uses | 可继续/不能依赖的具体用途，不能仅写“部分通过” |
| next | 下一阶段、ready、blocker_ids；只对所声明范围计算 |
| payload | 本步PRD、契约、API、模型、前端、发布等专业结构或文件索引 |

[空模板](../templates/handoff.json)默认未就绪；所有示例值都不是已经发生的验收。各步专业内容写入payload，共同外壳负责跨步路由。

## 状态不能互相代替

- 检查：passed / failed / pending / not_applicable。passed必须有实际证据；not_applicable须有理由。
- 阶段评审：pass / conditional_pass / return_for_revision。
- 用户验收：pending / accepted / changes_requested / not_required；required=true时不能用not_required。
- 业务产物：active / needs_revalidation / superseded / retracted，由运行卡artifact_registry维护当前有效版本。
- 运行状态：发布/工具任务保持自己原始枚举及建议归一化状态，放payload；不拿发布成功替代以上三类验收。

## 版本与推进

1. 读取运行卡登记的当前有效交接；引用版本不符或状态非active则阻断对应依赖。
2. 所声明范围必需检查满足、阶段评审允许、必要用户检查点接受了**本交接版本、范围和环境**，才能ready=true。
3. 有限制通过可继续明确允许的范围；不得将受阻用途包含在下一步。无法细分时新建局部范围交接，不粗暴放行整份失败记录。
4. 用户反馈/输入/Prompt/模型/schema/API变化时，逐依赖标待重验；无关分支保留。不要因为更改文件标题自动失效全部结果。
5. 权限与实施授权来自用户真实请求/系统工具权限；human_review.accepted只表示验收，不自动授权付费、部署或对外发送。

## 实际检查工具

在本skill根目录运行：

```bash
python3 scripts/check_handoff.py templates/handoff.json --registry templates/run-card.json --root .
```

空模板会报告不就绪，这是预期。实际执行替换为项目自己的路径；脚本只读JSON和产物文件，不调用模型、浏览器或外部服务。使用Python标准库。

脚本返回结构/引用/版本错误和推进阻断；它校验摘要、声明一致性及必要字段，**不能判断用户是否真的说过某句话、证据是否支持命题、画面质量是否合格或来源是否可信**。AI仍须回看证据，用户仍须验收。测试fixture默认拒绝，用`--allow-fixtures`才可演练；该标记不能拿来证明实际项目通过。

脚本的next.ready检查只覆盖当前交接声明范围。一个JSON不能概括所有阶段授权，不能拿它做自动部署许可。

## 用户明确调整检查点时

默认S04/B4/C7/F1/F4/P7的H1–H6由脚本检查，不能仅改required=false绕过。若用户明确调整某版本的检查安排，在运行卡review_overrides中按stage写：required=false、artifact_version、scope、environment、reason以及source（kind=user_message、path、sha256、locator）。仅与当前版本/范围/环境匹配且有可定位原始指令时，脚本接受该声明。AI必须回看原话判断授权与含义，摘要和字段不能证明真伪。

这只是允许调整该验收点，不使未通过的AI检查变绿，也不授权部署/付费等操作。没有明确用户调整则保留默认检查点。

## 声明一致性检查

allowed_uses、blocked_uses、next.blocker_ids的元素必须是非空字符串；首尾空格归一化后，同一用途不能既允许又禁止。阻断项无论next.ready为true还是false，都阻止eligible_to_advance。单纯主动暂停且无阻断时可以eligible=true、declared_ready=false；调用者必须尊重后者，不能把CLI退出成功当执行授权。

这些检查只处理明确字面冲突，不理解同义词或实际业务语义；仍需AI自检与用户验收。
