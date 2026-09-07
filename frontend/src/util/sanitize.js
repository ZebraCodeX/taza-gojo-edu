// util/sanitize.js — tiny HTML sanitizer for cached material bodies.
// Strips scripts/styles/event handlers and unknown tags; keeps headings,
// paragraphs, lists, links, code. Good enough for agent-written study packs.

export function sanitizeHtml(html) {
  if (typeof DOMParser === "undefined") return "";
  const doc = new DOMParser().parseFromString(html || "", "text/html");

  const allowed = new Set([
    "H1", "H2", "H3", "P", "UL", "OL", "LI", "STRONG", "B", "EM", "I",
    "PRE", "CODE", "BLOCKQUOTE", "BR", "A", "TABLE", "TR", "TD", "TH",
  ]);

  const walk = (node) => {
    if (node.nodeType === 3) return; // text
    if (node.nodeType !== 1) {
      node.remove();
      return;
    }
    const tag = node.tagName.toUpperCase();
    if (!allowed.has(tag)) {
      while (node.firstChild) node.parentNode.insertBefore(node.firstChild, node);
      node.remove();
      return;
    }
    for (const attr of [...node.attributes]) {
      if (attr.name.startsWith("on") || attr.name === "style" || attr.name === "class") {
        node.removeAttribute(attr.name);
      }
    }
    for (const child of [...node.childNodes]) walk(child);
  };
  for (const child of [...doc.body.childNodes]) walk(child);
  return doc.body.innerHTML;
}