# Store 使用指南

## 读取状态
```js
var theme = Store.get('theme');
var all = Store.get();  // 全部状态副本
```

## 更新状态
```js
Store.set('theme', 'light');
Store.set({theme: 'light', layout: 2});  // 批量更新
```

## 监听变化
```js
Store.on('theme', function(newVal) { applyTheme(newVal); });
Store.on('*', function(state, changedKey) { /* 全部变化 */ });
```

## 现有代码兼容
现有的 window.panels、window.agents 等全局变量继续正常工作。
新代码推荐使用 Store.get/set 替代直接读写全局变量。

## 持久化
theme、lang、layout、agencyProfile、apiProvider、outputDir
自动持久化到 localStorage，页面刷新后恢复。

持久化 key 格式：`agency-<key>`（如 `agency-theme`），不与其他 key 冲突。
