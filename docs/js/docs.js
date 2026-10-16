// If the url has a hash, and a details element with that id exists, open it on page load.
document.addEventListener("DOMContentLoaded", () => {
  if (!window.location.hash) return;

  const elem = document.querySelector(window.location.hash)
  if (!elem) return;

  if (elem.tagName === "DETAILS") {
    elem.open = true
  }
});

// When a details element is opened, make its id the URL hash, if it has one.
// When the element is closed, remove the hash from the URL.
// Instant navigation replaces the page content, so the listener is on the document instead
// of on each element. A `toggle` event does not bubble, so it is caught on the way down.
document.addEventListener("toggle", event => {
  const details = event.target;
  if (!(details instanceof HTMLDetailsElement) || !details.id) return;

  if (details.open) {
    history.replaceState(null, "", `#${details.id}`);
  }
  else if (`#${details.id}` === window.location.hash) {
    history.replaceState(null, "", window.location.pathname);
  }
}, true);


// When an anchor containing a hash is clicked, and the hash corresponds to an
// id of a details element, open the details element.
document.addEventListener("click", event => {
  const anchor = event.target.closest('a[href^="#"]');
  if (!anchor) return;

  const href = anchor.getAttribute("href");
  if (!href) return;

  const elem = document.querySelector(href);
  if (!elem) return;

  if (elem.tagName === "DETAILS") {
    elem.open = true;
  }
});


// Register the service worker for caching docs offline.
// The dev server serves the service worker template with its placeholders unreplaced,
// so the worker cannot install and a worker from an earlier build keeps serving stale files.
// Local builds therefore get no worker, and any worker left over from before is removed.
const isLocalHost = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);

// This script is in "js/" at the site root, so the worker URL is resolved from the script's own URL.
// This works whether the site is served from a domain root or from a sub-path.
// "currentScript" is only set while the script first runs, so the URL is resolved here.
const serviceWorkerUrl = new URL('../service-worker.js', document.currentScript.src);

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    if (isLocalHost) {
      navigator.serviceWorker.getRegistrations()
        .then(regs => Promise.all(regs.map(reg => reg.unregister())))
        .then(results => {
          if (results.some(Boolean)) {
            console.log('Service Worker unregistered. Reload to serve files from the network.');
          }
        })
        .catch(err => console.error('Service Worker unregistration failed:', err));
      return;
    }

    navigator.serviceWorker.register(serviceWorkerUrl)
      .then(reg => console.log('Service Worker registered:', reg.scope))
      .catch(err => console.error('Service Worker registration failed:', err));
  });
}
