export const HTML_PREVIEW_SCROLL_MESSAGE_SOURCE = "deerflow-artifact-preview-scroll"

export function appendHtmlPreviewSandboxCompatibility(content: string) {
  if (content.includes("data-deerflow-artifact-sandbox-compatibility")) {
    return content
  }

  const script = `<script data-deerflow-artifact-sandbox-compatibility>
(() => {
  const createStorage = () => {
    const values = new Map();
    return {
      get length() { return values.size; },
      clear() { values.clear(); },
      getItem(key) { key = String(key); return values.has(key) ? values.get(key) : null; },
      key(index) { return Array.from(values.keys())[index] ?? null; },
      removeItem(key) { values.delete(String(key)); },
      setItem(key, value) { values.set(String(key), String(value)); },
    };
  };
  const install = (name) => {
    try {
      void window[name];
    } catch {
      Object.defineProperty(window, name, { configurable: true, value: createStorage() });
    }
  };
  install("localStorage");
  install("sessionStorage");
})();
</script>`

  if (/<head(?:\s[^>]*)?>/i.test(content)) {
    return content.replace(/<head(?:\s[^>]*)?>/i, (headTag) => `${headTag}${script}`)
  }
  return `${script}${content}`
}

export function appendHtmlPreviewBaseHref(
  content: string,
  url?: string,
  currentHref = globalThis.location?.href ?? "http://localhost/",
) {
  if (!url || /<base\s/i.test(content)) {
    return content
  }

  const baseUrl = new URL(url, currentHref)
  baseUrl.pathname = baseUrl.pathname.replace(/\/[^/]*$/, "/")
  baseUrl.search = ""
  baseUrl.hash = ""
  const baseElement = `<base href="${escapeHtmlAttribute(baseUrl.toString())}">`

  if (/<head[^>]*>/i.test(content)) {
    return content.replace(/<head([^>]*)>/i, `<head$1>${baseElement}`)
  }
  return `${baseElement}${content}`
}

export function createHtmlPreviewScrollKey(value: string) {
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return `artifact-scroll:${(hash >>> 0).toString(36)}`
}

export function appendHtmlPreviewScrollRestoration(content: string, scrollKey = "default") {
  if (content.includes("data-deerflow-artifact-scroll-restoration")) {
    return content
  }

  const script = htmlScrollRestorationScript(createHtmlPreviewScrollKey(scrollKey))
  if (/<head(?:\s[^>]*)?>/i.test(content)) {
    return content.replace(/<head(?:\s[^>]*)?>/i, (headTag) => `${headTag}${script}`)
  }
  if (/<\/body\s*>/i.test(content)) {
    return content.replace(/<\/body\s*>/i, `${script}</body>`)
  }
  return `${content}${script}`
}

function htmlScrollRestorationScript(messageKey: string) {
  return `<script data-deerflow-artifact-scroll-restoration>
(() => {
  const source = ${escapeJavaScriptString(HTML_PREVIEW_SCROLL_MESSAGE_SOURCE)};
  const key = ${escapeJavaScriptString(messageKey)};
  const post = (type, payload = {}) => {
    window.parent.postMessage({ source, key, type, ...payload }, "*");
  };
  const save = () => {
    post("save", {
      x: Math.round(window.scrollX || 0),
      y: Math.round(window.scrollY || 0),
    });
  };
  window.addEventListener("message", (event) => {
    const data = event.data;
    if (!data || data.source !== source || data.key !== key || data.type !== "restore") {
      return;
    }
    if (Number.isFinite(data.x) && Number.isFinite(data.y)) {
      window.scrollTo(data.x, data.y);
    }
  });
  window.addEventListener("scroll", save, { passive: true });
  window.addEventListener("pagehide", save);
  const requestRestore = () => post("restore-request");
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", requestRestore, { once: true });
  } else {
    requestRestore();
  }
  window.addEventListener("load", requestRestore, { once: true });
})();
</script>`
}

function escapeHtmlAttribute(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll('"', "&quot;")
}

function escapeJavaScriptString(value: string) {
  return JSON.stringify(value)
    .replace(/</g, "\\u003C")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029")
}
