/* Card covers hotlink each entry's own preview image (og:image / GitHub social card).
 * When one fails to load — dead link, hotlink-blocked host, offline — hide the <img> so
 * the pure-CSS pastel initials tile rendered beneath it shows instead. Error events don't
 * bubble, so listen in the capture phase; this also covers images swapped in by Material's
 * instant navigation. */
document.addEventListener(
  "error",
  (e) => {
    const t = e.target;
    if (t instanceof HTMLImageElement && t.classList.contains("card-thumb")) {
      t.classList.add("thumb-broken");
    }
  },
  true
);
