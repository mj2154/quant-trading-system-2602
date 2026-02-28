---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: b6756e4d2d7691fae5684e27ff86d977
    PropagateID: b6756e4d2d7691fae5684e27ff86d977
    ReservedCode1: 30450220493d322fe9faeca403b4caf4d6ca820a7d3e1d7e796ea4750be485137be1ae5102210091d6a3785b5ce83d9acbf426254cdf8019126d4d2826044a4fc997458b69d40a
    ReservedCode2: 3046022100d9e720f9cebfa924fe033015d8d205e1f2eee959054b11a6361970c7582df679022100ba99383767514a56bab3b0475f88390f9107a481f66d7fcf699701f688738862
---

# 这次玩点不一样的，使用 BrowserView 优化 Electron 应用的性能

**作者：** 长桥技术团队  
**发布时间：** 2024-09-11  
**阅读量：** 3,022  
**阅读时间：** 11分钟

## 概述

为了提升长桥桌面端应用 Longbridge Pro 的整体性能体验，在相当长的时间里，长桥桌面端团队一直在追踪 Electron 中体验特性 BrowserView 组件的开发进展以及 Bug 修复状态。

在 Electron v26 版本后，BrowserView 组件终于趋于稳定，长桥桌面端团队就开始尝试使用 BrowserView 组件来优化 Longbridge Pro 的整体性能，在完成了阶段性的优化并发布后，在这里记录一下探索优化并最终选择了 BrowserView 方案的过程。

## 什么是 Longbridge Pro

Longbridge Pro 是长桥推出的一款专门针对股票专业投资者的专业交易前台软件，根据投资者自身操作习惯自定义面板组件和内容排布，设置不同操作快捷键，在前台实现日常的盯盘交易、订单处理等操作。

### 核心特性

* **灵活的自定义面板组件布局**
* **支持上百种技术指标**
* **丰富的快捷键设置支持全键盘操作**
* **面向全球市场设计，多语言多系统支持**

> 要使用 Longbridge Pro 可以前往 [longportapp.com/zh-CN/download/longbridge](https://link.juejin.cn?target=https%3A%2F%2Flongportapp.com%2Fzh-CN%2Fdownload%2Flongbridge) 下载安装使用体验。

## 问题背景

在 Longbridge Pro 中，使用了类似浏览器的结构，给用户提供了灵活的自定义面板布局，并且提供了丰富的组件可供用户使用。

对于系统自带的布局，或者是用户创建的每个自定义布局页面，都支持自由拼接各种复杂的组件，例如自选列表、行情图表、交易面板、盘口等，并这些组件需要在一个页面中全屏展示。

以下是一些系统预设页面的截图（个股、行情、选股器）：

* 个股页面截图
* 行情页面截图  
* 选股器页面截图

### 用户反馈的问题

在用户使用的过程中，我们会收到一些反馈，为什么各个页面在切换时，会有延迟，点击以后，并不是马上展示点击的标签页，而是要过一会才能展示出来对应的页面。

对于用户来说，期望的是在鼠标点击不同的标签页后，能立马展示对应的面板。针对这一诉求，我们开始优化整体标签页的切换体验，先从前端的角度来尝试解决一下。

## 从前端框架解决

在一开始优化时，我们从前端开发的角度来观察如何优化这个标签页切换体验，尝试从前端框架中找到解决方案。

在 Vue 中，可以使用两种方式来切换整体标签页的显示与否：

### 方案一：v-if 指令
使用了 v-if 指令，确保了在切换时，条件区块内的事件监听器和子组件都会被销毁与重建，但这个方式在 view 切换的场景下，代价比较昂贵，而我们的目标是能够更接近 native 的切换体验

### 方案二：v-show 指令
之后为了减少组件重建的成本，改成了使用 v-show 指令，会在 DOM 渲染中保留该元素，元素无论初始条件如何，始终会被渲染，只有 CSS `display` 属性会被切换。

上述两种方式在常见的前端标签页切换场景中基本已经能够满足秒切的目的。

### 遇到的问题

但是在 Longbridge Pro 中，每个标签页 view 内的每个组件复杂度都很高，导致即使只进行了 `display` 属性切换，由于触发了每个组件的重排和重绘使得在切换页面时花费大量时间在 Rendering 阶段，产生了 long task。

如下图，通过开发者工具的 Performance 监测可以观测到问题：

* Performance 监测截图

### DOM 数量统计

同时我们也统计了页面内 DOM 数，侧面证明了组件复杂度：

* Body 内的 DOM 数：**15,170**
* 个股：**4,155**
* 行情：**2,561**
* 选股器：**975**

中间也有想过是否使用 `<keep-alive>` 组件进行包裹，但是这个方案因为只是缓存被移除的组件实例，所以切换时，还需要插入数量巨大的 DOM 节点，也一样会遇到 Rendering 需要花费大量时间的问题

## 基于 Electron 特有的 BrowserView 方案

当存渲染进程的方案没找到解决方案时，这个时候我们提出一个想法，是否能将页面切换做成和 Chrome 的 Tab 切换一样呢，即使是不同的网站，在切换时，也不会出现加载的问题。

这时在翻阅 Electron 时，一个还处于实验中的 API - BrowserView 给我们实现这一效果带来了希望。

### BrowserView 官方介绍

官方文档是这么介绍 BrowserView 的：

> `BrowserView` 被用来让 **`BrowserWindow`** 嵌入更多的 web 内容。它就像一个子窗口，除了它的位置是相对于父窗口。这意味着可以替代`webview`标签。

### 渲染进程观察

经测试，每启动一个 BrowserView 就会多增加一个渲染进程，观察了一下 Chrome 的表现，他的每一个 Tab 也是一个渲染进程（如下图）。

* Chrome 渲染进程截图

Electron 本身就是基于 Chromium 实现，那么按 Chrome 浏览器的思路来优化，应该是一个可行的方向，那就使用 BrowserView 来尝试优化一下。

### 布局架构设计

确定了使用 BrowserView 方案后，需要先完成底层结构的设计。

根据现在 Longbridge Pro 的信息组件架构，将整个桌面端的组件进行拆解，根据 BrowserView 的特性，形成以下架构设计：

* BrowserView 架构设计图

主窗口加载 header 和 footer，内容区域占位，有几个 view 就对应建几个 BrowserView，并将他们定位在主窗口的内容占位区域。

由于 BrowserView 没有提供 hide API，所以一开始是做成像图层一样叠在一起，当页面切换时把当前页面设置到最顶层（这里也是由于 Electron 提供的 API 里只提供了 setTopBrowserView）

后面发现有 `win.removeBrowserView(BrowserView)` API，改成了再切换时 remove 掉对应的 `BrowserView`，这个方法只是在 window 级别移除了，并不会销毁 `BrowserView` 对象本身，所以内存和资源还是会占用，但是好处是可以释放部分窗口资源（如渲染层、绘制资源），且由于其内部状态、加载的内容和运行的脚本仍然保留，方便后续重新添加时快速恢复。当然这里在 remove 后，通过 `BrowserWindow.fromWebContents(webContents)` 就无法获取到 remove 后对应 `BrowserView` 曾经添加的 wid 了，因为它已经不归属于任何 window，对应在一些跨窗口通信上需要做判定处理。

### 数据通信处理

因为 Longbridge Pro 本身就是多进程的项目，所以我们的数据中心是放在 main 进程的，这个时候比如一只股票的行情变动时，是数据中心进行广播到所有的渲染进程，那么当有多个 `BrowserView` 时，如何避免其他 `BrowserView` 的界面由于数据中心的通知导致页面时也会跟着一起实时渲染呢？

处理办法也简单，我们设计一个 `BrowserViewManager`，里面维护了一些数据状态：

* `viewList` 决定了顶部 tab 栏的页面顺序
* `viewsInfo` 里维护了具体每个 tab 的名称，是否是系统 tab 还是自定义 tab 等业务属性
* `viewsBrowserView` 里建立了 viewKey 和 BrowserView 实例的关系
* `currentViewKey` 显示了当前用户正在看的 view

#### BrowserViewManager 代码示例

```typescript
type ViewKey = string

class BrowserViewManager {
  public viewsBrowserView: Record<ViewKey, BrowserView> = {}
  
  /**
   * 每个 view 的具体数据包
   * (注意 渲染进程 和 web 进程均不修改改值，修改在 main 进程中进行分析，这里只做同步和检测)
   */
  public viewsInfo: ViewsInfo = {}
  
  /** 所有 view 的排序 */
  public viewsList: ViewKey[] = []
  
  /** 当前 viewKey */
  public currentViewKey: ViewKey = ''
}
```

通过这个基本的数据结果，我们可以在渲染进程判断，当前页面的 viewKey 是否等于 currentViewKey 来判断是否是激活页面。并在渲染构建了一个自定义 ref，实现成只有当前是激活页面时，才会触发更新，来确保页面上响应式的行为只有在激活页面场景下才触发，类似于实现了 viewEnter 和 viewLeave。

延伸探索，调研 Chrome 会发现，Chrome 本身多 Tab 模式也做了类似的优化，甚至更彻底一些，他会根据页面距离上一次访问时间等条件通过打分算分进行打分，根据分值去判断是否要 discard 这个页面，类比我们的场景就是在 discard 后连 BrowserView 对象都销毁了，下次切换时，会重新创建该页面。这样做好处是长期不用的页面，就不会再占用系统资源了，但我们没做到这么彻底是考虑到用户大多时候会在我们的 tab 下高频切换，使用场景还不太一样。

* Chrome Tab 优化策略截图

当然上面的探索不是没有意义的，这里还有进一步优化的空间。比如我们可以去监测用户本机环境，是否系统资源较为紧张，如果本身已经较为紧张了，也可以考虑做类似的 discard 操作，手动销毁长期没有访问的 BrowserView，释放相关资源。

## 复杂问题处理

在引入 BrowserView 之后，相比之前全部页面在一个 Window，也随之而来一些复杂的问题需要处理。

### 弹出层跨窗口

在之前使用一个 Window 展示所有内容时，所有弹出层窗口都可以由前端控制，但是在改成使用 BrowserView 显示组件后，组件内部的内容无法超出 BrowserView 的范围，因此对于各种弹出层窗口都需要进行特殊处理。

* 跨窗口展示示例图一
* 跨窗口展示示例图二

#### 解决方案

* **图一**这种 UI 上必须要跨窗口的展示的，同样是需要新建一个 BrowserView 进行定位展示
* **图二**这种触发部分在一个 BrowserView，显示部分在另一个 BrowserView 的，通过 IPC 通信进行通知，当前 BrowserView 接收通知并展示自己区域的内容

### 创建过多 BrowserView 会导致卡顿

在用户启动桌面端时，最开始的界面初始化，包含了非常多的组件和界面，在没有优化时，会一次性创建过多的 BrowserView，这将会堵塞住整个页面的渲染，在开发模式下时特别明显。

#### 解决方案

优先创建 currentViewKey 对应的 BrowserView，并在当前 BrowserView did-finish-load 时，再创建其余的 BrowserView。另外在其余 BrowserView 未创建时，用户进行了 Tab 切换等操作，需要能检测到 BrowserView 未创建并且立即进行创建和加载显示内容。

### Toast、Notification、Dialog 提示

在之前，Longbridge Pro 应用内部的 Toast、Notification、Dialog 都是主窗口的 DOM 层级渲染的，在主窗口内部其他组件替换为使用 BrowserView 来渲染后，这些 Toast、Notification、Dialog 都将被 BrowserView 遮挡，无法正确展示。

#### 解决方案

**Toast**
* Renderer 层调用的，渲染在当前 Renderer 窗口或 BrowserView 上
* Main 进程调用的，渲染在当前 focus 的 BrowserView 上

**Notification**
* 和 Toast 方案一致，且多了消息中心处理常驻的一些提示

**Dialog**
* 用窗口级 Dialog 替换 DOM 级的 Dialog

### 全局快捷键失效

原来全局快捷键注册在主窗口，但是当 focus BrowserView 之后，主窗口的快捷键无法被触发，全局快捷键失效。

#### 解决方案

新增主窗口级别快捷键
* 主窗口注册快捷键事件，触发后执行回调
* BrowserView 也注册相同的快捷键，触发后通知主窗口执行回调

## 优化效果对比

### 优化前

可以看到在优化前，使用鼠标切换几次标签页之后，后续的切换动作已经不太跟随鼠标点击事件马上响应了，会有一个延迟。

* 优化前效果截图

### 优化后

在优化后，标签页的显示一直都能保持跟随鼠标动作响应，切换速度没有变慢。

* 优化后效果截图

## Electron API 变更

在包含了 BrowserView 优化的 Longbridge Pro 发布后，我们观察到 Electron 发布了 30.0.0 版本，其中 BrowserView API 已经被废弃，换成了 WebContentsView，继承的 `View`类。

这样从视图结构的角度观察其实更合理些，毕竟它本身也是 view 的形式被 add 到了 window 上。业务上改造成本不大，本质思想都是一样的，只是语法糖需要调整下。

* Electron API 变更截图

## 欢迎使用 Longbridge Pro

* Longbridge Pro 宣传图

长桥 Longbridge Pro 是由长桥证券为专业投资者而开发的专业交易平台，具有以下特点：

### 核心优势

**机遇由你布局**
分屏盯盘，多端联动，无缝操纵；各类卡片式自定义组件任你调遣，你的交易由你布局。

**指间运筹画策**
超百种技术指标，联手 Trading View 12 种多维度划线工具，把你的策略推向价值新高度。

**大招一键即发**
一键快捷下单，配合港股涡轮牛熊、美股期权等多种衍生品，交易高手放大招得心应手。

> 欢迎下载使用：[longportapp.com/zh-CN/download/longbridge](https://link.juejin.cn?target=https%3A%2F%2Flongportapp.cn%2Fzh-CN%2Fdownload%2Flongbridge%3Fchannel%3DWO000020)

---

**作者信息**

* 长桥技术团队
* 文章数：3
* 阅读量：5.9k
* 粉丝数：52

## 目录

- [什么是 Longbridge Pro](#heading-0)
- [问题背景](#heading-1)
- [从前端框架解决](#heading-2)
- [基于 Electron 特有的 BrowserView 方案](#heading-3)
  - [布局架构设计](#heading-4)
  - [数据通信处理](#heading-5)
- [复杂问题处理](#heading-6)
  - [弹出层跨窗口](#heading-7)
  - [创建过多 BrowserView 会导致卡顿](#heading-8)
  - [Toast、Notification、Dialog 提示](#heading-9)
  - [全局快捷键失效](#heading-10)
- [优化效果对比](#heading-11)
  - [优化前](#heading-12)
  - [优化后](#heading-13)
- [Electron API 变更](#heading-14)
- [欢迎使用 Longbridge Pro](#heading-15)