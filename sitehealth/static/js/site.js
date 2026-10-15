const revealables = document.querySelectorAll("[data-reveal]");
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function reveal(element) {
  element.classList.add("is-revealed");
}

if (prefersReducedMotion || !("IntersectionObserver" in window)) {
  revealables.forEach(reveal);
} else {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          reveal(entry.target);
          observer.unobserve(entry.target);
        }
      }
    },
    { rootMargin: "0px 0px -8% 0px" },
  );
  revealables.forEach((element) => observer.observe(element));
}
