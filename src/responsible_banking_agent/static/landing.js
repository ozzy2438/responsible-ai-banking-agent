document.querySelectorAll("button.persona").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const errorEl = document.getElementById("persona-error");
    errorEl.style.display = "none";
    document.querySelectorAll("button.persona").forEach((b) => (b.disabled = true));
    try {
      const res = await fetch("/dev/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alias: btn.dataset.alias }),
      });
      if (!res.ok) {
        throw new Error("Sign-in is only available in the local/test demo environment.");
      }
      window.location.href = btn.dataset.target;
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.style.display = "block";
      document.querySelectorAll("button.persona").forEach((b) => (b.disabled = false));
    }
  });
});
