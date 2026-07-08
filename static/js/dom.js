// Tiny DOM helpers — no framework (ADR-010). Everything styles via .sq-* classes;
// the only inline style allowed is a dynamic value on a CSS custom property.

export function el(tag, opts = {}, children = []) {
  const node = document.createElement(tag);
  if (opts.class) node.className = opts.class;
  if (opts.text != null) node.textContent = opts.text;
  if (opts.html != null) node.innerHTML = opts.html;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  if (opts.on) for (const [k, v] of Object.entries(opts.on)) node.addEventListener(k, v);
  if (opts.cssVars) for (const [k, v] of Object.entries(opts.cssVars)) node.style.setProperty(k, v);
  for (const c of [].concat(children)) if (c) node.appendChild(c);
  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

export function mount(root, node) {
  clear(root).appendChild(node);
  return node;
}
