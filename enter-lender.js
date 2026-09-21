document.querySelectorAll(".password-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = document.getElementById(btn.dataset.target);
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    btn.setAttribute("aria-pressed", String(!showing));
    btn.querySelector('[aria-hidden="true"]').textContent = showing ? "Show" : "Hide";
    btn.querySelector(".visually-hidden").textContent = showing ? "Show password" : "Hide password";
  });
});