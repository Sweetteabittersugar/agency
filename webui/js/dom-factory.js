/* ══════════════════════════════════════════════
   dom-factory.js — 统一 DOM 创建工厂

   替代 innerHTML 字符串拼接，提供声明式 DOM 创建 API。
   所有 JS 文件通过此工厂创建 DOM，保证一致性和 XSS 安全。

   API:
     Dom.create('div', {class:'foo', onclick:fn}, [child])
     Dom.div('.foo .bar', [child])         // 简写
     Dom.button('Click', {class:'primary', onclick:fn})
     Dom.icon('🚀')
     Dom.toast('msg', {level:'error', duration:3000})

   设计原则：
     - class 支持字符串('.foo')和对象({class:'foo'})
     - children 支持文本(自动textContent)、DOM节点、数组
     - 事件用 onclick/onchange 等属性绑定（动态添加用 addEventListener）
     - 不引入虚拟 DOM，只是标准化 createElement 调用
   ══════════════════════════════════════════════ */

const Dom = {
  /**
   * 创建任意 HTML 元素
   * @param {string} tag - 标签名
   * @param {object|string} [attrs] - 属性对象或 className 字符串
   * @param {Array|string|Node} [children] - 子元素
   * @returns {HTMLElement}
   */
  create(tag, attrs, children) {
    const el = document.createElement(tag);

    // 处理 attrs：字符串 → {class: str}
    if (typeof attrs === 'string') {
      el.className = attrs;
    } else if (attrs) {
      for (const [key, val] of Object.entries(attrs)) {
        if (key === 'class' || key === 'className') {
          el.className = val;
        } else if (key === 'style' && typeof val === 'object') {
          Object.assign(el.style, val);
        } else if (key.startsWith('on')) {
          // onclick → addEventListener('click', ...)
          const event = key.slice(2).toLowerCase();
          el.addEventListener(event, val);
        } else if (key === 'dataset' && typeof val === 'object') {
          Object.assign(el.dataset, val);
        } else if (key === 'html') {
          // 显式 innerHTML（仅用于信任源，如 Markdown 渲染）
          el.innerHTML = val;
        } else if (typeof val === 'boolean') {
          if (val) el.setAttribute(key, '');
          else el.removeAttribute(key);
        } else {
          el.setAttribute(key, val);
        }
      }
    }

    // 处理 children
    if (children !== undefined) {
      if (Array.isArray(children)) {
        for (const child of children) {
          appendChild(el, child);
        }
      } else {
        appendChild(el, children);
      }
    }

    return el;
  },

  /** 简写：Dom.div('class', [children]) 或 Dom.div({onclick:fn}, [children]) */
  div(attrs, children) {
    return Dom.create('div', attrs, children);
  },

  span(attrs, children) {
    return Dom.create('span', attrs, children);
  },

  /** Dom.button('Click', {class:'btn primary', onclick:fn}) */
  button(text, attrs) {
    return Dom.create('button', Object.assign({}, attrs), [text || '']);
  },

  /** Dom.icon('🤖') → <span class="nav-icon" aria-hidden="true">🤖</span> */
  icon(emoji, extraClass) {
    return Dom.create('span', {
      class: `nav-icon${extraClass ? ' ' + extraClass : ''}`,
      'aria-hidden': 'true',
    }, [emoji]);
  },

  /**
   * Dom.toast('操作成功')
   * Dom.toast('删除失败', {level:'error', duration:5000})
   * @returns {HTMLElement} toast 元素
   */
  toast(message, opts) {
    opts = opts || {};
    const level = opts.level || '';
    const duration = opts.duration || 3000;
    const el = Dom.create('div', { class: `toast${level ? ' ' + level : ''}` }, [message]);
    document.body.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(8px)';
      setTimeout(() => el.remove(), 300);
    }, duration);
    return el;
  },

  /**
   * Dom.confirmBox('确定要删除吗？', {
   *   message: '此操作不可撤销',
   *   confirmText: '删除',
   *   danger: true,
   *   onConfirm: () => {...},
   *   onCancel: () => {...},
   * })
   * @returns {HTMLElement} 弹窗元素
   */
  confirmBox(opts) {
    opts = opts || {};
    const title = opts.title || '确认';
    const message = opts.message || '';
    const confirmText = opts.confirmText || '确定';
    const danger = opts.danger || false;

    const overlay = Dom.div('confirm-overlay', [
      Dom.div('confirm-box', [
        Dom.div('confirm-title', [title]),
        message ? Dom.div('confirm-message', [message]) : null,
        Dom.div('confirm-btns', [
          Dom.button('取消', {
            class: 'btn',
            onclick() {
              overlay.remove();
              if (opts.onCancel) opts.onCancel();
            },
          }),
          Dom.button(confirmText, {
            class: `btn${danger ? ' danger' : ' primary'}`,
            onclick() {
              overlay.remove();
              if (opts.onConfirm) opts.onConfirm();
            },
          }),
        ]),
      ]),
    ]);

    document.body.appendChild(overlay);
    return overlay;
  },

  /** 清空元素所有子节点 */
  empty(el) {
    if (el) {
      while (el.firstChild) el.removeChild(el.firstChild);
    }
    return el;
  },

  /** 简写 document.getElementById */
  $(id) {
    return document.getElementById(id);
  },
};

/** 内部：向元素追加子节点 */
function appendChild(parent, child) {
  if (child === null || child === undefined || child === false) return;
  if (typeof child === 'string' || typeof child === 'number') {
    parent.appendChild(document.createTextNode(String(child)));
  } else if (child instanceof Node) {
    parent.appendChild(child);
  }
}

window.Dom = Dom;
