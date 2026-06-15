# 可顺手修复规则清单（code-style）

这个文件是 **`auto-fix` 和 `myreview` 两个 skill 共用的「单一真相源」**，定义哪些
问题属于「可顺手修复」。规则只维护这一份，往这里加，两个 skill 都生效。

- **`auto-fix`** 用它：命中规则、且守卫判定安全的，**直接改**；触碰守卫的列成
  「⚠️ 建议确认」清单，不静默改。
- **`myreview`** 用它：审查时把命中规则的发现**标注为「可 auto-fix」**，提示你可以
  跑 `/auto-fix` 清理，但 myreview 自己不动手改。

判定逻辑很简单：一条问题**只有命中下面某一条规则时，才算「可顺手修复」**；没命中
的一律归「需决策」，交给人。

收录原则——**只放「改了也几乎不可能引入 bug」的规则**：改动机械、改法基本唯一、
**不改变程序的运行逻辑**（或仅在行为完全等价的前提下做性能优化）。凡是会改变运行
语义、或「改成什么」有多个合理答案的（如判空后如何处理、`==` 改 `equals`、异常
处理方式），**不要**放进来——那些应该留给人决策。

> 维护方式：往下面对应分类里加规则即可。每条规则尽量写清「命中条件」和「怎么改」，
> 最好附一个反例 → 正例，这样修复 agent 不会理解偏。



---

## 一、无用代码清理

1. **删除无用 import**：未被引用的 import 直接删。
2. **删除无用的局部变量 / 私有字段**：声明后从未读取的，删掉（注意别删有副作用的
   初始化表达式）。
3. **删除注释掉的废代码**：成块被注释掉的旧代码，删。

## 二、注解与修饰符

4. **补 `@Override`**：覆写父类 / 实现接口方法但漏标 `@Override` 的，补上。
5. **补 `final`**：声明后不再被重新赋值的局部变量 / 字段，按项目习惯加 `final`
   （仅当项目其它代码普遍这么写时才加，避免与风格不一致）。

## 三、性能（行为等价的前提下）

6. **循环内字符串拼接 → `StringBuilder`**：在 `for`/`while` 里用 `+` 拼 `String`
   的，换成循环外声明的 `StringBuilder`。行为等价，只是更快。
   ```java
   // 反例
   String s = "";
   for (String x : list) s += x + ",";
   // 正例
   StringBuilder sb = new StringBuilder();
   for (String x : list) sb.append(x).append(",");
   String s = sb.toString();
   ```
7. **集合显式初始容量**：已知大致元素个数时，给 `new ArrayList<>()` / `new
   HashMap<>()` 补初始容量。纯优化，不改行为。

## 四、可读性

8. **魔法值抽常量**：散落的字面量数字 / 字符串（非 0/1/"" 这类显而易见的），抽成
   命名清晰的 `private static final` 常量。仅当含义明确、不需要业务确认时才抽。
9. **日志用占位符而非字符串拼接**：SLF4J 日志里 `log.info("x=" + x)` 改成
   `log.info("x={}", x)`。既是性能也是规范。
   ```java
   // 反例
   log.info("订单 " + orderId + " 处理失败：" + msg);
   // 正例
   log.info("订单 {} 处理失败：{}", orderId, msg);
   ```
10. **局部变量 / 私有方法重命名**：命名词不达意时，重命名为更清晰的名字。**仅限
    作用域不外溢的**（局部变量、`private` 方法 / 字段）；public API、跨文件引用的
    符号不在此列——那要走「需决策」。

---

## 五、我的自定义规则（往这里加）

11. **精简字段名（去掉与类名重复的前缀）**：`class Xxxx` 里的字段若以类名为前缀，
    如 `xxxxId` / `xxxxCode` / `xxxxName`，精简为 `id` / `code` / `name`。
    - 命中条件：字段名前缀 = 所属类名（忽略大小写），去掉前缀后仍是合法、达意的
      名字（如 `OrderItem` 的 `orderItemId` → `id`）。
    - 怎么改：重命名字段，并**同步更新本类的 getter/setter、构造器、`toString`、
      以及本类内部对该字段的引用**。
    - ⚠️ 守卫——满足以下任一条，**降级为「需决策」、不要自动改**：
      - 字段带序列化 / 映射注解（`@JsonProperty`、`@JSONField`、`@TableField`、
        `@Column`、`@TableId` 等），或所属类用作 JSON 出入参 / ORM 实体——重命名
        会改变对外字段名或数据库列名，必须人来定。
      - 字段被**跨文件引用**（其它类直接访问或通过 getter 使用）——影响面超出本类。
      - 去前缀后会与已有字段 / 关键字冲突。
    - 只有字段是纯内部、无对外契约、改动能闭环在本类时，才算「可顺手修复」。
    ```java
    // 反例（纯内部 DTO，无注解、无外部引用）
    class OrderItem { private Long orderItemId; private String orderItemName; }
    // 正例
    class OrderItem { private Long id; private String name; }
    ```

12. **优先用 `YihengStreamSupportUtils` 替代裸 Stream**：遇到 Java 8 的 Stream 写法
    时，先在工程里搜出 `YihengStreamSupportUtils`（如 `grep -r YihengStreamSupportUtils`）
    并读它的方法，看有没有**语义等价**的封装方法可替代。
    - 命中条件：工具类里存在与这段 stream **完全等价**的方法（如 list→map 转换、
      按 key 分组、求和/计数、去重、join 等常见操作），替换后行为一致。
    - 怎么改：用对应工具方法替换原 stream 链，注意保持入参/出参类型一致。
    - 若工具类里**没有合适方法、或语义不完全等价**，标「需决策」（或不报此项），
      不要为了套用而硬改。

13. **字段冗余（只检测、只建议，永不自动删）**：同一个类里既存了 ID 又存了由它派生
    的字段，如同时有 `xxxId` 和 `xxxName`（`name` 本可由 `id` 查出来）、或 `xxxId` +
    `xxxCode` 这类一存一冗余。这是 AI 按需求开发时常见的过度建模。
    - 命中条件：类里有一个标识字段（`*Id`），又有一个明显由它派生、可现查的字段
      （`*Name` / `*Code` / `*Desc` 等），且两者指向同一实体。
    - **处理方式固定为「⚠️ 建议确认」——绝不自动删字段。** 删字段会改数据模型、可能
      有调用方在用、可能影响序列化和持久化，必须人来判断「到底留哪个、谁在用」。
    - 汇报时说清：哪两个字段疑似冗余、为什么、建议保留哪个，由用户定夺。
    > 这条是「检测规则」而非「修复规则」：它让 auto-fix 能把冗余揪出来提醒你，但
    > 落地删除永远由你拍板。

14. **禁止在类内部定义数据容器 class**：业务类、service、domain service、controller
    等类内部不允许定义只承载数据的内部类，例如 `Payload` / `Dto` / `Vo` / `Result` /
    `Command` / `Context` / `Request` / `Response` 这类只有字段、构造器、getter/setter
    的内部数据容器。
    - 命中条件：成员内部类或静态内部类用于承载数据，且没有依赖外部类实例状态，没有
      复杂业务行为；常见形态是 `public/private/static class XxxPayload` 里只有字段、
      构造器、getter/setter。
    - 怎么改：把内部数据容器拆成同 package 下独立顶级类（或项目已有的 dto/vo/payload
      包），保留字段、构造器、getter/setter 和可见性语义；同步更新原引用，删除内部类。
    - ⚠️ 守卫——以下情况不要自动拆，只列「需决策」或跳过：内部类不是数据容器，而是
      行为类、策略类、回调类、枚举、builder，或它直接访问外部类实例字段/方法导致拆出后
      需要改变语义。
    ```java
    // 反例
    class OrderService {
        static class OrderPayload { private final Long id; }
    }
    // 正例
    class OrderPayload { private final Long id; }
    ```

15. **枚举必须统一使用 `code` / `desc`**：业务枚举不允许只声明裸枚举常量，必须像
    `RuntimeNodeStatus` 一样提供稳定编码和中文描述。
    - 命中条件：Java `enum` 的枚举常量没有携带 `code`、`desc`，或缺少 `code` /
      `desc` 字段、`fromCode` 解析方法、序列化 / 持久化注解。
    - 怎么改：每个枚举常量改成 `NAME("code", "描述")`；补 `private final String code`
      和 `private final String desc`；`code` 字段加 `@EnumValue`、`@JsonValue`；补
      `@JsonCreator(mode = JsonCreator.Mode.DELEGATING)` 的 `fromCode(String code)`；
      优先实现 `CodeDescEnum`，保证有 `getCode()` / `getDesc()`。
    - `code` 默认用稳定的小写英文或小写下划线，例如 `IN_PROGRESS("in_progress",
      "进行中")`；不要直接依赖 `name()` 作为对外编码。
    - ⚠️ 守卫——以下情况不要静默改，只列「需决策」：已有对外接口、数据库存量数据或
      三方消息明确使用枚举 `name()` 的大写值；枚举实现了其它业务接口且接口字段不是
      `code` / `desc`；`code` 取值需要产品或协议确认。
    ```java
    // 反例
    enum OrderStatus { CREATED, CLOSED }
    // 正例
    enum OrderStatus implements CodeDescEnum {
        CREATED("created", "已创建"),
        CLOSED("closed", "已关闭");

        @EnumValue
        @JsonValue
        private final String code;
        private final String desc;

        @JsonCreator(mode = JsonCreator.Mode.DELEGATING)
        public static OrderStatus fromCode(String code) { ... }
    }
    ```

16. **禁止使用含义不明确的 `Object` 泛型容器**：业务数据结构、DTO、VO、PO、Struct、
    Entity 中不允许使用 `List<Object>`、`Set<Object>`、`Map<String, Object>` 等无法表达元素
    语义的泛型容器。
    - 命中条件：字段、方法参数或返回值使用 `Object` 作为集合 / Map 的元素值类型，且该字段
      承载业务数据，而不是底层框架的通用扩展点。
    - 怎么改：定义明确的顶级数据类型或已有领域类型，例如 `List<RepairMeasure>`、
      `List<AttachmentRef>`、`Map<String, ParameterValue>`；类型名必须表达元素语义。
    - ⚠️ 守卫——如果真实元素结构尚未确定、来源协议确实是任意 JSON、或属于框架级
      passthrough 字段，**不要自动改**，列为「需决策」并要求补明确类型或明确豁免原因。
    ```java
    // 反例
    private List<Object> repairMeasures;
    private Map<String, Object> payload;

    // 正例
    private List<RepairMeasure> repairMeasures;
    private Map<String, ParameterValue> values;
    ```

17. **禁止用 `String` 表达枚举语义**：业务字段如果只有有限取值，不允许声明为 `String`
    再靠注释说明取值范围，必须定义并使用枚举类型。
    - 命中条件：`String` 字段 / 参数 / 返回值的注释中出现固定取值说明，例如
      `type: a-甲、b-乙`、`status: normal-正常、abnormal-异常`，或字段名以
      `type` / `status` / `mode` / `method` / `category` / `policy` / `result` 等结尾且
      注释列出了枚举候选值。
    - 怎么改：新增或复用业务枚举，并按「枚举必须统一使用 `code` / `desc`」规则补齐
      `@EnumValue`、`@JsonValue`、`fromCode`；字段类型改为该枚举。
    - ⚠️ 守卫——如果该 `String` 是用户自由输入文本、三方原样透传值、或枚举取值还需要
      产品 / 协议确认，**不要自动改**，列为「需决策」。
    ```java
    // 反例
    /** 反馈类型：normal-正常、abnormal-异常 */
    private String feedbackType;

    // 正例
    private FeedbackType feedbackType;
    ```

18. **审计字段只允许定义在 Base 类中**：创建人、创建时间、更新人、更新时间、版本号等
    数据表审计字段只能由项目统一 Base PO / Base Entity 提供，业务 Entity、PO、Struct、
    DTO 中不允许重复声明。
    - 命中条件：业务类中出现 `createdAt` / `updatedAt` / `createTime` /
      `lastUpdateTime` / `createBy` / `lastUpdateBy` / `version` 等审计字段，且该类已经通过
      Base 类继承统一审计能力，或该字段只是表达数据表审计时间而非业务事件时间。
    - 怎么改：删除业务类中的重复审计字段，使用 Base 类字段；如果需要表达真实业务时间，
      必须改成明确业务语义命名，例如 `submittedAt`、`verifiedAt`、`calculatedAt`、
      `completedAt`，不要叫 `updatedAt`。
    - ⚠️ 守卫——如果字段已经对外暴露为接口契约、数据库存量列，或无法判断是审计时间还是
      业务事件时间，先列为「需决策」，不要静默改。
    ```java
    // 反例
    class WorkOrderStruct {
        private Long updatedAt;
    }

    // 正例
    class WorkOrderPo extends BaseGroupPo { ... } // 使用 BasePo.lastUpdateTime
    class WorkOrderStruct {
        private Long submittedAt;
    }
    ```

19. **`domain/entity` 包只能放领域实体**：`domain/entity` 目录只允许放有实体身份、
    生命周期和持久化主键语义的领域实体；值对象、快照结构、配置结构、反馈值、明细项等
    纯数据结构不允许放在 `entity` 包。
    - 命中条件：`domain/entity` 包中的类没有实现项目实体接口（如 `DomainEntity`），没有
      继承实体 PO，或仅由字段、getter/setter、构造器组成，用于嵌入其它实体 / struct。
    - 怎么改：将值对象移动到更准确的数据结构包。若它是 PO 的可展开结构或被
      `domain/repository/struct` 引用，优先放入同模块的 `domain/repository/struct`；
      若项目已有专门的 `domain/model`、`domain/valueobject` 包，也可按项目既有约定放置。
      同步更新所有 import。
    - ⚠️ 守卫——如果类虽然没有实现实体接口，但承担领域行为、聚合根语义、领域事件能力，
      或移动会影响公开 API / 序列化类名 / 跨模块引用，先列为「需决策」。
    ```java
    // 反例
    package xxx.domain.entity;
    class FeedbackValue { private ValueCategory valueCategory; }

    // 正例
    package xxx.domain.repository.struct;
    class FeedbackValue { private ValueCategory valueCategory; }

    package xxx.domain.entity;
    class WorkOrderDraft extends WorkOrderDraftPo implements DomainEntity { ... }
    ```

20. **领域过程数据应成对建模 `Draft` / `Record`**：`domain/entity` 中表达执行过程、
    业务单据、任务、维修、读数、签到等会从“待处理/草稿态”流转为“完成/记录态”的
    领域数据，命名和持久化模型应明确区分 `Draft` 与 `Record`，不要只生成单边模型。
    - 命中条件：同一业务概念下存在 `XxxDraft` 但没有对应 `XxxRecord`，或存在
      `XxxRecord` 但没有对应 `XxxDraft`；类注释 / 表名表达“记录”，但类名仍为
      `Draft`；或相同流程中其它对象都已按 `Draft` / `Record` 成对建模，唯独该对象缺失
      一侧。
    - 怎么改：补齐缺失的一侧实体、PO、Struct、Mapper、Repository、Assembler 和必要的
      Service，并让状态流转从 `Draft` 生成 `Record`；如果该数据实际上是规则、要求、
      配置或模板，不参与草稿到记录的生命周期，则不要伪造成 Draft/Record，应改成更准确
      的命名并写清生命周期归属。
    - ⚠️ 守卫——补齐或改名会影响表结构、数据迁移、接口契约、序列化字段和流程语义，
      不允许 auto-fix 静默修改；审查时列为「需决策」，由人确认是否补模型、改名或保留
      例外。
    ```java
    // 反例：注释表达记录，但只有草稿实体
    class MeterReadingDraft extends MeterReadingDraftPo implements DomainEntity { ... }

    // 正例：过程数据成对表达生命周期
    class MeterReadingDraft extends MeterReadingDraftPo implements DomainEntity { ... }
    class MeterReadingRecord extends MeterReadingRecordPo implements DomainEntity { ... }
    ```

21. **`domain/service` 包只能放 domain service**：`domain.service` / `domain/service`
    包内只允许放表达领域行为的领域服务类，不允许混放结果对象、参数对象、上下文对象、
    helper、纯算法工具或数据容器。
    - 命中条件：`domain/service` 包里出现 `*Result` / `*Context` / `*Command` /
      `*Request` / `*Response` / `*Dto` / `*Vo` / `*Payload` 等只承载数据的类，或出现
      不表达领域服务语义的 `*Helper` / `*Util` / `*Builder` / `*Factory` 等。
    - 怎么改：纯数据对象移到 `domain/model`（或项目已有的 `domain/dto`、`domain/entity`
      等更准确包）；工具/辅助对象移到 `domain/support`；真正承担领域行为、需要留在
      `domain/service` 的类，命名应清晰表达服务语义，优先使用 `*Service` 后缀。
      由于包名已经表达 domain 语义，类名不要再重复带 `Domain`，例如使用
      `AemEventService`，不要使用 `AemEventDomainService`。
      静态建模阶段参考 WMO / workflow：每个 `domain/entity` 实体应有对应的
      `domain/service/XxxService`，并继承项目统一 `BaseService<Entity, Po, Repository,
      StructMapper>`；此阶段不要在 service 中提前写动态执行逻辑。
    - ⚠️ 守卫——如果移动类会改变 public API、Spring bean 名称、序列化类型名或跨模块
      依赖，需要同步更新全部引用并跑编译；不确定语义归属时只列「需决策」。
    ```java
    // 反例
    package xxx.domain.service;
    class OrderEvaluationResult { ... }

    // 正例
    package xxx.domain.model;
    class OrderEvaluationResult { ... }

    package xxx.domain.service;
    class OrderEvaluationService { ... }
    ```

22. **禁止手写纯 getter / setter，统一使用 Lombok**：普通 Java Bean、DTO、VO、
    PO、配置属性类、领域实体、事件消息、结果对象等，不允许手写只读写字段的
    `getXxx()` / `setXxx(...)` / `isXxx()` 方法。
    - 命中条件：方法体只是 `return field;` 或 `this.field = field;`，没有校验、归一化、
      派生计算、事件发布等额外逻辑。
    - 怎么改：删除纯手写 accessor，在类上加 `@Getter` / `@Setter`；只读对象或只有
      getter 的结果对象只加 `@Getter`；少数字段需要 setter 时优先用字段级 `@Setter`。
    - ⚠️ 守卫——以下情况不要自动删：accessor 内有额外逻辑，例如 `null` 转空集合、
      参数校验、懒加载、格式化、兼容旧字段名、同步维护其它字段，或方法是业务查询
      方法（如 `isAbnormal()` 这类不是字段 accessor 的行为方法）。这些方法可以保留，
      但要确认它不是纯粹样板 getter/setter。
    ```java
    // 反例
    class OrderCommand {
        private String code;
        public String getCode() { return code; }
        public void setCode(String code) { this.code = code; }
    }

    // 正例
    @Getter
    @Setter
    class OrderCommand {
        private String code;
    }
    ```

23. **不要用 `unmappedTargetPolicy = ReportingPolicy.IGNORE` 掩盖 MapStruct 未映射警告**：
    MapStruct 的 `Unmapped target property/properties` 可能暴露真实字段漏映射，不能为了消除
    warning 在 `@Mapper` 上直接加全局/局部 `unmappedTargetPolicy = ReportingPolicy.IGNORE`。
    - 命中条件：新增或修改的 mapper 使用了 `unmappedTargetPolicy = ReportingPolicy.IGNORE`，
      目的只是压掉未映射 warning，而不是逐个字段明确处理。
    - 怎么改：删除该 ignore 配置，让 warning 暴露；或者对每个确认不应映射的字段使用显式
      `@Mapping(target = "xxx", ignore = true)`，并优先补齐实际缺失的字段映射。
    - ⚠️ 守卫：如果确实是框架级基础 mapper、DTO 边界或历史兼容需要统一忽略，必须在代码
      附近有明确原因说明；否则不要自动加 ignore。

24. **`@ExpandForDelegate` 委托字段统一命名和访问级别**：通过 `@ExpandForDelegate`
    展开的委托字段，字段名必须统一叫 `properties`，并且必须禁止 Lombok 为该字段本身生成
    getter / setter。
    - 命中条件：字段标注了 `@ExpandForDelegate`。
    - 怎么改：确保同一个字段同时具备 `@Delegate`、`@ExpandForDelegate`、
      `@Getter(AccessLevel.NONE)`、`@Setter(AccessLevel.NONE)`，字段名改为 `properties`。
      如果原字段名是 `xxxStruct` / `workflowDefinitionStruct` / `outboundOrderStruct` 等，统一
      重命名为 `properties`。
    - 这条属于安全可自动修复项：注解组合和字段名是项目约定，改法唯一；修改后同步更新
      本类内部对该委托字段的直接引用。
    - ⚠️ 守卫——如果外部代码直接访问该字段名，或存在序列化 / 反射 / 框架配置显式引用
      原字段名，先列为「需决策」，不要静默改。
    ```java
    // 反例
    @Delegate
    @ExpandForDelegate
    @Getter(AccessLevel.PRIVATE)
    @Setter(AccessLevel.PRIVATE)
    private WorkflowDefinitionStruct workflowDefinitionStruct = new WorkflowDefinitionStruct();

    // 正例
    @Delegate
    @ExpandForDelegate
    @Getter(AccessLevel.NONE)
    @Setter(AccessLevel.NONE)
    private WorkflowDefinitionStruct properties = new WorkflowDefinitionStruct();
    ```

25. **业务 Entity 不继承业务 PO，业务字段通过委托结构暴露**：`domain/entity` 中的领域实体
    不应直接继承同名业务 PO（如 `XxxDraftPo`、`XxxRecordPo`、`XxxRulePo`、
    `XxxSubmittalPo`），避免领域对象和持久化对象通过继承耦合业务字段。
    - 命中条件：领域实体形如 `class Xxx extends XxxPo implements DomainEntity`，且该 `XxxPo`
      是同一业务对象的持久化模型，不是统一 Base 类。
    - 推荐改法：Entity 继承项目统一 Base 类（如 `BaseGroupPo`）或项目约定的实体基类；将
      Entity 与 PO 共享的业务字段抽到顶级 `XxxStruct`（优先放在 `domain/repository/struct`），
      Entity 和 PO 都通过 `@Delegate @ExpandForDelegate private XxxStruct properties` 暴露字段。
      `@ExpandForDelegate` 字段继续遵守上一条规则。
    - 这条默认只列为「⚠️ 建议确认」，不要 auto-fix 静默重构。原因是抽 Struct、搬字段、补
      Entity 额外字段、调整 MapStruct / MyBatis / 序列化边界都可能影响持久化和对外契约。
    - 只有在项目已经存在可复用 Struct，且本次修改只是补齐注解、字段名或访问级别时，才可
      按上一条规则自动修复。
    ```java
    // 反例
    class WorkflowDefinitionRecord extends WorkflowDefinitionRecordPo implements DomainEntity { ... }

    // 正例
    class WorkflowDefinitionRecord extends BaseGroupPo implements DomainEntity {
        @Delegate
        @ExpandForDelegate
        @Getter(AccessLevel.NONE)
        @Setter(AccessLevel.NONE)
        private WorkflowDefinitionStruct properties = new WorkflowDefinitionStruct();
    }
    ```

26. **数据容器类和字段必须有注释**：承载数据结构的类必须写清类注释，字段必须逐个写清
    字段语义，不能只靠字段名猜含义。
    - 命中条件：DTO、VO、PO、Struct、Entity、Command、Request、Response、Result、
      Event、Message 等数据容器类缺少类级 Javadoc，或字段缺少字段级 Javadoc。
    - 怎么改：为类补一句简洁 Javadoc，说明该数据结构代表什么；为每个字段补一句简洁
      Javadoc，说明业务语义、ID 指向、时间含义、状态含义等。注释应描述领域含义，不要
      写“字段 xxx”这类空话。
    - 对 `domain/repository/struct` 中被 `@ExpandForDelegate` 复用的公共字段结构要求更严：
      类和所有字段必须有注释，因为它会同时影响 Entity、PO、Draft、Record 等多个模型。
    - ⚠️ 守卫——如果字段含义不明确、缩写无法确认、或注释可能改变业务理解，不要编造；
      列为「需决策」，要求补充准确业务含义。
    ```java
    // 反例
    class AemProblemStruct {
        private String rwdObjectId;
    }

    // 正例
    /**
     * AEM 问题公共字段结构。
     */
    class AemProblemStruct {
        /**
         * 关联的 RWD 对象 ID。
         */
        private String rwdObjectId;
    }
    ```

27. **优先用 Lombok 简化样板代码**：项目里已经使用 Lombok 的类，不应继续保留纯样板的
    构造器、getter、setter、`equals` / `hashCode` / `toString` 等代码。
    - 命中条件：类中的构造器只是为 `final` 字段或 `@NonNull` 字段赋值，没有校验、默认值
      计算、注册回调、事件发布等业务逻辑；或类中存在纯样板 accessor / 常见对象方法。
    - 怎么改：构造器注入优先改为 `@RequiredArgsConstructor`，纯 getter / setter 按第 22 条
      改为 `@Getter` / `@Setter`，常见对象方法可按实际需要改为 `@EqualsAndHashCode`、
      `@ToString` 或 `@Data`。有 Spring `@Value`、`@Qualifier`、`@Autowired` 等构造器参数
      注解时，优先把注解移到对应字段，并确认项目 `lombok.config` 已配置
      `lombok.copyableAnnotations`；配置缺失时先补配置或降级为「需决策」，不要让注入失效。
    - ⚠️ 守卫——构造器里有非赋值逻辑、多构造器兼容、构造参数顺序承担外部反射 / 序列化 /
      框架契约，或类尚未使用 Lombok 且引入 Lombok 会改变团队约定时，不要静默改。
    ```java
    // 反例
    @Service
    class OrderService {
        private final OrderRepository orderRepository;

        OrderService(OrderRepository orderRepository) {
            this.orderRepository = orderRepository;
        }
    }

    // 正例
    @Service
    @RequiredArgsConstructor
    class OrderService {
        private final OrderRepository orderRepository;
    }
    ```
