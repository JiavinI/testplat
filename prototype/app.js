// 一次性设计验证原型：Project 是一级上下文，所有数据均在内存中按项目隔离。
const projectData = {
  go2: {
    code: 'GO2',
    name: '订单与履约',
    description: '采购订单、履约与门户验证',
    revision: 'go2-release-2026.09.23',
    targets: ['go2-api', 'go2-web'],
    connection: 'go2-test-readonly',
    identities: 3,
    quickAsset: '订单可见性验证',
    quickDescription: 'API 建单后，通过独立 Browser 会话搜索订单并完成清理。',
    metrics: { today: 12, passRate: '100%', duration: '02:18', failures: 0 },
    assets: [
      { kind:'Scenario', name:'订单可见性验证', id:'go2.order.visible', desc:'API 建单 -> Browser 搜索 -> 清理', tags:['smoke','browser'], updated:'今天 10:42', result:'pass' },
      { kind:'Scenario', name:'测试用户 SQL 探针', id:'go2.sql.user-id', desc:'MySQL 只读查询，结果恰好一行', tags:['sql','read-only'], updated:'昨天 18:06', result:'pass' },
      { kind:'ApiCheckSet', name:'订单创建接口校验', id:'go2.api.order-create', desc:'正向 + 业务失败变体（4 项）', tags:['api-check'], updated:'9 月 20 日', result:'pass' }
    ],
    runs: [
      { id:'run_go2_20260923_1042', asset:'订单可见性验证', trigger:'手动运行', time:'10:42:03', duration:'02:15', result:'pass' },
      { id:'run_go2_20260923_0931', asset:'订单创建接口校验', trigger:'API', time:'09:31:04', duration:'00:48', result:'pass' },
      { id:'run_go2_20260922_1806', asset:'测试用户 SQL 探针', trigger:'定时任务', time:'昨天 18:06', duration:'00:03', result:'pass' }
    ]
  },
  e3e3: {
    code: 'E3E3',
    name: '交易与售后',
    description: '多 SKU 交易、拿货、退货与退款',
    revision: 'e3e3-release-2026.09.23',
    targets: ['e3e3-api'],
    connection: 'e3e3-test-readonly',
    identities: 5,
    quickAsset: '多 SKU 余额支付',
    quickDescription: '精确选择多个商品，创建单笔订单并完成一次余额支付。',
    metrics: { today: 7, passRate: '85.7%', duration: '05:36', failures: 1 },
    assets: [
      { kind:'Scenario', name:'多 SKU 余额支付', id:'e3e3.order.pay', desc:'商品选择 -> 建单 -> 余额支付', tags:['smoke','api'], updated:'今天 09:58', result:'pass' },
      { kind:'Scenario', name:'部分售后与整批退款', id:'e3e3.order.refund', desc:'拿货 -> 售后 -> 退货 -> 退款', tags:['核心链路','api'], updated:'昨天 16:02', result:'fail' },
      { kind:'ApiCheckSet', name:'退款接口校验', id:'e3e3.api.refund-check', desc:'退款接口正向与业务失败变体', tags:['api-check'], updated:'9 月 21 日', result:'pass' }
    ],
    runs: [
      { id:'run_e3e3_20260923_0958', asset:'多 SKU 余额支付', trigger:'手动运行', time:'09:58:12', duration:'03:42', result:'pass' },
      { id:'run_e3e3_20260923_0817', asset:'部分售后与整批退款', trigger:'定时任务', time:'08:17:22', duration:'06:29', result:'fail' },
      { id:'run_e3e3_20260922_1641', asset:'退款接口校验', trigger:'API', time:'昨天 16:41', duration:'01:16', result:'pass' }
    ]
  }
};

// 演示数据仅供核对信息结构；此处的账号、请求和 SQL 均不是运行配置。
const catalog = {
  go2: [
    { id:'go2.api.order-create', kind:'ApiCheckSet', module:'订单 / 创建', name:'订单创建接口校验', target:'go2-api', actor:'buyer.primary', summary:'POST /api/orders', variants:[
      {name:'正常 · 创建待支付订单', method:'POST', path:'/api/orders', request:'{"productNumber":"GO2-DEMO-001","quantity":1}', expect:'HTTP 200 · orderNo 非空'},
      {name:'异常 · 数量为零', method:'POST', path:'/api/orders', request:'{"productNumber":"GO2-DEMO-001","quantity":0}', expect:'业务失败 · 数量必须大于零'},
      {name:'异常 · 商品不存在', method:'POST', path:'/api/orders', request:'{"productNumber":"NOT-FOUND","quantity":1}', expect:'业务失败 · 商品不存在'}] },
    { id:'go2.order.visible', kind:'Scenario', module:'订单 / 查询', name:'订单可见性验证', target:'go2-api + go2-web', actor:'buyer.primary', summary:'API 建单 → Browser 搜索 → 清理', steps:[
      {name:'API · 创建待支付订单', target:'go2-api', value:'POST /api/orders\n{"productNumber":"GO2-DEMO-001","quantity":1}', expect:'HTTP 200 · 返回 orderNo'},
      {name:'Browser · 搜索订单', target:'go2-web', value:'打开 /orders · 以步骤输出 orderNo 搜索', expect:'订单列表显示相同 orderNo'},
      {name:'Cleanup · 取消待支付订单', target:'go2-api', value:'POST /api/orders/{orderNo}/cancel', expect:'订单状态 CANCELLED'}] },
    { id:'go2.sql.user-id', kind:'Scenario', module:'用户 / 数据验证', name:'测试用户 SQL 探针', target:'go2-test-readonly', actor:'无业务身份', summary:'只读 SQL 查询并校验单行', steps:[
      {name:'SQL · 查询测试用户', target:'go2-test-readonly', value:"select id from db_go2.user where username = '刘高杰' and source = 'e3e3';", expect:'恰好 1 行 · id 非空'}] },
    { id:'go2.contract.order', kind:'ApiContract', module:'订单 / 创建', name:'创建订单接口定义', target:'go2-api', summary:'POST /api/orders · 供接口校验引用', reusable:true },
    { id:'go2.data.order', kind:'DataSet', module:'订单 / 创建', name:'订单固定测试数据', target:'—', summary:'productNumber、quantity 等可复用业务数据', reusable:true },
    { id:'go2.page.order', kind:'PageContract', module:'订单 / 查询', name:'订单页面定位', target:'go2-web', summary:'订单列表、搜索框和状态元素', reusable:true }
  ],
  e3e3: [
    { id:'e3e3.api.refund-check', kind:'ApiCheckSet', module:'售后 / 退款', name:'退款接口校验', target:'e3e3-api', actor:'refund.operator', summary:'POST /api/refunds', variants:[
      {name:'正常 · 申请退款', method:'POST', path:'/api/refunds', request:'{"orderNo":"DEMO-ORDER-001","amount":12.50}', expect:'HTTP 200 · 返回 refundNo'},
      {name:'异常 · 金额超限', method:'POST', path:'/api/refunds', request:'{"orderNo":"DEMO-ORDER-001","amount":99999}', expect:'业务失败 · 金额超限'}] },
    { id:'e3e3.order.pay', kind:'Scenario', module:'交易 / 支付', name:'多 SKU 余额支付', target:'e3e3-api', actor:'buyer.primary', summary:'选商品 → 建单 → 一次支付 → 只读确认', steps:[
      {name:'API · 精确选择两个商品', target:'e3e3-api', value:'GET /api/products?keyword=演示\n按 productNumber 选 DEMO-001、DEMO-002', expect:'两个商品均唯一命中'},
      {name:'API · 创建订单', target:'e3e3-api', value:'POST /api/orders\n{"items":[{"productNumber":"DEMO-001","quantity":1},{"productNumber":"DEMO-002","quantity":2}]}', expect:'返回待支付 orderNo'},
      {name:'API · 余额支付', target:'e3e3-api', value:'POST /api/orders/{orderNo}/pay\n{"method":"balance"}', expect:'成功响应 · 不自动重放'},
      {name:'API · 确认订单', target:'e3e3-api', value:'GET /api/orders/{orderNo}', expect:'status = PAID'}] },
    { id:'e3e3.order.refund', kind:'Scenario', module:'售后 / 退款', name:'部分售后与整批退款', target:'e3e3-api', actor:'refund.operator', summary:'拿货 → 售后 → 退货 → 退款', steps:[
      {name:'API · 查询可售后订单', target:'e3e3-api', value:'GET /api/orders/{orderNo}/items', expect:'返回每个 orderItemId'},
      {name:'API · 发起售后', target:'e3e3-api', value:'POST /api/after-sales\n{"orderItemId":"DEMO-ITEM-001"}', expect:'返回售后单号'},
      {name:'API · 确认退款', target:'e3e3-api', value:'GET /api/refunds/{refundNo}', expect:'status = REFUNDED'}] },
    { id:'e3e3.flow.refund-prepare', kind:'Flow', module:'售后 / 退款', name:'退款前置数据准备', target:'e3e3-api', summary:'按输入准备订单与售后单引用', reusable:true },
    { id:'e3e3.data.refund', kind:'DataSet', module:'售后 / 退款', name:'退款业务测试数据', target:'—', summary:'退款金额和业务备注样本', reusable:true },
    { id:'e3e3.contract.refund', kind:'ApiContract', module:'售后 / 退款', name:'退款接口定义', target:'e3e3-api', summary:'POST /api/refunds · 响应语义', reusable:true }
  ]
};

const configData = {
  go2: { systems:[['go2-api','API 地址 · test 绑定'],['go2-web','Web 地址 · test 绑定']], identities:[['buyer.primary','go2-api / go2-web · 分通道 Profile'],['buyer.secondary','并发隔离身份槽位']], connections:[['go2-test-readonly','MySQL · 只读'],['redis-vcode','仅认证 Adapter 获取验证码']], public:['go2.contract.order · ApiContract','go2.data.order · DataSet','订单页面定位 · PageContract'] },
  e3e3: { systems:[['e3e3-api','API 地址 · test 绑定']], identities:[['buyer.primary','e3e3-api · API Profile'],['refund.operator','售后操作身份']], connections:[['e3e3-test-readonly','MySQL · 只读'],['redis-vcode','仅认证 Adapter 获取验证码']], public:['e3e3.flow.refund-prepare · Flow','e3e3.data.refund · DataSet','e3e3.contract.refund · ApiContract'] }
};

const params = new URLSearchParams(location.search);
const state = {
  view: 'overview',
  projectId: projectData[params.get('project')] ? params.get('project') : 'go2',
  selectedAsset: '', selectedRun: '', environment:'test', rawVisible: false,
  module:'全部模块', assetType:'全部类型', query:'', reportStep:0
};

const nav = [
  {id:'overview', icon:'⌂', label:'项目总览'},
  {id:'assets', icon:'◇', label:'测试资产'},
  {id:'runs', icon:'◷', label:'运行记录'},
  {id:'projects', icon:'▦', label:'项目配置'},
  {id:'audit', icon:'≡', label:'审计事件'}
];

const currentProject = () => projectData[state.projectId];
const pageName = active => ({overview:'项目总览',assets:'测试资产',runs:'运行记录',projects:'项目配置',audit:'审计事件'}[active] || '运行报告');
const currentCatalog = () => catalog[state.projectId];
const findAsset = id => currentCatalog().find(asset=>asset.id===id);
const findRun = () => currentProject().runs.find(run=>run.id===state.selectedRun) || currentProject().runs[0];
const escapeHtml = value => String(value).replace(/[&<>"']/g, char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const projectOptions = () => Object.entries(projectData).map(([id,p]) => `<option value="${id}" ${id===state.projectId?'selected':''}>${p.code} · ${p.name}</option>`).join('');

function status(result, text) {
  return `<span class="result ${result}"><span class="dot"></span>${text || (result==='pass'?'通过':result==='fail'?'失败':'运行中')}</span>`;
}

function shell(content, active='overview') {
  const project = currentProject();
  return `<div class="shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">TP</div><div><strong>TestPlat</strong><span>测试执行平台</span></div></div>
      <div class="project-switch">
        <label>当前测试项目</label>
        <select data-project-switch aria-label="当前测试项目">${projectOptions()}</select>
        <small>${currentCatalog().filter(a=>!a.reusable).length} 个可运行资产 · ${currentCatalog().length} 个资产</small>
      </div>
      <div class="nav-section">PROJECT WORKSPACE</div>
      <div class="nav">${nav.map(item=>`<button class="${active===item.id?'active':''}" data-nav="${item.id}"><span class="nav-icon">${item.icon}</span>${item.label}</button>`).join('')}</div>
      <div class="side-bottom"><div class="user"><div class="avatar">刘</div><div><b>刘高杰</b><small>测试开发 · 基础用户</small></div></div></div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="crumbs">TestPlat <span>/</span> ${project.code} <span>/</span> <b>${pageName(active)}</b></div>
        <div class="top-actions"><div class="env-pill"><span class="dot"></span>${project.code} / ${state.environment}</div><button class="top-link" data-nav="projects">项目配置</button><button class="top-link" data-toast="这是 ${project.code} 项目的通知入口">通知 <span style="color:var(--teal)">●</span></button></div>
      </header>${content}
    </main>
  </div>`;
}

function metrics() {
  const m = currentProject().metrics;
  return `<div class="metrics">
    <div class="panel metric"><div class="label">今日运行</div><div class="value">${m.today}</div><div class="delta">当前项目</div></div>
    <div class="panel metric"><div class="label">通过率</div><div class="value">${m.passRate}</div><div class="delta">最近 7 天</div></div>
    <div class="panel metric"><div class="label">平均耗时</div><div class="value">${m.duration}</div><div class="delta dim">最近 7 天</div></div>
    <div class="panel metric"><div class="label">待处理失败</div><div class="value">${m.failures}</div><div class="delta ${m.failures?'':'dim'}" style="${m.failures?'color:var(--red)':''}">${m.failures?'需要关注':'暂无'}</div></div>
  </div>`;
}

function assetRows(items) {
  return items.map(a=>`<tr><td><div class="asset-name"><div class="asset-mark">${a.kind==='ApiCheckSet'?'A':a.kind==='Scenario'?'S':'Y'}</div><div><b>${a.name}</b><small>${a.id}</small></div></div></td>
    <td><span class="tag">${a.kind}</span></td><td>${a.summary}</td><td><code>${a.target}</code></td>
    <td><button class="btn" data-asset="${a.id}">${a.reusable?'查看定义':'查看与运行'}</button></td></tr>`).join('');
}

function runRows(limit) {
  const project = currentProject();
  return project.runs.slice(0,limit || project.runs.length).map(run=>`<tr class="clickable" data-open-report="${run.id}">
    <td><b>${run.id}</b><small style="display:block;color:var(--muted);margin-top:3px">${run.asset}</small></td>
    <td>${project.code} / ${run.environment || 'test'}</td><td>${run.trigger}</td><td>${run.time}</td><td>${run.duration}</td><td>${status(run.result)}</td>
  </tr>`).join('');
}

function overviewA() {
  const p = currentProject();
  return shell(`<div class="content">
    <div class="eyebrow">${p.code} PROJECT WORKSPACE</div><h1>${p.name}</h1><p class="lead">${p.description}。当前页面只展示 ${p.code} 的资产、配置和运行。</p>
    <div class="hero-grid" style="margin-top:25px">
      <section class="panel panel-pad run-card"><div class="eyebrow">QUICK RUN · ${p.code}</div><h2>${p.quickAsset}</h2><p>${p.quickDescription}</p><button class="btn" data-run="${p.quickAsset}">▶ 运行此场景</button><div class="run-meta"><div><b>${p.metrics.duration}</b>平均耗时</div><div><b>${p.runs.length}</b>最近运行</div><div><b>${p.metrics.passRate}</b>近 7 日通过</div></div></section>
      <section class="panel panel-pad"><div class="panel-title" style="padding:0 0 5px;border:0"><b>${p.code} / test 运行依赖</b><span>${p.revision}</span></div><div class="health">${p.targets.map(t=>`<div class="row"><span>目标系统 · ${t}</span><span class="status"><i class="dot"></i>已绑定</span></div>`).join('')}<div class="row"><span>认证 Profile</span><span class="status"><i class="dot"></i>${p.identities} 个可用</span></div><div class="row"><span>SQL · ${p.connection}</span><span class="status"><i class="dot"></i>只读</span></div></div></section>
    </div>${metrics()}
    <div class="section-head"><div><h2>${p.code} 最近运行</h2><p>不会混入其他项目的运行记录</p></div><button class="btn" data-nav="runs">查看全部 →</button></div>
    <div class="panel"><table class="table"><thead><tr><th>运行 / 资产</th><th>项目 / 环境</th><th>触发方式</th><th>开始时间</th><th>耗时</th><th>结果</th></tr></thead><tbody>${runRows(3)}</tbody></table></div>
  </div>`, 'overview');
}

function assetsView() {
  const p = currentProject();
  const items=currentCatalog().filter(a=>(state.module==='全部模块'||a.module===state.module) && (state.assetType==='全部类型'||(state.assetType==='可运行'?!a.reusable:a.reusable)) && (a.name+a.id+a.summary).toLowerCase().includes(state.query.toLowerCase()));
  const groups=[['单接口用例',items.filter(a=>a.kind==='ApiCheckSet')],['业务流程用例',items.filter(a=>a.kind==='Scenario')],['公共 YAML 资产',items.filter(a=>a.reusable)]];
  const modules=[...new Set(currentCatalog().map(a=>a.module))];
  return shell(`<div class="content"><div class="eyebrow">${p.code} / ${p.revision}</div><h1>测试资产</h1><p class="lead">单接口正常/异常校验与业务流程按模块归档；公共 YAML 是不可直接运行的资产定义。</p>
    <div class="asset-workspace"><aside class="asset-tree"><b>模块</b><button class="${state.module==='全部模块'?'active':''}" data-module="全部模块">全部模块 <small>${currentCatalog().length}</small></button>${modules.map(m=>`<button class="${state.module===m?'active':''}" data-module="${m}">${m} <small>${currentCatalog().filter(a=>a.module===m).length}</small></button>`).join('')}<div class="tree-rule"></div><button data-nav="projects">项目配置 ↗</button></aside>
    <div class="asset-content"><div class="filterbar"><input data-asset-search value="${escapeHtml(state.query)}" placeholder="搜索资产名称或 ID" /><select data-asset-type><option ${state.assetType==='全部类型'?'selected':''}>全部类型</option><option ${state.assetType==='可运行'?'selected':''}>可运行</option><option ${state.assetType==='公共 YAML'?'selected':''}>公共 YAML</option></select></div>
    ${groups.map(([label,list])=>`<section class="asset-band"><div class="section-head"><div><h2>${label} <span class="tag">${list.length}</span></h2></div></div>${list.length?`<div class="panel table-scroll"><table class="table"><thead><tr><th>资产</th><th>类型</th><th>内容摘要</th><th>目标引用</th><th></th></tr></thead><tbody>${assetRows(list)}</tbody></table></div>`:`<div class="empty-line">当前筛选下无此类资产</div>`}</section>`).join('')}</div></div></div>`, 'assets');
}

function assetView() {
  const a=findAsset(state.selectedAsset) || currentCatalog()[0];
  const entries=a.variants||a.steps||[];
  return shell(`<div class="content"><button class="btn ghost" data-nav="assets">← 返回测试资产</button><div class="section-head"><div><div class="eyebrow">${currentProject().code} / ${a.module} / ${a.kind}</div><h1>${a.name}</h1><p class="lead"><code>${a.id}</code> · ${a.summary}</p></div>${!a.reusable?`<button class="btn primary" data-run="${a.id}">▶ 选择环境并运行</button>`:''}</div>
    <div class="detail-meta"><span>发布修订 <code>${currentProject().revision}</code></span><span>目标 <code>${a.target}</code></span><span>执行身份 <code>${a.actor||'不适用'}</code></span></div>
    ${a.reusable?`<section class="asset-band"><h2>公共 YAML 资产摘要</h2><p class="lead">${a.summary}。通过稳定 ID 被同项目资产引用；环境地址和登录凭据由项目配置管理。</p><div class="detail-meta"><span>类型 <code>${a.kind}</code></span><span>稳定 ID <code>${a.id}</code></span></div></section>`:`<section class="asset-band"><h2>${a.kind==='ApiCheckSet'?'接口校验变体':'流程步骤'} <span class="tag">${entries.length}</span></h2>${entries.map((e,i)=>`<div class="detail-row"><div class="detail-index">${i+1}</div><div><b>${e.name}</b><small>${e.target||a.target}</small><div class="detail-grid"><div><label>请求 / 操作值</label><pre>${escapeHtml((e.method?`${e.method} ${e.path}\n`:'')+(e.request || e.value))}</pre></div><div><label>预期结果</label><p>${escapeHtml(e.expect)}</p></div></div></div></div>`).join('')}</section>`}</div>`, 'assets');
}

function runsView() {
  const p = currentProject();
  return shell(`<div class="content"><div class="eyebrow">${p.code} RUN HISTORY</div><h1>运行记录</h1><p class="lead">${p.code} 项目每次运行都有独立报告，点击记录查看对应请求与结果。</p><div class="section-head"><div><h2>项目运行</h2><p>${p.runs.length} 条模拟记录</p></div><button class="btn primary" data-nav="assets">选择资产运行 →</button></div><div class="panel table-scroll"><table class="table"><thead><tr><th>运行 / 资产</th><th>项目 / 环境</th><th>触发</th><th>开始时间</th><th>耗时</th><th>结果</th></tr></thead><tbody>${runRows()}</tbody></table></div></div>`, 'runs');
}

function projectsView() {
  const p = currentProject();
  const c=configData[state.projectId];
  const section=(title,rows,description)=>`<section class="config-section"><div class="section-head"><div><h2>${title}</h2><p>${description}</p></div></div><div class="config-list">${rows.map(([name,detail])=>`<div><code>${name}</code><span>${detail}</span></div>`).join('')}</div></section>`;
  return shell(`<div class="content"><div class="eyebrow">${p.code} / SETTINGS</div><h1>项目配置</h1><p class="lead">项目下分别管理运行配置与 Git 中的公共 YAML 资产；后者不保存地址或凭据。</p>
    <div class="config-nav"><a href="#environment">环境绑定</a><a href="#targets">目标系统</a><a href="#identities">被测身份与登录</a><a href="#connections">受控连接</a><a href="#public-yaml">公共 YAML</a></div>
    <section class="config-section" id="environment"><div class="section-head"><div><h2>环境绑定</h2><p>一次运行只选一个环境；分别解析目标系统与受控连接。</p></div></div><div class="config-list"><div><code>test</code><span>${p.targets.length} 个目标系统 · MySQL 只读 · 认证 Profile 已绑定</span></div>${state.projectId==='go2'?'<div><code>dev</code><span>仅 go2-api 和 go2-web 已绑定 · SQL 用例不可运行</span></div>':''}</div></section>
    <div id="targets">${section('目标系统 Target System',c.systems,'被测业务应用的 API / Web 部署绑定')}</div>
    <div id="identities">${section('执行身份与认证 Profile',c.identities,'actorRef 是确定的逻辑身份；项目/环境/目标/通道解析登录 Profile')}</div>
    <div class="config-section"><div class="section-head"><div><h2>登录策略与账号</h2><p>旧 config 的身份、Profile、路由和认证流程作为能力参考；新资产显式声明 actorRef。</p></div></div><div class="config-list"><div><code>actorRef → Profile</code><span>逻辑身份按环境、目标和 API/Web 通道绑定</span></div><div><code>credentialRef</code><span>已配置 · 凭据不展示在公共 YAML 中</span></div><div><code>验证码</code><span>认证 Adapter 使用专用 Redis 连接</span></div><div><code>登录会话</code><span>失效后按 Profile 刷新；业务动作不自动重放</span></div></div></div>
    <div id="connections">${section('受控连接 Managed Connection',c.connections,'SQL 与认证 Redis 属不同用途；浏览器不直接连接')}</div>
    <section class="config-section" id="public-yaml"><div class="section-head"><div><h2>公共 YAML 资产</h2><p>由 Git 发布并复用，和上方的 Web 项目配置分别管理。</p></div><button class="btn" data-nav="assets">查看资产 →</button></div><div class="config-list">${c.public.map(a=>`<div><code>${a}</code><span>已发布 · ${p.revision}</span></div>`).join('')}</div></section></div>`, 'projects');
}

function auditView() {
  const p = currentProject();
  return shell(`<div class="content"><div class="eyebrow">${p.code} AUDIT TRAIL</div><h1>${p.code} 审计事件</h1><p class="lead">默认限定当前项目；平台级管理员可在后续全局入口跨项目检索。</p><div class="section-head"><div><h2>最近事件</h2><p>Asia/Shanghai · Project = ${p.code}</p></div><button class="btn" data-toast="筛选器保持当前项目边界">筛选</button></div><div class="panel"><table class="table"><thead><tr><th>时间</th><th>操作者</th><th>动作</th><th>项目</th><th>对象</th><th>结果</th></tr></thead><tbody><tr><td>09-23 10:44:21</td><td>刘高杰</td><td><b>view_raw_run_data</b></td><td>${p.code}</td><td>${p.runs[0].id}</td><td>${status('pass','成功')}</td></tr><tr><td>09-23 10:42:02</td><td>刘高杰</td><td><b>create_run</b></td><td>${p.code}</td><td>${p.assets[0].id}</td><td>${status('pass','成功')}</td></tr><tr><td>09-23 09:13:44</td><td>陈晓</td><td><b>publish_revision</b></td><td>${p.code}</td><td>${p.revision}</td><td>${status('pass','成功')}</td></tr></tbody></table></div></div>`, 'audit');
}

function reportView() {
  const p = currentProject();
  const run=findRun();
  const a=currentCatalog().find(item=>item.id===run.assetId || item.name===run.asset) || currentCatalog()[0];
  const entries=a.variants||a.steps||[];
  const entry=entries[Math.min(state.reportStep,entries.length-1)]||{};
  const rawRequest=(entry.method?`${entry.method} ${entry.path}\n`:'' )+(entry.request||entry.value||'');
  const response=run.result==='fail' && state.reportStep===entries.length-1 ? '{"code":"ASSERTION_FAILED","message":"模拟断言未通过"}' : a.kind==='ApiCheckSet' && state.reportStep>0 ? '{"code":"BUSINESS_ERROR","message":"模拟业务失败"}' : a.id.includes('sql') ? '[{"id":1024}]' : '{"code":0,"data":{"orderNo":"DEMO-ORDER-001","status":"WAIT_PAY"}}';
  const header=state.rawVisible && !a.id.includes('sql') ? `\nAuthorization: Bearer demo_${state.projectId}_token_123\nCookie: session=demo_${state.projectId}_session_456` : !a.id.includes('sql') ? '\nAuthorization: Bearer ••••••\nCookie: ••••••' : '';
  return shell(`<div class="content"><button class="btn ghost" data-nav="runs">← 返回运行记录</button><div class="section-head"><div><div class="eyebrow">${p.code} / RUN REPORT / ${run.id}</div><h1>${run.asset}</h1><p class="lead">${status(run.result)}　${p.code} / ${run.environment||'test'} · ${run.trigger} · ${run.time}</p></div></div>
    <div class="detail-meta"><span>运行 ID <code>${run.id}</code></span><span>资产 <code>${a.id}</code></span><span>修订 <code>${p.revision}</code></span><span>身份 <code>${a.actor||'不适用'}</code></span></div>
    <div class="run-layout report-layout"><section><h2>本次执行内容</h2><p class="lead">${a.kind==='ApiCheckSet'?'各变体独立记录结果':'按执行顺序查看请求、响应和断言'}</p><div class="report-steps">${entries.map((e,i)=>`<button class="${state.reportStep===i?'active':''}" data-report-step="${i}"><span class="detail-index">${i+1}</span><span><b>${e.name}</b><small>${e.target||a.target} · ${e.expect}</small></span>${status(run.result==='fail'&&i===entries.length-1?'fail':'pass')}</button>`).join('')}</div></section>
    <section class="report-detail"><div class="section-head"><div><h2>${entry.name||'执行记录'}</h2><p>${entry.target||a.target} · 模拟请求和响应</p></div><button class="btn" data-raw-toggle>${state.rawVisible?'隐藏真实值':'查看真实值'}</button></div>
      <div class="evidence"><label>请求 / 执行值</label><pre>${escapeHtml(rawRequest+header)}</pre></div><div class="evidence"><label>响应 / 查询结果</label><pre>${escapeHtml(response)}</pre></div><div class="evidence"><label>断言与结果</label><p>${escapeHtml(entry.expect||'—')} · ${run.result==='fail'&&state.reportStep===entries.length-1?'失败':'通过'}</p></div><p class="report-foot">${state.rawVisible?'已模拟记录 raw 查看审计事件。':'敏感值默认遮罩；授权查看会记录审计。'}不提供下载。</p></section></div></div>`, 'runs');
}

function setProject(projectId) {
  if (!projectData[projectId]) return;
  state.projectId = projectId;
  state.selectedAsset = currentCatalog()[0].id;
  state.selectedRun = currentProject().runs[0].id;
  state.environment='test'; state.module='全部模块'; state.assetType='全部类型'; state.query='';
  state.rawVisible = false; state.reportStep=0;
  const url = new URL(location.href);
  url.searchParams.delete('variant');
  url.searchParams.set('project', projectId);
  history.replaceState({},'',url);
  render();
}

function showToast(message) {
  const toast=document.getElementById('toast');
  toast.textContent=message;
  toast.classList.remove('show');
  void toast.offsetWidth;
  toast.classList.add('show');
}

function openModal(asset) {
  const p=currentProject();
  const chosen=currentCatalog().find(a=>a.id===asset||a.name===asset) || currentCatalog()[0];
  state.selectedAsset=chosen.id;
  state.environment='test';
  updatePreview();
  document.getElementById('runModal').classList.add('show');
}

function updatePreview() {
  const p=currentProject(), a=findAsset(state.selectedAsset), entries=a.variants||a.steps||[];
  const canRun=!(state.environment==='dev' && (state.projectId!=='go2' || a.id.includes('sql')));
  document.getElementById('modalPreview').innerHTML=`<div class="modal-section"><div class="modal-row"><span>项目 / 修订</span><b>${p.code} · ${p.revision}</b></div><div class="modal-row"><span>测试资产</span><b>${a.name}</b></div><div class="modal-row"><span>身份 / 目标</span><code>${a.actor} · ${a.target}</code></div></div>
  <label class="modal-label" for="runEnvironment">本次运行环境</label><select id="runEnvironment" data-run-environment><option value="test" ${state.environment==='test'?'selected':''}>test · 已配置</option>${state.projectId==='go2'?`<option value="dev" ${state.environment==='dev'?'selected':''}>dev · 仅 API / Web</option>`:''}</select>
  ${!canRun?'<p class="preview-error">当前环境缺少 SQL 连接绑定，本资产不能入队。</p>':''}
  <div class="preview-entries"><b>${a.kind==='ApiCheckSet'?'本次接口变体':'本次流程步骤'} · ${entries.length}</b>${entries.map((e,i)=>`<div><span>${i+1}. ${e.name}</span><small>${escapeHtml((e.method?`${e.method} ${e.path}\n`:'')+(e.request||e.value))}</small><small>预期：${escapeHtml(e.expect)}</small></div>`).join('')}</div>`;
  document.querySelector('[data-confirm-run]').disabled=!canRun;
  document.getElementById('runEnvironment').addEventListener('change',event=>{state.environment=event.target.value; updatePreview();});
}

function bind() {
  document.querySelectorAll('[data-nav]').forEach(el=>el.addEventListener('click',()=>{state.view=el.dataset.nav; render();}));
  document.querySelectorAll('[data-project-switch]').forEach(el=>el.addEventListener('change',()=>setProject(el.value)));
  document.querySelectorAll('[data-switch-project]').forEach(el=>el.addEventListener('click',()=>{setProject(el.dataset.switchProject); state.view='overview'; render();}));
  document.querySelectorAll('[data-run]').forEach(el=>el.addEventListener('click',()=>openModal(el.dataset.run)));
  document.querySelectorAll('[data-open-report]').forEach(el=>el.addEventListener('click',()=>{state.selectedRun=el.dataset.openReport;state.reportStep=0;state.rawVisible=false;state.view='report'; render();}));
  document.querySelectorAll('[data-asset]').forEach(el=>el.addEventListener('click',()=>{state.selectedAsset=el.dataset.asset;state.view='asset';render();}));
  document.querySelectorAll('[data-module]').forEach(el=>el.addEventListener('click',()=>{state.module=el.dataset.module;render();}));
  document.querySelector('[data-asset-type]')?.addEventListener('change',event=>{state.assetType=event.target.value;render();});
  document.querySelector('[data-asset-search]')?.addEventListener('input',event=>{state.query=event.target.value;state.view='assets'; const selection=event.target.selectionStart;render();const input=document.querySelector('[data-asset-search]');input.focus();input.setSelectionRange(selection,selection);});
  document.querySelectorAll('[data-report-step]').forEach(el=>el.addEventListener('click',()=>{state.reportStep=Number(el.dataset.reportStep);render();}));
  document.querySelectorAll('[data-toast]').forEach(el=>el.addEventListener('click',()=>showToast(el.dataset.toast)));
  document.querySelectorAll('[data-raw-toggle]').forEach(el=>el.addEventListener('click',()=>{state.rawVisible=!state.rawVisible; render();}));
  document.querySelectorAll('[data-close-modal]').forEach(el=>el.addEventListener('click',()=>document.getElementById('runModal').classList.remove('show')));
  document.querySelectorAll('[data-confirm-run]').forEach(el=>el.addEventListener('click',()=>{
    const p=currentProject(), a=findAsset(state.selectedAsset);
    const run={id:`run_${state.projectId}_${Date.now()}`,asset:a.name,assetId:a.id,environment:state.environment,trigger:'手动运行',time:new Date().toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}),duration:'00:02',result:'pass'};
    p.runs.unshift(run);
    state.selectedRun=run.id;
    document.getElementById('runModal').classList.remove('show');
    state.reportStep=0;state.rawVisible=false;state.view='report';
    render();
    showToast(`${p.code} / ${run.environment} 模拟运行已完成 · ${a.name}`);
  }));
}

function render() {
  let html;
  if (state.view==='assets') html=assetsView();
  else if (state.view==='runs') html=runsView();
  else if (state.view==='asset') html=assetView();
  else if (state.view==='projects') html=projectsView();
  else if (state.view==='audit') html=auditView();
  else if (state.view==='report') html=reportView();
  else html=overviewA();
  document.getElementById('app').innerHTML=html;
  bind();
  document.title=`TestPlat · ${currentProject().code} · prototype`;
}

if (params.has('variant')) {
  const url = new URL(location.href);
  url.searchParams.delete('variant');
  history.replaceState({},'',url);
}
state.selectedAsset=currentCatalog()[0].id;
state.selectedRun=currentProject().runs[0].id;
render();
window.addEventListener('popstate',()=>{const url=new URL(location.href); if(projectData[url.searchParams.get('project')]) state.projectId=url.searchParams.get('project'); render();});
document.addEventListener('keydown',event=>{
  if (event.key==='Escape') document.getElementById('runModal').classList.remove('show');
});
