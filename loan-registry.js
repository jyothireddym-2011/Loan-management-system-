const tabs = Array.from(document.querySelectorAll('#serviceTabs [role="tab"]'));

function activateTab(tab) {
  tabs.forEach((t) => {
    const selected = t === tab;
    t.setAttribute("aria-selected", String(selected));
    t.tabIndex = selected ? 0 : -1;
    t.classList.toggle("active", selected);
    const panel = document.getElementById(t.getAttribute("aria-controls"));
    panel.hidden = !selected;
  });
  tab.focus();
}

tabs.forEach((tab, i) => {
  tab.addEventListener("click", () => activateTab(tab));

  // Arrow-key navigation between tabs, per the standard ARIA tabs pattern
  tab.addEventListener("keydown", (e) => {
    let newIndex = null;
    if (e.key === "ArrowRight") newIndex = (i + 1) % tabs.length;
    if (e.key === "ArrowLeft") newIndex = (i - 1 + tabs.length) % tabs.length;
    if (e.key === "Home") newIndex = 0;
    if (e.key === "End") newIndex = tabs.length - 1;
    if (newIndex !== null) {
      e.preventDefault();
      activateTab(tabs[newIndex]);
    }
  });
});