export function mountNav(active) {
  const items = [
    { href: "index.html", id: "overview", label: "Overview" },
    { href: "playground.html", id: "playground", label: "Playground" },
    { href: "step-through.html", id: "step", label: "Step-through" },
    { href: "scorecard.html", id: "scorecard", label: "Scorecard" },
  ];
  return `
    <aside class="sidebar">
      <p class="brand">MPC Heater Lab</p>
      <nav class="nav">
        ${items
          .map(
            (it) =>
              `<a href="${it.href}" class="${it.id === active ? "active" : ""}">${it.label}</a>`
          )
          .join("")}
      </nav>
      <p class="note" style="margin-top:32px">Static Vercel build of the Streamlit lab. Full interactive solvers stay on Streamlit Cloud.</p>
    </aside>
  `;
}
