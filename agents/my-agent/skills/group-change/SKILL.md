---
name: group-change
description: >
  将当前 git 仓库的所有变更文件（含未跟踪文件）按预定义规则归类，并写入
  IntelliJ IDEA 的 changelist 分组（编辑 .idea/workspace.xml）。当用户想要
  "把改动按 changelist 分组""整理变更归类""group changes / changelist 分组
  /分组提交准备""把这次改的文件分一下类"，或在 review/提交前希望把样板代码、
  数据结构、接口流程、枚举、文档等分门别类时，使用本 skill。即使用户没有明说
  "changelist" 三个字，只要意图是"把这堆 git 改动按类型整理到 IDEA 里方便
  review"，也应触发。
---

# group-change：把 git 变更按规则分到 IDEA changelist

## 这个 skill 在做什么

IDEA 的 changelist 没有命令行 API，分组信息存在项目根的 `.idea/workspace.xml`
里（`<component name="ChangeListManager">` 块）。本 skill 的工作是：读取当前
git 仓库的全部变更（修改 / 新增 / 删除 / 重命名，含未跟踪文件），按下面的规则
把每个文件归到一个 changelist，再调用 `scripts/apply_changelists.py` 把结果写
进 workspace.xml。

**重要前提（已和用户确认）：**
- 用户主要用的是 **changelist 模式，git 暂存区通常是关闭的**。默认不要执行真正的
  `git add`（不要把内容 staged 进提交）。但 IntelliJ 对大量未跟踪文件有时只显示在
  `Unversioned Files`，导致写入 `workspace.xml` 后 changelist 不生效。遇到这种情况
  时，主动执行 `git add -N -- <未跟踪文件...>` 把新文件登记为 intent-to-add，然后
  **重新生成 mapping 并再次写入 workspace.xml**。`git add -N` 不暂存文件内容，只是让
  Git/IDEA 把新文件纳入可管理变更；这一步是本 skill 的正常补救流程，不要等用户提醒。
- 运行时 **IDEA 通常开着**。脚本会先备份 `workspace.xml`，写完后 IDEA 会弹出
  "Project components changed externally — Reload" 通知，用户点 Reload 即生效。
  写完后一定要提醒用户去 IDEA 点 Reload。

## 工作流

1. **确认环境**：`git status --porcelain` 确认有变更；找到项目根的 `.idea/`
   目录（可能在 git 根，也可能在子目录；`.idea` 所在目录就是 `$PROJECT_DIR$`）。
   没有 `.idea/` 就不是 IDEA 项目，停下来告诉用户。注意 `git status` 输出的路径
   是相对 **git 根**的，而 workspace.xml 里用的是相对 **$PROJECT_DIR$**；脚本会
   自动换算，你不用操心。
2. **读已有 changelist——这是关键一步**：打开 `.idea/workspace.xml`，看
   `<component name="ChangeListManager">` 里**已经存在哪些 changelist、它们的
   `comment` 是什么**。如果项目已经有一套 changelist，**它们（连同 comment）就是
   这个项目真正的分类标准**，要照着它们分，而不是套用本文档下面的默认 6 类。
   comment 往往写明了路由规则，例如 `comment="api 及 pom 依赖"` 意味着 api 文件
   和 pom.xml 都进这个 list、`comment="枚举与值对象"` 意味着枚举和值对象合并进
   一个 list。**只有当项目里还没有任何业务 changelist 时**，才用下面的默认 7 类
   新建。
3. **收集变更文件**：`git status --porcelain --untracked-files=all` 拿到全部变更
   文件路径（含未跟踪、删除、改名）。你读路径是为了**分类**；脚本会自己再跑一遍
   status 确定每个文件是改/增/删/改名。
4. **必要时登记未跟踪文件**：如果第 3 步里有 `??` 未跟踪文件，且本次目标是让 IDEA
   changelist 立即接管这些文件，先执行 `git add -N -- <这些未跟踪文件>`。执行后再跑一遍
   `git status --porcelain --untracked-files=all`，确认它们从 `??` 变成 intent-to-add
   状态（通常显示为 ` A`）。如果命令因 worktree index 在主仓库 `.git/worktrees/...`
   而被沙箱拦截，需要请求权限重跑，不要跳过。
5. **分类**：按第 2 步得到的目标 changelist（已有的就用已有的，没有就用默认 7 类）
   把每个文件归类。绝大多数靠路径 / 包名 / 文件名后缀就能判断；少数边界文件——
   尤其是 PO 字段引用的**值对象**——需要打开文件看内容确认（见下方「值对象链」）。
6. **生成 mapping 并应用**：分类结果写成 JSON `{changelist名: [文件路径, ...]}`
   （changelist 名必须和已有的**完全一致**，否则会建出重名的新 list），交给脚本。
   先 `--dry-run` 给用户看一眼，确认后再正式写。若项目有 `reviewed` 之类用户手动
   维护的 list，加 `--preserve reviewed` 保护它（见下）。
7. **提醒刷新**：告诉用户去 IDEA 点 "Reload" 让分组生效，并汇报每个 changelist
   放了哪些文件、各几个，特别点出兜底进「其他」的文件让用户复核。

## 默认 changelist 与规则（仅在项目还没有自己的 changelist 时用）

> ⚠️ **优先用项目已有的 changelist（见工作流第 2 步）。** 下面这 8 类只是项目从零
> 开始时的默认骨架。实际项目常常已经演化出更细的分法——例如把枚举并进
> `数据结构定义`、让 pom 跟 api 一起进 `逻辑过程`、把 assembler/StructMapper 算进
> `样板代码`。这些都写在已有 changelist 的 `comment` 里，**以 comment 为准**，目标
> list 名要换成项目里真实存在的那些。

一个文件只进一个 changelist，**按下面的顺序从上往下判断，命中即停**（这个优先级
很重要，因为一个文件可能同时像两类，比如 domain 里的枚举既在 domain 又是枚举——
枚举优先；而**测试模块下的文件最高优先**，哪怕它是个枚举或 PO，也先归「测试文件」）：

1. **测试文件** — 测试模块下的所有文件，**优先级最高**。判断依据：路径在测试源码
   目录下，典型是 `src/test/**`（Maven/Gradle 标准测试目录），也包括 `**/test/**`、
   `**/tests/**` 这类测试包，以及测试资源 `src/test/resources/**`。**只要文件落在
   测试模块下，无论它是枚举、PO、Service 还是 fixture，一律归这里，不再往下匹配。**
   *为什么单独分且最高优先：测试代码和生产代码的 review 关注点不同，集中放一起，
   review 生产改动时可整体略过或单独看；放最高优先是为了避免测试里的枚举/PO 被下面
   的「枚举」「数据结构」规则抢走。*

2. **文档** — 不是代码、用于描述需求/计划/任务的文件。典型：`openspec/`、
   `superpower/` 等 AI 开发流程目录下的文件，以及 `.md` / `.txt` 等需求、方案、
   任务说明文档。判断依据：路径在这些文档目录下，或扩展名是文档类。
   *为什么单独分：这些不是业务代码，review 时可快速略过或单独看。*

3. **枚举** — 枚举类型。判断依据：文件名以 `Enum` / `Enums` 结尾，或（边界情况
   打开看）内容是 Java `enum` 声明。无论它在哪个目录，只要是枚举就归这里（测试模块
   下的枚举除外——那些已在第 1 条归入「测试文件」）。
   *为什么单独分：枚举改动往往牵涉取值范围变化，值得集中看。*

4. **存储结构** — PO 通过 `@Delegate` 直接内嵌的那个 **Struct**，对应数据库表结构，
   **需要重点关注**。判断依据：打开本次变更里的 PO 文件（路径在
   `domain/**/repository/po/**`，文件名通常以 `PO` 结尾），看它用 `@Delegate` 内嵌
   了哪个 Struct（典型 `@Delegate private XxxStruct s;`，多在 `repository/struct/**`）；
   该 Struct 若也在本次变更里，归「存储结构」。**只装直接被 `@Delegate` 关联的这一层
   Struct**，不含它再往下引用的更深值对象（那些进第 5 条）。注意 PO 自身不进这里——
   PO 归「样板代码」（见第 7 条）。
   *为什么重点：它直接对应数据库表的列结构，改动影响面大。*

5. **数据结构** — 「存储结构」里的 Struct 再往下引用的**更深层值对象**，**需要重点
   关注**。判断依据：打开第 4 条的 Struct，看它的非基本类型字段引用了哪些值对象类
   （如 `FeedbackValue`、`ObservationTargetParameter` 这种 `@Data` 数据类，常在
   `entity/`、`struct/`、`vo/` 等目录），本次变更里的一并归「数据结构」。详见下方
   「值对象链」。
   *为什么重点：它们是表结构里嵌套的业务数据模型，改动同样影响面大。*

6. **接口和流程** — `interface` 层里承载业务流程的文件，**需要重点关注**。判断
   依据：路径在 `interface/**` 下，且是 `Dto` / `Vo` / `api`（接口定义）/
   `application service`（应用服务）这类文件（文件名后缀或所在子包）。
   *为什么重点：这里业务流程逻辑最强，是 review 的核心。*

7. **样板代码** — domain 层里继承基类、无特殊逻辑的常规文件，**简单过一下即可**。
   判断依据：路径在 `domain/**` 下，文件名以 `PO` / `Service` / `ServiceImpl` /
   `Entity` / `Repository` / `Mapper` 结尾（且未被上面更具体的规则命中，比如 domain
   下的枚举已在第 3 条归入「枚举」、被 `@Delegate` 关联的 Struct 已在第 4 条归入
   「存储结构」）。**PO 也算样板代码归这里**——它只是持久化壳，真正的表结构在它
   `@Delegate` 的 Struct 里。
   *为什么单独分：这些大多是模板化代码，review 时快速扫过即可。*

8. **其他** — 以上都不命中的文件，以及构建/配置类文件。典型包括：
   `pom.xml`、`build.gradle`、`application.yml`、`application.yaml`、
   `application.properties`、`bootstrap.yml`、`bootstrap.properties`、
   `src/main/resources/config/**/*.yml`、`src/main/resources/config/**/*.yaml`。脚本
   会自动把任何**没出现在 mapping 里**的变更文件兜底放进「其他」，但 pom 和配置文件
   不要放到「接口和流程」里，除非项目已有 changelist 的 comment 明确要求这么做。
   注意：**测试模块下的文件已在第 1 条全部归入「测试文件」**，不要再落到这里——包括
   测试用 memory/in-memory repository、只为测试服务的 fixture，只要它们在测试源码目录
   下都进「测试文件」。

> 这些路径片段（`domain/`、`interface/`、`repository/po/` 等）是约定俗成的 DDD
> 分层名，不同项目大小写或层级可能略有不同。匹配时按**语义**而非死抠字符串：看到
> `.../domain/.../po/FooPO.java` 就该判成 PO（归样板代码），它 `@Delegate` 的
> Struct 才是「存储结构」，哪怕中间多一层模块名。拿不准的少数文件，打开看一眼内容
> 再决定。

### 值对象链：怎么把「存储结构」和「数据结构」分清、找全

这一段是「存储结构」「数据结构」两类最容易出错的地方：PO 自己只是壳（归样板代码），
真正的表结构在它 `@Delegate` 的 Struct（「存储结构」），Struct 再往下嵌套的值对象才
是「数据结构」。值对象往往不在 `po/` 目录里（可能在 `entity/`、`struct/`、`vo/` 等），
光看路径会误判成「样板代码」。正确做法是顺着引用链找：

1. 打开每个 **PO** 文件（PO 本身归「样板代码」），看它用 `@Delegate` 内嵌了哪个
   `XxxStruct`（典型 `@Delegate private XxxStruct s;`）。
2. 这个被 `@Delegate` 直接关联的 `XxxStruct` → 归「**存储结构**」。只算这**一层**。
3. **再往下一层**：打开这个 Struct，看它的非基本类型字段（跳过 String/Long/Integer/
   Boolean/BigDecimal/LocalDateTime 等）引用了哪些更深的值对象（如 `FeedbackValue`、
   `ObservationTargetParameter` 这种 `@Data` 数据类）或枚举。引用到的值对象 → 归
   「**数据结构**」，枚举 → 归「枚举」（或项目对应的 list）。更深层若还嵌套值对象，
   继续往下，都归「数据结构」。
4. 只把**本次确实有变更**的类纳入，没改的不用管。

> 实战例子：`OrderPo`（→ 样板代码）里 `@Delegate private OrderStruct s;` →
> `OrderStruct` 进**存储结构**；`OrderStruct` 里 `private FeedbackValue fv; private
> OrderStatus st;` → `FeedbackValue`（值对象）进**数据结构**、`OrderStatus`（枚举）
> 进枚举。被删除的值对象（git 状态是 `D`/`AD`）同样按上面规则归类，脚本会正确写成
> 删除型 change。

> 关于 `assembler` / `*StructMapper`：这些是 MapStruct 之类的转换器，属于继承/生成
> 的模板代码，归「样板代码」（很多项目的 `样板代码` comment 会明确写上 `mapper`/
> `assembler`）。不要把它们和它们转换的值对象混为一类。

## 应用分组（调用脚本）

把分类结果存成 JSON。**key 必须和目标 changelist 名完全一致**（项目已有的就照抄，
别自己改名，否则会建出重名 list）；**路径相对 git 根**，和 `git status` 输出一字
不差（脚本按这个 key 匹配）。例：

```json
{
  "1-文档规范":      ["openspec/changes/xxx/proposal.md"],
  "2-样板代码":      ["backend/.../domain/service/OrderService.java",
                      "backend/.../domain/assembler/OrderStructMapper.java",
                      "backend/.../domain/repository/po/OrderPo.java"],
  "3-存储结构":      ["backend/.../domain/repository/struct/OrderStruct.java"],
  "4-数据结构定义":  ["backend/.../domain/enums/OrderStatus.java",
                      "backend/.../domain/entity/FeedbackValue.java"],
  "5-逻辑过程":      ["backend/.../interfaces/api/OrderApi.java", "backend/pom.xml"],
  "6-测试文件":      ["backend/src/test/java/.../OrderServiceTest.java",
                      "backend/src/test/resources/order.json"]
}
```

> 文件多时，与其手写 JSON，不如写个十几行的小脚本读 `git status -z`、按路径规则
> 分桶、`json.dump` 出来——更快也不易抄错路径。分类逻辑（哪个目录/后缀进哪个 list）
> 由你定，脚本只负责把它落地。

先 `--dry-run` 看一遍归类对不对，再正式写入：

```bash
# 预览（不写文件）
python3 scripts/apply_changelists.py --repo <项目目录> --mapping /tmp/mapping.json --dry-run

# 正式应用（会自动备份 workspace.xml）。若有手动维护的 list（如 reviewed），
# 用 --preserve 保护它里面已有的文件不被重新分走：
python3 scripts/apply_changelists.py --repo <项目目录> --mapping /tmp/mapping.json --preserve reviewed
```

`--repo` 给项目里任意路径即可，脚本会向上找 `.idea/`。脚本会：
- 自己跑 `git status` 确定每个文件是改/增/删/改名，生成对应的 `<change>` 元素，并
  把 git 根相对路径换算成 `$PROJECT_DIR$` 相对路径（处理 macOS `/var`→`/private`
  软链等情况）；
- **已存在的同名 changelist 不重建**，复用其 id / default / comment，只更新文件
  归属；缺失的才新建；空 list 也保留；
- 保留 workspace.xml 里其它所有内容（只替换 ChangeListManager 那一块），写入前备份
  成 `workspace.xml.bak-<时间戳>`；
- `--preserve <名,名>` 列出的 list 里现有的文件**原地保留**，无视 mapping；
- mapping 里没提到的变更文件兜底放进「其他」。

## 收尾

写完后告诉用户：
1. 切到 IDEA，点弹出的 "Project components changed externally → Reload"（或
   File → Reload All from Disk）让分组生效；
2. 简要汇报每个 changelist 各放了哪些文件、几个；
3. 如有被兜底进「其他」的文件，提示用户复核。
