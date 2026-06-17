/* Agency — 渐进式功能暴露 (Round 3: 从 utils.js 剥离) */
(function() {
  'use strict';

  let FEATURE_SCHEDULE = {
    day0:   { minDay:0, features:['chat','settings'],                         desc:{zh:'基础聊天 + Key 配置',en:'Basic chat + Key config'} },
    day1_2: { minDay:0, features:['dashboard','agents'],                      desc:{zh:'仪表盘 + Agent 列表',en:'Dashboard + Agent list'} },
    day3_5: { minDay:0, features:['routing','multipanel'],                    desc:{zh:'智能调度 + 多面板',en:'Smart routing + Multi-panel'} },
    day7:   { minDay:0, features:['agent-factory','skills','profiles'],       desc:{zh:'Agent 工厂 + Skill 编辑 + Profile',en:'Agent factory + Skill edit + Profile'} }
  };

  let FEATURE_UNLOCK_DAYS = {};
  (function() {
    let ks = Object.keys(FEATURE_SCHEDULE);
    for (let i = 0; i < ks.length; i++) {
      let s = FEATURE_SCHEDULE[ks[i]];
      for (let j = 0; j < s.features.length; j++) {
        FEATURE_UNLOCK_DAYS[s.features[j]] = s.minDay;
      }
    }
  })();

  function getUserDay() {
    let first = localStorage.getItem('agency_first_visit');
    if (!first) {
      let now = new Date().toISOString().slice(0, 10);
      localStorage.setItem('agency_first_visit', now);
      first = now;
    }
    let diff = Math.floor((Date.now() - new Date(first).getTime()) / 86400000);
    return Math.max(0, diff);
  }

  function isFeatureUnlocked(name) {
    if (localStorage.getItem('agency_unlock_all') === 'true') return true;
    let minDay = FEATURE_UNLOCK_DAYS[name];
    if (minDay === undefined) return true;
    return getUserDay() >= minDay;
  }

  function checkNewUnlocks() {
    let day = getUserDay();
    let seen = {};
    try { seen = JSON.parse(localStorage.getItem('agency_unlock_seen') || '{}'); } catch(e) { console.warn('解析解锁记录失败:',e); }
    let newUnlocks = [];
    let ks = Object.keys(FEATURE_SCHEDULE);
    for (let i = 0; i < ks.length; i++) {
      let s = FEATURE_SCHEDULE[ks[i]];
      if (day >= s.minDay && !seen[ks[i]]) {
        for (let j = 0; j < s.features.length; j++) { newUnlocks.push(s.features[j]); }
        seen[ks[i]] = true;
      }
    }
    if (newUnlocks.length > 0) {
      localStorage.setItem('agency_unlock_seen', JSON.stringify(seen));
      let labelMap = {chat:'基础聊天',settings:'设置面板',dashboard:'仪表盘',agents:'Agent列表',routing:'智能调度',multipanel:'多面板','agent-factory':'Agent工厂',skills:'Skill编辑',profiles:'Profile切换'};
      let names = newUnlocks.map(function(f) { return labelMap[f] || f; });
      showToast(t('newFeatureUnlocked').replace('{name}', names.join('、')));
    }
    autoSelectProfile(day);
  }

  function autoSelectProfile(day) {
    if (localStorage.getItem('profile_manual') === 'true') return;
    let cur = localStorage.getItem('agency_profile') || 'standard';
    if (day >= 7 && cur !== 'full') {
      showToast(t('profileRecommendFull').replace('{n}', day), false, 'warn', 5000);
    } else if (day >= 3 && cur === 'minimal') {
      localStorage.setItem('agency_profile', 'standard');
      if (typeof agencyProfile !== 'undefined') agencyProfile = 'standard';
      if (typeof updateProfileUI === 'function') updateProfileUI();
      showToast(t('profileAutoUpgraded').replace('{n}', day), false, 'warn', 6000);
    }
  }

  window.FEATURE_SCHEDULE = FEATURE_SCHEDULE;
  window.FEATURE_UNLOCK_DAYS = FEATURE_UNLOCK_DAYS;
  window.getUserDay = getUserDay;
  window.isFeatureUnlocked = isFeatureUnlocked;
  window.checkNewUnlocks = checkNewUnlocks;
  window.autoSelectProfile = autoSelectProfile;
})();
